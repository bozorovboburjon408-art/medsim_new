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
    tts_provider: str = "edge"
    debug_token: str = ""  # /voice_lab (ovoz sozlash sahifasi) uchun; bo'sh bo'lsa o'chiq
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    # Vertex AI (Google Cloud, $300 kredit): service account JSON matni. Bo'sh bo'lsa AI Studio kaliti ishlatiladi
    google_sa_json: str = ""
    vertex_project: str = ""  # bo'sh bo'lsa JSON ichidagi project_id olinadi
    vertex_location: str = "global"
    vertex_models: str = "gemini-2.5-flash-lite,gemini-2.5-flash"
    vertex_eval_models: str = "gemini-2.5-flash,gemini-2.5-pro"
    vertex_tts_models: str = "gemini-2.5-flash-tts,gemini-2.5-pro-tts,gemini-2.5-flash-preview-tts,gemini-2.5-pro-preview-tts"
    stt_models: str = "gemini-2.5-flash,gemini-2.5-flash-lite"  # Gemini orqali ovozdan matn (Vertex'da)
    gemini_tts_model: str = "gemini-2.5-flash-tts"  # tts="gemini" rejimi uchun (Vertex yoki AI Studio)
    chat_tts: str = "edge_only"  # standart suhbat ovozi: edge_only (bepul). Premium (eleven) ilovada sozlamalardan yoqiladi
    elevenlabs_api_key: str = ""
    eleven_stt_model: str = "scribe_v1"
    chirp_region: str = "us-central1"
    chirp_model: str = "chirp_2"
    eleven_tts_model: str = "eleven_multilingual_v2"
    google_tts_api_key: str = ""  # Google Cloud Text-to-Speech API kaliti ($300 Cloud krediti uchun); faqat laboratoriya


settings = Settings()
