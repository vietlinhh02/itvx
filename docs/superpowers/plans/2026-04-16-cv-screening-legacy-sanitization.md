# CV Screening Legacy Sanitization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair legacy CV screening records and prevent stale follow-up questions, risk flags, and audit metadata from reaching the detail API.

**Architecture:** Add a backend normalization path that converts stored screening payloads into the current `StoredScreeningPayload` shape before the detail response is built. Use the candidate profile row and screening row metadata to fill safe fields, strip legacy-only content that cannot be trusted, and provide a one-shot backfill command that rewrites existing legacy records in place.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic v2, pytest

---

## File Structure

- Modify: `backend/src/services/cv_screening_service.py`
  - Add a normalization entry point for stored screening payloads.
  - Reuse it from `get_screening()` and history summary extraction.
  - Add a small backfill helper that can sanitize one `CandidateScreening` row at a time.
- Modify: `backend/src/schemas/cv.py`
  - Add any minimal helper model or typing support needed for legacy payload detection only if the service code becomes unclear without it.
- Create: `backend/src/scripts/backfill_cv_screening_payloads.py`
  - Query stored screenings, normalize legacy payloads, persist repaired payloads, and print a short summary.
- Modify: `backend/tests/services/test_cv_screening_service.py`
  - Add red-green coverage for legacy payload normalization and safe audit fallback behavior.
- Modify: `backend/tests/api/test_cv_api.py`
  - Add API coverage proving that detail responses for legacy records do not leak stale follow-ups, risks, or audit values.

---

### Task 1: Cover legacy payload behavior in service tests

**Files:**
- Modify: `backend/tests/services/test_cv_screening_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing test for legacy payload normalization**

Add these fixtures and tests near the existing screening service tests:

```python
def sample_legacy_screening_payload() -> dict[str, object]:
    return {
        "match_score": 0.61,
        "recommendation": "review",
        "decision_reason": {
            "vi": "Can xac minh them.",
            "en": "Needs more verification.",
        },
        "screening_summary": {
            "vi": "Ban ghi cu khong con dang tin cay.",
            "en": "This legacy record is no longer trustworthy as-is.",
        },
        "knockout_assessments": [],
        "minimum_requirement_checks": [],
        "dimension_scores": [],
        "strengths": [],
        "gaps": [],
        "uncertainties": [],
        "follow_up_questions": [
            {
                "question": {
                    "vi": "Ban co the lam full-time khong?",
                    "en": "Can you work full-time?",
                },
                "purpose": {
                    "vi": "Du lieu cu.",
                    "en": "Legacy-only content.",
                },
            }
        ],
        "risk_flags": [
            {
                "title": {"vi": "Rui ro cu", "en": "Legacy risk"},
                "reason": {
                    "vi": "Khong con dang tin cay.",
                    "en": "No longer trustworthy.",
                },
                "severity": "medium",
            }
        ],
        "audit": {
            "extraction_model": "gpt-4o",
            "screening_model": "gpt-4o",
            "profile_schema_version": "1.0",
            "screening_schema_version": "1.0",
            "generated_at": "2025-05-20T10:00:00Z",
            "reconciliation_notes": [
                "Corrected May 2025 start date to a potential typo in analysis.",
            ],
            "consistency_flags": [],
        },
    }


