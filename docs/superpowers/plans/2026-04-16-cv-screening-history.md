# CV Screening History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users reopen older CV screenings from both the JD detail page and the screening detail page.

**Architecture:** Add one backend endpoint that lists lightweight screening records for a JD. Reuse that list in two frontend surfaces: a `Previous screenings` section on the JD detail page, and an `Other screenings for this JD` switcher on the screening detail page.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, Next.js App Router, React, TypeScript

---

## File structure

- Modify: `backend/src/schemas/cv.py`
  - Add a lightweight list-item schema and list response schema for screening history.
- Modify: `backend/src/services/cv_screening_service.py`
  - Add a query method that lists screenings for one JD in newest-first order.
- Modify: `backend/src/api/v1/cv.py`
  - Expose the new history endpoint.
- Modify: `backend/tests/api/test_cv_api.py`
  - Add route tests for screening history.
- Modify: `backend/tests/services/test_cv_screening_service.py`
  - Add service tests for screening history ordering and payload shape.
- Modify: `frontend/src/components/jd/cv-screening-types.ts`
  - Add frontend types for screening history items.
- Create: `frontend/src/components/jd/cv-screening-history.tsx`
  - Render reusable history list UI for both pages.
- Modify: `frontend/src/app/dashboard/jd/[id]/page.tsx`
  - Fetch and show previous screenings below the upload form.
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
  - Fetch and show other screenings for the same JD.
- Modify: `frontend/src/components/jd/cv-screening-detail.tsx`
  - Accept history props and render the quick-switch block.

### Task 1: Add backend schemas for screening history

**Files:**
- Modify: `backend/src/schemas/cv.py`
- Test: `backend/tests/schemas/test_cv_schema.py`

- [ ] **Step 1: Write the failing schema test**

```python
def test_cv_screening_history_response_validates() -> None:
    payload = {
        "items": [
            {
                "screening_id": "screening-1",
                "jd_id": "jd-1",
                "candidate_id": "candidate-1",
                "file_name": "candidate.pdf",
                "created_at": "2026-04-16T10:00:00+00:00",
                "recommendation": "review",
                "match_score": 0.76,
            }
        ]
    }

    validated = CVScreeningHistoryResponse.model_validate(payload)

    assert validated.items[0].screening_id == "screening-1"
    assert validated.items[0].recommendation == "review"
```

- [ ] **Step 2: Run the schema test to verify it fails**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/schemas/test_cv_schema.py -k history_response`
Expected: FAIL with missing schema name such as `CVScreeningHistoryResponse` not defined

- [ ] **Step 3: Add the new schemas**

```python
class CVScreeningHistoryItem(BaseModel):
    """Lightweight metadata for one persisted screening."""

    screening_id: str
    jd_id: str
    candidate_id: str
    file_name: str
    created_at: str
    recommendation: ScreeningRecommendation
    match_score: float = Field(ge=0, le=1)


class CVScreeningHistoryResponse(BaseModel):
    """List response for all screenings under one JD."""

    items: list[CVScreeningHistoryItem]
```
```

Add both names to `__all__`.

- [ ] **Step 4: Run the schema test again**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/schemas/test_cv_schema.py -k history_response`
Expected: PASS

### Task 2: Add service support for listing screenings by JD

**Files:**
- Modify: `backend/src/services/cv_screening_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing service test**

```python
async def test_list_screenings_for_jd_returns_newest_first(
    db_session: AsyncSession,
    completed_jd_document: JDDocument,
) -> None:
    older = CandidateScreening(
        jd_document_id=completed_jd_document.id,
        candidate_profile_id="profile-older",
        model_name="gemini-2.5-pro",
        screening_payload={
            "candidate_profile": build_candidate_profile_fixture().model_dump(mode="json"),
            "result": build_screening_payload_fixture().result.model_dump(mode="json"),
            "audit": build_screening_payload_fixture().audit.model_dump(mode="json"),
        },
    )
    newer = CandidateScreening(
        jd_document_id=completed_jd_document.id,
        candidate_profile_id="profile-newer",
        model_name="gemini-2.5-pro",
        screening_payload={
            "candidate_profile": build_candidate_profile_fixture().model_dump(mode="json"),
            "result": {
                **build_screening_payload_fixture().result.model_dump(mode="json"),
                "match_score": 0.92,
                "recommendation": "advance",
            },
            "audit": build_screening_payload_fixture().audit.model_dump(mode="json"),
        },
    )

    db_session.add_all([older, newer])
    await db_session.commit()

    service = CVScreeningService(db_session=db_session)
    items = await service.list_screenings_for_jd(completed_jd_document.id)

    assert [item.screening_id for item in items] == [newer.id, older.id]
    assert items[0].recommendation == "advance"
    assert items[0].match_score == 0.92
```

