import json
import logging
import re
import time
from typing import AsyncIterator

import httpx

from . import vertex
from .config import settings

TIMEOUT = 30
log = logging.getLogger("uvicorn.error")
_no_think: set[str] = set()  # thinkingLevel'ni tanimagan modellar

# Sekin yoki xato bergan model qisqa vaqtga o'tkazib yuboriladi (qayta-qayta kutib qolmaslik uchun)
_bad: dict[str, float] = {}


def mark_bad(model: str, seconds: float = 90) -> None:
    _bad[model] = time.monotonic() + seconds


def healthy_first(models: list[str]) -> list[str]:
    now = time.monotonic()
    ok = [m for m in models if _bad.get(m, 0) <= now]
    return ok + [m for m in models if m not in ok]  # buzuqlari oxirida, lekin zaxira sifatida qoladi


def chat_models() -> list[str]:
    raw = settings.vertex_models if vertex.enabled() else settings.gemini_models
    return [m.strip() for m in raw.split(",") if m.strip()]


def eval_models() -> list[str]:
    raw = settings.vertex_eval_models if vertex.enabled() else settings.gemini_eval_models
    return [m.strip() for m in raw.split(",") if m.strip()]


async def target(model: str, method: str) -> tuple[str, dict]:
    """Gemini so'rovi manzili va sarlavhalari: Vertex AI (kredit) yoki AI Studio (kalit)."""
    if vertex.enabled():
        return await vertex.target(model, method)
    return (f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}",
            {"x-goog-api-key": settings.gemini_api_key})


def think_config(model: str) -> dict | None:
    """Vertex 2.5 modellari thinkingBudget bilan o'chiriladi (tezlik/narx); AI Studio uchun thinkingLevel."""
    if vertex.enabled():
        return None if "pro" in model else {"thinkingBudget": 0}
    return {"thinkingLevel": settings.gemini_thinking} if settings.gemini_thinking else None


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
    models = chat_models()
    last = "model ro'yxati bo'sh"
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        for model in models:
            url, hdr = await target(model, "generateContent")
            r = await c.post(url, json=body, headers=hdr)
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
    if vertex.enabled():  # Vertex'da ro'yxat alohida; sozlangan modellarni ko'rsatamiz
        return sorted(set(chat_models() + eval_models()))
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
    models = chat_models()
    if model and re.fullmatch(r"[a-z0-9.\-]+", model):  # sinov uchun tanlangan model birinchi
        models = [model] + [m for m in models if m != model]
    last = "model ro'yxati bo'sh"
    tries = info.setdefault("tries", []) if info is not None else []
    # Tez almashtirish: 8 soniya ichida javob bermagan model o'tkazib yuboriladi
    models = healthy_first(models)
    fast = httpx.Timeout(connect=4, read=6, write=5, pool=5)
    async with httpx.AsyncClient(timeout=fast) as c:
        for model in models:
            url, hdr = await target(model, "streamGenerateContent?alt=sse")
            got, failed = False, False
            # "O'ylash" darajasi past qilinadi (tezroq va arzonroq); model tanimasa, bir marta o'ylashsiz qayta uriniladi
            think = think_config(model)
            variants = [True, False] if (think and model not in _no_think) else [False]
            for use_think in variants:
                b = body
                if use_think:
                    b = {**body, "generationConfig": {**body["generationConfig"],
                                                      "thinkingConfig": think}}
                retry_plain = False
                try:
                    async with c.stream("POST", url, json=b, headers=hdr) as r:
                        if r.status_code == 400 and use_think:
                            _no_think.add(model)
                            log.warning("%s o'ylash sozlamasini qabul qilmadi, usiz davom etiladi", model)
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


STT_PROMPT = ("Transcribe the speech in this audio verbatim. The speaker talks Uzbek; write in Uzbek Latin script "
              "(o', g', sh, ch, ng). Write ONLY the words that are actually spoken. Do NOT add, repeat, complete or invent any words, "
              "and do not add greetings or vocabulary that you did not hear. If the audio is silent, unclear or only noise, "
              "output an empty string. Output only the transcript text.")

_STT_LEAK = ("qon bosimi, qand, dori",)  # eski prompt ro'yxati sizib chiqsa, bo'sh deb hisoblanadi


async def transcribe(audio: bytes, mime: str = "audio/wav", model: str | None = None) -> tuple[str, str]:
    """Gemini audio tushunishi orqali ovozdan matn. Qaytaradi: (matn, ishlatilgan model)."""
    import base64
    body = {
        "contents": [{"role": "user", "parts": [
            {"text": STT_PROMPT},
            {"inlineData": {"mimeType": mime, "data": base64.b64encode(audio).decode()}}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 300,
                             **({"thinkingConfig": {"thinkingBudget": 0}} if vertex.enabled() else {})},
    }
    models = [m.strip() for m in settings.stt_models.split(",") if m.strip()]
    if model and re.fullmatch(r"[a-z0-9.\-]+", model):
        models = [model] + [m for m in models if m != model]
    last = "model ro'yxati bo'sh"
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=20, write=10, pool=5)) as c:
        for m in healthy_first(models):
            url, hdr = await target(m, "generateContent")
            try:
                r = await c.post(url, json=body, headers=hdr)
            except httpx.TimeoutException:
                last = f"{m}: timeout"; mark_bad(m, 60); continue
            if r.status_code >= 400:
                last = f"{m}: {r.status_code} {r.text[:200]}"; mark_bad(m); continue
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
                if any(x in text.lower() for x in _STT_LEAK):
                    text = ""
                return text, m
            except (KeyError, IndexError, ValueError):
                return "", m  # nutq topilmadi
    raise RuntimeError(f"Ovozdan matn xatosi. Oxirgisi: {last}")
