import httpx

from .config import settings

TIMEOUT = 30


async def generate(system: str, history: list[dict]) -> str:
    """history: [{"role": "user"|"assistant", "content": str}] — user = hamshira."""
    if settings.llm_provider == "claude":
        return await _claude(system, history)
    return await _gemini(system, history)


async def _gemini(system: str, history: list[dict]) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.gemini_model}:generateContent")
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in history
        ],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300},
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(url, json=body, headers={"x-goog-api-key": settings.gemini_api_key})
        r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _claude(system: str, history: list[dict]) -> str:
    body = {"model": settings.claude_model, "max_tokens": 300, "system": system, "messages": history}
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages", json=body,
            headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"})
        r.raise_for_status()
    return r.json()["content"][0]["text"].strip()
