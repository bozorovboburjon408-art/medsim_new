import asyncio
import base64
import json
import logging
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import llm, tts
from .patients import PATIENTS

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="MedSim backend")


class Turn(BaseModel):
    role: str  # "user" (hamshira) yoki "assistant" (bemor)
    content: str


class ChatRequest(BaseModel):
    patient_id: str
    history: list[Turn]  # oxirgisi hamshiraning yangi gapi bo'lishi kerak


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
        audio = await tts.synthesize(text, p)
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
        q: asyncio.Queue = asyncio.Queue()

        info: dict = {}

        async def synth(s: str, t_llm: int):
            t = time.perf_counter()
            audio = await tts.synthesize(s, p)
            return s, audio, t_llm, int((time.perf_counter() - t) * 1000)

        async def producer():
            try:
                async for s in llm.stream_sentences(p.system_prompt(), history, info):
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
                    s, audio, t_llm, t_tts = await item
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
                                  "llm_ms": t_llm, "tts_ms": t_tts,
                                  "model": info.get("model", ""), "tries": ", ".join(info.get("tries", []))}) + "\n"
        finally:
            prod.cancel()

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.get("/models")
async def models():
    """Kalitingiz bilan ishlaydigan Gemini model ID'lari (GEMINI_MODELS uchun)."""
    return await llm.list_gemini_models()


@app.get("/health")
def health():
    return {"ok": True}
