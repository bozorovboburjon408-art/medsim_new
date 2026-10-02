import asyncio
import base64
import json
import time
import io
import logging
import wave
from xml.sax.saxutils import escape

import edge_tts
import httpx

from .config import settings
from .patients import Patient

log = logging.getLogger("uvicorn.error")


async def synthesize(text: str, p: Patient, provider: str | None = None) -> tuple[bytes, str, str]:
    """Matnni ovozga aylantiradi. Qaytaradi: (audio baytlari, format 'mp3'|'wav', ishlatilgan provayder)."""
    prov = provider if provider in ("edge", "gemini", "azure") else settings.tts_provider
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
            "temperature": 0.4,
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
