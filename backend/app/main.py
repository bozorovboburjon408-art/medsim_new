import asyncio
import base64
import json
import logging
import re
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel

from . import evaluator, llm, tts
from .config import settings
from .patients import PATIENTS

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="MedSim backend")


class Turn(BaseModel):
    role: str  # "user" (hamshira) yoki "assistant" (bemor)
    content: str


class ChatRequest(BaseModel):
    patient_id: str
    history: list[Turn]  # oxirgisi hamshiraning yangi gapi bo'lishi kerak
    model: str | None = None  # ixtiyoriy: shu model birinchi sinaladi
    tts: str | None = None  # ixtiyoriy: 'edge' | 'gemini' | 'azure'


class ChatResponse(BaseModel):
    text: str
    audio_b64: str  # mp3
    llm_ms: int = 0
    tts_ms: int = 0


@app.get("/patients")
def patients():
    return [{"id": p.id, "title": p.title} for p in PATIENTS.values()]


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    p = PATIENTS.get(req.patient_id)
    if not p:
        raise HTTPException(404, "Bemor topilmadi")
    if not req.history or req.history[-1].role != "user":
        raise HTTPException(400, "Oxirgi xabar hamshiradan bo'lishi kerak")
    t0 = time.perf_counter()
    try:
        text = await llm.generate(p.system_prompt(), [t.model_dump() for t in req.history])
    except Exception as e:
        raise HTTPException(502, f"AI xatosi: {e}"[:400])
    t1 = time.perf_counter()
    try:
        audio, _fmt, _used = await tts.synthesize(text, p)
    except Exception as e:
        raise HTTPException(502, f"Ovoz (TTS) xatosi: {e} | javob: {text}"[:400])
    t2 = time.perf_counter()
    if not audio:
        raise HTTPException(502, f"Ovoz bo'sh chiqdi (TTS) | javob: {text}"[:400])
    return ChatResponse(text=text, audio_b64=base64.b64encode(audio).decode(),
                        llm_ms=int((t1 - t0) * 1000), tts_ms=int((t2 - t1) * 1000))


@app.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    """NDJSON oqimi: har qator = bitta gap {"text","audio_b64","ms"} yoki {"error"}."""
    p = PATIENTS.get(req.patient_id)
    if not p:
        raise HTTPException(404, "Bemor topilmadi")
    if not req.history or req.history[-1].role != "user":
        raise HTTPException(400, "Oxirgi xabar hamshiradan bo'lishi kerak")
    history = [t.model_dump() for t in req.history]

    async def gen():
        t0 = time.perf_counter()
        info: dict = {}

        if (req.tts or settings.tts_provider) == "gemini":
            # Gemini ovozi: javob to'liq yoziladi, so'ng butun matn bitta oqimli so'rovda ovozlashtiriladi
            # (bir ohang, birinchi bo'lak ~0.5 s da keladi); bo'laklar darrov ilovaga uzatiladi.
            try:
                async def collect():
                    return [s async for s in llm.stream_sentences(p.system_prompt(), history, info, req.model)]
                sents = await asyncio.wait_for(collect(), timeout=22)
            except asyncio.TimeoutError:
                yield json.dumps({"error": "AI vaqtida javob bermadi, qayta urinib ko'ring"}) + "\n"
                return
            except Exception as e:
                yield json.dumps({"error": f"AI xatosi: {e}"[:400]}) + "\n"
                return
            if not sents:
                yield json.dumps({"error": "AI bo'sh javob qaytardi"}) + "\n"
                return
            full = " ".join(sents)
            t_llm = int((time.perf_counter() - t0) * 1000)
            t_tts0 = time.perf_counter()
            first = True
            try:
                async for pcm in tts.gemini_stream(full, p):
                    tts_ms = int((time.perf_counter() - t_tts0) * 1000) if first else 0
                    if first:
                        log.info("gemini-stream patient=%s llm=%dms first_chunk=%dms model=%s",
                                 p.id, t_llm, tts_ms, info.get("model", ""))
                    yield json.dumps({
                        "pcm_b64": base64.b64encode(pcm).decode(), "rate": 24000,
                        "text": full if first else "", "ms": int((time.perf_counter() - t0) * 1000),
                        "llm_ms": t_llm, "tts_ms": tts_ms, "tts": "gemini-stream",
                        "model": info.get("model", ""), "usage": info.get("usage", ""), "tries": ", ".join(info.get("tries", [])),
                    }) + "\n"
                    first = False
                return
            except Exception as e:
                if not first:  # ovoz yarmigacha chalingan: Edge'ga o'tib bo'lmaydi
                    yield json.dumps({"error": f"Ovoz oqimi uzildi: {e}"[:400]}) + "\n"
                    return
                log.warning("Gemini TTS oqimi xato, Edge'ga o'tildi: %s", e)
            try:  # zaxira: Edge
                audio = await tts._edge(full, p)
                yield json.dumps({
                    "text": full, "audio_b64": base64.b64encode(audio).decode(), "fmt": "mp3",
                    "ms": int((time.perf_counter() - t0) * 1000), "llm_ms": t_llm,
                    "tts_ms": int((time.perf_counter() - t_tts0) * 1000), "tts": "edge (gemini xato)",
                    "model": info.get("model", ""), "usage": info.get("usage", ""), "tries": ", ".join(info.get("tries", [])),
                }) + "\n"
            except Exception as e:
                yield json.dumps({"error": f"Ovoz (TTS) xatosi: {e}"[:400]}) + "\n"
            return

        q: asyncio.Queue = asyncio.Queue()

        async def synth(s: str, t_llm: int):
            t = time.perf_counter()
            audio, fmt, used = await tts.synthesize(s, p, req.tts)
            return s, audio, fmt, used, t_llm, int((time.perf_counter() - t) * 1000)

        async def producer():
            try:
                async for s in llm.stream_sentences(p.system_prompt(), history, info, req.model):
                    t_llm = int((time.perf_counter() - t0) * 1000)
                    await q.put(asyncio.create_task(synth(s, t_llm)))  # TTS parallel boshlanadi
            except Exception as e:
                await q.put(RuntimeError(f"AI xatosi: {e}"))
            await q.put(None)

        prod = asyncio.create_task(producer())
        try:
            while (item := await q.get()) is not None:
                try:
                    if isinstance(item, Exception):
                        raise item
                    s, audio, fmt, used, t_llm, t_tts = await item
                    if not audio:
                        raise RuntimeError(f"Ovoz bo'sh chiqdi | javob: {s}")
                except Exception as e:
                    yield json.dumps({"error": str(e)[:400]}) + "\n"
                    break
                log.info("seg patient=%s total=%dms llm=%dms tts=%dms model=%s tries=%s",
                         p.id, int((time.perf_counter() - t0) * 1000), t_llm, t_tts,
                         info.get("model", ""), info.get("tries", []))
                yield json.dumps({"text": s, "audio_b64": base64.b64encode(audio).decode(),
                                  "ms": int((time.perf_counter() - t0) * 1000),
                                  "llm_ms": t_llm, "tts_ms": t_tts, "fmt": fmt, "tts": used,
                                  "model": info.get("model", ""), "usage": info.get("usage", ""), "tries": ", ".join(info.get("tries", []))}) + "\n"
        finally:
            prod.cancel()

    return StreamingResponse(gen(), media_type="application/x-ndjson")


