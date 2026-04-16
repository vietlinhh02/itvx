# CV Screening Phase 2 Design

## Goal

Build the second production-ready module for InterviewX after JD analysis. This phase accepts one uploaded CV for an existing analyzed JD, extracts a structured candidate profile, evaluates the candidate against the stored JD analysis, and returns an evidence-backed screening result for HR review.

This phase is decision support only. It does not rank multiple candidates, generate interview plans, or trigger downstream actions automatically.

## Scope

This phase includes:

- CV upload for an existing `jd_id`
- Support for `PDF` and `DOCX` CV inputs
- Original CV file storage with metadata
- Gemini-driven CV extraction through LangChain
- Persisted candidate profile extracted from the CV
- Persisted screening result linked to one JD and one candidate profile
- Evidence-backed screening output with requirement checks, dimension scores, strengths, gaps, and uncertainties
- HR-facing bilingual explanatory fields where the result is read directly by humans

This phase does not include:

- Batch CV upload
- Candidate ranking or shortlist generation
- Interview question generation
- Interview scheduling
- Automatic advance or reject actions
- HR feedback loop tuning
- Anti-cheating features

## Product Position in the Workflow

The product document describes the hiring flow as:

1. HR uploads a JD
2. The system analyzes the JD and creates the hiring blueprint
3. HR uploads a CV
4. The system screens the CV against the JD
5. HR reviews the result before deciding who moves forward

This phase implements step 4. It sits directly on top of the existing JD analysis module.

## Architecture

Phase 2 extends the current FastAPI backend instead of introducing a new service. It reuses the same architectural style established in JD analysis.

The AI stack for this phase is:

- FastAPI for request handling
- LangChain for model orchestration and structured output binding
- Gemini as the underlying LLM
- Pydantic as the output contract and validation layer
- SQLAlchemy async ORM for persistence

The request flow is:

1. HR uploads one CV to `POST /api/v1/cv/screen` with a `jd_id`
2. Backend validates the file type, size, and basic file signature
3. Backend verifies that the referenced JD exists and has a completed analysis
4. Backend stores the original CV file and creates a `candidate_documents` record
5. `CVExtractionService` extracts a structured candidate profile from the stored CV
6. `CVScreeningService` loads the persisted JD analysis for the given `jd_id`
7. The screening service evaluates the candidate profile against JD requirements and rubric dimensions
8. Backend validates the screening payload
9. Backend stores the candidate profile and screening result
10. API returns the completed screening response to the caller

## Design Principles

This phase follows five principles.

### Evidence over assertion

The screening result should not make claims without support. Every important positive or negative judgment should include evidence from the CV when possible.

### Uncertainty over invention

When the CV does not provide enough support for a requirement, the system should mark the result as unclear instead of guessing.

### Decision support, not auto-rejection

The system may recommend `advance`, `review`, or `reject`, but the result is for HR review. The product should not present screening as a final hiring decision.

### Reusable extracted data

The extracted candidate profile should be stored separately from the screening result. This keeps CV extraction reusable for later phases.

### Compatibility with existing JD analysis

The screening logic must consume the persisted JD analysis structure that already exists, especially:

- `requirements`
- `rubric_seed`
- `screening_rules`
- `ambiguities_for_human_review`

## Components

### API layer

Primary endpoint:

- `POST /api/v1/cv/screen`
- Accepts one CV file and one `jd_id`
- Rejects unsupported, empty, oversized, or invalid files early
- Rejects unknown or incomplete JD references early
- Returns the stored candidate id, file metadata, status, and screening payload

Read endpoint:

- `GET /api/v1/cv/screenings/{screening_id}`
- Returns one persisted screening result for later review in the dashboard

### CV file storage layer

- Stores the original uploaded CV file on disk
- Tracks metadata needed for later retrieval and auditing
- Keeps file lifecycle separate from extracted profile lifecycle

### CV extraction layer

- Uses LangChain and Gemini to convert a CV into a structured candidate profile
- Extracts the data needed for evaluation instead of returning raw free-form summaries
- Must avoid inventing missing qualifications

### CV screening layer

- Loads the persisted JD analysis for the given `jd_id`
- Evaluates the candidate profile against requirement checks and rubric dimensions
- Produces an evidence-backed screening result with uncertainty handling
- Persists one screening result per candidate profile and JD pair

