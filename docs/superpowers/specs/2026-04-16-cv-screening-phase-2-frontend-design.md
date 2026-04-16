# CV Screening Phase 2 Frontend Design

## Goal

Update the frontend CV screening experience to fully consume the new Phase 2 backend response.

The UI must render the screening response as a review dossier for HR, including candidate profile,
knockout and minimum-requirement assessments, rubric scores, strengths, gaps, uncertainties,
follow-up questions, risk flags, and audit metadata.

## Scope

This design includes:

- Frontend integration with the new Phase 2 backend response contract
- Type updates for the CV screening response
- A refactor of the CV screening UI into smaller files
- Full rendering of the Phase 2 review payload on the JD detail page

This design does not include:

- Backend changes
- Screening history pages
- A dedicated screening detail route
- Refetch by `screening_id`
- Dashboard redesign outside the current JD detail page

## Current Problem

The current frontend still expects the old CV screening payload.

Observed gaps:

- The TypeScript response type omits `candidate_profile` and `audit`
- The UI does not render `screening_summary`
- The UI does not render `knockout_assessments`
- The UI does not render `follow_up_questions`
- The UI does not render `risk_flags`
- The UI does not render the extracted candidate profile snapshot
- The current `cv-screening-panel.tsx` is too small for the new payload and should not absorb every
  new rendering concern directly

## Architecture

The frontend should treat the Phase 2 response as a review board.

The page entry stays the same:

- `frontend/src/app/dashboard/jd/[id]/page.tsx`

The CV screening panel remains the upload container and state owner:

- `frontend/src/components/jd/cv-screening-panel.tsx`

The rendering work is split into smaller components with one clear responsibility each.

## File Structure

- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`
  - keep upload behavior and request flow
  - render the new Phase 2 review sections
- Create: `frontend/src/components/jd/cv-screening-types.ts`
  - hold the full Phase 2 response contract
- Create: `frontend/src/components/jd/cv-screening-summary.tsx`
  - top-level recommendation, score, summary, and decision reason
- Create: `frontend/src/components/jd/cv-candidate-profile.tsx`
  - candidate profile snapshot
- Create: `frontend/src/components/jd/cv-screening-assessments.tsx`
  - knockout and minimum requirement sections
- Create: `frontend/src/components/jd/cv-screening-dimensions.tsx`
  - rubric dimension scores
- Create: `frontend/src/components/jd/cv-screening-insights.tsx`
  - strengths, gaps, uncertainties
- Create: `frontend/src/components/jd/cv-screening-followups.tsx`
  - follow-up questions
- Create: `frontend/src/components/jd/cv-screening-risks.tsx`
  - risk flags
- Create: `frontend/src/components/jd/cv-screening-audit.tsx`
  - audit metadata
- Create if needed: `frontend/src/components/jd/cv-screening-ui.tsx`
  - small shared helpers for badges and repeated display blocks

## Data Contract

The frontend response contract must match the Phase 2 backend response exactly.

Top-level fields:

- `screening_id`
- `jd_id`
- `candidate_id`
- `file_name`
- `status`
- `created_at`
- `candidate_profile`
- `result`
- `audit`

### Candidate profile

The frontend must support:

- `candidate_summary`
- `work_experience`
- `projects`
- `skills_inventory`
- `education`
- `certifications`
- `languages`
- `profile_uncertainties`

### Result

The frontend must support:

- `match_score`
- `recommendation`
- `decision_reason`
- `screening_summary`
- `knockout_assessments`
- `minimum_requirement_checks`
- `dimension_scores`
- `strengths`
- `gaps`
- `uncertainties`
- `follow_up_questions`
- `risk_flags`

### Audit

The frontend must support:

- `extraction_model`
- `screening_model`
- `profile_schema_version`
- `screening_schema_version`
- `generated_at`
- `reconciliation_notes`
- `consistency_flags`

## UI Mapping

### 1. Summary

Render at the top of the result block.

Fields:

- recommendation badge
- match score
- `screening_summary`
- `decision_reason`

The score should be shown as a percentage for readability.

## 2. Candidate profile snapshot

Render the extracted profile as a separate section.

Subsections:

- candidate summary
- experience cards
- project cards
- skill inventory
- education
- certifications
- languages
- profile uncertainties

## 3. Knockout and minimum requirements

Render both assessment groups as structured review lists.

Each item should show:

- criterion
- status badge (`met`, `not_met`, `unclear`)
- reason
- evidence

## 4. Rubric dimension scores

Render one card per dimension.

Each card should show:

- dimension name
- priority badge
- weight
- score
- reason
- evidence
- confidence note when available

## 5. Insights

Render three blocks:

- strengths
- gaps
- uncertainties

These blocks should preserve bilingual titles and explanations where available.

## 6. Follow-up questions

Render interviewer follow-up questions as a separate list.

Each item should show:

- question
- purpose
- linked dimension if present

## 7. Risk flags

Render risk flags as their own section.

Each item should show:

- severity badge
- title
- reason

## 8. Audit metadata

Render audit metadata at the bottom.

This is a full-audit view, so it should be visible, but visually secondary.

Display:

- extraction model
- screening model
- schema versions
- generated timestamp
- reconciliation notes
- consistency flags

## UX Rules

- Keep the upload form behavior unchanged
- Preserve current backend error handling behavior
- After a successful upload, render the full review board in the same page
- Keep the layout aligned with the current JD analysis visual language
- Prefer clear sectioning over dense blocks of text
- Use smaller components rather than growing `cv-screening-panel.tsx`

## Implementation Strategy

Recommended approach: rich review board with smaller files.

Reason:

- it matches the full Phase 2 backend contract
- it keeps the UI maintainable
- it avoids turning one component into an oversized file
- it fits the current JD detail page structure without requiring a routing redesign

## Success Criteria

Frontend integration is complete when:

- the frontend type contract matches the Phase 2 backend response
- a successful CV screening request renders the full review payload
- the candidate profile is visible in the UI
- knockout and minimum requirement checks are visible
- dimension scores, strengths, gaps, uncertainties, follow-up questions, risk flags, and audit metadata are visible
- the rendering code is split into smaller files with focused responsibilities
