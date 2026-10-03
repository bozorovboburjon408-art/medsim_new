import asyncio
import base64
import re
import json
import time
import uuid
from typing import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
import io
import logging
import wave
from xml.sax.saxutils import escape

import edge_tts
import httpx

from .config import settings
from .patients import Patient

log = logging.getLogger("uvicorn.error")


def gemini_budget_ok() -> bool:
    """Gemini TTS kunlik limiti: 0 bo'lsa o'chiq. Ruxsat berilsa hisoblagichni oshiradi."""
    limit = settings.gemini_tts_daily_limit
    if limit <= 0:
        return False
    day = time.strftime("%Y-%m-%d", time.gmtime())
    if _gem_count["day"] != day:
        _gem_count["day"], _gem_count["n"] = day, 0
    if _gem_count["n"] >= limit:
        return False
    _gem_count["n"] += 1
    return True


def clean_for_tts(text: str) -> str:
    """Ovozga berilmaydigan belgilarni olib tashlaydi. Ayniqsa ikki nuqta va qo'shtirnoq: Gemini TTS ularni
    'spiker: gap' deb o'qib, boshqa ovozga o'tib ketishi mumkin. O'zbekcha tutuq belgilari (o', g', ʻ, ’) saqlanadi."""
    t = re.sub(r"[*_#`~<>\[\](){}]", " ", text)
    for q in ("«", "»", '"', "“", "”", "„"):
        t = t.replace(q, " ")
    t = re.sub(r"\s*[:;]\s*", ", ", t)
    t = re.sub(r"\s[—–-]+\s", ", ", t)
    t = re.sub(r"\.{2,}|…", ".", t)
    t = re.sub(r"\s*,(\s*,)+", ",", t)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"\s+([.,!?])", r"\1", t)

_gem_count = {"day": "", "n": 0}
_tts_bad: dict[str, float] = {}  # sekin/xato TTS modellari vaqtincha oxiriga o'tkaziladi


async def synthesize(text: str, p: Patient, provider: str | None = None) -> tuple[bytes, str, str]:
    """Matnni ovozga aylantiradi. Qaytaradi: (audio baytlari, format 'mp3'|'wav', ishlatilgan provayder)."""
    text = clean_for_tts(text)
    prov = provider if provider in ("edge", "gemini", "azure", "voicelab") else settings.tts_provider
    if prov == "voicelab":
        cfg = voicelab_cfg(p.id)
        if not cfg.get("voice_id"):  # bu bemor uchun VoiceLab ovozi tanlanmagan (masalan bola): Edge
            return await _edge(text, p), "mp3", "edge"
        try:
            audio, ct = await voicelab_tts(text, cfg["voice_id"], cfg.get("speed"))
            return audio, ("wav" if "wav" in ct or "wave" in ct else "mp3"), "voicelab"
        except Exception as e:  # ovoz to'xtab qolmasin
            log.warning("VoiceLab xatosi, Edge'ga o'tildi: %s", e)
            return await _edge(text, p), "mp3", "edge (voicelab xato)"
    if prov == "gemini":
        try:
            return await _gemini(text, p), "wav", "gemini"
        except Exception as e:  # ovoz to'xtab qolmasin: Edge'ga o'tamiz
            log.warning("Gemini TTS xatosi, Edge'ga o'tildi: %s", e)
            return await _edge(text, p), "mp3", "edge (gemini xato)"
    if prov == "azure":
        return await _azure(text, p), "mp3", "azure"
    return await _edge(text, p), "mp3", "edge"


def _pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


