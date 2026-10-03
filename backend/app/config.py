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
    # Gemini TTS qimmat (~90% xarajat shundan chiqdi): 0 = o'chiq, N = bir kunda ko'pi bilan N ta so'rov (hozir yoqilgan, himoya chegarasi 200)
    gemini_tts_daily_limit: int = 200
    # Ovoz profili + rejissyor ko'rsatmalari + past temperature/seed (bir xil ohang uchun). Agar Gemini ko'rsatmani
    # ovoz chiqarib o'qib yuborsa, Render'da GEMINI_TTS_STYLE=0 qiling.
    gemini_tts_style: bool = True
    # VoiceLab (o'zbekcha TTS/STT). Manzillar rasmiy SDK (voicelab-sdk 0.1.0) manba kodidan olingan
    voicelab_api_key: str = ""
    voicelab_base: str = "https://api.voicelab.uz"
    # Bemor -> ovoz xaritasi (JSON), masalan {"buvi":{"voice_id":"...","speed":0.9}}. Bo'sh bemor Edge'da gapiradi
    voicelab_voices: str = "{}"
    voicelab_tts_path: str = "/v1/tts"
    voicelab_voices_path: str = "/v1/voices"
    voicelab_ticket_path: str = "/v1/ticket"
    debug_token: str = ""  # /tts_test uchun; bo'sh bo'lsa sinov yo'li o'chiq
    gemini_tts_models: str = "gemini-3.8-flash-lite-tts,gemini-3.8-flash-tts"
    azure_speech_key: str = ""
    azure_speech_region: str = ""


settings = Settings()
