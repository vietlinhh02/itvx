# CV Screening Detail Page Design

## Goal
Make Phase 2 CV screening survive page refresh and reduce page overload by moving each screening result to its own page.

## Problem
Today the JD detail page both uploads a CV and renders the full screening result. The result lives only in client state inside `frontend/src/components/jd/cv-screening-panel.tsx`. After a successful upload, the user can see the result, but a browser refresh clears it. This is confusing because the backend already persists the screening in the database.

## Decision
Use one dedicated route per screening result:

- Route: `/dashboard/cv-screenings/[screeningId]`
- After `POST /api/v1/cv/screen` succeeds, redirect to that route with the returned `screening_id`
- Load the detail page from `GET /api/v1/cv/screenings/{screening_id}`

This makes the database the source of truth for Phase 2 results and removes the need to keep the full result in JD-page local state.

## Why this approach
This option is the cleanest fit for the current backend and UX.

- It fixes refresh persistence because the page can reload from the stored record.
- It keeps the JD detail page focused on JD context and CV submission.
- It reuses the existing screening detail API instead of adding a new backend contract.
- It gives every screening a stable URL for debugging and future navigation.

## Rejected alternatives

### Keep screening on the JD page with a `screeningId` query param
This would preserve refresh behavior, but the JD page would still own too many responsibilities. It would also keep routing and rendering logic coupled to the JD page.

### Store the screening result in browser storage
This would make refresh work in one browser, but it would duplicate data that already exists in the database and would not be reliable across sessions or devices.

## UX changes

### JD detail page
The JD detail page continues to show:

- the stored JD analysis
- the Phase 2 CV upload form
- upload and submission errors

The JD detail page no longer shows the full screening result after submission.

After a successful CV screening request, the page redirects to the dedicated screening detail page.

### Screening detail page
The new screening detail page shows the existing screening result UI sections:

- summary
- candidate profile
- knockout and minimum requirement assessments
- dimension scores
- insights, gaps, and uncertainties
- follow-up questions
- risk flags
- audit metadata

The page should also include a simple path back to the related JD detail page.

## Routing design

### Existing route kept
- `frontend/src/app/dashboard/jd/[id]/page.tsx`

### New route added
- `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`

This new page will:

1. require an authenticated session
2. fetch the screening by `screeningId`
3. render the screening detail UI using the existing Phase 2 presentation components

## Data flow

### Successful screening flow
1. User opens JD detail page.
2. User uploads one CV from the Phase 2 form.
3. Frontend sends `POST /api/v1/cv/screen`.
4. Backend stores the document, extracted profile, and screening result.
5. Backend returns `screening_id`.
6. Frontend redirects to `/dashboard/cv-screenings/[screeningId]`.
7. The new page fetches `GET /api/v1/cv/screenings/{screening_id}`.
8. The page renders from database-backed data.

### Refresh flow
1. User refreshes the screening detail page.
2. The page fetches the same screening again by `screeningId`.
3. The result remains visible because it is loaded from the backend, not from client memory.

## Frontend component design

### `CVScreeningPanel`
Change its responsibility so it only handles:

- file selection
- submit state
- upload error state
- redirect on success

Remove the local result state that currently stores and renders the full screening response.

### Screening detail page composition
The new page should reuse the existing display components already used under `CVScreeningPanel`, rather than creating a second rendering system. That keeps the UI consistent and limits the change to routing and data-loading responsibilities.

## Error handling

### Upload errors on JD detail page
If `POST /api/v1/cv/screen` fails, stay on the JD detail page and show the existing inline error message.

### Missing screening
If `GET /api/v1/cv/screenings/{screening_id}` returns 404, render `notFound()`.

### Auth or invalid session
Follow the same auth guard pattern already used by the JD detail page. If there is no valid session or backend base URL, redirect to login.

### Unexpected fetch failure
If the screening detail fetch fails for a non-404 reason, show a compact error state instead of crashing the page.

## Testing plan

### Golden path
Verify that:

1. a CV upload succeeds
2. the user is redirected to the screening detail route
3. the screening detail page renders the stored result
4. refreshing the page keeps the result visible

### Error paths
Verify that:

1. upload failures still show inline errors on the JD detail page
2. an unknown `screeningId` returns the not-found page

### Regression checks
Verify that:

1. JD detail still loads correctly
2. Phase 1 JD analysis remains unchanged
3. existing Phase 2 rendering components still display the same sections on the new page

## Scope boundaries
In scope:

- new screening detail route
- redirect after successful screening
- move Phase 2 result rendering off the JD detail page
- fetch persisted data from the existing backend endpoint

Out of scope:

- screening history lists
- multiple-screening navigation for one JD
- backend schema changes
- local browser persistence

## Implementation notes
- Prefer server-side data loading in the new route to match the existing dashboard page pattern.
- Reuse the existing `CVScreeningResponse` frontend type.
- Keep the backend API unchanged unless implementation uncovers a missing field needed for navigation.

## Success criteria
The design is successful when:

- a user can upload a CV and land on a stable screening URL
- refreshing that page does not lose the screening result
- the JD detail page is simpler and no longer renders the full Phase 2 result inline
- the implementation reuses the existing persisted screening API and existing result UI components
