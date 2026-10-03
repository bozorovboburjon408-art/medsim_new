from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_thinking: str = "low"  # AI "o'ylash" darajasi (bo'sh = standart). Tezlik va narxga ta'sir qiladi
    # vergul bilan ajratilgan zanjir: birinchisi limitga yetsa keyingisiga o'tadi
    gemini_models: str = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    # Baholash kamdan-kam chaqiriladi (suhbat boshiga 1 marta), shuning uchun sifatliroq model
    gemini_eval_models: str = "gemini-3.8-flash,gemini-3.5-flash-lite"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"
    tts_provider: str = "edge"  # "edge" (bepul va asosiy), "gemini" (pullik audio), "azure"
    gemini_tts_models: str = "gemini-2.5-flash-preview-tts,gemini-3.8-flash-lite-tts,gemini-3.8-flash-tts,gemini-3.1-flash-tts-preview"  # audio output modellar
    debug_token: str = ""  # /voice_lab (ovoz sozlash sahifasi) uchun; bo'sh bo'lsa o'chiq
    azure_speech_key: str = ""
    azure_speech_region: str = ""


settings = Settings()
