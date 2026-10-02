import logging
import base64
import edge_tts
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    @staticmethod
    async def synthesize(text: str, mannequin_slug: str = "homilador", voice_config: dict = None) -> bytes:
        """
        Matnni tabiiy va sof O'zbek tili ovoziga aylantirish (Microsoft Edge Neural TTS):
        - homilador (Gulnora opa): uz-UZ-MadinaNeural (mayin, muloyim ayol ovozi)
        - bobo: uz-UZ-SardorNeural (vazmin qariya ovozi)
        - bola: uz-UZ-MadinaNeural (baland tonli bola ovozi)
        - chaqaloq: ovoz sintezi qilinmaydi (MP3 presetlar ishlatiladi)
        """
        clean_text = text.replace('*', '').strip()
        if not clean_text:
            return b""

        # 1. Edge Neural TTS (Eng yuqori sifatli sof O'zbek tili ovozi)
        voice = "uz-UZ-MadinaNeural"
        pitch = "+0Hz"
        rate = "+0%"

        if mannequin_slug == "bobo":
            # Salomat buvi (75 yoshli onaxon)
            voice = "uz-UZ-MadinaNeural"
            pitch = "-6Hz"
            rate = "-15%"
        elif mannequin_slug == "homilador":
            # Gulnora opa (28 yoshli homilador ayol)
            voice = "uz-UZ-MadinaNeural"
            pitch = "+0Hz"
            rate = "-4%"
        elif mannequin_slug == "bola":
            # Jasurbek (5 yosh) va onasi Nilufar opa
            voice = "uz-UZ-MadinaNeural"
            pitch = "+5Hz"
            rate = "-2%"
        elif mannequin_slug == "chaqaloq":
            return b""

        try:
            communicate = edge_tts.Communicate(clean_text, voice=voice, pitch=pitch, rate=rate)
            audio_bytes = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes.extend(chunk["data"])
            if audio_bytes:
                return bytes(audio_bytes)
        except Exception as e:
            logger.warning(f"Edge TTS xatosi: {e}, tashqi TTS tekshirilmoqda")

        # 2. Tashqi O'zbek tili TTS API (agar mavjud bo'lsa)
        if settings.TTS_API_URL:
            try:
                async with httpx.AsyncClient() as client:
                    payload = {
                        "text": clean_text,
                        "voice_id": (voice_config or {}).get("voice_id", "default"),
                        "pitch": (voice_config or {}).get("pitch", 1.0),
                        "speed": (voice_config or {}).get("speed", 1.0)
                    }
                    response = await client.post(settings.TTS_API_URL, json=payload, timeout=15.0)
                    if response.status_code == 200:
                        return response.content
            except Exception as e:
                logger.error(f"External TTS API xatosi: {e}")

        return b""

    @staticmethod
    def to_base64(audio_bytes: bytes) -> str:
        """Audio baytlarni Base64 stringga o'tkazish"""
        if not audio_bytes:
            return ""
        return base64.b64encode(audio_bytes).decode("utf-8")