- [ ] **Step 2: Run the service test to verify it fails**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/services/test_cv_screening_service.py -k list_screenings_for_jd`
Expected: FAIL with `list_screenings_for_jd` missing

- [ ] **Step 3: Implement the list method in the service**

```python
async def list_screenings_for_jd(self, jd_id: str) -> list[CVScreeningHistoryItem]:
    """Return persisted screenings for one JD in reverse chronological order."""
    if self._db_session is None:
        raise RuntimeError("CVScreeningService requires a database session")

    statement = (
        select(CandidateScreening, CandidateDocument)
        .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
        .join(CandidateDocument, CandidateDocument.id == CandidateProfile.candidate_document_id)
        .where(CandidateScreening.jd_document_id == jd_id)
        .order_by(CandidateScreening.created_at.desc())
    )
    rows = (await self._db_session.execute(statement)).all()

    items: list[CVScreeningHistoryItem] = []
    for screening, document in rows:
        payload = StoredScreeningPayload.model_validate(screening.screening_payload)
        items.append(
            CVScreeningHistoryItem(
                screening_id=screening.id,
                jd_id=screening.jd_document_id,
                candidate_id=document.id,
                file_name=document.file_name,
                created_at=screening.created_at.replace(tzinfo=UTC).isoformat(),
                recommendation=payload.result.recommendation,
                match_score=payload.result.match_score,
            )
        )
    return items
```

- [ ] **Step 4: Run the service test again**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/services/test_cv_screening_service.py -k list_screenings_for_jd`
Expected: PASS

### Task 3: Expose the backend history endpoint

**Files:**
- Modify: `backend/src/api/v1/cv.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Write the failing API test**

```python
def test_cv_screening_history_returns_items(monkeypatch: MonkeyPatch) -> None:
    stub_cv_service(monkeypatch, screening_history=True)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/cv/jd/test-jd-id/screenings")

    assert response.status_code == 200
    payload = CVScreeningHistoryResponse.model_validate(response.json())
    assert payload.items[0].screening_id == "test-screening-id"
```

- [ ] **Step 2: Run the API test to verify it fails**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/api/test_cv_api.py -k screening_history`
Expected: FAIL with 404 or missing stub method

- [ ] **Step 3: Add the route**

```python
@router.get("/jd/{jd_id}/screenings", response_model=CVScreeningHistoryResponse)
async def list_cv_screenings_for_jd(
    jd_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CVScreeningHistoryResponse:
    """Return all stored CV screenings for one JD."""
    service = CVScreeningService(upload_dir=settings.cv_upload_path, db_session=db)
    return CVScreeningHistoryResponse(items=await service.list_screenings_for_jd(jd_id))
```

- [ ] **Step 4: Run the API test again**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/api/test_cv_api.py -k screening_history`
Expected: PASS

### Task 4: Add shared frontend types and history list UI

**Files:**
- Modify: `frontend/src/components/jd/cv-screening-types.ts`
- Create: `frontend/src/components/jd/cv-screening-history.tsx`
- Test: `frontend` type check

- [ ] **Step 1: Add frontend history types**

```ts
export type CVScreeningHistoryItem = {
  screening_id: string
  jd_id: string
  candidate_id: string
  file_name: string
  created_at: string
  recommendation: ScreeningRecommendation
  match_score: number
}

export type CVScreeningHistoryResponse = {
  items: CVScreeningHistoryItem[]
}
```

- [ ] **Step 2: Create the reusable history component**

```tsx
import type { Route } from "next"
import Link from "next/link"

import type { CVScreeningHistoryItem } from "@/components/jd/cv-screening-types"

type CVScreeningHistoryProps = {
  title: string
  items: CVScreeningHistoryItem[]
  currentScreeningId?: string
}

