"""Migrate legacy interview tables to the realtime interview schema."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from src.database import Base, engine
from src.models import InterviewRuntimeEvent, InterviewSession, InterviewTurn  # noqa: F401


LEGACY_SCHEMA = "interview_legacy"


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


async def _table_exists(conn: AsyncConnection, table_name: str) -> bool:
    result = await conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
            LIMIT 1
            """
        ),
        {"table_name": table_name},
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


async def _archive_table(conn: AsyncConnection, table_name: str, suffix: str) -> None:
    await conn.execute(text(f'ALTER TABLE public."{table_name}" SET SCHEMA {LEGACY_SCHEMA}'))
    await conn.execute(
        text(f'ALTER TABLE {LEGACY_SCHEMA}."{table_name}" RENAME TO "{table_name}_{suffix}"')
    )


async def main() -> None:
    """Archive incompatible interview tables and create the realtime schema."""
    async with engine.begin() as conn:
        has_interview_sessions = await _table_exists(conn, "interview_sessions")
        has_share_token = await _column_exists(conn, "interview_sessions", "share_token")
        has_livekit_room_name = await _column_exists(conn, "interview_sessions", "livekit_room_name")

        if has_interview_sessions and (not has_share_token or not has_livekit_room_name):
            suffix = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {LEGACY_SCHEMA}"))

            for table_name in ("interview_runtime_events", "interview_turns", "interview_sessions"):
                if await _table_exists(conn, table_name):
                    await _archive_table(conn, table_name, suffix)

        await conn.run_sync(Base.metadata.create_all)
        if await _table_exists(conn, "interview_sessions"):
            await _ensure_realtime_columns(conn)

    print("Interview runtime migration applied")


if __name__ == "__main__":
    asyncio.run(main())
