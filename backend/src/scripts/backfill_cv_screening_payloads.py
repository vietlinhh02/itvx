"""Backfill legacy CV screening payloads into the Phase 2 schema."""

import asyncio

from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.cv import CandidateScreening
from src.services.cv_screening_service import CVScreeningService


async def main() -> None:
    """Normalize all stored legacy screening payloads in the local database."""
    async with AsyncSessionLocal() as session:
        service = CVScreeningService(db_session=session)
        screening_ids = list(
            (await session.execute(select(CandidateScreening.id))).scalars().all()
        )
        changed = 0
        skipped = 0
        for screening_id in screening_ids:
            if await service.backfill_screening_payload(screening_id):
                changed += 1
            else:
                skipped += 1
        print(f"Backfill complete: changed={changed} skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(main())