async def _gemini(text: str, p: Patient) -> bytes:
    prompt = text  # uslub ko'rsatmasi qo'shilmaydi: Gemini uni ovoz chiqarib o'qib yuboradi
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": p.gemini_voice}}},
        },
    }
    last = "model ro'yxati bo'sh"
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=15, write=5, pool=5)) as c:
        for model in [m.strip() for m in settings.gemini_tts_models.split(",") if m.strip()]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                r = await c.post(url, json=body, headers={"x-goog-api-key": settings.gemini_api_key})
            except httpx.TimeoutException:
                last = f"{model}: timeout"; continue
            if r.status_code >= 400:
                last = f"{model}: {r.status_code} {r.text[:150]}"; continue
            try:
                part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
                rate = 24000
                if "rate=" in part.get("mimeType", ""):
                    rate = int(part["mimeType"].split("rate=")[1].split(";")[0])
                return _pcm_to_wav(base64.b64decode(part["data"]), rate)
            except (KeyError, IndexError, ValueError):
                last = f"{model}: audio qaytmadi"
    raise RuntimeError(last)


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


async def benchmark(text: str) -> dict:
    """Gemini TTS modellarini oddiy va oqimli usulda, Edge'ni esa solishtirish uchun o'lchaydi."""
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}},
        },
    }
    hdr = {"x-goog-api-key": settings.gemini_api_key}
    models = [m.strip() for m in settings.gemini_tts_models.split(",") if m.strip()]
    base = "https://generativelanguage.googleapis.com/v1beta/models/"
    tmo = httpx.Timeout(connect=5, read=60, write=5, pool=5)

    async def plain(model: str) -> dict:
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=tmo) as c:
                r = await c.post(f"{base}{model}:generateContent", json=body, headers=hdr)
            out = {"status": r.status_code, "sec": round(time.perf_counter() - t0, 2)}
            if r.status_code == 200:
                d = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                out["audio_sec"] = round(len(base64.b64decode(d)) / 48000, 1)
            else:
                out["error"] = r.text[:200]
            return out
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "sec": round(time.perf_counter() - t0, 2)}

    async def stream(model: str) -> dict:
        t0 = time.perf_counter(); first = None; chunks = 0; pcm = 0
        try:
            async with httpx.AsyncClient(timeout=tmo) as c:
                async with c.stream("POST", f"{base}{model}:streamGenerateContent?alt=sse", json=body, headers=hdr) as r:
                    if r.status_code != 200:
                        return {"status": r.status_code, "error": (await r.aread()).decode()[:200]}
                    async for line in r.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        try:
                            d = json.loads(line[5:])["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                        except (KeyError, IndexError, ValueError):
                            continue
                        chunks += 1; pcm += len(base64.b64decode(d))
                        if first is None:
                            first = round(time.perf_counter() - t0, 2)
            return {"first_chunk_sec": first, "total_sec": round(time.perf_counter() - t0, 2),
                    "chunks": chunks, "audio_sec": round(pcm / 48000, 1)}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "sec": round(time.perf_counter() - t0, 2)}

    async def edge() -> dict:
        t0 = time.perf_counter()
        try:
            from .patients import PATIENTS
            a = await _edge(text, PATIENTS["buvi"])
            return {"sec": round(time.perf_counter() - t0, 2), "bytes": len(a)}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    jobs = [edge()] + [f(m) for m in models for f in (plain, stream)]
    res = await asyncio.gather(*jobs)
    out = {"text_chars": len(text), "edge": res[0]}
    for i, m in enumerate(models):
        out[m] = {"plain": res[1 + 2 * i], "stream": res[2 + 2 * i]}
    return out


_gem_nodet = False  # temperature/seed qabul qilinmasa, ularsiz davom etamiz


