"""Google Cloud Speech-to-Text v2 (Chirp) orqali o'zbekcha ovozdan matn. Kalit: GOOGLE_SA_JSON (vertex.py bilan umumiy)."""
import httpx

from . import vertex
from .config import settings

# Tibbiy so'zlar: model shularga moyil bo'ladi (so'z maslahatlari)
HINTS = ["qon bosimi", "qand", "qandli diabet", "gijja", "harorat", "hojatxona", "uvishish", "yara", "shifokor",
         "tez yordam", "dori", "homilador", "bosim", "qorin og'riyapti", "qichiyapti", "uyqu", "holsizlik", "oyoq",
         "bosh og'rig'i", "nafas", "ko'ngil aynishi", "ishtaha", "insulin", "ro'za"]


async def stt(audio: bytes, mime: str = "audio/wav", hints: bool = True) -> str:
    region = settings.chirp_region.strip() or "us-central1"
    host = "speech.googleapis.com" if region == "global" else f"{region}-speech.googleapis.com"
    cfg: dict = {"autoDecodingConfig": {}, "languageCodes": ["uz-UZ"], "model": settings.chirp_model.strip() or "chirp_2"}
    if hints:
        cfg["adaptation"] = {"phraseSets": [{"inlinePhraseSet": {"boost": 10, "phrases": [{"value": h, "boost": 10} for h in HINTS]}}]}
    url = f"https://{host}/v2/projects/{vertex.project()}/locations/{region}/recognizers/_:recognize"
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=30, write=15, pool=5)) as c:
        r = await c.post(url, headers={"Authorization": f"Bearer {await vertex.token()}"},
                         json={"config": cfg, "content": __import__("base64").b64encode(audio).decode()})
    if r.status_code >= 400:
        raise RuntimeError(f"Chirp {r.status_code}: {r.text[:300]}")
    parts = [(x.get("alternatives") or [{}])[0].get("transcript", "") for x in r.json().get("results", [])]
    return " ".join(p.strip() for p in parts if p.strip())