export function CVScreeningHistory({ title, items, currentScreeningId }: CVScreeningHistoryProps) {
  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phase 2 history</p>
        <h2 className="text-2xl font-semibold text-[var(--color-brand-text-primary)]">{title}</h2>
      </div>

      {items.length ? (
        <div className="mt-6 space-y-3">
          {items.map((item) => {
            const isCurrent = item.screening_id === currentScreeningId
            return (
              <Link
                key={item.screening_id}
                className="flex items-center justify-between rounded-[16px] border border-[var(--color-brand-input-border)] px-4 py-3"
                href={buildScreeningRoute(item.screening_id)}
              >
                <div>
                  <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">
                    {item.file_name}
                  </p>
                  <p className="text-sm text-[var(--color-brand-text-body)]">
                    {item.recommendation} · score {item.match_score}
                  </p>
                </div>
                <span className="text-xs text-[var(--color-brand-text-muted)]">
                  {isCurrent ? "Current" : new Date(item.created_at).toLocaleString()}
                </span>
              </Link>
            )
          })}
        </div>
      ) : (
        <p className="mt-6 rounded-[16px] border border-dashed border-[var(--color-brand-input-border)] px-4 py-6 text-sm text-[var(--color-brand-text-muted)]">
          No screenings yet.
        </p>
      )}
    </section>
  )
}

function buildScreeningRoute(screeningId: string): Route {
  return `/dashboard/cv-screenings/${screeningId}` as Route
}
```

- [ ] **Step 3: Run frontend type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm run type-check`
Expected: PASS or only targeted type errors in the new files

- [ ] **Step 4: Fix any type issues, then re-run type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm run type-check`
Expected: PASS

### Task 5: Show history on the JD detail page

**Files:**
- Modify: `frontend/src/app/dashboard/jd/[id]/page.tsx`
- Test: `frontend` type check

- [ ] **Step 1: Fetch the screening history in the JD page**

```tsx
const screeningsResponse = await fetch(`${backendBaseUrl}/api/v1/cv/jd/${id}/screenings`, {
  method: "GET",
  headers: {
    Authorization: `Bearer ${session.accessToken}`,
  },
  cache: "no-store",
})

const screeningHistory = screeningsResponse.ok
  ? ((await screeningsResponse.json()) as CVScreeningHistoryResponse)
  : { items: [] }
```

- [ ] **Step 2: Render the history section below the upload panel**

```tsx
<main className="flex w-full flex-col gap-6 py-6">
  <JDAnalysisContent result={result} />
  <CVScreeningPanel accessToken={session.accessToken} backendBaseUrl={backendBaseUrl} jd={result} />
  <CVScreeningHistory title="Previous screenings" items={screeningHistory.items} />
</main>
```

- [ ] **Step 3: Run frontend type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm run type-check`
Expected: PASS

### Task 6: Show quick-switch history on the screening detail page

**Files:**
- Modify: `frontend/src/components/jd/cv-screening-detail.tsx`
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
- Test: `frontend` type check

- [ ] **Step 1: Extend the detail component props**

```tsx
import { CVScreeningHistory } from "@/components/jd/cv-screening-history"
import type {
  CVScreeningHistoryItem,
  CVScreeningResponse,
} from "@/components/jd/cv-screening-types"

type CVScreeningDetailProps = {
  screening: CVScreeningResponse
  historyItems: CVScreeningHistoryItem[]
}
```

- [ ] **Step 2: Render the quick-switch block near the top**

```tsx
<CVScreeningHistory
  title="Other screenings for this JD"
  items={historyItems}
  currentScreeningId={screening.screening_id}
/>
```

- [ ] **Step 3: Fetch history in the detail route and pass it through**

```tsx
const historyResponse = await fetch(`${backendBaseUrl}/api/v1/cv/jd/${screening.jd_id}/screenings`, {
  method: "GET",
  headers: {
    Authorization: `Bearer ${session.accessToken}`,
  },
  cache: "no-store",
})

const history = historyResponse.ok
  ? ((await historyResponse.json()) as CVScreeningHistoryResponse)
  : { items: [] }

return <CVScreeningDetail screening={screening} historyItems={history.items} />
```

- [ ] **Step 4: Run frontend type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm run type-check`
Expected: PASS

### Task 7: Verify backend and frontend integration

**Files:**
- Modify only if verification reveals issues

- [ ] **Step 1: Run targeted backend tests**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q tests/schemas/test_cv_schema.py -k history_response && pytest -q tests/services/test_cv_screening_service.py -k list_screenings_for_jd && pytest -q tests/api/test_cv_api.py -k screening_history`
Expected: PASS

- [ ] **Step 2: Run frontend type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm run type-check`
Expected: PASS

- [ ] **Step 3: Manually verify the two entry points**

Check that:
1. JD detail shows `Previous screenings`
2. clicking a row opens the saved screening detail page
3. screening detail shows `Other screenings for this JD`
4. clicking another row switches to the selected screening
5. refreshing the detail page still keeps the result

- [ ] **Step 4: Review changed files for scope control**

Checklist:
- one backend list endpoint only
- no search, filtering, or pagination
- one reusable history component shared by both pages
