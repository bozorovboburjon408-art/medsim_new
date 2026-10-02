"""
MedSim Backend Configuration
DeepSeek API to'liq integratsiya qilindi.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL ulanish
    DATABASE_URL: str = "postgresql+asyncpg://medsim:medsim123@localhost:5432/medsim_db"

    # DeepSeek AI API kaliti
    OPENAI_API_KEY: str = "sk-42874f7bcf1f44adb2988b9ae0bc39cc"
    
    # DeepSeek Server manzili
    OPENAI_BASE_URL: str = "https://api.deepseek.com"
    
    # DeepSeek modeli
    AI_MODEL: str = "deepseek-chat"

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
