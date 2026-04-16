# CV Screening History Design

## Goal
Let users reopen older CV screenings from both the JD detail page and the screening detail page.

## Problem
The current flow can open one screening by `screeningId`, but it does not expose a way to browse older screenings for the same JD. Users need a visible way to return to previous uploads without guessing URLs or keeping old links.

## Decision
Add one backend list endpoint for screenings under a JD, then surface that list in two places:

- on the JD detail page as a `Previous screenings` section
- on the screening detail page as an `Other screenings for this JD` switcher

This keeps one source of truth and supports both entry points the user asked for.

## Backend contract
Add a list endpoint scoped to one JD:

- `GET /api/v1/cv/jd/{jd_id}/screenings`

Return lightweight list items only. Each item should include:

- `screening_id`
- `jd_id`
- `candidate_id`
- `file_name`
- `created_at`
- `recommendation`
- `match_score`

Sort newest first.

## Frontend UX

### JD detail page
Keep the upload form. Add a `Previous screenings` section below it.

Each row should show:

- file name
- recommendation
- match score
- created time

Clicking a row opens `/dashboard/cv-screenings/[screeningId]`.

### Screening detail page
Keep the current full result layout. Add a compact `Other screenings for this JD` block near the top of the page.

This block should show the same lightweight list and allow quick navigation to a different screening for the same JD.

The current screening should be visually distinct in the list.

## Error handling
- No screenings yet: show a clear empty state.
- List fetch fails: show a compact error state, but keep the rest of the page usable.
- Detail fetch returns 404: keep the current not-found behavior.

## Testing
Verify that:

1. JD detail shows older screenings for that JD.
2. Clicking a history item opens the saved screening.
3. Screening detail shows other screenings for the same JD.
4. Clicking another item switches to that screening.
5. Refresh on the detail page still works.

## Scope
In scope:

- one backend list endpoint by JD
- one history section on JD detail
- one quick-switch section on screening detail

Out of scope:

- global screening history across all JDs
- filtering, search, or pagination
- deleting screenings
