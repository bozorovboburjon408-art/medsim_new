import asyncio
import base64
import json
import logging
import re
import time

import httpx

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel

from . import evaluator, live, llm, tts
from .config import settings
from .patients import PATIENTS

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="MedSim backend")
app.include_router(live.router)


class Turn(BaseModel):
    role: str  # "user" (hamshira) yoki "assistant" (bemor)
    content: str


class ChatRequest(BaseModel):
    patient_id: str
    history: list[Turn]  # oxirgisi hamshiraning yangi gapi bo'lishi kerak
    model: str | None = None  # ixtiyoriy: shu model birinchi sinaladi
    tts: str | None = None  # "gemini", "edge", yoki bo'sh (default: config dagi)


class ChatResponse(BaseModel):
    text: str
    audio_b64: str  # mp3 yoki wav
    fmt: str = "mp3"
    tts: str = ""
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
        audio, used = await tts.synthesize(text, p, req.tts)
    except Exception as e:
        raise HTTPException(502, f"Ovoz (TTS) xatosi: {e} | javob: {text}"[:400])
    t2 = time.perf_counter()
    if not audio:
        raise HTTPException(502, f"Ovoz bo'sh chiqdi (TTS) | javob: {text}"[:400])
    fmt = "wav" if used == "gemini" else "mp3"
    return ChatResponse(text=text, audio_b64=base64.b64encode(audio).decode(),
                        fmt=fmt, tts=used,
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

        q: asyncio.Queue = asyncio.Queue()

        async def synth(s: str, t_llm: int):
            t = time.perf_counter()
            audio, used = await tts.synthesize(s, p, req.tts)
            fmt = "wav" if used == "gemini" else "mp3"
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


VOICES = ("uz-UZ-MadinaNeural", "uz-UZ-SardorNeural")
SAMPLES = {
    "buvi": "Og'zim tinmay qurib, suv ichganim-ichgan. Kechasi bilan hojatxonaga qatnayman, uyqu yo'q. Oyoqlarim ham uvishib, muzlaydi.",
    "homilador": "Belim simillab og'riyapti, boshim aylanib, tez charchab qolayapman. Siydigimning rangi ham to'qroq bo'lib qoldi.",
    "bola": "Qornim og'riyapti, kechasi orqamni qashlayman. Uxlay olmayman, ovqat yegim kelmayapti.",
    "bobo": "Vaalaykum assalom, qizim. Oxirgi paytlarda holsizlik, kechalari uxlashim qiyin, tez-tez hojatxonaga qatnayman.",
}


def _check_token(token: str):
    if not settings.debug_token or token != settings.debug_token:
        raise HTTPException(403, "Ruxsat yo'q")


@app.get("/voice_demo")
async def voice_demo(token: str = "", patient: str = "buvi", voice: str = "", rate: str = "", pitch: str = "", text: str = "",
                     engine: str = "edge", gvoice: str = "", gmodel: str = "", gstyle: str = "", gmode: str = "none"):
    """Ovozni eshittiradi: engine=edge (tezlik/ohang bilan) yoki engine=gemini (faqat laboratoriya, pulli)."""
    _check_token(token)
    import edge_tts
    p = PATIENTS.get(patient)
    if not p:
        raise HTTPException(404, "Bemor topilmadi")
    if engine == "cloud":
        txt = tts.clean_for_tts(text[:300]) or SAMPLES.get(patient, "Assalomu alaykum.")
        gv = gvoice if gvoice in tts.GEMINI_VOICES else tts.GEMINI_DEFAULT_VOICE.get(patient, "Kore")
        if not settings.google_tts_api_key:
            raise HTTPException(400, "GOOGLE_TTS_API_KEY Render muhitida o'rnatilmagan")
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,60}", gmodel):
            raise HTTPException(400, "Cloud TTS modeli noto'g'ri")
        try:
            return Response(await tts.cloud_tts_lab(txt, gv, gmodel, gstyle), media_type="audio/mpeg")
        except Exception as e:
            raise HTTPException(502, f"Cloud TTS: {e}")
    if engine == "gemini":
        txt = tts.clean_for_tts(text[:300]) or SAMPLES.get(patient, "Assalomu alaykum.")
        gv = gvoice if gvoice in tts.GEMINI_VOICES else tts.GEMINI_DEFAULT_VOICE.get(patient, "Kore")
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,80}", gmodel):
            raise HTTPException(400, "Gemini TTS modeli tanlanmagan")
        try:
            return Response(await tts.gemini_tts_lab(txt, gv, gmodel, gstyle, gmode if gmode in ('say', 'director') else 'none'), media_type="audio/wav")
        except Exception as e:
            raise HTTPException(502, f"Gemini TTS: {e}")
    v = voice if voice in VOICES else p.voice
    r = rate if re.fullmatch(r"[+-]\d{1,3}%", rate) else p.rate
    pt = pitch if re.fullmatch(r"[+-]\d{1,3}Hz", pitch) else p.pitch
    txt = tts.clean_for_tts(text[:300]) or SAMPLES.get(patient, "Assalomu alaykum.")
    audio = b""
    async for ch in edge_tts.Communicate(txt, v, rate=r, pitch=pt).stream():
        if ch["type"] == "audio":
            audio += ch["data"]
    return Response(audio, media_type="audio/mpeg")


GEMINI_STYLES = {
    "buvi": "slowly, in a weak, warm, slightly tired voice of a 75-year-old Uzbek grandmother",
    "homilador": "naturally and conversationally, like a real 32-year-old pregnant woman talking to her nurse, slightly tired, soft, with natural pauses, small breaths and varied intonation, not like a reader",
    "bola": "in the high, small, playful voice of a 5-year-old Uzbek child, slightly whiny, with childlike intonation and short breaths",
    "bobo": "slowly, in a calm, warm, slightly hoarse voice of a 78-year-old Uzbek grandfather",
}

_LAB = r"""<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MedSim ovoz laboratoriyasi</title><style>
body{font-family:system-ui,sans-serif;background:#f3f7f6;margin:0;padding:16px;color:#0f172a}
h1{color:#0f766e;font-size:22px}.card{background:#fff;border-radius:18px;padding:16px;margin:14px 0;box-shadow:0 1px 4px #0002}
label{display:block;margin:10px 0 2px;font-size:14px;color:#475569}input[type=range]{width:100%}select,textarea{width:100%;font-size:15px;padding:6px;box-sizing:border-box}
button{background:#0f766e;color:#fff;border:0;border-radius:12px;padding:12px 18px;font-size:16px;margin:10px 6px 0 0}
button.g{background:#7c3aed}button.c{background:#334155}
code{background:#e4eceb;padding:2px 6px;border-radius:6px}.m{font-size:13px;color:#475569;margin:6px 0}</style></head><body>
<h1>Ovoz laboratoriyasi: Edge va Gemini</h1>
<p>Har bemor uchun Edge (bepul) va Gemini (pulli, har bosish ~bir necha sent) ovozini yonma-yon eshiting. "Ketma-ket" tugmasi ikkalasini birin-ketin chaladi.</p>
<div class="card"><label>Gemini TTS modeli (serverdan olinadi)</label><select id="gm"><option value="">yuklanmoqda...</option></select><div class="m" id="gmnote"></div></div>
<div class="card"><label>Google Cloud TTS modeli ($300 kredit; GOOGLE_TTS_API_KEY kerak)</label>
<select id="cm"><option>gemini-2.5-flash-tts</option><option>gemini-2.5-pro-tts</option><option value="Chirp3-HD">Chirp3-HD</option></select>
<button class="c" id="cv">O\u2018zbekcha ovozlarni tekshirish</button><div class="m" id="cvnote"></div></div>
<div id="c"></div>
<script>
const token=new URLSearchParams(location.search).get('token')||'';
const P=__DATA__, GV=__GV__, GD=__GD__, GS=__GS__;
const box=document.getElementById('c');
const sg=n=>(n>=0?'+':'')+n;
document.getElementById('cv').onclick=async()=>{const n=document.getElementById('cvnote');n.textContent='tekshirilmoqda...';
 try{const r=await fetch('/cloud_voices?token='+encodeURIComponent(token));const t=await r.text();
  n.textContent=r.ok?(JSON.parse(t).length+' ta uz-UZ ovozi: '+t.slice(0,300)):'Xato: '+t.slice(0,300);}catch(e){n.textContent='Xato: '+e;}};
fetch('/tts_models?token='+encodeURIComponent(token)).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).then(l=>{
 const s=document.getElementById('gm');
 s.innerHTML=l.map(m=>'<option>'+m+'</option>').join('')||'<option value="">TTS modeli topilmadi</option>';
 const i=l.findIndex(m=>m.indexOf('lite')>=0);if(i>=0)s.selectedIndex=i;
 document.getElementById('gmnote').textContent=l.length+' ta TTS modeli topildi';
}).catch(e=>{document.getElementById('gm').innerHTML='<option value="">roʻyxat yuklanmadi</option>';document.getElementById('gmnote').textContent=String(e);});
for(const [id,d] of Object.entries(P)){
 const r=parseInt(d.rate), pt=parseInt(d.pitch);
 box.insertAdjacentHTML('beforeend','<div class="card" id="'+id+'"><b>'+d.title+'</b>'+
 '<label>Edge ovozi</label><select class="v"><option '+(d.voice.includes('Madina')?'selected':'')+' value="uz-UZ-MadinaNeural">Madina (ayol)</option><option '+(d.voice.includes('Sardor')?'selected':'')+' value="uz-UZ-SardorNeural">Sardor (erkak)</option></select>'+
 '<label>Edge tezlik: <span class="rv">'+r+'</span>%</label><input class="r" type="range" min="-50" max="50" value="'+r+'">'+
 '<label>Edge ohang: <span class="pv">'+pt+'</span> Hz</label><input class="p" type="range" min="-60" max="90" value="'+pt+'">'+
 '<label>Gemini ovozi</label><select class="gv">'+GV.map(v=>'<option'+(v===GD[id]?' selected':'')+'>'+v+'</option>').join('')+'</select>'+
 '<label>Gemini uslub ko\u2018rsatmasi (ingliz tilida yozing)</label><textarea class="gs" rows="2">'+(GS[id]||'')+'</textarea>'+
 '<label>Uslub shakli</label><select class="gmo"><option value="none">Uslubsiz (tavsiya)</option><option value="say">Say ...: matn</option><option value="director">Rejissyor yozuvi</option></select>'+
 '<label>Balandlik (oʻynatish tezligi): <span class="pbv">1.00</span>x (bolaga: 1.15\u20131.35)</label><input class="pb" type="range" min="80" max="160" value="100">'+
 '<label>Matn</label><textarea class="t" rows="3">'+d.sample+'</textarea>'+
 '<button class="e">▶ Edge</button><button class="g">▶ Gemini</button><button class="c">⇄ Ketma-ket</button><button class="k" style="background:#0369a1">☁ Cloud</button>'+
 '<div class="m">Qiymat: <code class="o"></code></div><div class="m st"></div><audio controls style="width:100%"></audio></div>');
}
document.querySelectorAll('.card[id]').forEach(c=>{
 const v=c.querySelector('.v'),r=c.querySelector('.r'),p=c.querySelector('.p'),t=c.querySelector('.t'),gv=c.querySelector('.gv'),gs=c.querySelector('.gs'),gmo=c.querySelector('.gmo'),pb=c.querySelector('.pb'),a=c.querySelector('audio'),st=c.querySelector('.st');
 const upd=()=>{c.querySelector('.rv').textContent=r.value;c.querySelector('.pv').textContent=p.value;
  c.querySelector('.o').textContent=c.id+': '+v.value.split('-')[2]+', tezlik '+sg(+r.value)+'%, ohang '+sg(+p.value)+'Hz, Gemini '+gv.value;};
 [v,r,p,gv].forEach(e=>e.oninput=upd);pb.oninput=()=>{c.querySelector('.pbv').textContent=(pb.value/100).toFixed(2);a.preservesPitch=false;a.playbackRate=pb.value/100;};upd();
 const url=eng=>{const q=new URLSearchParams({token:token,patient:c.id,text:t.value,engine:eng});
  if(eng==='edge'){q.set('voice',v.value);q.set('rate',sg(+r.value)+'%');q.set('pitch',sg(+p.value)+'Hz');}
  else if(eng==='cloud'){q.set('gvoice',gv.value);q.set('gmodel',document.getElementById('cm').value);q.set('gstyle',gs.value);}
  else{q.set('gvoice',gv.value);q.set('gmodel',document.getElementById('gm').value);q.set('gstyle',gs.value);q.set('gmode',gmo.value);}
  return '/voice_demo?'+q.toString();};
 const play=async eng=>{const nm={edge:'Edge',gemini:'Gemini',cloud:'Cloud'}[eng];st.textContent=nm+' tayyorlanmoqda...';const t0=performance.now();
  try{const res=await fetch(url(eng));if(!res.ok)throw new Error('HTTP '+res.status+' '+(await res.text()).slice(0,200));
   const blob=await res.blob();const sec=((performance.now()-t0)/1000).toFixed(1);
   st.textContent=nm+': '+sec+' s da tayyor boʻldi';a.src=URL.createObjectURL(blob);
   a.preservesPitch=false;a.playbackRate=eng==='edge'?1:pb.value/100;
   await a.play();await new Promise(ok=>{a.onended=ok;a.onerror=ok;});}
  catch(e){st.textContent='Xato: '+e;}};
 c.querySelector('.e').onclick=()=>play('edge');
 c.querySelector('.g').onclick=()=>play('gemini');
 c.querySelector('.k').onclick=()=>play('cloud');
 c.querySelector('.c').onclick=async()=>{await play('edge');await play('gemini');};
});
</script></body></html>"""


