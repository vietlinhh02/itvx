"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings

# Convert postgresql:// to postgresql+asyncpg://
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.app_env == "development",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


async def _column_exists(conn: AsyncConnection, table_name: str, column_name: str) -> bool:
    result = await conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar() == 1


async def _ensure_realtime_columns(conn: AsyncConnection) -> None:
    interview_session_columns = {
        "approved_questions": "ALTER TABLE public.interview_sessions ADD COLUMN approved_questions JSONB NOT NULL DEFAULT '[]'::jsonb",
        "manual_questions": "ALTER TABLE public.interview_sessions ADD COLUMN manual_questions JSONB NOT NULL DEFAULT '[]'::jsonb",
        "question_guidance": "ALTER TABLE public.interview_sessions ADD COLUMN question_guidance TEXT",
        "plan_payload": "ALTER TABLE public.interview_sessions ADD COLUMN plan_payload JSONB NOT NULL DEFAULT '{}'::jsonb",
    }
    for column_name, statement in interview_session_columns.items():
        if not await _column_exists(conn, "interview_sessions", column_name):
            await conn.execute(text(statement))


async def _ensure_company_document_columns(conn: AsyncConnection) -> None:
    company_document_columns = {
        "error_message": "ALTER TABLE public.jd_company_documents ADD COLUMN error_message TEXT",
        "chunk_count": "ALTER TABLE public.jd_company_documents ADD COLUMN chunk_count INTEGER NOT NULL DEFAULT 0",
    }
    for column_name, statement in company_document_columns.items():
        if not await _column_exists(conn, "jd_company_documents", column_name):
            await conn.execute(text(statement))


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_realtime_columns(conn)
        if await _column_exists(conn, "jd_company_documents", "id"):
            await _ensure_company_document_columns(conn)
