"""
MedSim API Routes
Barcha endpoint'lar — hamshira plansheti va tizim orasidagi aloqa.
"""
import re
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import Mannequin, Scenario, ScriptQA, AudioPreset, Session, SessionLog
from app.models.schemas import (
    MannequinResponse,
    MannequinListResponse,
    FocusRequest,
    ChatRequest,
    SpeechResponse,
    ScenarioResponse,
    SessionCreate,
    SessionResponse,
    SessionLogResponse,
)
from app.services.stt_service import STTService
from app.services.tts_service import TTSService
from app.services.ai_engine import AIEngine
from app.services.audio_router import AudioRouter

logger = logging.getLogger(__name__)
router = APIRouter()
ai_engine = AIEngine()

# =====================
# Sessiya holati (in-memory, dev uchun)
# Production'da Redis yoki DB ga o'tkaziladi
# =====================
active_focus: dict = {
    "mannequin_slug": None,
    "mannequin_id": None,
    "session_id": None,
}


# =====================
# MANNEQUIN ENDPOINTS
# =====================

def _get_fallback_mannequins() -> list[Mannequin]:
    from app.db.init_db import INITIAL_MANNEQUINS
    items = []
    for idx, m in enumerate(INITIAL_MANNEQUINS, start=1):
        items.append(
            Mannequin(
                id=idx,
                slug=m["slug"],
                name=m["name"],
                age_range=m["age_range"],
                character_description=m["character_description"],
                voice_config=m["voice_config"],
                ip_address=m["ip_address"],
                esp32_port=m["esp32_port"],
                allowed_topics=m["allowed_topics"],
                forbidden_topics=m["forbidden_topics"],
                system_prompt=m["system_prompt"],
                use_preset_audio=m["use_preset_audio"],
                is_active=True
            )
        )
    return items

def _get_fallback_mannequin_by_slug(slug: str) -> Optional[Mannequin]:
    for m in _get_fallback_mannequins():
        if m.slug == slug:
            return m
    return None

def _get_fallback_scripts_for_mannequin(mannequin: Mannequin) -> list[ScriptQA]:
    from app.db.init_db import INITIAL_SCRIPTS
    scripts = []
    for idx, s in enumerate(INITIAL_SCRIPTS, start=1):
        if s.get("mannequin_slug") == mannequin.slug:
            scripts.append(
                ScriptQA(
                    id=idx,
                    mannequin_id=mannequin.id,
                    trigger_keywords=s.get("trigger_keywords", []),
                    trigger_pattern=s.get("trigger_pattern", ""),
                    question_template=s.get("question_template", ""),
                    answer_template=s.get("answer_template", ""),
                    emotion=s.get("emotion", "oddiy"),
                    priority=s.get("priority", 0)
                )
            )
    return scripts


@router.get("/api/mannequins", response_model=MannequinListResponse)
async def list_mannequins(db: AsyncSession = Depends(get_db)):
    """Barcha faol manikenlar ro'yxati"""
    if db is not None:
        try:
            result = await db.execute(
                select(Mannequin).where(Mannequin.is_active == True).order_by(Mannequin.id)
            )
            items = result.scalars().all()
            if items:
                return MannequinListResponse(items=items, total=len(items))
        except Exception as e:
            logger.warning(f"DB dan manikenlarni olishda ogohlantirish: {e}")

    fallback_items = _get_fallback_mannequins()
    return MannequinListResponse(items=fallback_items, total=len(fallback_items))


@router.get("/api/mannequins/{slug}", response_model=MannequinResponse)
async def get_mannequin(slug: str, db: AsyncSession = Depends(get_db)):
    """Bitta manikenning to'liq ma'lumoti"""
    if db is not None:
        try:
            result = await db.execute(select(Mannequin).where(Mannequin.slug == slug))
            mannequin = result.scalar_one_or_none()
            if mannequin:
                return mannequin
        except Exception as e:
            logger.warning(f"DB mannequin select xatosi: {e}")

    fallback_m = _get_fallback_mannequin_by_slug(slug)
    if fallback_m:
        return fallback_m
    raise HTTPException(status_code=404, detail=f"'{slug}' nomli manikenni topib bo'lmadi")


# =====================
# FOCUS ENDPOINT
# =====================

@router.post("/api/focus")
async def set_focus(req: FocusRequest, db: AsyncSession = Depends(get_db)):
    """Hamshira qaysi manikendga murojaat qilayotganini belgilash"""
    mannequin = None
    if db is not None:
        try:
            result = await db.execute(select(Mannequin).where(Mannequin.slug == req.slug))
            mannequin = result.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"DB focus xatosi: {e}")

    if not mannequin:
        mannequin = _get_fallback_mannequin_by_slug(req.slug)

    if not mannequin:
        raise HTTPException(status_code=404, detail=f"'{req.slug}' nomli manikenni topib bo'lmadi")

    active_focus["mannequin_slug"] = mannequin.slug
    active_focus["mannequin_id"] = mannequin.id
    logger.info(f"Fokus belgilandi: {mannequin.name} ({mannequin.slug})")

    return {
        "status": "success",
        "focused_mannequin": mannequin.slug,
        "name": mannequin.name
    }


