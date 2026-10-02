import json
import re
from typing import AsyncIterator

import httpx

from .config import settings

TIMEOUT = 30


async def generate(system: str, history: list[dict]) -> str:
    """history: [{"role": "user"|"assistant", "content": str}] — user = hamshira."""
    if settings.llm_provider == "claude":
        return await _claude(system, history)
    return await _gemini(system, history)


async def _gemini(system: str, history: list[dict]) -> str:
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in history
        ],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
    }
    models = [m.strip() for m in settings.gemini_models.split(",") if m.strip()]
    last = "model ro'yxati bo'sh"
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            r = await c.post(url, json=body, headers={"x-goog-api-key": settings.gemini_api_key})
            if r.status_code in (404, 429, 500, 503):  # limit/yo'q/band: keyingi modelga o'tamiz
                last = f"{model}: {r.status_code} {r.text[:200]}"
                continue
            if r.status_code >= 400:
                last = f"{model}: {r.status_code} {r.text[:200]}"
                continue
            data = r.json()
            try:
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            except (KeyError, IndexError):
                text = ""
            if text:
                return text
            last = f"{model}: bo'sh javob ({str(data)[:200]})"
    raise RuntimeError(f"Hamma Gemini modellari muvaffaqiyatsiz. Oxirgisi: {last}")


async def list_gemini_models() -> list[str]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                        headers={"x-goog-api-key": settings.gemini_api_key})
        r.raise_for_status()
    return [m["name"].removeprefix("models/") for m in r.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])]


async def _claude(system: str, history: list[dict]) -> str:
    body = {"model": settings.claude_model, "max_tokens": 300, "system": system, "messages": history}
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages", json=body,
            headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"})
        r.raise_for_status()
    return r.json()["content"][0]["text"].strip()


_SENT = re.compile(r"(.+?[.!?…]+)(?:\s+|$)", re.S)


def _split(buf: str) -> tuple[list[str], str]:
    """Tugagan gaplarni ajratadi; tugallanmagan qoldiqni qaytaradi."""
    out, pos = [], 0
    for m in _SENT.finditer(buf):
        if m.end() == len(buf) and not buf[-1].isspace() and m.group(0) == m.group(1):
            break  # oxirgi belgi: keyingi chunk "5." ni "5.5" ga aylantirishi mumkin
        out.append(m.group(1).strip()); pos = m.end()
    return out, buf[pos:]


async def stream_sentences(system: str, history: list[dict], info: dict | None = None,
                           model: str | None = None) -> AsyncIterator[str]:
    """Javobni tayyor bo'lgan gaplar bo'yicha qaytaradi (birinchi gap tez keladi)."""
    if settings.llm_provider == "claude":
        text = await _claude(system, history)
        sents, rest = _split(text + " ")
        for s in sents + ([rest.strip()] if rest.strip() else []):
            yield s
        return
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in history
        ],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
    }
    models = [m.strip() for m in settings.gemini_models.split(",") if m.strip()]
    if model and re.fullmatch(r"[a-z0-9.\-]+", model):  # sinov uchun tanlangan model birinchi
        models = [model] + [m for m in models if m != model]
    last = "model ro'yxati bo'sh"
    tries = info.setdefault("tries", []) if info is not None else []
    # Tez almashtirish: 8 soniya ichida javob bermagan model o'tkazib yuboriladi
    fast = httpx.Timeout(connect=5, read=8, write=5, pool=5)
    async with httpx.AsyncClient(timeout=fast) as c:
        for model in models:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{model}:streamGenerateContent?alt=sse")
            got = False
            try:
                async with c.stream("POST", url, json=body,
                                    headers={"x-goog-api-key": settings.gemini_api_key}) as r:
                    if r.status_code >= 400:
                        last = f"{model}: {r.status_code} {(await r.aread()).decode()[:200]}"
                        tries.append(f"{model} {r.status_code}")
                        continue
                    buf = ""
                    async for line in r.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        try:
                            parts = json.loads(line[5:])["candidates"][0]["content"]["parts"]
                        except (KeyError, IndexError, ValueError):
                            continue
                        buf += "".join(p.get("text", "") for p in parts if not p.get("thought"))
                        sents, buf = _split(buf)
                        for s in sents:
                            if s:
                                got = True
                                if info is not None:
                                    info["model"] = model
                                yield s
                    if buf.strip():
                        got = True
                        if info is not None:
                            info["model"] = model
                        yield buf.strip()
            except httpx.TimeoutException:
                if got:
                    return  # javob boshlangan edi, bor narsani beramiz
                last = f"{model}: timeout"
                tries.append(f"{model} timeout")
                continue
            if got:
                return
            last = f"{model}: bo'sh javob"
            tries.append(f"{model} bo'sh")
    raise RuntimeError(f"Hamma Gemini modellari muvaffaqiyatsiz. Oxirgisi: {last}")
