# CV Screening Phase 2 Backend Design

## Goal

Complete the backend slice of CV Screening Phase 2 for InterviewX.

This phase must accept one CV for an existing analyzed JD, extract a review-ready candidate profile,
screen that candidate against the stored JD analysis with Gemini, apply deterministic guardrails to the
model output, persist the resulting review artifacts, and return a complete HR-facing screening payload.

This design replaces the current MVP screening logic with a spec-complete Phase 2 backend.

## Scope

This design includes:

- Backend-only Phase 2 completion
- Redesign of the candidate profile schema
- LLM-assisted CV screening using Gemini
- Full review artifacts in the screening response
- Deterministic validation and reconciliation of model outputs
- Persistence of extracted profiles and screening artifacts
- API contract updates for Phase 2
- Schema, service, and API test updates

This design does not include:

- Frontend rendering changes
- Background jobs or async orchestration
- Screening history UI
- Manual HR editing workflows
- Backward-compatibility shims for the old CV screening payload

## Current Problems

The current backend flow works, but it is still an MVP.

Observed gaps in the current implementation:

- `CandidateProfilePayload` is too thin for review-grade screening.
- Screening logic is mostly hard-coded.
- Minimum requirement evaluation is limited to a single Python check.
- Knockout criteria from JD analysis are not enforced.
- Strengths, gaps, and decision reasons are mostly fixed text.
- Recommendation logic does not reflect must-have failure, knockout failure, or uncertainty well.
- The response shape is too small for auditability and HR review.

## Architecture

Phase 2 backend uses four layers.

### 1. CV intake layer

Responsibilities:

- Accept `POST /api/v1/cv/screen`
- Validate file type, file size, and file content
- Require a completed JD analysis for the supplied `jd_id`
- Store the original CV file
- Persist a `candidate_documents` record

This layer stays synchronous and request-driven.

### 2. Candidate profile extraction layer

Responsibilities:

- Read the uploaded CV with Gemini
- Extract a structured Phase 2 candidate profile
- Prefer omission over unsupported inference
- Preserve evidence-bearing claims and ambiguities
- Persist the normalized profile in `candidate_profiles`

This layer replaces the current thin profile schema with a review-ready representation.

### 3. Screening artifact generation layer

Responsibilities:

- Load the stored `JDAnalysisPayload`
- Pass the JD analysis and normalized candidate profile to Gemini
- Produce structured review artifacts:
  - knockout assessments
  - minimum requirement assessments
  - dimension-by-dimension scores
  - strengths
  - gaps
  - uncertainties
  - follow-up questions
  - HR-facing summary
  - proposed recommendation

This layer is LLM-assisted, but it must return structured output only.

### 4. Deterministic validation and persistence layer

Responsibilities:

- Validate returned screening artifacts against the schema
- Reconcile model output with hard backend rules
- Recompute or verify weighted scores
- Enforce knockout and must-have constraints
- Persist screening artifacts in `candidate_screenings`
- Return a final response that is internally consistent

This layer prevents the model from returning attractive but invalid results.

## Request Flow

For `POST /api/v1/cv/screen`:

1. Validate the uploaded file.
2. Load the completed JD analysis for `jd_id`.
3. Store the CV file on disk.
4. Create `candidate_documents` with `status="processing"`.
5. Extract the Phase 2 candidate profile with Gemini.
6. Persist `candidate_profiles.profile_payload`.
7. Generate screening artifacts with Gemini using JD analysis plus candidate profile.
8. Validate and reconcile the screening artifacts.
9. Persist `candidate_screenings.screening_payload`.
10. Mark the candidate document as `completed`.
11. Return the full Phase 2 screening response.

For `GET /api/v1/cv/screenings/{screening_id}`:

1. Load the persisted screening and candidate profile.
2. Return the same Phase 2 response contract used by the create endpoint.

## Candidate Profile Schema

The current `CandidateProfilePayload` will be replaced.

### Top-level structure

