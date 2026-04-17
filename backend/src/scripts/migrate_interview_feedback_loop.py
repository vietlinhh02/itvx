"""Create interview feedback loop tables for session feedback and JD policies."""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from src.database import Base, engine
from src.models import (  # noqa: F401
    InterviewFeedbackPolicy,
    InterviewFeedbackPolicyAudit,
    InterviewFeedbackRecord,
)


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


async def main() -> None:
    """Create the interview feedback loop tables if they do not exist yet."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table_name in (
            "interview_feedback_records",
            "interview_feedback_policies",
            "interview_feedback_policy_audits",
        ):
            if not await _table_exists(conn, table_name):
                raise RuntimeError(f"Expected table {table_name} to exist after metadata creation")
    print("Interview feedback loop migration applied")


if __name__ == "__main__":
    asyncio.run(main())
