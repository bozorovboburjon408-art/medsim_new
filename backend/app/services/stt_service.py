import io
import os
import tempfile
import logging
import httpx
import speech_recognition as sr
from app.core.config import settings

logger = logging.getLogger(__name__)

class STTService:
    @staticmethod
    async def transcribe(audio_bytes: bytes) -> str:
        """
        Audio baytlarni o'zbek tilidagi matnga aylantirish (Google Speech Recognition / External API)
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        # 1. Tashqi STT API (agar sozlangan bo'lsa)
        if settings.STT_API_URL:
            try:
                async with httpx.AsyncClient() as client:
                    files = {'file': ('audio.wav', audio_bytes, 'audio/wav')}
                    response = await client.post(settings.STT_API_URL, files=files, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        text = data.get('text', '').strip()
                        if text:
                            return text
            except Exception as e:
                logger.debug(f"Tashqi STT API xatosi: {e}")

        # 2. Google Speech Recognition orqali O'zbek tili STT (uz-UZ)
        try:
            r = sr.Recognizer()
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True

            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name

            try:
                with sr.AudioFile(tmp_path) as source:
                    audio_data = r.record(source)
                    text = r.recognize_google(audio_data, language='uz-UZ')
                    if text and text.strip():
                        logger.info(f"✅ STT (uz-UZ) natijasi: '{text}'")
                        return text.strip()
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        except sr.UnknownValueError:
            logger.debug("Google STT audio ichidagi so'zlarni taniy olmadi (shovqin yoki sukunat)")
        except Exception as e:
            logger.debug(f"Google STT audio konvertatsiya xatosi: {e}")

        # 3. OpenAI Whisper (agar kalit kiritilgan bo'lsa)
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    tmp_file.write(audio_bytes)
                    tmp_path = tmp_file.name

                with open(tmp_path, 'rb') as audio_file:
                    transcription = await client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="uz"
                    )
                os.remove(tmp_path)
                if transcription.text:
                    return transcription.text.strip()
            except Exception as e:
                logger.debug(f"Whisper fallback xatosi: {e}")

        return ""
