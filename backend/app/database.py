from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.config import settings

# --- 1. ASYNC ENGINE (For FastAPI) ---
async_engine = create_async_engine(
    settings.DATABASE_URL, # Ensure this starts with postgresql+asyncpg://
    echo=False,
    future=True
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# --- 2. SYNC ENGINE (For Ingestion Scripts & Celery) ---
# We need a separate URL for sync (postgresql:// instead of postgresql+asyncpg://)
SYNC_DATABASE_URL = settings.DATABASE_URL.replace("+asyncpg", "")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    future=True
)

# This is what process_artifacts.py imports!
SessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    autocommit=False,
    autoflush=False
)

# --- 3. MODELS BASE ---
class Base(DeclarativeBase):
    pass

# --- 4. DEPENDENCIES ---
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()