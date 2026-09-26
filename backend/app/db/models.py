"""
MedSim ORM Modellari
PostgreSQL init.sql jadvallariga to'liq mos keladi.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    Float, Text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, INET, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Mannequin(Base):
    """Manikenlar jadvali — har bir qahramon profili"""
    __tablename__ = "mannequins"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    age_range = Column(String(20))
    character_description = Column(Text)
    voice_config = Column(JSONB)
    ip_address = Column(String(50), default="192.168.1.10")
    esp32_port = Column(Integer, default=80)
    allowed_topics = Column(ARRAY(Text))
    forbidden_topics = Column(ARRAY(Text))
    system_prompt = Column(Text, nullable=False)
    use_preset_audio = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    scenarios = relationship("Scenario", back_populates="mannequin", cascade="all, delete-orphan")
    scripts = relationship("ScriptQA", back_populates="mannequin", cascade="all, delete-orphan")
    audio_presets = relationship("AudioPreset", back_populates="mannequin", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="mannequin", cascade="all, delete-orphan")


class Scenario(Base):
    """Ssenariylar jadvali — har bir manikenning mashg'ulot ssenariylari"""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    mannequin_id = Column(Integer, ForeignKey("mannequins.id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    difficulty_level = Column(
        String(20),
        CheckConstraint("difficulty_level IN ('oson', 'o''rta', 'qiyin')")
    )
    expected_actions = Column(JSONB)  # {"actions": ["salomlashish", "tekshirish", ...]}
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    mannequin = relationship("Mannequin", back_populates="scenarios")
    scripts = relationship("ScriptQA", back_populates="scenario")
    sessions = relationship("Session", back_populates="scenario")


class ScriptQA(Base):
    """Savol-javob skriptlari — trigger keywords va tayyor javoblar"""
    __tablename__ = "script_qa"

    id = Column(Integer, primary_key=True, index=True)
    mannequin_id = Column(Integer, ForeignKey("mannequins.id", ondelete="CASCADE"))
    scenario_id = Column(Integer, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=True)
    trigger_keywords = Column(ARRAY(Text), nullable=False)  # ["qandaysiz", "ahvolingiz"]
    trigger_pattern = Column(String(500))  # Regex pattern
    question_template = Column(Text)  # Kutilayotgan savol namunasi
    answer_template = Column(Text, nullable=False)  # Javob shabloni
    emotion = Column(String(50), default="oddiy")  # oddiy, xavotirli, og'riqli, qo'rqqan
    priority = Column(Integer, default=0)  # Kattaroq = birinchi tekshiriladi
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    mannequin = relationship("Mannequin", back_populates="scripts")
    scenario = relationship("Scenario", back_populates="scripts")


class AudioPreset(Base):
    """Tayyor audio fayllar — chaqaloq uchun yig'lash, kulish MP3'lari"""
    __tablename__ = "audio_presets"

    id = Column(Integer, primary_key=True, index=True)
    mannequin_id = Column(Integer, ForeignKey("mannequins.id", ondelete="CASCADE"))
    trigger_type = Column(String(50), nullable=False)  # yiglash, kulish, uhh, nola
    file_path = Column(String(500), nullable=False)
    duration_seconds = Column(Float)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    mannequin = relationship("Mannequin", back_populates="audio_presets")


class Session(Base):
    """Mashg'ulot sessiyalari — hamshiraning har bir mashg'uloti"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    mannequin_id = Column(Integer, ForeignKey("mannequins.id", ondelete="CASCADE"))
    scenario_id = Column(Integer, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=True)
    nurse_name = Column(String(100))
    started_at = Column(TIMESTAMP, server_default=func.now())
    ended_at = Column(TIMESTAMP, nullable=True)
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)

    # Relationships
    mannequin = relationship("Mannequin", back_populates="sessions")
    scenario = relationship("Scenario", back_populates="sessions")
    logs = relationship("SessionLog", back_populates="session", cascade="all, delete-orphan")


class SessionLog(Base):
    """Sessiya loglari — har bir suhbat qaydnomasi"""
    __tablename__ = "session_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    speaker = Column(
        String(20), nullable=False,
        # nurse = hamshira, mannequin = manikenning javobi
    )
    message_text = Column(Text)
    audio_file_path = Column(String(500))
    response_time_ms = Column(Integer)  # Javob berish vaqti (ms)
    emotion_detected = Column(String(50))
    matched_script_id = Column(Integer, ForeignKey("script_qa.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="logs")
    matched_script = relationship("ScriptQA")
