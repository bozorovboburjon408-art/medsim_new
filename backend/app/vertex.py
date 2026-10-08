"""Gemini'ni Google Cloud (Vertex AI) orqali chaqirish: $300 Cloud krediti shu yo'l bilan yechiladi.
Service account JSON faqat Render muhitida (GOOGLE_SA_JSON) turadi."""
import asyncio
import json
import logging
import time

from .config import settings

log = logging.getLogger("uvicorn.error")
_creds = None
_info: dict = {}


def enabled() -> bool:
    return bool(settings.google_sa_json.strip())


def _load():
    global _creds, _info
    if _creds is None:
        from google.oauth2 import service_account
        _info = json.loads(settings.google_sa_json)
        _creds = service_account.Credentials.from_service_account_info(
            _info, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return _creds


def project() -> str:
    _load()
    return settings.vertex_project.strip() or _info.get("project_id", "")


def _refresh_sync() -> str:
    from google.auth.transport.requests import Request
    c = _load()
    if not c.valid:
        c.refresh(Request())
    return c.token


async def token() -> str:
    return await asyncio.to_thread(_refresh_sync)


def base() -> str:
    loc = settings.vertex_location.strip() or "global"
    host = "aiplatform.googleapis.com" if loc == "global" else f"{loc}-aiplatform.googleapis.com"
    return f"https://{host}/v1/projects/{project()}/locations/{loc}/publishers/google/models"


async def target(model: str, method: str) -> tuple[str, dict]:
    """(url, headers) — method: generateContent yoki streamGenerateContent?alt=sse"""
    return f"{base()}/{model}:{method}", {"Authorization": f"Bearer {await token()}"}