class EvalRequest(BaseModel):
    patient_id: str
    history: list[Turn]
    model: str | None = None


@app.post("/evaluate")
async def evaluate(req: EvalRequest):
    """Suhbat tugagach hamshirani 5 mezon bo'yicha baholaydi."""
    p = PATIENTS.get(req.patient_id)
    if not p:
        raise HTTPException(404, "Bemor topilmadi")
    history = [t.model_dump() for t in req.history if t.content.strip()]
    if not any(t["role"] == "user" for t in history):
        raise HTTPException(400, "Baholash uchun suhbat kerak")
    try:
        return await evaluator.evaluate(p, history, req.model)
    except Exception as e:
        raise HTTPException(502, f"Baholash xatosi: {e}"[:400])


@app.get("/tts_test")
async def tts_test(token: str = "", text: str = "Assalomu alaykum, qizim. Kelganing yaxshi bo'ldi, oxirgi paytlarda juda holsizlanib qolayapman."):
    """Ovoz tezligini o'lchash (faqat DEBUG_TOKEN sozlangan bo'lsa)."""
    if not settings.debug_token or token != settings.debug_token:
        raise HTTPException(403, "Ruxsat yo'q")
    return await tts.benchmark(text[:300])


VOICES = ("uz-UZ-MadinaNeural", "uz-UZ-SardorNeural")
SAMPLES = {
    "buvi": "Og'zim tinmay qurib, suv ichganim-ichgan. Kechasi bilan hojatxonaga qatnayman, uyqu yo'q. Oyoqlarim ham uvishib, muzlaydi.",
    "homilador": "Belim simillab og'riyapti, boshim aylanib, tez charchab qolayapman. Siydigimning rangi ham to'qroq bo'lib qoldi.",
    "bola": "Qornim og'riyapti, kechasi orqamni qashlayman. Uxlay olmayman, ovqat yegim kelmayapti.",
}


def _check_token(token: str):
    if not settings.debug_token or token != settings.debug_token:
        raise HTTPException(403, "Ruxsat yo'q")