```json
{
  "candidate_summary": {},
  "work_experience": [],
  "projects": [],
  "skills_inventory": [],
  "education": [],
  "certifications": [],
  "languages": [],
  "profile_uncertainties": []
}
```

### `candidate_summary`

Purpose: high-level identity and career summary for HR review.

Fields:

- `full_name: str | null`
- `current_title: str | null`
- `location: str | null`
- `total_years_experience: float | null`
- `seniority_signal: Literal["intern", "junior", "mid", "senior", "lead", "manager", "unknown"]`
- `professional_summary: BilingualText | null`

### `work_experience`

Purpose: structured, evidence-bearing role history.

Fields per item:

- `company: str`
- `role: str`
- `start_date_text: str | null`
- `end_date_text: str | null`
- `duration_text: str | null`
- `responsibilities: list[str]`
- `achievements: list[str]`
- `technologies: list[str]`
- `evidence_excerpts: list[str]`
- `ambiguity_notes: list[str]`

### `projects`

Purpose: capture project evidence that may not fit cleanly into job history.

Fields per item:

- `name: str | null`
- `role: str | null`
- `summary: str`
- `technologies: list[str]`
- `domain_context: str | null`
- `evidence_excerpts: list[str]`

### `skills_inventory`

Purpose: normalized skills with evidence, not a flat string list.

Fields per item:

- `skill_name: str`
- `proficiency_signal: str | null`
- `evidence_excerpts: list[str]`
- `source_section: Literal["experience", "project", "summary", "skills", "other"]`

### `education`

Fields per item:

- `institution: str`
- `degree: str | null`
- `field_of_study: str | null`
- `graduation_text: str | null`
- `evidence_excerpts: list[str]`

### `certifications`

Fields per item:

- `name: str`
- `issuer: str | null`
- `date_text: str | null`
- `evidence_excerpts: list[str]`

### `languages`

Fields per item:

- `language_name: str`
- `proficiency_signal: str | null`
- `evidence_excerpts: list[str]`

### `profile_uncertainties`

Purpose: preserve important missing or unclear facts.

Fields per item:

- `title: BilingualText`
- `reason: BilingualText`
- `impact: BilingualText`

## Screening Response Schema

The current `CVScreeningResponse` and `CVScreeningPayload` will be replaced with a richer Phase 2
contract.

### Top-level response

```json
{
  "screening_id": "uuid",
  "jd_id": "uuid",
  "candidate_id": "uuid",
  "file_name": "candidate.pdf",
  "status": "completed",
  "created_at": "2026-04-16T10:00:00Z",
  "candidate_profile": {},
  "result": {},
  "audit": {}
}
```

### `candidate_profile`

This is a snapshot of the normalized Phase 2 candidate profile.

Reason:

- HR review should not require a second fetch to understand what the system extracted.
- Frontends can render screening and extracted profile together.
- Debugging is easier when the response carries the exact normalized input to screening.

### `result`

`result` contains the full screening artifacts.

Fields:

- `match_score: float`
- `recommendation: Literal["advance", "review", "reject"]`
- `decision_reason: BilingualText`
- `screening_summary: BilingualText`
- `knockout_assessments: list[KnockoutAssessment]`
- `minimum_requirement_checks: list[MinimumRequirementCheck]`
- `dimension_scores: list[DimensionScore]`
- `strengths: list[ScreeningInsight]`
- `gaps: list[ScreeningInsight]`
- `uncertainties: list[ScreeningUncertainty]`
- `follow_up_questions: list[FollowUpQuestion]`
- `risk_flags: list[RiskFlag]`

### `KnockoutAssessment`

Fields:

- `criterion: BilingualText`
- `status: Literal["met", "not_met", "unclear"]`
- `reason: BilingualText`
- `evidence: list[BilingualText]`

### `MinimumRequirementCheck`

Retained, but must now cover all minimum requirements the JD exposes, not one hard-coded example.

Fields:

