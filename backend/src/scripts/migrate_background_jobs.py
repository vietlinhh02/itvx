"""Apply local database schema updates for background jobs."""

import asyncio

from sqlalchemy import text

from src.database import engine

MIGRATION_SQL = [
    """
    ALTER TABLE candidate_screenings
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'completed'
    """,
    """
    CREATE TABLE IF NOT EXISTS background_jobs (
        id VARCHAR(36) PRIMARY KEY,
        job_type VARCHAR(50) NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'queued',
        resource_type VARCHAR(50) NOT NULL,
        resource_id VARCHAR(36) NOT NULL,
        payload JSONB NOT NULL,
        error_message TEXT NULL,
        started_at TIMESTAMP NULL,
        completed_at TIMESTAMP NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


async def main() -> None:
    """Run idempotent SQL statements for the local background job schema."""
    async with engine.begin() as conn:
        for statement in MIGRATION_SQL:
            await conn.execute(text(statement))
    print("Background job migration applied")


if __name__ == "__main__":
    asyncio.run(main())
