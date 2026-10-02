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
        ESP32 manikenga Wi-Fi yoki mDNS orqali to'g'ridan-to'g'ri audio yuborish (POST /play).
        """
        hosts = [ip_address, "medsim-speaker.local"] if ip_address else ["medsim-speaker.local"]
        headers = {"Content-Type": content_type}

        for host in hosts:
            if not host:
                continue
            url = f"http://{host}:{port}/play"
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, content=audio_data, headers=headers, timeout=3.5)
                    if response.status_code == 200:
                        logger.info(f"✅ Audio {host}:{port} ga muvaffaqiyatli yetkazildi")
                        return True
            except Exception as e:
                logger.debug(f"Audio uzatish xatosi ({host}): {e}")

        return False

    @staticmethod
    async def send_command_to_esp(ip_address: str, port: int, endpoint: str, params: dict = None) -> bool:
        """
        ESP32 moduliga to'g'ridan-to'g'ri buyruq yuborish (IP yoki mDNS orqali)
        """
        hosts = [ip_address, "medsim-speaker.local"] if ip_address else ["medsim-speaker.local"]
        for host in hosts:
            if not host:
                continue
            url = f"http://{host}:{port}{endpoint}"
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(url, params=params, timeout=2.0)
                    if res.status_code == 200:
                        return True
            except Exception:
                pass
        return False

    @staticmethod
    async def check_health(ip_address: str, port: int) -> bool:
        """
        ESP32 kalonka holatini tekshirish (/status yoki /health orqali)
        """
        if not ip_address:
            return False
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"http://{ip_address}:{port}/status", timeout=1.5)
                if res.status_code == 200:
                    return True
                res = await client.get(f"http://{ip_address}:{port}/health", timeout=1.5)
                return res.status_code == 200
        except Exception:
            return False


