import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

try:
    engine = create_async_engine(settings.async_database_url, echo=settings.DEBUG)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except Exception as e:
    logger.warning(f"Async DB engine initialization warning: {e}")
    engine = None
    AsyncSessionLocal = None

async def get_db():
    if AsyncSessionLocal is None:
        yield None
        return
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except Exception as e:
        logger.warning(f"DB session error: {e}")
        yield None