def test_normalize_stored_screening_payload_sanitizes_legacy_content() -> None:
    service = CVScreeningService.__new__(CVScreeningService)
    candidate_profile = sample_candidate_profile_payload()

    normalized = service._normalize_stored_screening_payload(  # pyright: ignore[reportPrivateUsage]
        screening_payload=sample_legacy_screening_payload(),
        candidate_profile_payload=candidate_profile.model_dump(mode="json"),
        model_name="gemini-2.5-pro",
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    assert normalized.candidate_profile == candidate_profile
    assert normalized.result.follow_up_questions == []
    assert normalized.result.risk_flags == []
    assert normalized.audit.extraction_model == "gemini-2.5-pro"
    assert normalized.audit.screening_model == "gemini-2.5-pro"
    assert normalized.audit.generated_at == "2026-04-16T00:00:00+00:00"
    assert any(
        "legacy" in note.lower()
        for note in normalized.audit.reconciliation_notes
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/services/test_cv_screening_service.py -k legacy
```

Expected: FAIL because `_normalize_stored_screening_payload` does not exist yet.

- [ ] **Step 3: Add the failing test for persisted detail loading**

Append this integration-style test near the existing persistence tests:

```python
@pytest.mark.asyncio
async def test_get_screening_normalizes_legacy_payload(
    db_session: AsyncSession,
) -> None:
    candidate_document = CandidateDocument(
        file_name="candidate.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/candidate.pdf",
        status="completed",
    )
    db_session.add(candidate_document)
    await db_session.flush()

    candidate_profile = CandidateProfile(
        candidate_document_id=candidate_document.id,
        profile_payload=sample_candidate_profile_payload().model_dump(mode="json"),
    )
    db_session.add(candidate_profile)
    await db_session.flush()

    screening = CandidateScreening(
        jd_document_id="jd-1",
        candidate_profile_id=candidate_profile.id,
        model_name="gemini-2.5-pro",
        screening_payload=sample_legacy_screening_payload(),
    )
    db_session.add(screening)
    await db_session.commit()

    service = CVScreeningService(upload_dir=Path("/tmp"), db_session=db_session)

    result = await service.get_screening(screening.id)

    assert result is not None
    assert result.audit.extraction_model == "gemini-2.5-pro"
    assert result.result.follow_up_questions == []
    assert result.result.risk_flags == []
```

- [ ] **Step 4: Run the tests to verify they fail for the right reason**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/services/test_cv_screening_service.py -k "legacy or normalizes_legacy"
```

Expected: FAIL with validation or missing-method errors, not import errors.

- [ ] **Step 5: Commit the red tests**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/tests/services/test_cv_screening_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "test: cover legacy cv screening payloads"
```

---

### Task 2: Implement backend normalization for detail responses

**Files:**
- Modify: `backend/src/services/cv_screening_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Add a small legacy-detection helper and normalization entry point**

In `backend/src/services/cv_screening_service.py`, add imports and helpers near `_extract_history_summary`:

```python
from collections.abc import Mapping
```

Add these methods inside `CVScreeningService`:

```python
    def _is_current_screening_payload(self, screening_payload: Mapping[str, object]) -> bool:
        return {
            "candidate_profile",
            "result",
            "audit",
        }.issubset(screening_payload.keys())

    def _normalize_stored_screening_payload(
        self,
        *,
        screening_payload: dict[str, object],
        candidate_profile_payload: dict[str, object],
        model_name: str,
        created_at: datetime,
    ) -> StoredScreeningPayload:
        if self._is_current_screening_payload(screening_payload):
            payload = StoredScreeningPayload.model_validate(screening_payload)
            return self._reconcile_screening_payload(payload)

        candidate_profile = CandidateProfilePayload.model_validate(candidate_profile_payload)
        sanitized_payload = {
            "candidate_profile": candidate_profile.model_dump(mode="json"),
            "result": {
                "match_score": float(screening_payload.get("match_score", 0.0)),
                "recommendation": str(screening_payload.get("recommendation", "review")),
                "decision_reason": screening_payload.get(
                    "decision_reason",
                    {
                        "vi": "Ban ghi legacy da duoc lam sach de tranh hien thi noi dung cu.",
                        "en": "This legacy record was sanitized to avoid showing stale content.",
                    },
                ),
                "screening_summary": screening_payload.get(
                    "screening_summary",
                    {
                        "vi": "Ket qua screening cu da duoc chuan hoa.",
                        "en": "This legacy screening result has been normalized.",
                    },
                ),
                "knockout_assessments": screening_payload.get("knockout_assessments", []),
                "minimum_requirement_checks": screening_payload.get(
                    "minimum_requirement_checks",
                    [],
                ),
                "dimension_scores": screening_payload.get("dimension_scores", []),
                "strengths": screening_payload.get("strengths", []),
                "gaps": screening_payload.get("gaps", []),
                "uncertainties": screening_payload.get("uncertainties", []),
                "follow_up_questions": [],
                "risk_flags": [],
            },
            "audit": {
                "extraction_model": model_name,
                "screening_model": model_name,
                "profile_schema_version": PROFILE_SCHEMA_VERSION,
                "screening_schema_version": SCREENING_SCHEMA_VERSION,
                "generated_at": created_at.replace(tzinfo=UTC).isoformat(),
                "reconciliation_notes": [
                    "Sanitized a legacy screening payload and removed stale follow-up questions, risk flags, and audit metadata.",
                ],
                "consistency_flags": [
                    "Legacy screening payload was normalized from a pre-phase2 schema.",
                ],
            },
        }
        payload = StoredScreeningPayload.model_validate(sanitized_payload)
        return self._reconcile_screening_payload(payload)
```

- [ ] **Step 2: Use the normalizer in `get_screening()`**

Replace the validation block in `get_screening()` with:

```python
        screening, candidate_profile, candidate_document = cast(
            tuple[CandidateScreening, CandidateProfile, CandidateDocument],
            cast(object, row),
        )
        payload = self._normalize_stored_screening_payload(
            screening_payload=screening.screening_payload,
            candidate_profile_payload=candidate_profile.profile_payload,
            model_name=screening.model_name,
            created_at=screening.created_at,
        )
```

- [ ] **Step 3: Keep history extraction tolerant but consistent**

Update `_extract_history_summary()` to avoid broad exception fallback:

```python
    def _extract_history_summary(
        self,
        screening_payload: dict[str, object],
    ) -> tuple[ScreeningRecommendation, float]:
        if self._is_current_screening_payload(screening_payload):
            payload = StoredScreeningPayload.model_validate(screening_payload)
            return payload.result.recommendation, payload.result.match_score

        recommendation = ScreeningRecommendation(str(screening_payload.get("recommendation", "review")))
        match_score = float(screening_payload.get("match_score", 0.0))
        return recommendation, match_score
```

- [ ] **Step 4: Run the service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/services/test_cv_screening_service.py -k "legacy or normalizes_legacy or reconcile"
```

Expected: PASS.

- [ ] **Step 5: Commit the normalization logic**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/cv_screening_service.py backend/tests/services/test_cv_screening_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "fix: normalize legacy cv screening payloads"
```

---

### Task 3: Prove the detail API no longer leaks stale metadata

**Files:**
- Modify: `backend/tests/api/test_cv_api.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Add a fake service response for sanitized legacy data**

Extend `FakeCVScreeningService.get_screening()` or add a new fake branch that returns a sanitized response for a legacy id:

```python
    async def get_screening(self, screening_id: str) -> CVScreeningResponse | None:
        if screening_id == "legacy-screening-id":
            return CVScreeningResponse.model_validate(
                {
                    "screening_id": screening_id,
                    "jd_id": "test-jd-id",
                    "candidate_id": "candidate-id",
                    "file_name": "candidate.pdf",
                    "status": "completed",
                    "created_at": "2026-04-16T00:00:00Z",
                    "candidate_profile": {
                        "candidate_summary": {
                            "full_name": "Nguyen Van A",
                            "current_title": "Backend Engineer",
                            "location": "Ho Chi Minh City",
                            "total_years_experience": 4,
                            "seniority_signal": "mid",
                            "professional_summary": {
                                "vi": "Kỹ sư backend tập trung vào Python.",
                                "en": "Backend engineer focused on Python.",
                            },
                        },
                        "work_experience": [],
                        "projects": [],
                        "skills_inventory": [],
                        "education": [],
                        "certifications": [],
                        "languages": [],
                        "profile_uncertainties": [],
                    },
                    "result": {
                        "match_score": 0.61,
                        "recommendation": "review",
                        "decision_reason": {
                            "vi": "Ban ghi legacy da duoc lam sach.",
                            "en": "The legacy record was sanitized.",
                        },
                        "screening_summary": {
                            "vi": "Da loai bo noi dung cu khong dang tin cay.",
                            "en": "Stale legacy content has been removed.",
                        },
                        "knockout_assessments": [],
                        "minimum_requirement_checks": [],
                        "dimension_scores": [],
                        "strengths": [],
                        "gaps": [],
                        "uncertainties": [],
                        "follow_up_questions": [],
                        "risk_flags": [],
                    },
                    "audit": {
                        "extraction_model": "gemini-2.5-pro",
                        "screening_model": "gemini-2.5-pro",
                        "profile_schema_version": "phase2.v1",
                        "screening_schema_version": "phase2.v1",
                        "generated_at": "2026-04-16T00:00:00Z",
                        "reconciliation_notes": [
                            "Sanitized a legacy screening payload and removed stale follow-up questions, risk flags, and audit metadata.",
                        ],
                        "consistency_flags": [
                            "Legacy screening payload was normalized from a pre-phase2 schema.",
                        ],
                    },
                }
            )
```

- [ ] **Step 2: Add the failing API test**

Add this test:

```python
def test_get_cv_screening_returns_sanitized_legacy_payload(monkeypatch: MonkeyPatch) -> None:
    stub_cv_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/cv/screenings/legacy-screening-id")

    assert response.status_code == 200
    payload = CVScreeningResponse.model_validate(response.json())
    assert payload.result.follow_up_questions == []
    assert payload.result.risk_flags == []
    assert payload.audit.generated_at == "2026-04-16T00:00:00Z"
    assert payload.audit.extraction_model == "gemini-2.5-pro"
```

- [ ] **Step 3: Run the test to verify it fails before the fake is updated or contract is corrected**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/api/test_cv_api.py -k sanitized_legacy
```

Expected: FAIL before the fake service branch exists, then PASS after the fake contract is updated.

- [ ] **Step 4: Run the targeted API suite**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/api/test_cv_api.py -k "cv_screening or sanitized_legacy"
```

Expected: PASS.

- [ ] **Step 5: Commit the API regression coverage**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/tests/api/test_cv_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "test: pin sanitized legacy cv screening responses"
```

---

### Task 4: Add a backfill command for stored legacy records

**Files:**
- Create: `backend/src/scripts/backfill_cv_screening_payloads.py`
- Modify: `backend/src/services/cv_screening_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing test for row backfill**

Add this service test:

```python
@pytest.mark.asyncio
async def test_backfill_legacy_screening_payload_updates_stored_row(
    db_session: AsyncSession,
) -> None:
    candidate_document = CandidateDocument(
        file_name="candidate.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/candidate.pdf",
        status="completed",
    )
    db_session.add(candidate_document)
    await db_session.flush()

    candidate_profile = CandidateProfile(
        candidate_document_id=candidate_document.id,
        profile_payload=sample_candidate_profile_payload().model_dump(mode="json"),
    )
    db_session.add(candidate_profile)
    await db_session.flush()

    screening = CandidateScreening(
        jd_document_id="jd-1",
        candidate_profile_id=candidate_profile.id,
        model_name="gemini-2.5-pro",
        screening_payload=sample_legacy_screening_payload(),
    )
    db_session.add(screening)
    await db_session.commit()

    service = CVScreeningService(upload_dir=Path("/tmp"), db_session=db_session)

    changed = await service.backfill_screening_payload(screening.id)
    await db_session.refresh(screening)

    assert changed is True
    assert "candidate_profile" in screening.screening_payload
    assert screening.screening_payload["result"]["follow_up_questions"] == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/services/test_cv_screening_service.py -k backfill_legacy
```

Expected: FAIL because `backfill_screening_payload` does not exist yet.

- [ ] **Step 3: Add a row-level backfill method to the service**

In `backend/src/services/cv_screening_service.py`, add:

```python
    async def backfill_screening_payload(self, screening_id: str) -> bool:
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        statement = (
            select(CandidateScreening, CandidateProfile)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .where(CandidateScreening.id == screening_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            return False

        screening, candidate_profile = cast(
            tuple[CandidateScreening, CandidateProfile],
            cast(object, row),
        )
        if self._is_current_screening_payload(screening.screening_payload):
            return False

        normalized = self._normalize_stored_screening_payload(
            screening_payload=screening.screening_payload,
            candidate_profile_payload=candidate_profile.profile_payload,
            model_name=screening.model_name,
            created_at=screening.created_at,
        )
        screening.screening_payload = normalized.model_dump(mode="json")
        await self._db_session.commit()
        return True
```

- [ ] **Step 4: Create the backfill script**

Create `backend/src/scripts/backfill_cv_screening_payloads.py` with:

```python
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.cv import CandidateScreening
from src.services.cv_screening_service import CVScreeningService


async def main() -> None:
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
    import asyncio

    asyncio.run(main())
```

- [ ] **Step 5: Run the backfill test and the script against local data**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/services/test_cv_screening_service.py -k backfill_legacy
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run python -m src.scripts.backfill_cv_screening_payloads
```

Expected: test PASS, then script prints `Backfill complete: changed=<n> skipped=<n>`.

- [ ] **Step 6: Commit the backfill tooling**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/cv_screening_service.py backend/src/scripts/backfill_cv_screening_payloads.py backend/tests/services/test_cv_screening_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: backfill legacy cv screening records"
```

---

### Task 5: Verify the repaired endpoint and page behavior

**Files:**
- Modify: none
- Test: `backend/tests/services/test_cv_screening_service.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Run the targeted backend test set**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/services/test_cv_screening_service.py tests/api/test_cv_api.py
```

Expected: PASS.

- [ ] **Step 2: Start or reuse the backend and frontend dev servers**

Run only if they are not already running:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run uvicorn src.main:app --reload
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm run dev
```

Expected: backend on localhost:8000 and frontend on localhost:3000.

- [ ] **Step 3: Backfill the local database**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run python -m src.scripts.backfill_cv_screening_payloads
```

Expected: changed count is at least `1` if the stale record still exists.

- [ ] **Step 4: Verify the raw API payload for the reported screening**

Run:

```bash
curl -s "http://localhost:8000/api/v1/cv/screenings/8dfb4b83-9e58-4271-84a2-be004a7bf484" | jq
```

Expected:
- `result.follow_up_questions` is `[]`
- `result.risk_flags` is `[]`
- `audit.extraction_model` and `audit.screening_model` match the stored screening model, not `gpt-4o`
- `audit.generated_at` is not `2025-05-20T10:00:00Z`

- [ ] **Step 5: Verify the frontend page manually**

Open:

```text
http://localhost:3000/dashboard/cv-screenings/8dfb4b83-9e58-4271-84a2-be004a7bf484
```

Confirm:
- Follow-up Questions shows an empty state instead of stale prompts.
- Risk Flags shows an empty state instead of legacy warnings.
- Audit Metadata no longer shows the stale `gpt-4o` and `2025-05-20T10:00:00Z` values.

- [ ] **Step 6: Commit the final verification state**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" status --short
```

If only the intended files changed, create the final commit:

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/cv_screening_service.py backend/src/scripts/backfill_cv_screening_payloads.py backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "fix: sanitize legacy cv screening detail data"
```

---

## Self-Review

- Spec coverage: this plan covers both requested outcomes: sanitize legacy detail responses now and repair stored rows with a backfill command.
- Placeholder scan: no TODO or TBD markers remain.
- Type consistency: all tasks use the same helper names: `_is_current_screening_payload`, `_normalize_stored_screening_payload`, and `backfill_screening_payload`.
