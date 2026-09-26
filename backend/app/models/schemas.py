"""
MedSim Pydantic Schemas
API request/response modellari — frontend bilan muloqot uchun.
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime


# =====================
# Mannequin Schemas
# =====================
class MannequinResponse(BaseModel):
    """Manikenning to'liq ma'lumoti"""
    id: int
    slug: str
    name: str
    age_range: Optional[str] = None
    character_description: Optional[str] = None
    voice_config: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    esp32_port: int = 80
    allowed_topics: Optional[list[str]] = None
    forbidden_topics: Optional[list[str]] = None
    use_preset_audio: bool = False
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MannequinListResponse(BaseModel):
    """Manikenlar ro'yxati"""
    items: List[MannequinResponse]
    total: int


# =====================
# Focus Request
# =====================
class FocusRequest(BaseModel):
    """Hamshira qaysi manikenni tanlayotganini bildirish"""
    slug: str  # mannequin slug: 'bobo', 'homilador', 'bola', 'chaqaloq'


# =====================
# Speech Schemas
# =====================
class SpeechResponse(BaseModel):
    """Ovozli so'rov javobini qaytarish"""
    text: str  # AI javob matni
    user_text: Optional[str] = None  # STT natijasi — hamshira nima dedi
    audio_url: Optional[str] = None  # Audio fayl URL (agar mavjud bo'lsa)
    status: str  # success, stt_failed, ai_error, no_audio
    emotion: Optional[str] = None  # oddiy, xavotirli, og'riqli, qo'rqqan
    matched_script_id: Optional[int] = None  # Mos kelgan skript ID'si


# =====================
# Scenario Schemas
# =====================
class ScenarioResponse(BaseModel):
    """Ssenariy ma'lumoti"""
    id: int
    mannequin_id: int
    title: str
    description: Optional[str] = None
    difficulty_level: Optional[str] = None
    expected_actions: Optional[dict[str, Any]] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


# =====================
# Session Schemas
# =====================
class SessionCreate(BaseModel):
    """Yangi sessiya boshlash"""
    mannequin_id: int
    scenario_id: Optional[int] = None
    nurse_name: Optional[str] = None


class SessionResponse(BaseModel):
    """Sessiya ma'lumoti"""
    id: int
    mannequin_id: int
    scenario_id: Optional[int] = None
    nurse_name: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    score: Optional[int] = None
    feedback: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionLogResponse(BaseModel):
    """Sessiya log yozuvi"""
    id: int
    session_id: int
    speaker: str  # nurse | mannequin
    message_text: Optional[str] = None
    response_time_ms: Optional[int] = None
    emotion_detected: Optional[str] = None
    matched_script_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================
# ESP32 Health
# =====================
class ESP32HealthResponse(BaseModel):
    """ESP32 modulining holati"""
    slug: str
    name: str
    ip_address: str
    is_online: bool
    uptime: Optional[int] = None
    free_memory: Optional[int] = None
