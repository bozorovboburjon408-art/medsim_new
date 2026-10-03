"""Matnni o'zbekcha ovozga aylantirish. Ovoz faqat Edge (bepul) yoki Azure (ixtiyoriy) orqali.
Gemini faqat matn (suhbat va baholash) uchun ishlatiladi, ovoz uchun emas."""
import asyncio
import logging
import re
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