@app.get("/voice_demo")
async def voice_demo(token: str = "", patient: str = "buvi", voice: str = "", rate: str = "", pitch: str = "", text: str = ""):
    """Edge ovozini berilgan tezlik/ohang bilan eshittiradi (sozlash uchun)."""
    _check_token(token)
    import edge_tts
    p = PATIENTS.get(patient)
    if not p:
        raise HTTPException(404, "Bemor topilmadi")
    v = voice if voice in VOICES else p.voice
    r = rate if re.fullmatch(r"[+-]\d{1,3}%", rate) else p.rate
    pt = pitch if re.fullmatch(r"[+-]\d{1,3}Hz", pitch) else p.pitch
    txt = tts.clean_for_tts(text[:300]) or SAMPLES.get(patient, "Assalomu alaykum.")
    audio = b""
    async for ch in edge_tts.Communicate(txt, v, rate=r, pitch=pt).stream():
        if ch["type"] == "audio":
            audio += ch["data"]
    return Response(audio, media_type="audio/mpeg")


_LAB = """<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MedSim ovoz laboratoriyasi</title><style>
body{font-family:system-ui,sans-serif;background:#f3f7f6;margin:0;padding:16px;color:#0f172a}
h1{color:#0f766e;font-size:22px}.card{background:#fff;border-radius:18px;padding:16px;margin:14px 0;box-shadow:0 1px 4px #0002}
label{display:block;margin:10px 0 2px;font-size:14px;color:#475569}input[type=range]{width:100%}select,textarea{width:100%;font-size:15px;padding:6px;box-sizing:border-box}
button{background:#0f766e;color:#fff;border:0;border-radius:12px;padding:12px 22px;font-size:16px;margin-top:10px}
code{background:#e4eceb;padding:2px 6px;border-radius:6px}</style></head><body>
<h1>Ovoz laboratoriyasi (Edge)</h1><p>Chizg'ichlarni suring va "Tinglash" ni bosing. Yoqqan qiymatlarni menga yozing.</p><div id="c"></div>
<script>
const token=new URLSearchParams(location.search).get('token')||'';
const P=__DATA__;
const box=document.getElementById('c');
for(const [id,d] of Object.entries(P)){
 const r=parseInt(d.rate), pt=parseInt(d.pitch);
 box.insertAdjacentHTML('beforeend',`<div class="card" id="${id}"><b>${d.title}</b>
 <label>Ovoz</label><select class="v"><option ${d.voice.includes('Madina')?'selected':''} value="uz-UZ-MadinaNeural">Madina (ayol)</option><option ${d.voice.includes('Sardor')?'selected':''} value="uz-UZ-SardorNeural">Sardor (erkak)</option></select>
 <label>Tezlik: <span class="rv">${r}</span>%</label><input class="r" type="range" min="-50" max="50" value="${r}">
 <label>Ohang (balandlik): <span class="pv">${pt}</span> Hz</label><input class="p" type="range" min="-60" max="90" value="${pt}">
 <label>Matn</label><textarea class="t" rows="3">${d.sample}</textarea>
 <button>▶ Tinglash</button><p>Qiymat: <code class="o"></code></p><audio controls style="width:100%"></audio></div>`);
}
document.querySelectorAll('.card').forEach(c=>{
 const v=c.querySelector('.v'),r=c.querySelector('.r'),p=c.querySelector('.p'),t=c.querySelector('.t'),a=c.querySelector('audio');
 const sg=n=>(n>=0?'+':'')+n;
 const upd=()=>{c.querySelector('.rv').textContent=r.value;c.querySelector('.pv').textContent=p.value;
  c.querySelector('.o').textContent=`${c.id}: ${v.value.split('-')[2]}, tezlik ${sg(+r.value)}%, ohang ${sg(+p.value)}Hz`;};
 [v,r,p].forEach(e=>e.oninput=upd);upd();
 c.querySelector('button').onclick=()=>{
  const q=new URLSearchParams({token,patient:c.id,voice:v.value,rate:sg(+r.value)+'%',pitch:sg(+p.value)+'Hz',text:t.value});
  a.src='/voice_demo?'+q.toString();a.play();};
});
</script></body></html>"""


@app.get("/voice_lab", response_class=HTMLResponse)
async def voice_lab(token: str = ""):
    _check_token(token)
    data = {pid: {"title": p.title, "voice": p.voice, "rate": p.rate, "pitch": p.pitch, "sample": SAMPLES.get(pid, "")}
            for pid, p in PATIENTS.items()}
    return _LAB.replace("__DATA__", json.dumps(data, ensure_ascii=False))


@app.get("/models")
async def models():
    """Kalitingiz bilan ishlaydigan Gemini model ID'lari (GEMINI_MODELS uchun)."""
    return await llm.list_gemini_models()


@app.get("/health")
def health():
    return {"ok": True}
