import json
import logging
import os
import time
from typing import Any

from .config import settings

log = logging.getLogger("uvicorn.error")

_credentials: Any = None
_token_cache: dict[str, Any] = {"token": None, "expiry": 0.0}


def get_vertex_credentials():
    """Service Account JSON orqali Google OAuth2 credentials qaytaradi."""
    global _credentials
    if _credentials is not None:
        return _credentials

    # 1. GOOGLE_APPLICATION_CREDENTIALS_JSON orqali (Render uchun)
    raw_json = settings.google_application_credentials_json.strip()
    if raw_json:
        try:
            from google.oauth2 import service_account

            info = json.loads(raw_json)
            _credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            log.info("Vertex AI: Service Account JSON yuklandi (project_id=%s)", _credentials.project_id)
            return _credentials
        except Exception as e:
            log.error("Vertex AI Service Account JSON tahlilida xatolik: %s", e)

    # 2. Fayl yo'li orqali (GOOGLE_APPLICATION_CREDENTIALS)
    cred_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if cred_file and os.path.exists(cred_file):
        try:
            from google.oauth2 import service_account

            _credentials = service_account.Credentials.from_service_account_file(
                cred_file,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            log.info("Vertex AI: Service Account fayldan yuklandi (%s)", cred_file)
            return _credentials
        except Exception as e:
            log.error("Vertex AI Service Account fayl xatosi: %s", e)

    # 3. Standart muhit
    try:
        import google.auth

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        _credentials = creds
        return _credentials
    except Exception:
        return None


def get_project_id() -> str:
    """Project ID ni aniqlaydi."""
    if settings.vertex_project_id:
        return settings.vertex_project_id.strip()

    creds = get_vertex_credentials()
    if creds and hasattr(creds, "project_id") and creds.project_id:
        return creds.project_id

    # JSON matnidan qidirib ko'rish
    raw_json = settings.google_application_credentials_json.strip()
    if raw_json:
        try:
            data = json.loads(raw_json)
            if "project_id" in data:
                return data["project_id"]
        except Exception:
            pass

    return ""


def get_access_token() -> str:
    """Google Cloud OAuth2 Bearer tokenini qaytaradi (avtomatik yangilanadi)."""
    global _token_cache
    now = time.time()
    if _token_cache["token"] and _token_cache["expiry"] > (now + 60):
        return _token_cache["token"]

    creds = get_vertex_credentials()
    if not creds:
        raise RuntimeError("Google Cloud credentials topilmadi. GOOGLE_APPLICATION_CREDENTIALS_JSON ni tekshiring.")

    from google.auth.transport.requests import Request

    creds.refresh(Request())
    _token_cache["token"] = creds.token
    # expiry odatda 3600 soniya
    expiry = getattr(creds, "expiry", None)
    if expiry:
        _token_cache["expiry"] = expiry.timestamp()
    else:
        _token_cache["expiry"] = now + 3500

    return _token_cache["token"]


def is_vertex_configured() -> bool:
    """Vertex AI orqali ishlash imkoniyati bormi?"""
    return bool(settings.google_application_credentials_json.strip() or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
