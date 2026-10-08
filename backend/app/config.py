from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_thinking: str = "low"  # AI "o'ylash" darajasi (bo'sh = standart). Tezlik va narxga ta'sir qiladi
    # vergul bilan ajratilgan zanjir: birinchisi limitga yetsa keyingisiga o'tadi
    gemini_models: str = "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-2.5-flash-lite,gemini-2.5-flash"
    # Baholash kamdan-kam chaqiriladi (suhbat boshiga 1 marta)
    gemini_eval_models: str = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"
    tts_provider: str = "edge"  # "edge" (bepul va asosiy), "gemini", "azure"
    gemini_tts_models: str = "gemini-2.5-flash-preview-tts"
    debug_token: str = ""  # /voice_lab (ovoz sozlash sahifasi) uchun; bo'sh bo'lsa o'chiq
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    google_tts_api_key: str = ""  # Google Cloud Text-to-Speech API kaliti ($300 Cloud krediti uchun); faqat laboratoriya


settings = Settings()
