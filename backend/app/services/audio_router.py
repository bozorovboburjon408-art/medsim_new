"""
MedSim Audio Router
ESP32 Audio Speaker modullari bilan Wi-Fi orqali muloqot qilish.
ESP32_Audio_Speaker.ino protokollariga (GET /status, GET /stream, GET /set, POST /play) to'liq moslashtirilgan.
"""
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AudioRouter:
    @staticmethod
    async def send_to_mannequin(ip_address: str, port: int, audio_data: bytes, content_type: str = 'audio/wav') -> bool:
        """
        ESP32 manikenga Wi-Fi orqali audio yuborish.
        """
        url = f"http://{ip_address}:{port}/play"
        headers = {"Content-Type": content_type}
        
        for attempt in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, content=audio_data, headers=headers, timeout=5.0)
                    if response.status_code == 200:
                        logger.info(f"✅ Audio {ip_address}:{port} manikeniga muvaffaqiyatli uzatildi")
                        return True
                    else:
                        logger.warning(f"Urinish {attempt+1}: Maniken kodi {response.status_code}")
            except httpx.RequestError as e:
                logger.debug(f"Urinish {attempt+1}: {ip_address}:{port} ga ulanish xatosi - {e}")
                
        return False

    @staticmethod
    async def trigger_stream_url(ip_address: str, port: int, stream_url: str) -> bool:
        """
        ESP32_Audio_Speaker.ino dagi GET /stream?url=... orqali audioni ishga tushirish
        """
        url = f"http://{ip_address}:{port}/stream"
        params = {"url": stream_url}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=3.0)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"ESP32 stream trigger xatosi ({ip_address}): {e}")
            return False

    @staticmethod
    async def set_volume(ip_address: str, port: int, vol: int = 80, bass: int = 0, treble: int = 0) -> bool:
        """
        ESP32 kalonkasi ovozini sozlash: GET /set?vol=80&bass=0&treble=0
        """
        url = f"http://{ip_address}:{port}/set"
        params = {"vol": vol, "bass": bass, "treble": treble}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=3.0)
                return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def check_health(ip_address: str, port: int) -> bool:
        """
        ESP32 kalonka holatini tekshirish (/status yoki /health orqali)
        """
        try:
            async with httpx.AsyncClient() as client:
                # 1. ESP32_Audio_Speaker.ino /status endpointi
                res = await client.get(f"http://{ip_address}:{port}/status", timeout=1.5)
                if res.status_code == 200:
                    return True
                
                # 2. Fallback /health
                res = await client.get(f"http://{ip_address}:{port}/health", timeout=1.5)
                return res.status_code == 200
        except Exception:
            return False
