import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class STTService:
    @staticmethod
    async def transcribe(audio_bytes: bytes) -> str:
        """
        Convert audio bytes to text using external API or fallback.
        """
        if settings.STT_API_URL:
            try:
                async with httpx.AsyncClient() as client:
                    files = {'file': ('audio.wav', audio_bytes, 'audio/wav')}
                    response = await client.post(settings.STT_API_URL, files=files, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    return data.get('text', '')
            except Exception as e:
                logger.error(f"External STT API failed: {e}")
                # Fallback to OpenAI Whisper or return empty
        
        # Mock/Fallback if no API or error
        try:
            import openai
            from openai import AsyncOpenAI
            import tempfile
            import os
            
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # OpenAI requires a file-like object with a filename
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
                
            with open(tmp_file_path, 'rb') as audio_file:
                transcription = await client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language="uz"
                )
            
            os.remove(tmp_file_path)
            return transcription.text
        except Exception as e:
            logger.error(f"Whisper fallback failed: {e}")
            return ""
