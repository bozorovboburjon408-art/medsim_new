"""ElevenLabs: ovozdan matn (Scribe), ovoz yaratish va ovoz kutubxonasini qidirish. Kalit faqat Render muhitida."""
import httpx

from .config import settings

BASE = "https://api.elevenlabs.io"

# Antigravity tanlagan o'zbek kutubxona ovozlari (maxfiy emas). Bola uchun foydalanuvchi tanlaydi.
DEFAULT_VOICE = {"buvi": "6Fkh9WgMXOqBcOWxX91f", "bobo": "xDwfBjUEPdIoQekNOXAX", "homilador": "132QLQIkg1RJGmpicuhR", "bola": "O72h9AUwisM6Zj4He72B"}
# Bemor bo'yicha model: Madinaxon eleven_v3 da qotirilgan, qolganlari standart (settings.eleven_tts_model)
DEFAULT_MODEL = {"bola": "eleven_v3"}
TTS_MODELS = ["eleven_multilingual_v2", "eleven_v3", "eleven_flash_v2_5", "eleven_turbo_v2_5"]


def enabled() -> bool:
    return bool(settings.elevenlabs_api_key.strip())


def _hdr() -> dict:
    return {"xi-api-key": settings.elevenlabs_api_key.strip()}


def latin_to_cyrillic(text: str) -> str:
    """O'zbek lotinini kirillga o'giradi (ba'zi modellar q, x, g' ni kirillda to'g'riroq o'qiydi)."""
    pairs = [("sh", "ш"), ("ch", "ч"), ("o'", "ў"), ("o‘", "ў"), ("o’", "ў"), ("g'", "ғ"), ("g‘", "ғ"), ("g’", "ғ"),
             ("Sh", "Ш"), ("Ch", "Ч"), ("O'", "Ў"), ("O‘", "Ў"), ("G'", "Ғ"), ("G‘", "Ғ"),
             ("ya", "я"), ("yu", "ю"), ("yo", "ё"), ("ye", "е"), ("Ya", "Я"), ("Yu", "Ю"), ("Yo", "Ё"), ("Ye", "Е")]
    single = dict(zip("abdefghijklmnopqrstuvxyz", "абдефгҳижклмнопқрстувхйз"))
    single.update({k.upper(): v.upper() for k, v in single.items()})
    single["'"] = "ъ"
    import re
    text = re.sub(r"\bE", "Э", re.sub(r"\be", "э", text))  # so'z boshidagi e -> э, boshqa joyda е
    for a, b in pairs:
        text = text.replace(a, b)
    return "".join(single.get(ch, ch) for ch in text)


async def stt(audio: bytes, mime: str = "audio/wav") -> str:
    """Scribe: o'zbekcha (uzb) ovozdan matn."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=30, write=15, pool=5)) as c:
        r = await c.post(f"{BASE}/v1/speech-to-text", headers=_hdr(),
                         data={"model_id": settings.eleven_stt_model, "language_code": "uzb", "tag_audio_events": "false"},
                         files={"file": ("audio.wav", audio, mime)})
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs STT {r.status_code}: {r.text[:200]}")
    return (r.json().get("text") or "").strip()


async def tts(text: str, voice_id: str, model: str = "", cyrillic: bool = False, fmt: str = "pcm_24000") -> bytes:
    """Bitta gapni ovozga aylantiradi (fmt: pcm_24000 yoki mp3_44100_128)."""
    body = {"text": latin_to_cyrillic(text) if cyrillic else text,
            "model_id": model or settings.eleven_tts_model,
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.85, "style": 0.15, "use_speaker_boost": True}}
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=30, write=10, pool=5)) as c:
        r = await c.post(f"{BASE}/v1/text-to-speech/{voice_id}/stream", params={"output_format": fmt},
                         json=body, headers=_hdr())
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs TTS {r.status_code}: {r.text[:200]}")
    return r.content


async def library(search: str = "", language: str = "uz", gender: str = "", age: str = "") -> list[dict]:
    """Umumiy ovoz kutubxonasidan qidirish."""
    params = {"page_size": 30}
    if language:
        params["language"] = language
    if search:
        params["search"] = search
    if gender:
        params["gender"] = gender
    if age:
        params["age"] = age
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{BASE}/v1/shared-voices", params=params, headers=_hdr())
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs kutubxona {r.status_code}: {r.text[:200]}")
    return [{"voice_id": v.get("voice_id"), "owner": v.get("public_owner_id"), "name": v.get("name"),
             "gender": v.get("gender"), "age": v.get("age"), "accent": v.get("accent"),
             "description": (v.get("description") or "")[:140], "preview": v.get("preview_url")}
            for v in r.json().get("voices", [])]


async def add_to_account(owner: str, voice_id: str) -> str:
    """Kutubxona ovozini 'mening ovozlarim'ga qo'shadi (shundan keyin ishlatsa bo'ladi)."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{BASE}/v1/voices/add/{owner}/{voice_id}", json={"new_name": f"medsim_{voice_id[:6]}"}, headers=_hdr())
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs qo'shish {r.status_code}: {r.text[:200]}")
    return r.json().get("voice_id", voice_id)
