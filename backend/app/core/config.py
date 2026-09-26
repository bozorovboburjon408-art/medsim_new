"""
MedSim Backend Configuration
Environment variables dan o'qiladi (.env yoki Render dashboard).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL ulanish
    # Render: postgres://user:pass@host/db
    # Lokal:  postgresql+asyncpg://user:pass@localhost/db
    DATABASE_URL: str = "postgresql+asyncpg://medsim:medsim123@localhost:5432/medsim_db"

    # OpenAI API kaliti
    OPENAI_API_KEY: str = "sk-placeholder"

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
        """
        Render.com 'postgres://' beradi, asyncpg esa 'postgresql+asyncpg://' kutadi.
        Bu property avtomatik konvertatsiya qiladi.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
