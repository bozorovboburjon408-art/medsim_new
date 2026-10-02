import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    @staticmethod
    async def synthesize(text: str, voice_config: dict = None) -> bytes:
        """
        Matnni ovozga aylantirish:
        1. Tashqi O'zbek tili TTS API (agar sozlangan bo'lsa)
        2. OpenAI TTS modeli (avtomatik fallback)
        """
        voice_config = voice_config or {}
        
        # 1. Maxsus O'zbek tili TTS API
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
                logger.error(f"External TTS API failed: {e}")
                
        # 2. OpenAI TTS Fallback
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-place") and not settings.OPENAI_API_KEY.startswith("sk-test"):
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                
                # Qahramon yoshi va jinsiga qarab ovoz tanlash
                pitch = voice_config.get("pitch", 1.0)
                if pitch < 0.9:
                    voice = "onyx"     # Bobo (og'ir erkak ovozi)
                elif pitch > 1.2:
                    voice = "nova"     # Bola (sho'x, ingichka ovoz)
                else:
                    voice = "shimmer"  # Homilador ayol (mayin ayol ovozi)
                
                response = await client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text
                )
                return response.content
            except Exception as e:
                logger.error(f"OpenAI TTS fallback failed: {e}")

        logger.warning("TTS API sozlanmagan, bo'sh audio qaytarildi.")
        return b""
