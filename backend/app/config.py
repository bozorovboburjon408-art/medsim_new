from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    # vergul bilan ajratilgan zanjir: birinchisi limitga yetsa keyingisiga o'tadi
    gemini_models: str = "gemini-3.8-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"
    tts_provider: str = "edge"
    debug_token: str = ""  # /tts_test uchun; bo'sh bo'lsa sinov yo'li o'chiq
    gemini_tts_models: str = "gemini-3.8-flash-lite-tts,gemini-3.8-flash-tts,gemini-3.1-flash-tts-preview,gemini-2.5-flash-preview-tts"
    azure_speech_key: str = ""
    azure_speech_region: str = ""


settings = Settings()
