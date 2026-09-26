"""
MedSim Backend — FastAPI Application
Hamshiralar simulyatsiya tizimining asosiy server ilovasi.
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import router

# Logging sozlash
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("medsim")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ilova boshlanganda va to'xtaganda bajariladigan ishlar"""
    logger.info("🏥 MedSim Backend ishga tushmoqda...")

    # Audio presets papkasini yaratish
    os.makedirs(settings.AUDIO_PRESETS_DIR, exist_ok=True)
    logger.info(f"📂 Audio presets: {settings.AUDIO_PRESETS_DIR}")

    # DB jadvallarni yaratish (dev rejimda)
    if settings.DEBUG:
        try:
            from app.db.database import engine, Base
            # ORM modellarni import qilish (jadvallar ro'yxatxat olish uchun)
            from app.db import models  # noqa: F401
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ DB jadvallar tayyor")
        except Exception as e:
            logger.warning(f"⚠️ DB ulanish xatosi (PostgreSQL ishlamayotgan bo'lishi mumkin): {e}")

    logger.info("✅ MedSim Backend tayyor!")
    yield

    # Tozalash
    logger.info("🛑 MedSim Backend to'xtamoqda...")
    try:
        from app.db.database import engine
        await engine.dispose()
    except Exception:
        pass


# FastAPI ilovasi
app = FastAPI(
    title="MedSim API",
    description="Hamshiralar simulyatsiya tizimi — manikenlar bilan ovozli muloqot",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — frontend bilan bog'lanish uchun
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev uchun. Production'da aniq domenlar yoziladi
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routelarni qo'shish
app.include_router(router)

# Audio fayllar uchun statik server
if os.path.isdir(settings.AUDIO_PRESETS_DIR):
    app.mount(
        "/static/audio_presets",
        StaticFiles(directory=settings.AUDIO_PRESETS_DIR),
        name="audio_presets"
    )


@app.get("/")
async def root():
    """API holat tekshiruvi"""
    return {
        "service": "MedSim API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }
