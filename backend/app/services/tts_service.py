import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    @staticmethod
    async def synthesize(text: str, voice_config: dict = None) -> bytes:
        """
        Synthesize text into audio bytes using external TTS API.
        """
        voice_config = voice_config or {}
        if settings.TTS_API_URL:
            try:
                async with httpx.AsyncClient() as client:
                    payload = {
                        "text": text,
                        "voice_id": voice_config.get("voice_id", "default"),
                        "pitch": voice_config.get("pitch", 1.0),
                        "speed": voice_config.get("speed", 1.0)
                    }
                    response = await client.post(settings.TTS_API_URL, json=payload, timeout=15.0)
                    response.raise_for_status()
                    return response.content
            except Exception as e:
                logger.error(f"TTS API failed: {e}")
                
        # Mock implementation returning empty bytes if real TTS is unavailable
        logger.warning("TTS API not configured or failed, returning dummy bytes.")
        return b""
