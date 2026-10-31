"""ElevenLabs: ovozdan matn (Scribe), ovoz yaratish va ovoz kutubxonasini qidirish. Kalit faqat Render muhitida."""
import asyncio
import re

import httpx

from .config import settings

BASE = "https://api.elevenlabs.io"

# Antigravity tanlagan o'zbek kutubxona ovozlari (maxfiy emas). Bola uchun foydalanuvchi tanlaydi.
DEFAULT_VOICE = {"buvi": "6Fkh9WgMXOqBcOWxX91f", "bobo": "xDwfBjUEPdIoQekNOXAX", "homilador": "132QLQIkg1RJGmpicuhR", "bola": "O72h9AUwisM6Zj4He72B"}
# Bemor bo'yicha model: hammasi eleven_v3 (v2 o'zbekchada ruscha talaffuz berdi)
DEFAULT_MODEL = {"buvi": "eleven_v4", "homilador": "eleven_v4", "bobo": "eleven_v4", "bola": "eleven_v4"}  # v4: tez va barqaror (v3 ba'zan 6-9 s kechikardi)
TTS_MODELS = ["eleven_multilingual_v2", "eleven_v3", "eleven_v4", "eleven_v4_turbo", "eleven_flash_v2_5", "eleven_turbo_v2_5"]


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


TAGS = {"crying", "sobbing", "whining", "sniffles", "laughs", "sighs", "whispers", "excited"}
_TAG = re.compile(r"\[([A-Za-z ]{2,20})\]")


def strip_tags(text: str) -> str:
    """[crying] kabi belgilarni olib tashlaydi (ekranda ko'rsatish va boshqa ovoz xizmatlari uchun)."""
    t = re.sub(r"\s+", " ", _TAG.sub("", text)).strip()
    return re.sub(r"\s+([.,!?])", r"\1", t)


def prepare(text: str) -> str:
    """ElevenLabs v3 uchun matn: ruxsat etilgan belgilar ([crying]...) saqlanadi, qolgani odatdagidek tozalanadi."""
    from . import tts as _tts
    found: list[str] = []

    def keep(m):
        tag = m.group(1).strip().lower()
        if tag in TAGS:
            found.append(f"[{tag}]")
            return f" TAGX{len(found) - 1}X "
        return " "

    t = _tts.clean_for_tts(_TAG.sub(keep, text))
    for i, tag in enumerate(found):
        t = t.replace(f"TAGX{i}X", tag)
    return re.sub(r"\s+", " ", t).strip()


def _settings(speed: float, stability: float, style: float = 0.15) -> dict:
    return {"stability": stability, "similarity_boost": 0.85, "style": style, "use_speaker_boost": True,
            "speed": max(0.7, min(1.2, speed))}


# ElevenLabs tarifida bir vaqtdagi so'rovlar soni cheklangan (429 concurrent_limit_exceeded): ortig'i navbatda kutadi
_SLOTS = asyncio.Semaphore(1)  # parallel yo'q: gaplar ketma-ket (har biri oqim bilan tez keladi)


def slots_free() -> bool:
    """Bo'sh joy bormi (sekin so'rovga qarshi ikkinchi nusxa faqat shunda yuboriladi)."""
    return _SLOTS._value > 0


async def subscription() -> dict:
    """Tarif va qolgan kredit (diagnostika)."""
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{BASE}/v1/user/subscription", headers=_hdr())
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:200]}")
    d = r.json()
    return {"tarif": d.get("tier"), "ishlatilgan": d.get("character_count"), "limit": d.get("character_limit"),
            "qolgan": (d.get("character_limit") or 0) - (d.get("character_count") or 0),
            "yangilanadi_unix": d.get("next_character_count_reset_unix"), "holat": d.get("status")}


async def tts_stream(text: str, voice_id: str, model: str = "", cyrillic: bool = False, speed: float = 1.0,
                     stability: float = 0.4, style: float = 0.15):
    """PCM (24 kHz, 16-bit) bo'laklari keladigan zahoti qaytariladi. Status oqim boshlanmasdan tekshiriladi."""
    body = {"text": latin_to_cyrillic(text) if cyrillic else text, "model_id": model or settings.eleven_tts_model,
            "voice_settings": _settings(speed, stability, style)}
    await asyncio.wait_for(_SLOTS.acquire(), 10)  # band joy 10 s da ham bo'shamasa xato (gap Edge'ga o'tadi)
    done = False

    def release():
        nonlocal done
        if not done:
            done = True
            _SLOTS.release()

    client = None
    try:
        for attempt in range(3):  # 429 (bir vaqtdagi chegara) bo'lsa qisqa kutib qayta uriniladi
            client = httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=30, write=10, pool=5))
            r = await client.send(client.build_request("POST", f"{BASE}/v1/text-to-speech/{voice_id}/stream",
                                                       params={"output_format": "pcm_24000"}, json=body, headers=_hdr()),
                                  stream=True)
            if r.status_code == 429 and attempt < 2:
                await r.aclose(); await client.aclose(); client = None
                await asyncio.sleep(0.4 * (attempt + 1))
                continue
            break
        if r.status_code >= 400:
            err = (await r.aread()).decode()[:200]
            await r.aclose(); await client.aclose(); client = None
            raise RuntimeError(f"ElevenLabs TTS {r.status_code}: {err}")
    except BaseException:
        if client is not None:
            await client.aclose()
        release()
        raise

    async def gen():
        left = b""
        try:
            async for ch in r.aiter_bytes(4800):
                b = left + ch
                if len(b) % 2:
                    left, b = b[-1:], b[:-1]
                else:
                    left = b""
                if b:
                    yield b
        finally:
            await r.aclose(); await client.aclose()
            release()
    return gen()


_CRY_WORD = re.compile(r"\b[Yy]ig['\u2019\u2018\u02bb`]?lay\w*\b[ ,]*(hozir)?[ ,]*", re.I)


def crying_fix(raw: str) -> str:
    """Model 'yig'layman' deb so'z bilan aytsa, o'rniga yig'lash belgisi qo'yiladi: [sobbing] va yig'lash tovushi."""
    if not _CRY_WORD.search(raw):
        return raw
    rest = _CRY_WORD.sub("", raw)
    rest = re.sub(r"^[\s,.!?-]+|\s+$", "", re.sub(r"\s+([.,!?])", r"\1", rest))
    rest = re.sub(r"(?i)\bmen[\s.,!?]*$", "", rest).strip()
    rest = re.sub(r"([.!?])[.!?]+", r"\1", rest)
    tag = "[sobbing] " if "[" not in rest else ""
    return f"{tag}{rest} Uu-hu-hu!".strip() if rest else "[sobbing] Uu-hu-hu, uu-hu-hu!"