async def gemini_stream(text: str, p: Patient) -> AsyncIterator[bytes]:
    """Gemini TTS oqimi: 24 kHz, 16-bit, mono PCM bo'laklari (juft uzunlikda) kelishi bilan qaytariladi.
    Bir xil ohang uchun: tuzilgan prompt (profil + ko'rsatmalar + transcript), past temperature va qat'iy seed."""
    global _gem_nodet
    text = clean_for_tts(text)
    prompt = structured_prompt(text, p.tts_style) if settings.gemini_tts_style else text
    cfg = {
        "responseModalities": ["AUDIO"],
        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": p.gemini_voice}}},
    }
    hdr = {"x-goog-api-key": settings.gemini_api_key}
    last = "model ro'yxati bo'sh"
    tmo = httpx.Timeout(connect=4, read=6, write=5, pool=5)
    models = [m.strip() for m in settings.gemini_tts_models.split(",") if m.strip()]
    now = time.monotonic()
    models = [m for m in models if _tts_bad.get(m, 0) <= now] + [m for m in models if _tts_bad.get(m, 0) > now]
    deadline = time.monotonic() + 12  # birinchi tovush uchun umumiy chegara
    # Ovoz uzunligi chegarasi (bayt, 24kHz 16-bit mono = 48000 bayt/s): matndan keskin oshib ketsa, bu cho'zilib
    # qolgan (nosoz) generatsiya, uzamiz. O'zbekcha nutq ~14 belgi/s, 2 baravar zaxira bilan.
    max_bytes = int(max(5.0, len(text) * 0.15 + 3.0) * 48000)
    sent = 0
    for model in models:
        if time.monotonic() > deadline:
            last = f"{last} | vaqt chegarasi"
            break
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
        got, carry, failed = False, b"", False
        for det in ([True, False] if (settings.gemini_tts_deterministic and not _gem_nodet) else [False]):
            gc = {**cfg, "temperature": 0.2, "seed": 7} if det else cfg
            body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gc}
            retry_plain = False
            try:
                async with httpx.AsyncClient(timeout=tmo) as c:
                    async with c.stream("POST", url, json=body, headers=hdr) as r:
                        if r.status_code == 400 and det:
                            _gem_nodet = True
                            log.warning("Gemini TTS temperature/seed ni qabul qilmadi, ularsiz davom etiladi")
                            retry_plain = True
                        elif r.status_code != 200:
                            last = f"{model}: {r.status_code} {(await r.aread()).decode()[:150]}"
                            _tts_bad[model] = time.monotonic() + 60
                            failed = True
                        else:
                            async for line in r.aiter_lines():
                                if not line.startswith("data:"):
                                    continue
                                try:
                                    raw = base64.b64decode(
                                        json.loads(line[5:])["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
                                except (KeyError, IndexError, ValueError):
                                    continue
                                raw = carry + raw
                                carry = raw[len(raw) // 2 * 2:]
                                raw = raw[:len(raw) // 2 * 2]
                                if raw:
                                    got = True
                                    sent += len(raw)
                                    if sent > max_bytes:
                                        log.warning("Gemini TTS ovozi me'yordan uzun (%.1fs, matn %d belgi): uzildi",
                                                    sent / 48000, len(text))
                                        return
                                    yield raw
            except httpx.TimeoutException:
                if got:
                    return
                last = f"{model}: timeout"
                _tts_bad[model] = time.monotonic() + 120
                failed = True
            if retry_plain:
                continue
            break
        if got:
            return
        if not failed:
            last = f"{model}: audio qaytmadi"
            _tts_bad[model] = time.monotonic() + 60
    raise RuntimeError(last)


GEMINI_VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe", "Autonoe",
    "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi",
    "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird",
    "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
]


def structured_prompt(text: str, style: str) -> str:
    """Gemini TTS uchun tavsiya etilgan format: profil va ko'rsatmalar alohida, o'qiladigani faqat TRANSCRIPT."""
    if not style.strip():
        return text
    return (
        f"# AUDIO PROFILE\n{style.strip()}\n\n"
        "### DIRECTOR'S NOTES\n"
        "Keep exactly the same voice, pitch, pace and mood from the first word to the last, "
        "and use the same calm, steady delivery regardless of the emotion of the words. "
        "Speak natural conversational Uzbek. Read ONLY the transcript below. "
        "Never read the profile or these notes aloud.\n\n"
        f"#### TRANSCRIPT\n{text}"
    )


async def gemini_once(text: str, voice: str, style: str = "", deterministic: bool = True) -> bytes:
    """Sinov (laboratoriya) uchun: butun javobni bir so'rovda ovozlashtiradi, WAV qaytaradi."""
    voice = voice if voice in GEMINI_VOICES else "Kore"
    cfg = {
        "responseModalities": ["AUDIO"],
        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
    }
    variants = [{**cfg, "temperature": 0.2, "seed": 7}, cfg] if deterministic else [cfg]
    prompt = structured_prompt(clean_for_tts(text), style)
    last = "model ro'yxati bo'sh"
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=40, write=5, pool=5)) as c:
        for model in [m.strip() for m in settings.gemini_tts_models.split(",") if m.strip()]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            for gc in variants:
                r = await c.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gc},
                                 headers={"x-goog-api-key": settings.gemini_api_key})
                if r.status_code == 400 and gc is not cfg:
                    continue  # temperature/seed qabul qilinmadi: ularsiz urinib ko'ramiz
                if r.status_code >= 400:
                    last = f"{model}: {r.status_code} {r.text[:150]}"
                    break
                try:
                    part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
                    rate = int(part["mimeType"].split("rate=")[1].split(";")[0]) if "rate=" in part.get("mimeType", "") else 24000
                    return _pcm_to_wav(base64.b64decode(part["data"]), rate)
                except (KeyError, IndexError, ValueError):
                    last = f"{model}: audio qaytmadi"
                    break
    raise RuntimeError(last)


