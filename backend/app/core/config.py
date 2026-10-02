"""
MedSim Backend Configuration
Environment variables dan o'qiladi (.env yoki Render dashboard).
OpenAI, DeepSeek yoki istalgan OpenAI-mos API'larni qo'llab-quvvatlaydi.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL ulanish
    DATABASE_URL: str = "postgresql+asyncpg://medsim:medsim123@localhost:5432/medsim_db"

    # AI API kaliti (OpenAI yoki DeepSeek)
    OPENAI_API_KEY: str = "sk-placeholder"
    
    # AI API Base URL (DeepSeek uchun: https://api.deepseek.com)
    OPENAI_BASE_URL: str = ""
    
    # Model nomi (masalan: deepseek-chat yoki gpt-4o-mini)
    AI_MODEL: str = ""

    # O'zbek tili STT/TTS API (ixtiyoriy)
    STT_API_URL: str = ""
    TTS_API_URL: str = ""

    # Wi-Fi tarmoq (ESP32 uchun)
    WIFI_NETWORK_PREFIX: str = "192.168.1"

    # Audio fayllar
    AUDIO_PRESETS_DIR: str = "static/audio_presets"

    # Debug rejimi
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
