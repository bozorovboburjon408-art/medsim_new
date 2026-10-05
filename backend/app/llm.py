import json
import logging
import re
import time
from typing import AsyncIterator

import httpx

from .config import settings
from . import vertex_auth

TIMEOUT = 30
log = logging.getLogger("uvicorn.error")
_no_think: set[str] = set()  # thinkingLevel'ni tanimagan modellar

# Sekin yoki xato bergan model qisqa vaqtga o'tkazib yuboriladi (qayta-qayta kutib qolmaslik uchun)
_bad: dict[str, float] = {}


def get_gemini_endpoint(model: str, stream: bool = False) -> tuple[str, dict[str, str]]:
    """Vertex AI sozlangan bo'lsa Vertex AI orqali (300$ bonusdan), aks holda AI Studio (API Key) orqali."""
    method = "streamGenerateContent?alt=sse" if stream else "generateContent"
    if vertex_auth.is_vertex_configured():
        project = vertex_auth.get_project_id()
        location = settings.vertex_location
        token = vertex_auth.get_access_token()
        # Vertex AI da mavjud rasmiy modellar: gemini-2.5-flash, gemini-2.5-flash-lite
        if "pro" in model:
            vertex_model = "gemini-2.5-pro"
        elif "lite" in model:
            vertex_model = "gemini-2.5-flash-lite"
        else:
            vertex_model = "gemini-2.5-flash"

        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{vertex_model}:{method}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        return url, headers

    # Standart AI Studio
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}"
    headers = {"x-goog-api-key": settings.gemini_api_key}
    return url, headers


def mark_bad(model: str, seconds: float = 90) -> None:
    _bad[model] = time.monotonic() + seconds


def healthy_first(models: list[str]) -> list[str]:
    now = time.monotonic()
    ok = [m for m in models if _bad.get(m, 0) <= now]
    return ok + [m for m in models if m not in ok]  # buzuqlari oxirida, lekin zaxira sifatida qoladi


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
            url, headers = get_gemini_endpoint(model, stream=False)
            r = await c.post(url, json=body, headers=headers)
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
    models = healthy_first(models)
    fast = httpx.Timeout(connect=4, read=6, write=5, pool=5)
    async with httpx.AsyncClient(timeout=fast) as c:
        for model in models:
            url, headers = get_gemini_endpoint(model, stream=True)
            got, failed = False, False
            # "O'ylash" darajasi past qilinadi (tezroq va arzonroq); model tanimasa, bir marta o'ylashsiz qayta uriniladi
            variants = [True, False] if (settings.gemini_thinking and model not in _no_think) else [False]
            for use_think in variants:
                b = body
                if use_think:
                    b = {**body, "generationConfig": {**body["generationConfig"],
                                                      "thinkingConfig": {"thinkingLevel": settings.gemini_thinking}}}
                retry_plain = False
                try:
                    async with c.stream("POST", url, json=b, headers=headers) as r:
                        if r.status_code == 400 and use_think:
                            _no_think.add(model)
                            log.warning("%s thinkingLevel=%s ni qabul qilmadi, o'ylash sozlamasisiz davom etiladi",
                                        model, settings.gemini_thinking)
                            retry_plain = True
                        elif r.status_code >= 400:
                            last = f"{model}: {r.status_code} {(await r.aread()).decode()[:200]}"
                            tries.append(f"{model} {r.status_code}")
                            mark_bad(model)
                            failed = True
                        else:
                            buf = ""
                            async for line in r.aiter_lines():
                                if not line.startswith("data:"):
                                    continue
                                try:
                                    ev = json.loads(line[5:])
                                except ValueError:
                                    continue
                                um = ev.get("usageMetadata")
                                if um and info is not None:
                                    info["usage"] = "AI tokenlar: kirish {} · chiqish {} · o'ylash {}".format(
                                        um.get("promptTokenCount", 0), um.get("candidatesTokenCount", 0),
                                        um.get("thoughtsTokenCount", 0))
                                try:
                                    parts = ev["candidates"][0]["content"]["parts"]
                                except (KeyError, IndexError):
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
                            if info is not None and info.get("usage"):
                                log.info("llm %s %s", model, info["usage"])
                except httpx.TimeoutException:
                    if got:
                        return  # javob boshlangan edi, bor narsani beramiz
                    last = f"{model}: timeout"
                    tries.append(f"{model} timeout")
                    mark_bad(model, 120)
                    failed = True
                if retry_plain:
                    continue
                break
            if got:
                return
            if not failed:
                last = f"{model}: bo'sh javob"
                tries.append(f"{model} bo'sh")
    raise RuntimeError(f"Hamma Gemini modellari muvaffaqiyatsiz. Oxirgisi: {last}")