def voicelab_cfg(patient_id: str) -> dict:
    try:
        return json.loads(settings.voicelab_voices or "{}").get(patient_id, {}) or {}
    except ValueError:
        return {}


async def voicelab_tts(text: str, voice_id: str = "", speed: float | None = None) -> tuple[bytes, str]:
    """VoiceLab TTS (tasvirga ko'ra: POST /tts, JSON {text, language, voice_id}, Bearer kalit).
    Qaytaradi: (audio baytlari, content-type). Xatoda VoiceLab javobini ko'rsatuvchi RuntimeError."""
    if not settings.voicelab_api_key:
        raise RuntimeError("VOICELAB_API_KEY sozlanmagan")
    body = {"text": clean_for_tts(text), "language": "uz"}
    if voice_id:
        body["voice_id"] = voice_id
    if speed:
        body["speed"] = max(0.5, min(2.0, float(speed)))
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=30, write=5, pool=5)) as c:
        r = await c.post(settings.voicelab_base.rstrip("/") + settings.voicelab_tts_path, json=body,
                         headers={"Authorization": f"Bearer {settings.voicelab_api_key}",
                                  "Idempotency-Key": uuid.uuid4().hex})
    ct = r.headers.get("content-type", "")
    if r.status_code >= 400:
        raise RuntimeError(f"VoiceLab {r.status_code}: {r.text[:300]}")
    if ct.startswith("audio/") or ct == "application/octet-stream":
        return r.content, ("audio/wav" if "octet" in ct else ct)
    try:  # ba'zi API'lar JSON ichida base64 yoki havola qaytaradi
        j = r.json()
        for k in ("audio_base64", "audio", "data"):
            if isinstance(j.get(k), str) and len(j[k]) > 100:
                return base64.b64decode(j[k]), "audio/wav"
        for k in ("url", "audio_url"):
            if isinstance(j.get(k), str):
                async with httpx.AsyncClient(timeout=30) as c2:
                    r2 = await c2.get(j[k])
                return r2.content, r2.headers.get("content-type", "audio/wav")
    except ValueError:
        pass
    raise RuntimeError(f"VoiceLab kutilmagan javob ({ct}): {r.text[:300]}")


async def voicelab_voices() -> str:
    """VoiceLab ovozlar ro'yxatini xom ko'rinishda qaytaradi (tuzilmasini ko'rish uchun)."""
    if not settings.voicelab_api_key:
        raise RuntimeError("VOICELAB_API_KEY sozlanmagan")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(settings.voicelab_base.rstrip("/") + settings.voicelab_voices_path,
                        params={"language": "uz"},
                        headers={"Authorization": f"Bearer {settings.voicelab_api_key}"})
    return f"HTTP {r.status_code}\n{r.text[:6000]}"


