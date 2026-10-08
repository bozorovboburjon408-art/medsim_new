"""Matnni o'zbekcha ovozga aylantirish. Ovoz faqat Edge (bepul) yoki Azure (ixtiyoriy) orqali.
Gemini faqat matn (suhbat va baholash) uchun ishlatiladi, ovoz uchun emas."""
import asyncio
import base64
import io
import logging
import re
import wave
from xml.sax.saxutils import escape

import edge_tts
import httpx

from .config import settings
from .patients import Patient

log = logging.getLogger("uvicorn.error")


def clean_for_tts(text: str) -> str:
    """Ovozga berilmaydigan belgilarni olib tashlaydi (qo'shtirnoq, qavs, ikki nuqta, tire va h.k.).
    O'zbekcha tutuq belgilari (o', g', ʻ, ’) saqlanadi."""
    t = re.sub(r"[*_#`~<>\[\](){}]", " ", text)
    for q in ("«", "»", '"', "“", "”", "„"):
        t = t.replace(q, " ")
    t = re.sub(r"\s*[:;]\s*", ", ", t)
    t = re.sub(r"\s[—–-]+\s", ", ", t)
    t = re.sub(r"\.{2,}|…", ".", t)
    t = re.sub(r"\s*,(\s*,)+", ",", t)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"\s+([.,!?])", r"\1", t)


async def synthesize(text: str, p: Patient) -> tuple[bytes, str]:
    """Matnni ovozga aylantiradi. Qaytaradi: (mp3 baytlari, ishlatilgan xizmat nomi)."""
    text = clean_for_tts(text)
    if settings.tts_provider == "azure" and settings.azure_speech_key:
        return await _azure(text, p), "azure"
    return await _edge(text, p), "edge"


async def _edge(text: str, p: Patient) -> bytes:
    async def run() -> bytes:
        out = b""
        async for ch in edge_tts.Communicate(text, p.voice, rate=p.rate, pitch=p.pitch).stream():
            if ch["type"] == "audio":
                out += ch["data"]
        return out

    last: Exception | None = None
    for _ in range(2):  # osilib qolsa 8 soniyadan keyin bir marta qayta uriniladi
        try:
            return await asyncio.wait_for(run(), timeout=8)
        except Exception as e:
            last = e
    raise last


async def _azure(text: str, p: Patient) -> bytes:
    ssml = (f"<speak version='1.0' xml:lang='uz-UZ'><voice name='{p.voice}'>"
            f"<prosody rate='{p.rate}' pitch='{p.pitch}'>{escape(text)}</prosody></voice></speak>")
    url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(url, content=ssml.encode(), headers={
            "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"})
        r.raise_for_status()
    return r.content


def _pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


GEMINI_VOICES = ["Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe", "Autonoe",
                 "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi",
                 "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
                 "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"]
GEMINI_DEFAULT_VOICE = {"buvi": "Gacrux", "homilador": "Kore", "bola": "Puck", "bobo": "Charon"}


async def list_gemini_tts_models() -> list[str]:
    from . import vertex
    if vertex.enabled():  # Vertex'da ro'yxat olinmaydi: sozlangan nomlarni sinab ko'ramiz
        return [m.strip() for m in settings.vertex_tts_models.split(",") if m.strip()]
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                        headers={"x-goog-api-key": settings.gemini_api_key})
        r.raise_for_status()
    return sorted(m["name"].removeprefix("models/") for m in r.json().get("models", []) if "tts" in m["name"].lower())


def gemini_prompt(text: str, style: str = "", mode: str = "none") -> str:
    """Uslub ko'rsatmasini matnga qo'shish: say = 'Say ...: matn', director = rejissyor yozuvlari bloki."""
    style = style.strip()[:300]
    if not style or mode == "none":
        return text
    if mode == "say":
        return f"Say {style}: {text}"
    return (f"# AUDIO PROFILE\n## DIRECTOR'S NOTES\nStyle: {style}\nPace: natural, unhurried.\n"
            f"Do not read these notes aloud; speak only the transcript.\n\n#### TRANSCRIPT\n{text}")


async def gemini_tts_lab(text: str, voice: str, model: str, style: str = "", mode: str = "none") -> bytes:
    """Faqat laboratoriya uchun: Gemini TTS bilan bitta gapni wav qilib qaytaradi."""
    body = {"contents": [{"role": "user", "parts": [{"text": gemini_prompt(text, style, mode)}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    from . import llm
    url, hdr = await llm.target(model, "generateContent")  # Vertex (kredit) yoki AI Studio
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=40, write=5, pool=5)) as c:
        r = await c.post(url, json=body, headers=hdr)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:200]}")
    part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
    rate = 24000
    if "rate=" in part.get("mimeType", ""):
        rate = int(part["mimeType"].split("rate=")[1].split(";")[0])
    return _pcm_to_wav(base64.b64decode(part["data"]), rate)


CLOUD_TTS = "https://texttospeech.googleapis.com/v1"


async def cloud_voices(lang: str = "uz-UZ") -> list[dict]:
    """Google Cloud TTS: berilgan til uchun ovozlar ro'yxati (o'zbekcha qo'llab-quvvatlanishini tekshirish uchun)."""
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{CLOUD_TTS}/voices", params={"languageCode": lang, "key": settings.google_tts_api_key})
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return r.json().get("voices", [])


async def cloud_tts_lab(text: str, voice: str, model: str, style: str = "") -> bytes:
    """Google Cloud TTS (Gemini-TTS yoki Chirp3-HD). Uslub ko'rsatmasi matndan alohida 'prompt' maydonida: ovozda o'qilmaydi."""
    inp: dict = {"text": text}
    if style.strip() and model.startswith("gemini"):
        inp["prompt"] = style.strip()[:300]
    v = {"languageCode": "uz-UZ", "name": voice}
    if model.startswith("gemini"):
        v["modelName"] = model
    else:  # masalan Chirp3-HD: to'liq ovoz nomi (uz-UZ-Chirp3-HD-Kore)
        v["name"] = f"uz-UZ-{model}-{voice}"
    body = {"input": inp, "voice": v, "audioConfig": {"audioEncoding": "MP3"}}
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=40, write=5, pool=5)) as c:
        r = await c.post(f"{CLOUD_TTS}/text:synthesize", json=body, params={"key": settings.google_tts_api_key})
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return base64.b64decode(r.json()["audioContent"])
