import base64

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import llm, tts
from .patients import PATIENTS

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
    text = await llm.generate(p.system_prompt(), [t.model_dump() for t in req.history])
    audio = await tts.synthesize(text, p)
    return ChatResponse(text=text, audio_b64=base64.b64encode(audio).decode())


@app.get("/models")
async def models():
    """Kalitingiz bilan ishlaydigan Gemini model ID'lari (GEMINI_MODELS uchun)."""
    return await llm.list_gemini_models()


@app.get("/health")
def health():
    return {"ok": True}