# =====================
# CHAT & SPEECH ENDPOINTS
# =====================

@router.post("/api/chat", response_model=SpeechResponse)
async def process_chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Matnli yoki brauzer STT orqali kelgan savolga DeepSeek AI javob qaytarish.
    """
    start_time = time.time()
    user_text = request.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Savol matni bo'sh bo'lmasligi kerak")

    mannequin_slug = request.mannequin_slug or active_focus.get("mannequin_slug")
    if not mannequin_slug:
        raise HTTPException(status_code=400, detail="Avval manikenni tanlang")

    mannequin = None
    if db is not None:
        try:
            result = await db.execute(select(Mannequin).where(Mannequin.slug == mannequin_slug))
            mannequin = result.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"DB chat mannequin query xatosi: {e}")

    if not mannequin:
        mannequin = _get_fallback_mannequin_by_slug(mannequin_slug)

    if not mannequin:
        raise HTTPException(status_code=404, detail="Tanlangan manikenni topib bo'lmadi")

    scenario = None
    session_id = request.session_id or active_focus.get("session_id")
    if session_id and db is not None:
        try:
            session_result = await db.execute(
                select(Session).where(Session.id == session_id)
            )
            session = session_result.scalar_one_or_none()
            if session and session.scenario_id:
                scenario_result = await db.execute(
                    select(Scenario).where(Scenario.id == session.scenario_id)
                )
                scenario = scenario_result.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"DB scenario query xatosi: {e}")

    all_scripts = []
    if db is not None and mannequin.id:
        try:
            scripts_result = await db.execute(
                select(ScriptQA)
                .where(ScriptQA.mannequin_id == mannequin.id)
                .order_by(desc(ScriptQA.priority))
            )
            all_scripts = scripts_result.scalars().all()
        except Exception as e:
            logger.warning(f"DB scripts query xatosi: {e}")

    if not all_scripts:
        all_scripts = _get_fallback_scripts_for_mannequin(mannequin)

    matched_scripts = _match_scripts(user_text, all_scripts)

    # DeepSeek / AI orqali javob generatsiya qilish
    ai_response = await ai_engine.generate_response(
        mannequin=mannequin,
        user_text=user_text,
        scenario=scenario,
        matched_scripts=matched_scripts
    )

    # Ovoz generatsiyasi (Sof O'zbek tili Edge Neural TTS)
    audio_url = None
    audio_base64 = None
    if mannequin.use_preset_audio:
        # Chaqaloq audio presetlari
        audio_data, audio_url = await _get_preset_audio(mannequin.id, ai_response.emotion, db)
        if audio_data:
            audio_base64 = TTSService.to_base64(audio_data)
            import asyncio
            asyncio.create_task(
                AudioRouter.send_to_mannequin(
                    str(mannequin.ip_address), mannequin.esp32_port, audio_data, "audio/mpeg"
                )
            )
    else:
        # Homilador, Bobo, Bola uchun jonli sof o'zbekcha ovoz
        try:
            audio_bytes = await TTSService.synthesize(ai_response.text, mannequin.slug, mannequin.voice_config)
            if audio_bytes:
                audio_base64 = TTSService.to_base64(audio_bytes)
                audio_url = f"/api/tts?slug={mannequin.slug}&text={user_text[:30]}"
                # ESP32 ga yuborish (agar ulangan bo'lsa)
                if mannequin.ip_address:
                    import asyncio
                    asyncio.create_task(
                        AudioRouter.send_to_mannequin(
                            str(mannequin.ip_address), mannequin.esp32_port, audio_bytes, "audio/mpeg"
                        )
                    )
        except Exception as e:
            logger.warning(f"TTS audio generatsiya xatosi: {e}")

    return SpeechResponse(
        text=ai_response.text,
        user_text=user_text,
        audio_url=audio_url,
        audio_base64=audio_base64,
        status="success",
        emotion=ai_response.emotion,
        matched_script_id=ai_response.used_script_id
    )


@router.post("/api/speech", response_model=SpeechResponse)
async def process_speech(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Asosiy endpoint — hamshiraning ovozini qabul qilib javob qaytaradi.
    
    Jarayon:
    1. Ovozni STT orqali matnga aylantirish
    2. DB'dan mos skriptlarni qidirish
    3. AI Engine orqali javob generatsiya qilish (guardrails bilan)
    4. TTS orqali audio yaratish (yoki chaqaloq uchun MP3 tanlash)
    5. Audio'ni ESP32'ga Wi-Fi orqali yuborish
    6. Sessiya logini saqlash
    """
    start_time = time.time()

    # Fokus tekshiruvi
    mannequin_slug = active_focus.get("mannequin_slug")
    if not mannequin_slug:
        raise HTTPException(status_code=400, detail="Avval manikenni tanlang (POST /api/focus)")

    # Manikenni DB'dan olish
    result = await db.execute(select(Mannequin).where(Mannequin.slug == mannequin_slug))
    mannequin = result.scalar_one_or_none()
    if not mannequin:
        raise HTTPException(status_code=404, detail="Tanlangan manikenni topib bo'lmadi")

    # Joriy ssenariyni olish (agar sessiya faol bo'lsa)
    scenario = None
    if active_focus.get("session_id"):
        session_result = await db.execute(
            select(Session).where(Session.id == active_focus["session_id"])
        )
        session = session_result.scalar_one_or_none()
        if session and session.scenario_id:
            scenario_result = await db.execute(
                select(Scenario).where(Scenario.id == session.scenario_id)
            )
            scenario = scenario_result.scalar_one_or_none()

    # Manikenning skriptlarini olish (prioritet bo'yicha tartiblangan)
    scripts_result = await db.execute(
        select(ScriptQA)
        .where(ScriptQA.mannequin_id == mannequin.id)
        .order_by(desc(ScriptQA.priority))
    )
    all_scripts = scripts_result.scalars().all()

    # ========== 1. STT — Ovozni matnga aylantirish ==========
    audio_bytes = await file.read()
    user_text = await STTService.transcribe(audio_bytes)
    if not user_text:
        logger.warning("STT natija qaytarmadi")
        return SpeechResponse(text="", user_text="", status="stt_failed")

    logger.info(f"STT natija: '{user_text}'")

    # ========== 2. Skript moslashtirish ==========
    matched_scripts = _match_scripts(user_text, all_scripts)

    # ========== 3. AI javob generatsiya qilish ==========
    ai_response = await ai_engine.generate_response(
        mannequin=mannequin,
        user_text=user_text,
        scenario=scenario,
        matched_scripts=matched_scripts
    )

    # ========== 4. Audio tayyorlash ==========
    audio_sent = False
    audio_url = None

    if mannequin.use_preset_audio:
        # Chaqaloq — tayyor MP3 faylni tanlash
        audio_data, audio_url = await _get_preset_audio(mannequin.id, ai_response.emotion, db)
        if audio_data:
            audio_sent = await AudioRouter.send_to_mannequin(
                str(mannequin.ip_address), mannequin.esp32_port, audio_data, "audio/mpeg"
            )
    else:
        # Boshqa manikenlar — TTS orqali ovoz generatsiya qilish
        voice_config = mannequin.voice_config or {}
        if voice_config.get("enabled", True):
            audio_data = await TTSService.synthesize(ai_response.text, voice_config)
            if audio_data:
                audio_sent = await AudioRouter.send_to_mannequin(
                    str(mannequin.ip_address), mannequin.esp32_port, audio_data
                )

    # ========== 5. Logni saqlash ==========
    response_time_ms = int((time.time() - start_time) * 1000)

    if active_focus.get("session_id"):
        # Hamshiraning savoli
        nurse_log = SessionLog(
            session_id=active_focus["session_id"],
            speaker="nurse",
            message_text=user_text,
            created_at=datetime.utcnow()
        )
        # Manikenning javobi
        mannequin_log = SessionLog(
            session_id=active_focus["session_id"],
            speaker="mannequin",
            message_text=ai_response.text,
            response_time_ms=response_time_ms,
            emotion_detected=ai_response.emotion,
            matched_script_id=ai_response.used_script_id,
            created_at=datetime.utcnow()
        )
        db.add(nurse_log)
        db.add(mannequin_log)
        await db.commit()

    # ========== 6. Javobni qaytarish ==========
    return SpeechResponse(
        text=ai_response.text,
        user_text=user_text,
        audio_url=audio_url,
        status="success" if audio_sent else "success_no_audio",
        emotion=ai_response.emotion,
        matched_script_id=ai_response.used_script_id
    )


