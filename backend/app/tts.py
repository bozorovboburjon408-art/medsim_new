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


def latin_to_cyrillic(text: str) -> str:
    """ElevenLabs o'zbek tilidagi q, x, g' harflarini inglizcha o'qimasligi uchun
    Cyrillic ga o'tkazib yuboramiz. Shunda talaffuz 10x yaxshilanadi."""
    mapping = {
        "sh": "ш", "ch": "ч", "o'": "ў", "o‘": "ў", "g'": "ғ", "g‘": "ғ",
        "Sh": "Ш", "Ch": "Ч", "O'": "Ў", "O‘": "Ў", "G'": "Ғ", "G‘": "Ғ",
        "ya": "я", "yu": "ю", "yo": "ё", "ye": "е",
        "Ya": "Я", "Yu": "Ю", "Yo": "Ё", "Ye": "Е",
        "a": "а", "b": "б", "d": "д", "e": "э", "f": "ф", "g": "г", "h": "ҳ",
        "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
        "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
        "x": "х", "y": "й", "z": "з",
        "A": "А", "B": "Б", "D": "Д", "E": "Э", "F": "Ф", "G": "Г", "H": "Ҳ",
        "I": "И", "J": "Ж", "K": "К", "L": "Л", "M": "М", "N": "Н", "O": "О",
        "P": "П", "Q": "Қ", "R": "Р", "S": "С", "T": "Т", "U": "У", "V": "В",
        "X": "Х", "Y": "Й", "Z": "З",
        "'": "ъ"
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text

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

    if prov == "elevenlabs" and settings.elevenlabs_api_key:
        try:
            return await _elevenlabs(text, p), "elevenlabs"
        except Exception as e:
            log.warning("ElevenLabs TTS xatosi (%s), Edge ga o'tilmoqda", e)

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
        models = [
            "gemini-2.5-flash-preview-tts",
            "gemini-3.1-flash-tts-preview",
        ]

    voice = p.gemini_voice or "Aoede"
    
    body = {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            },
        },
    }
    hdr = {"x-goog-api-key": settings.gemini_api_key}

    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=12) as c:
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                r = await c.post(url, json=body, headers=hdr)
            except Exception as e:
                log.warning("Gemini TTS %s tarmoq xatosi: %s", m, e)
                last_err = e
                continue
            if r.status_code != 200:
                log.warning("Gemini TTS %s status %d: %s", m, r.status_code, r.text[:200])
                last_err = RuntimeError(f"{m} status {r.status_code}: {r.text[:200]}")
                continue
            try:
                data = r.json()
                parts = data["candidates"][0]["content"]["parts"]
                for pt in parts:
                    if "inlineData" in pt:
                        raw = base64.b64decode(pt["inlineData"]["data"])
                        mime = pt["inlineData"].get("mimeType", "").lower()
                        # PCM / L16 bo'lsa WAV sarlavha qo'shamiz, aks holda tayyor audio
                        if "pcm" in mime or not mime or "l16" in mime:
                            return pcm_to_wav(raw, 24000)
                        return raw
            except Exception as e:
                log.warning("Gemini TTS %s tahlil xatosi: %s", m, e)
                last_err = e
                continue

    raise RuntimeError(f"Gemini TTS modellaridan ovoz olinmadi: {last_err}")


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


async def _elevenlabs(text: str, p: Patient) -> bytes:
    """ElevenLabs orqali MP3 audio qaytaradi."""
    if not settings.elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY sozlanmagan")
    
    voice_id = p.elevenlabs_voice
    if not voice_id:
        raise ValueError(f"Bemor '{p.id}' uchun elevenlabs_voice kiritilmagan")
        
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json"
    }
    
    # ElevenLabs to'g'ri (q, x, g' ni) o'qishi uchun Krilchaga o'giramiz!
    cyrillic_text = latin_to_cyrillic(text)
    
    body = {
        "text": cyrillic_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.35,          # Pastroq barqarorlik = ko'proq emotsiya va jonlilik
            "similarity_boost": 0.85,   # Asl ovozga maksimal o'xshashlik
            "style": 0.15,              # Ovozga ozgina aktyorlik uslubi qo'shish
            "use_speaker_boost": True
        }
    }
    
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(url, json=body, headers=headers)
        if r.status_code != 200:
            log.warning("ElevenLabs xatosi: %s", r.text[:200])
            r.raise_for_status()
        return r.content