async def voicelab_open():
    """Realtime TTS: ticket olinadi (POST /v1/ticket), WebSocket ochiladi, 'ready' hodisasi kutiladi.
    Qaytaradi: (websocket, sample_rate). Format 16-bit mono PCM bo'lmasa, xato (REST zaxirasi ishlaydi)."""
    from websockets.asyncio.client import connect
    if not settings.voicelab_api_key:
        raise RuntimeError("VOICELAB_API_KEY sozlanmagan")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=10, write=5, pool=5)) as c:
        r = await c.post(settings.voicelab_base.rstrip("/") + settings.voicelab_ticket_path,
                         json={"transport": "websocket", "service": "tts"},
                         headers={"Authorization": f"Bearer {settings.voicelab_api_key}"})
    if r.status_code >= 400:
        raise RuntimeError(f"VoiceLab ticket {r.status_code}: {r.text[:200]}")
    j = r.json()
    u = urlparse(j["websocket_url"])
    url = urlunparse(u._replace(query=urlencode(parse_qsl(u.query, keep_blank_values=True) + [("ticket", j["ticket"])])))
    ws = await connect(url, open_timeout=5, max_size=None)
    try:
        ev = json.loads(await asyncio.wait_for(ws.recv(), 8))
        if ev.get("event") == "error":
            raise RuntimeError(f"VoiceLab realtime xatosi: {ev.get('message')}")
        if ev.get("event") != "ready":
            raise RuntimeError(f"VoiceLab 'ready' o'rniga: {str(ev)[:150]}")
        fmt = str(ev.get("format", "")).lower()
        if int(ev.get("channels", 1)) != 1 or not ("pcm" in fmt or "s16" in fmt or "l16" in fmt):
            raise RuntimeError(f"Realtime format qo'llab-quvvatlanmaydi: {ev}")
        return ws, int(ev.get("sample_rate", 24000))
    except Exception:
        await ws.close()
        raise


async def voicelab_synth(ws, text: str, voice_id: str, speed: float | None = None) -> AsyncIterator[bytes]:
    """Ochiq WebSocket orqali bitta matnni ovozlashtiradi: PCM bo'laklarini (juft uzunlikda) qaytaradi."""
    msg = {"text": clean_for_tts(text), "language": "uz", "voice_id": voice_id}
    if speed:
        msg["speed"] = max(0.5, min(2.0, float(speed)))
    await ws.send(json.dumps(msg))
    carry = b""
    while True:
        m = await asyncio.wait_for(ws.recv(), 15)
        if isinstance(m, bytes):
            raw = carry + m
            carry = raw[len(raw) // 2 * 2:]
            raw = raw[:len(raw) // 2 * 2]
            if raw:
                yield raw
            continue
        ev = json.loads(m)
        if ev.get("event") == "done":
            return
        if ev.get("event") == "error":
            raise RuntimeError(f"VoiceLab: {ev.get('message')} ({ev.get('code')})")


async def voicelab_voice_list() -> list[dict]:
    """Ovozlar ro'yxati (laboratoriyadagi tanlov uchun): [{id, name, desc}]."""
    if not settings.voicelab_api_key:
        raise RuntimeError("VOICELAB_API_KEY sozlanmagan")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(settings.voicelab_base.rstrip("/") + settings.voicelab_voices_path,
                        params={"language": "uz"},
                        headers={"Authorization": f"Bearer {settings.voicelab_api_key}"})
    if r.status_code >= 400:
        raise RuntimeError(f"VoiceLab {r.status_code}: {r.text[:200]}")
    return [{"id": v.get("id", ""), "name": v.get("display_name") or v.get("name", ""),
             "desc": (v.get("short_description") or "")[:60], "gender": v.get("gender") or ""}
            for v in r.json().get("data", [])]