@app.get("/voice_lab", response_class=HTMLResponse)
async def voice_lab(token: str = ""):
    _check_token(token)
    data = {pid: {"title": p.title, "voice": p.voice, "rate": p.rate, "pitch": p.pitch, "sample": SAMPLES.get(pid, "")}
            for pid, p in PATIENTS.items()}
    return (_LAB.replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__GV__", json.dumps(tts.GEMINI_VOICES)).replace("__GD__", json.dumps(tts.GEMINI_DEFAULT_VOICE)).replace("__GS__", json.dumps(GEMINI_STYLES)))


@app.get("/cloud_voices")
async def cloud_voices_ep(token: str = "", lang: str = "uz-UZ"):
    _check_token(token)
    if not settings.google_tts_api_key:
        raise HTTPException(400, "GOOGLE_TTS_API_KEY Render muhitida o'rnatilmagan")
    if not re.fullmatch(r"[a-z]{2,3}-[A-Z]{2}", lang):
        raise HTTPException(400, "Til kodi noto'g'ri")
    try:
        return [{"name": v.get("name"), "gender": v.get("ssmlGender")} for v in await tts.cloud_voices(lang)]
    except Exception as e:
        raise HTTPException(502, f"Cloud TTS: {e}")


@app.get("/tts_models")
async def tts_models(token: str = ""):
    _check_token(token)
    try:
        return await tts.list_gemini_tts_models()
    except Exception as e:
        raise HTTPException(502, f"Modellar ro'yxati olinmadi: {e}")


@app.get("/models")
async def models():
    """Kalitingiz bilan ishlaydigan Gemini model ID'lari (GEMINI_MODELS uchun)."""
    return await llm.list_gemini_models()


@app.get("/debug_tts")
async def debug_tts(text: str = "Assalomu alaykum, yaxshimisiz?", voice: str = "Aoede"):
    """Gemini TTS modellarini sinovdan o'tkazish va statuslarini ko'rish uchun."""
    if not settings.gemini_api_key:
        return {"error": "gemini_api_key sozlanmagan"}
    models = [m.strip() for m in settings.gemini_tts_models.split(",") if m.strip()]
    results = []
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            },
        },
    }
    hdr = {"x-goog-api-key": settings.gemini_api_key}
    async with httpx.AsyncClient(timeout=10) as c:
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                r = await c.post(url, json=body, headers=hdr)
                if r.status_code == 200:
                    data = r.json()
                    cands = data.get("candidates", [])
                    cand = cands[0] if cands else {}
                    parts = cand.get("content", {}).get("parts", [])
                    has_audio = any("inlineData" in pt for pt in parts)
                    results.append({
                        "model": m,
                        "status": 200,
                        "finish_reason": cand.get("finishReason"),
                        "has_audio": has_audio,
                        "parts_count": len(parts),
                        "cand_keys": list(cand.keys()),
                        "content_keys": list(cand.get("content", {}).keys()) if cand.get("content") else [],
                        "sample": str(cand)[:200]
                    })
                else:
                    results.append({"model": m, "status": r.status_code, "detail": r.text[:250]})
            except Exception as e:
                results.append({"model": m, "error": f"{type(e).__name__}: {e}"})
    return {"voice": voice, "results": results}


@app.get("/test_synth")
async def test_synth(patient: str = "buvi", text: str = "Assalomu alaykum qizim"):
    p = PATIENTS.get(patient)
    if not p:
        return {"error": "patient not found"}
    res = {"patient": patient, "voice": getattr(p, "gemini_voice", None), "speed": getattr(p, "gemini_speed", 1.0)}
    try:
        t0 = time.perf_counter()
        g_audio = await tts._gemini(tts.clean_for_tts(text), p)
        res["gemini_ok"] = True
        res["gemini_ms"] = int((time.perf_counter() - t0) * 1000)
        res["gemini_len"] = len(g_audio)
    except Exception as e:
        res["gemini_ok"] = False
        res["gemini_error"] = f"{type(e).__name__}: {e}"

    try:
        t0 = time.perf_counter()
        audio, used = await tts.synthesize(text, p)
        res["synth_ms"] = int((time.perf_counter() - t0) * 1000)
        res["used"] = used
        res["audio_len"] = len(audio)
        res["header"] = audio[:12].hex() if audio else ""
    except Exception as e:
        res["synth_error"] = f"{type(e).__name__}: {e}"
    return res


@app.get("/health")
def health():
    return {"ok": True}
