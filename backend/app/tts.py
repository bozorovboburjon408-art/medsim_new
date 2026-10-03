"""Matnni o'zbekcha ovozga aylantirish.
Asosiy: Gemini Audio (tabiiy Gemini ovozlari).
Zaxira / bepul: Edge TTS (uz-UZ Madina/Sardor) yoki Azure."""
import asyncio
import base64
import logging
import re
import struct
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


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """24kHz 16-bit mono PCM ma'lumotiga WAV sarlavhasini (RIFF header) qo'shadi."""
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(pcm_data),
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        len(pcm_data),
    )
    return header + pcm_data


async def synthesize(text: str, p: Patient, provider: str | None = None) -> tuple[bytes, str]:
    """Matnni ovozga aylantiradi. Qaytaradi: (audio_baytlari, ishlatilgan xizmat nomi).
    provider: 'gemini', 'edge', 'azure' yoki None (config bo'yicha)."""
    text = clean_for_tts(text)
    if not text:
        return b"", "none"

    prov = (provider or settings.tts_provider).strip().lower()

    if prov == "azure" and settings.azure_speech_key:
        try:
            return await _azure(text, p), "azure"
        except Exception as e:
            log.warning("Azure TTS xatosi (%s), Edge ga o'tilmoqda", e)

    if prov in ("gemini", "auto", ""):
        if settings.gemini_api_key:
            try:
                audio = await _gemini(text, p)
                if audio:
                    return audio, "gemini"
            except Exception as e:
                log.warning("Gemini TTS xatosi (%s), zaxira Edge TTS ga o'tilmoqda", e)
        else:
            log.warning("GEMINI_API_KEY sozlanmagan, Edge TTS ga o'tilmoqda")

    # Edge TTS (bepul va zaxira)
    return await _edge(text, p), "edge"


async def _gemini(text: str, p: Patient) -> bytes:
    """Gemini audio chiqish modalligi orqali o'zbekcha ovoz sintez qiladi."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY sozlanmagan")

    models = [m.strip() for m in settings.gemini_tts_models.split(",") if m.strip()]
    if not models:
        models = ["gemini-2.5-flash", "gemini-2.0-flash"]

    voice = p.gemini_voice or "Gacrux"
    body = {
        "contents": [{"parts": [{"text": f"Quyidagi matnni tabiiy o'zbek tilida o'qi:\n{text}"}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            },
            "temperature": 0.2,
        },
    }
    hdr = {"x-goog-api-key": settings.gemini_api_key}

    async with httpx.AsyncClient(timeout=10) as c:
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                r = await c.post(url, json=body, headers=hdr)
            except Exception as e:
                log.warning("Gemini TTS %s xatosi: %s", m, e)
                continue
            if r.status_code != 200:
                log.warning("Gemini TTS %s status %d: %s", m, r.status_code, r.text[:120])
                continue
            try:
                data = r.json()
                parts = data["candidates"][0]["content"]["parts"]
                for pt in parts:
                    if "inlineData" in pt:
                        raw = base64.b64decode(pt["inlineData"]["data"])
                        mime = pt["inlineData"].get("mimeType", "").lower()
                        if "pcm" in mime or not mime:
                            return pcm_to_wav(raw, 24000)
                        return raw
            except Exception as e:
                log.warning("Gemini TTS %s tahlil xatosi: %s", m, e)
                continue

    raise RuntimeError("Gemini TTS modellaridan ovoz olinmadi")


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