- `criterion: BilingualText`
- `status: Literal["met", "not_met", "unclear"]`
- `reason: BilingualText`
- `evidence: list[BilingualText]`

### `DimensionScore`

Retained, but the semantics change.

Fields:

- `dimension_name: BilingualText`
- `priority: Literal["must_have", "important", "nice_to_have"]`
- `weight: float`
- `score: float`
- `reason: BilingualText`
- `evidence: list[BilingualText]`
- `confidence_note: BilingualText | null`

### `ScreeningInsight`

Used for strengths and gaps.

Fields:

- `title: BilingualText`
- `reason: BilingualText`
- `evidence: list[BilingualText]`

### `ScreeningUncertainty`

Used for review blockers or unclear evidence.

Fields:

- `title: BilingualText`
- `reason: BilingualText`
- `follow_up_suggestion: BilingualText`

### `FollowUpQuestion`

Purpose: interviewer follow-up suggestions grounded in JD-CV mismatches.

Fields:

- `question: BilingualText`
- `purpose: BilingualText`
- `linked_dimension: BilingualText | null`

### `RiskFlag`

Purpose: explicit warning markers for HR review.

Fields:

- `title: BilingualText`
- `reason: BilingualText`
- `severity: Literal["low", "medium", "high"]`

### `audit`

Purpose: safe auditability without raw prompt dumping.

Fields:

- `extraction_model: str`
- `screening_model: str`
- `profile_schema_version: str`
- `screening_schema_version: str`
- `generated_at: str`
- `reconciliation_notes: list[str]`
- `consistency_flags: list[str]`

The audit object must not expose secrets, raw prompts with credentials, or raw uploaded CV text.

## Persistence Model

The existing tables are structurally sufficient and will be retained.

### `candidate_documents`

No schema change required.

Purpose remains:

- track original uploaded file
- represent upload lifecycle state

### `candidate_profiles`

No table split is required.

Change:

- `profile_payload` will store the new Phase 2 candidate profile schema.

### `candidate_screenings`

No table split is required.

Change:

- `screening_payload` will store the new Phase 2 screening result and audit payload.

### Metadata strategy

Model names and schema versions will live inside the persisted payload first.

Reason:

- avoids unnecessary migration complexity
- keeps the API contract self-describing
- allows future schema versioning without immediate table churn

If filtering by model or schema version becomes a product requirement later, metadata can be promoted to
first-class columns in a later phase.

## LLM Responsibilities

Phase 2 uses Gemini in two isolated steps.

### Step 1: candidate profile extraction

Input:

- uploaded CV file
- MIME type

Output:

- Phase 2 candidate profile schema

Prompt requirements:

- act as a conservative recruiting analyst
- extract only claims supported by the document
- preserve strong evidence-bearing statements
- keep ambiguous or missing information explicit
- prefer omission over speculation

### Step 2: screening artifact generation

Input:

- stored `JDAnalysisPayload`
- normalized candidate profile

Output:

- full structured screening artifacts

Prompt requirements:

- act as a hiring analyst comparing one candidate to one JD
- assess objective minimum requirements first
- respect must-have versus important versus nice-to-have priorities
- surface ambiguities instead of filling gaps
- produce bilingual HR-facing text where appropriate
- keep enums and schema keys normalized in English
- return structured output only

## Deterministic Backend Guards

The model may propose a recommendation, but the backend owns the final valid response.

### Guard 1: knockout failure

If any knockout criterion is clearly `not_met`, the final recommendation must not be `advance`.

### Guard 2: must-have insufficiency

If any must-have dimension lacks sufficient evidence and is rated effectively missing, the final
recommendation must not be `advance`.

### Guard 3: weighted score integrity

The backend must verify that weighted scores are internally consistent with dimension weights and scores.
If the model returns an invalid aggregate score, the backend must recompute it.

### Guard 4: recommendation reconciliation

If the proposed recommendation conflicts with knockout status, must-have status, or score evidence, the
backend must downgrade the recommendation and record a reconciliation note in `audit.reconciliation_notes`.