## Data Model

### `candidate_documents`

Stores the original uploaded CV and its upload lifecycle.

Fields:

- `id`
- `file_name`
- `mime_type`
- `storage_path`
- `status`
- `created_at`
- `updated_at`

### `candidate_profiles`

Stores the structured CV extraction result.

Fields:

- `id`
- `candidate_document_id`
- `profile_payload` as `JSONB`
- `created_at`

### `candidate_screenings`

Stores the screening result for one candidate profile against one JD.

Fields:

- `id`
- `jd_document_id`
- `candidate_profile_id`
- `model_name`
- `screening_payload` as `JSONB`
- `created_at`

This split keeps three concerns separate:

- raw upload storage
- candidate profile extraction
- JD-specific evaluation

It also allows future phases to rescreen the same candidate profile against another JD without re-uploading the CV.

## Candidate Profile Contract

The extracted profile should be structured enough to support scoring, auditing, and reuse.

### Top-level sections

- `candidate_summary`
- `experience`
- `skills`
- `education`
- `certifications`
- `languages`
- `projects_or_achievements`

### Extraction behavior

- Prefer normalized structured values over narrative summaries
- Keep uncertain information as missing or partial data
- Do not infer seniority, ownership, or domain depth without support in the CV

## Screening Output Contract

Top-level response:

```json
{
  "screening_id": "uuid",
  "jd_id": "uuid",
  "candidate_id": "uuid",
  "file_name": "nguyen-van-a-cv.pdf",
  "status": "completed",
  "created_at": "2026-04-16T12:00:00Z",
  "result": {}
}
```

The `result` object contains six sections.

### 1. Overall decision

Fields:

- `match_score` as a float from `0.0` to `1.0`
- `recommendation` as `advance | review | reject`
- `decision_reason` as bilingual text

This section gives HR a quick summary without hiding the detailed evidence.

### 2. Minimum requirement checks

Each minimum requirement check includes:

- `criterion` as bilingual text
- `status` as `met | not_met | unclear`
- `reason` as bilingual text
- `evidence` as bilingual text list

These checks are derived primarily from:

- `requirements`
- `screening_rules.minimum_requirements`
- objective knockout criteria that can be assessed from a CV

`unclear` is a first-class outcome. Missing evidence must not be treated as a hard failure by default.

### 3. Dimension scores

Each scored dimension includes:

- `dimension_name` as bilingual text
- `priority` as `must_have | important | nice_to_have`
- `weight` as a float
- `score` as a float from `0.0` to `1.0`
- `reason` as bilingual text
- `evidence` as bilingual text list

These dimensions are derived from the stored JD `rubric_seed.evaluation_dimensions`.

### 4. Strengths

Each strength includes:

- `title` as bilingual text
- `reason` as bilingual text
- `evidence` as bilingual text list

This section helps HR see the strongest positive signals quickly.

### 5. Gaps

Each gap includes:

- `title` as bilingual text
- `reason` as bilingual text
- `evidence` as bilingual text list

A gap may reflect either a clear mismatch or a notable absence of support for a desired area.

### 6. Uncertainties

Each uncertainty includes:

- `title` as bilingual text
- `reason` as bilingual text
- `follow_up_suggestion` as bilingual text

This section captures the places where the system cannot conclude safely from the CV alone.

## Bilingual Output Rules

Schema keys stay English-only.

Field values follow these rules:

- machine enums stay English-only
- HR-facing explanations are bilingual
- evidence is bilingual when it appears in screening output
- raw normalized profile fields may stay non-bilingual when they are not shown directly to HR

This keeps the payload predictable for downstream systems while preserving a readable HR experience.

## Prompt Strategy

The extractor prompt should position Gemini as a conservative recruiting analyst.

It must instruct Gemini to:

- extract only what the CV supports
- separate demonstrated experience from implied potential
- prefer `unclear` over unsupported claims
- preserve evidence snippets that justify scoring
- evaluate against the stored JD analysis instead of scoring in the abstract
- keep recommendation as decision support for HR

The schema and prompt together should prefer incomplete but defensible output over polished hallucinations.

## Scoring Strategy

The screening service should combine three signals.

### Minimum requirement status

The service should determine whether the candidate clearly meets, clearly misses, or does not provide enough support for each minimum requirement.