# =====================
# SCENARIO ENDPOINTS
# =====================

@router.get("/api/scenarios/{mannequin_id}", response_model=List[ScenarioResponse])
async def list_scenarios(mannequin_id: int, db: AsyncSession = Depends(get_db)):
    """Manikenning ssenariylari ro'yxati"""
    result = await db.execute(
        select(Scenario)
        .where(Scenario.mannequin_id == mannequin_id, Scenario.is_active == True)
    )
    return result.scalars().all()


# =====================
# SESSION ENDPOINTS
# =====================

@router.post("/api/sessions", response_model=SessionResponse)
async def create_session(req: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Yangi mashg'ulot sessiyasini boshlash"""
    new_session = Session(
        mannequin_id=req.mannequin_id,
        scenario_id=req.scenario_id,
        nurse_name=req.nurse_name
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    active_focus["session_id"] = new_session.id
    logger.info(f"Yangi sessiya boshlandi: #{new_session.id}")

    return new_session


@router.post("/api/sessions/{session_id}/end")
async def end_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Mashg'ulot sessiyasini yakunlash"""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    session.ended_at = datetime.utcnow()
    await db.commit()

    if active_focus.get("session_id") == session_id:
        active_focus["session_id"] = None

    logger.info(f"Sessiya yakunlandi: #{session_id}")
    return {"status": "success", "session_id": session_id}


@router.get("/api/sessions/{session_id}/logs", response_model=List[SessionLogResponse])
async def get_session_logs(session_id: int, db: AsyncSession = Depends(get_db)):
    """Sessiya loglarini olish"""
    result = await db.execute(
        select(SessionLog)
        .where(SessionLog.session_id == session_id)
        .order_by(SessionLog.created_at)
    )
    return result.scalars().all()


# =====================
# ESP32 HEALTH CHECK
# =====================

@router.get("/api/health/{slug}")
async def check_mannequin_health(slug: str, db: AsyncSession = Depends(get_db)):
    """ESP32 modulining online/offline holatini tekshirish"""
    result = await db.execute(select(Mannequin).where(Mannequin.slug == slug))
    mannequin = result.scalar_one_or_none()
    if not mannequin:
        raise HTTPException(status_code=404, detail="Manikenni topib bo'lmadi")

    is_online = await AudioRouter.check_health(str(mannequin.ip_address), mannequin.esp32_port)

    return {
        "slug": mannequin.slug,
        "name": mannequin.name,
        "ip_address": str(mannequin.ip_address),
        "is_online": is_online
    }


# =====================
# YORDAMCHI FUNKSIYALAR
# =====================

def _match_scripts(user_text: str, scripts: list[ScriptQA]) -> list[ScriptQA]:
    """
    Hamshiraning savoliga mos keladigan skriptlarni topish.
    Avval trigger_pattern (regex), keyin trigger_keywords bo'yicha tekshiriladi.
    """
    matched = []
    text_lower = user_text.lower().strip()

    for script in scripts:
        # 1. Regex pattern tekshiruvi
        if script.trigger_pattern:
            try:
                if re.search(script.trigger_pattern, text_lower, re.IGNORECASE):
                    matched.append(script)
                    continue
            except re.error:
                pass

        # 2. Keyword tekshiruvi
        if script.trigger_keywords:
            for keyword in script.trigger_keywords:
                if keyword.lower() in text_lower:
                    matched.append(script)
                    break

    return matched


async def _get_preset_audio(
    mannequin_id: int, emotion: str, db: AsyncSession
) -> tuple[Optional[bytes], Optional[str]]:
    """
    Chaqaloq uchun tayyor audio faylni tanlash.
    Emotion asosida tegishli trigger_type tanlanadi.
    """
    # Emotion -> trigger_type mapping
    emotion_map = {
        "yig'lash": "yiglash",
        "yiglash": "yiglash",
        "og'riq": "qattiq_yiglash",
        "og'riqli": "qattiq_yiglash",
        "kulish": "kulish",
        "xursand": "kulish",
        "yo'tal": "yo'tal",
    }
    trigger = emotion_map.get(emotion, "yiglash")  # Default: yig'lash

    result = await db.execute(
        select(AudioPreset)
        .where(AudioPreset.mannequin_id == mannequin_id, AudioPreset.trigger_type == trigger)
    )
    preset = result.scalar_one_or_none()

    if preset:
        audio_url = f"/static/audio_presets/{preset.file_path.split('/')[-1]}"
        try:
            with open(preset.file_path, "rb") as f:
                return f.read(), audio_url
        except FileNotFoundError:
            logger.warning(f"Audio fayl topilmadi: {preset.file_path}")

@router.get("/api/tts")
async def get_tts_audio(text: str, slug: str = "homilador"):
    """Sof o'zbek tilida MP3 audio oqimi (Edge Neural TTS)"""
    from fastapi.responses import Response
    audio_bytes = await TTSService.synthesize(text, slug)
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio generatsiya qilib bo'lmadi")
    return Response(content=audio_bytes, media_type="audio/mpeg")



@router.get("/api/debug/deepseek")
async def debug_deepseek():
    """Debug DeepSeek direct connectivity"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": "Bearer sk-42874f7bcf1f44adb2988b9ae0bc39cc",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "user", "content": "Salom, test"}
                    ]
                }
            )
            return {
                "status_code": resp.status_code,
                "response_json": resp.json() if resp.status_code == 200 else resp.text
            }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