### Guard 5: evidence sufficiency

When an assessment is `met` for a criterion that requires direct evidence, evidence must not be empty.
If the model omits evidence, the backend must either downgrade the status to `unclear` or reject the
payload as invalid.

### Guard 6: schema and enum integrity

All output must pass strict Pydantic validation. Invalid structured output must fail the request rather
than slipping through as a partial success.

## Scoring Strategy

Phase 2 scoring has three layers.

### 1. Requirement layer

Evaluates:

- knockout criteria
- minimum requirements
- experience requirements
- language requirements
- certifications or education requirements when relevant

### 2. Rubric layer

Uses `jd_analysis.rubric_seed.evaluation_dimensions`.

Each dimension receives:

- score
- reason
- evidence
- optional confidence note

### 3. Recommendation layer

Uses:

- knockout results
- must-have coverage
- weighted score
- uncertainty level
- risk flags

The final recommendation is the reconciled backend result, not a blind pass-through of model output.

## API Surface

Endpoints remain:

- `POST /api/v1/cv/screen`
- `GET /api/v1/cv/screenings/{screening_id}`

The response contract changes to the Phase 2 payload described above.

This is a replacement, not a compatibility layer.

## Error Handling

The backend must handle these cases explicitly:

- unsupported file type
- empty upload
- file exceeds size limit
- invalid PDF content
- invalid DOCX content
- JD analysis missing
- JD analysis not completed
- CV storage failure
- candidate profile extraction failure
- screening artifact generation failure
- structured output validation failure
- reconciliation failure that cannot produce a valid final payload

Rules:

- Do not mark the document complete if extraction or screening fails.
- Do not persist an invalid completed screening.
- Preserve candidate-facing uncertainty as `uncertainties`, not as a transport or system error.

## Testing Strategy

### Schema tests

Add and update tests for:

- candidate profile schema validation
- screening payload validation
- bilingual field shape validation
- enum validation
- audit metadata validation
- evidence object validation

### Service tests

Add and update tests for:

- successful profile extraction and screening
- knockout fail case
- must-have evidence shortfall case
- ambiguous CV case
- invalid model output case
- recommendation reconciliation case
- persistence of candidate profile and screening payload
- screening retrieval by id

### API tests

Add and update tests for:

- valid PDF upload
- valid DOCX upload
- unsupported file type
- invalid file content
- empty upload
- missing JD
- response shape includes candidate profile, result, and audit

### Test philosophy

Tests should verify:

- behavior
- payload invariants
- reconciliation rules
- persistence integrity

Tests should not depend on live Gemini calls.

## Files to Change

### Primary backend files

- `backend/src/schemas/cv.py`
- `backend/src/services/cv_extractor.py`
- `backend/src/services/cv_screening_service.py`
- `backend/src/api/v1/cv.py`
- `backend/src/models/cv.py` only if payload metadata changes require it

### Test files

- `backend/tests/schemas/test_cv_schema.py`
- `backend/tests/services/test_cv_screening_service.py`
- `backend/tests/api/test_cv_api.py`

### Supporting files

- `backend/src/services/__init__.py` if exports change
- `backend/src/schemas/__init__.py` if exports change
- `backend/src/config.py` only if the screening step needs new settings or model overrides

## Migration Stance

Phase 2 replaces the current MVP screening contract.

Rules:

- no backward-compatibility shim for the old response shape
- no duplicate old and new screening payloads
- tests updated to the new contract
- frontend adaptation is out of scope for this backend-only phase

## Success Criteria

Phase 2 backend is complete when:

- a CV can be uploaded against a completed JD analysis
- the backend extracts a review-ready candidate profile
- the backend generates structured screening artifacts through Gemini
- deterministic backend guards enforce knockout, must-have, and score consistency
- the final response includes candidate profile, result, and audit sections
- the screening payload is persisted and retrievable by id
- targeted schema, service, and API tests pass against the new contract
