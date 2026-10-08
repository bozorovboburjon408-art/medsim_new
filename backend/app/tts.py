"""Matnni o'zbekcha ovozga aylantirish. Gemini TTS (asosiy, jonli audio),
Edge TTS (bepul va zaxira), yoki Azure (ixtiyoriy)."""
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


async def synthesize(text: str, p: Patient, provider: str | None = None) -> tuple[bytes, str]:
    """Matnni ovozga aylantiradi. Qaytaradi: (audio_baytlari, ishlatilgan xizmat nomi).
    provider: 'gemini', 'edge', 'azure' yoki None (config bo'yicha)."""
    text = clean_for_tts(text)
    if not text:
        return b"", "none"

    prov = (provider or settings.tts_provider).strip().lower()
    # Agar alohida provider='edge' so'ralmagan bo'lsa va Gemini kaliti bo'lsa, Gemini'ni birlamchi qilamiz
    if provider is None and settings.gemini_api_key:
        prov = "gemini"

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

    if prov == "azure" and settings.azure_speech_key:
        try:
            return await _azure(text, p), "azure"
        except Exception as e:
            log.warning("Azure TTS xatosi (%s), Edge ga o'tilmoqda", e)

    # Edge TTS (bepul va zaxira)
    return await _edge(text, p), "edge"


def _adjust_audio(pcm: bytes, speed: float = 1.0, rate: int = 24000) -> bytes:
    """Ovoz tezligi va ohangini moslashtiradi: speed < 1.0 qari/sekin, speed > 1.0 yosh bola/chaqqon."""
    if abs(speed - 1.0) < 0.02:
        return pcm
    try:
        import audioop
        if len(pcm) % 2 != 0:
            pcm = pcm[:-1]
        in_rate = int(rate * speed)
        out_pcm, _ = audioop.ratecv(pcm, 2, 1, in_rate, rate, None)
        return out_pcm
    except Exception as e:
        log.warning("Ovoz tezligini moslashda xato: %s", e)
        return pcm


async def _gemini(text: str, p: Patient) -> bytes:
    """Gemini audio chiqish modalligi orqali o'zbekcha ovoz sintez qiladi."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY sozlanmagan")

    models = [m.strip() for m in settings.gemini_tts_models.split(",") if m.strip()]
    if not models:
        models = ["gemini-2.5-flash-preview-tts"]

    voice = getattr(p, "gemini_voice", None) or GEMINI_DEFAULT_VOICE.get(p.id, "Kore")

    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "temperature": 0.0,  # Ovoz va ritm tasodifiy o'zgarib ketmasligi, doim barqaror chiqishi uchun
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
    async with httpx.AsyncClient(timeout=15) as c:
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
                        rate = 24000
                        mime = pt["inlineData"].get("mimeType", "").lower()
                        if "rate=" in mime:
                            try:
                                rate = int(mime.split("rate=")[1].split(";")[0])
                            except Exception:
                                rate = 24000
                        speed = getattr(p, "gemini_speed", 1.0)
                        if raw.startswith(b"RIFF"):
                            pcm = raw[44:]
                            pcm = _adjust_audio(pcm, speed, rate)
                            return _pcm_to_wav(pcm, rate)
                        pcm = _adjust_audio(raw, speed, rate)
                        return _pcm_to_wav(pcm, rate)
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
GEMINI_DEFAULT_VOICE = {"buvi": "Gacrux", "homilador": "Kore", "bola": "Callirrhoe", "bobo": "Charon"}


async def list_gemini_tts_models() -> list[str]:
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
    body = {"contents": [{"parts": [{"text": gemini_prompt(text, style, mode)}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=40, write=5, pool=5)) as c:
        r = await c.post(url, json=body, headers={"x-goog-api-key": settings.gemini_api_key})
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