### Weighted dimension scores

The service should score each rubric dimension separately and combine them according to the stored JD weights.

### Uncertainty level

The service should lower confidence when too many important areas are unclear, even if the candidate shows some strong signals.

### Recommendation mapping

The mapping should follow these rules.

- `advance`
  - passes the key minimum requirements
  - has strong weighted performance on important dimensions
  - has enough evidence for core must-have areas
- `review`
  - has mixed evidence
  - or leaves important requirements unclear
  - or performs adequately without enough confidence for advance
- `reject`
  - clearly fails important minimum requirements
  - or performs materially below the threshold on core must-have areas

The recommendation should never be based on one aggregate score alone.

## Validation Rules

The backend should enforce these constraints after the model returns structured output:

- `match_score` must be between `0.0` and `1.0`
- every minimum requirement check status must be `met`, `not_met`, or `unclear`
- every dimension score must be between `0.0` and `1.0`
- returned dimensions must align with the JD rubric dimensions
- bilingual explanation fields must match the expected bilingual shape
- recommendation must be `advance`, `review`, or `reject`

If the screening payload fails validation, the request should not be marked complete.

## Error Handling

The module should handle these cases explicitly:

- unsupported file type
- empty upload
- file exceeds allowed size
- file content does not match content type
- unknown `jd_id`
- known `jd_id` without a completed JD analysis
- CV storage failure
- CV extraction failure
- screening generation failure
- screening validation failure
- partially informative CV with missing evidence

When the CV is incomplete, the preferred behavior is to return a completed screening with populated `uncertainties` instead of failing the request.

Suggested status mapping:

- `400` for invalid upload input
- `404` for missing JD references
- `409` for JDs that exist but are not ready for screening
- `500` or `502` for internal extraction or model failures

## Testing Strategy

Phase 2 should be covered at three layers.

### Schema tests

- bilingual field validation
- enum validation
- match score range validation
- minimum requirement status validation
- dimension score validation
- recommendation validation

### Service tests

- successful screening against a completed JD
- missing JD
- JD without completed analysis
- CV extraction with partial candidate evidence
- screening result that produces uncertainties
- recommendation mapping for `advance`, `review`, and `reject`
- persistence of candidate document, profile, and screening records

### API tests

- valid PDF upload with valid `jd_id`
- valid DOCX upload with valid `jd_id`
- unsupported upload type
- empty file upload
- invalid file signature
- unknown `jd_id`
- JD exists but is not ready
- success response shape

### UI expectations

The JD detail experience should let HR:

- upload one CV for the current JD
- review the overall decision
- inspect minimum checks
- inspect dimension-level scoring
- review strengths, gaps, and uncertainties

## Frontend Implications

The existing JD detail flow should become the launch point for CV screening.

The UI should add:

- one CV upload action scoped to the current JD
- a screening result panel under the JD analysis
- visual separation between recommendation, evidence, and uncertainties
- wording that makes it clear the result is an AI recommendation for HR review

## Success Criteria

Phase 2 is successful when:

- HR can upload one CV for an existing analyzed JD
- the original CV file is stored successfully
- the candidate profile is extracted successfully
- the screening result is persisted successfully
- the response contains evidence-backed requirement checks and dimension scores
- the response distinguishes clear failures from unclear evidence
- HR can use the result to decide whether the candidate deserves manual review or the next step

## Design Decisions

### Why keep Phase 2 to one CV at a time

Single-CV screening keeps the phase narrow and makes the result easier to validate. Batch ranking can come later after the single-candidate contract is stable.

### Why store candidate profile separately from screening result

A CV profile is reusable. A screening result is JD-specific. Keeping them separate prevents rework and supports later phases cleanly.

### Why include uncertainties explicitly

CVs often omit important context. A good screening system should surface uncertainty instead of turning silence into negative evidence.

### Why include minimum checks and dimension scores

Recruiters need both. Minimum checks explain gating logic. Dimension scores explain overall fit quality. One without the other makes the result harder to trust.

## Open Questions Resolved

- Phase 2 covers CV screening only, not shortlist or interview planning.
- The result should be more complete than a thin scorecard.
- The result should include evidence and uncertainty handling.
- Recommendation remains decision support for HR rather than an automatic action.
