import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AudioRouter:
    @staticmethod
    async def send_to_mannequin(ip_address: str, port: int, audio_data: bytes, content_type: str = 'audio/wav') -> bool:
        """
        Sends audio data to the ESP32 mannequin over Wi-Fi.
        """
        url = f"http://{ip_address}:{port}/play"
        headers = {"Content-Type": content_type}
        
        for attempt in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, content=audio_data, headers=headers, timeout=5.0)
                    if response.status_code == 200:
                        logger.info(f"Successfully sent audio to mannequin at {ip_address}:{port}")
                        return True
                    else:
                        logger.warning(f"Attempt {attempt+1}: Mannequin returned status {response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"Attempt {attempt+1}: Failed to connect to mannequin at {ip_address}:{port} - {e}")
                
        return False
        
    @staticmethod
    async def check_health(ip_address: str, port: int) -> bool:
        url = f"http://{ip_address}:{port}/health"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=2.0)
                return response.status_code == 200
        except:
            return False
