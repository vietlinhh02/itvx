# JD Analysis Phase 1 Design

## Goal

Build the first production-ready JD analysis module for InterviewX. This phase accepts an uploaded JD
file, stores the original document, sends it to Gemini through LangChain for structured extraction,
and returns a validated hiring blueprint that downstream CV screening can use consistently.

In this design, LangChain is the AI orchestration layer and Gemini is the underlying LLM.

## Scope

This phase includes:

- Upload-only JD intake
- Support for `PDF` and `DOCX` inputs
- Original file storage with metadata
- Gemini-driven structured extraction via LangChain
- Persisted analysis output for later reuse
- Bilingual HR-facing values in the analysis payload
- A rubric seed that can be used to score CVs objectively

This phase does not include:

- Raw text submission
- Background processing or async job orchestration
- Vector storage
- Full interview scorecard generation
- HR editing workflows
- Analysis versioning beyond the initial document-analysis split

## Architecture

Phase 1 fits into the existing FastAPI backend rather than introducing a separate service.

The AI stack for this phase is:

- FastAPI for request handling
- LangChain for model orchestration and structured output binding
- Gemini as the underlying LLM
- Pydantic as the output contract and validation layer

The request flow is:

1. HR uploads a JD file to `POST /api/v1/jd/analyze`
2. Backend validates file type and size
3. Backend stores the original file and creates a `jd_documents` record with `status="processing"`
4. `JDAnalysisService` orchestrates extraction
5. `GeminiJDExtractor` sends the file to Gemini through LangChain with a strict Pydantic schema
6. Backend validates the structured response again after model return
7. Backend stores the analysis payload in `jd_analyses`
8. API returns the completed analysis payload to the caller

## Components

### API layer

- Endpoint: `POST /api/v1/jd/analyze`
- Accepts one uploaded file
- Rejects unsupported or empty files early
- Returns the stored document id, file metadata, status, and analysis payload

### File storage layer

- Stores the original uploaded file on the backend storage path
- Tracks metadata needed for later retrieval and auditability
- Keeps file lifecycle separate from extracted analysis lifecycle

### JD analysis service

- Coordinates storage, extraction, validation, and persistence
- Shields the API layer from LangChain and Gemini integration details
- Produces one normalized response contract regardless of input file type

### Gemini extractor

- Uses LangChain as the model orchestration layer
- Uses Gemini as the underlying LLM through LangChain's Google GenAI integration
- Reads the uploaded JD file directly wherever possible
- Extracts job overview, requirements, and rubric seed data
- Must avoid filling gaps with fabricated assumptions

## Data Model

### `jd_documents`

Stores the original file and its upload lifecycle.

Fields:

- `id`
- `file_name`
- `mime_type`
- `storage_path`
- `status`
- `created_at`
- `updated_at`

### `jd_analyses`

Stores the structured Gemini result.

Fields:

- `id`
- `jd_document_id`
- `model_name`
- `analysis_payload` as `JSONB`
- `created_at`

This split allows future re-analysis without re-uploading the original file.

## Output Contract

Top-level response:

```json
{
  "jd_id": "uuid",
  "file_name": "backend-engineer.pdf",
  "status": "completed",
  "created_at": "2026-04-16T10:00:00Z",
  "analysis": {}
}
```

The `analysis` object contains three sections.

### `job_overview`

HR-facing role summary fields.

- Human-readable values are bilingual using `{ "vi": "...", "en": "..." }`
- Machine enums remain English-only

Representative fields:

- `job_title`
- `department`
- `seniority_level`
- `location`
- `work_mode`
- `role_summary`
- `company_benefits`

### `requirements`

Structured requirements used for CV screening.

- `required_skills`
- `preferred_skills`
- `tools_and_technologies`
- `experience_requirements`
- `education_and_certifications`
- `language_requirements`
- `key_responsibilities`
- `screening_knockout_criteria`

### `rubric_seed`

Structured scoring blueprint for downstream candidate evaluation.

- `evaluation_dimensions`
- `screening_rules`
- `ambiguities_for_human_review`

Each `evaluation_dimension` includes:

- `name` as bilingual text
- `description` as bilingual text
- `priority` as `must_have | important | nice_to_have`
- `weight` as a float
- `evidence_signals` as bilingual text list

## Bilingual Output Rules

Schema keys are English-only.

Field values follow these rules:

- Normalized enums stay English-only
- HR-facing descriptive text is bilingual
- Evidence and explanation fields are bilingual when surfaced in UI or review flows

This keeps the payload clean for downstream systems while allowing HR users to read the results in
Vietnamese or English.

## Prompt Strategy

The extractor prompt should position Gemini as a hiring analyst rather than a summarizer.

Implementation-wise, the prompt is constructed and executed through LangChain, not by calling Gemini in
an ad hoc way from the API layer.

It must instruct Gemini to:

- read the JD as both recruiter and hiring manager
- separate required from preferred criteria
- extract only job-relevant evaluation factors
- generate a rubric seed suitable for CV screening
- avoid subjective, speculative, or legally risky assumptions
- output bilingual HR-facing text values where appropriate
- keep machine enums normalized in English
- record unclear points under `ambiguities_for_human_review` instead of guessing

The schema and prompt together should prefer empty fields over hallucinated content.

## Validation Rules

The backend should enforce these constraints after Gemini returns structured output:

- total rubric `weight` equals `1.0`
- at least one dimension has `priority="must_have"`
- total `evaluation_dimensions` count stays between `4` and `6`
- knockout criteria are objective and job-related
- invalid bilingual field shapes are rejected

If the returned payload fails validation, the request should not be marked complete.

## Error Handling

The module should handle the following cases explicitly:

- unsupported file type
- empty upload
- storage failure
- Gemini upload or parsing failure
- structured output validation failure
- partially clear JD with missing requirements

When the JD is unclear, the preferred behavior is to preserve uncertainty in
`ambiguities_for_human_review` rather than over-infer requirements.

## Testing Strategy

Phase 1 should be covered at three layers.

### Schema tests

- bilingual field shape validation
- enum validation
- rubric weight validation
- evaluation dimension count validation

### Service tests

- successful Gemini response
- invalid Gemini response
- ambiguous JD response
- persistence of stored document and analysis records

### API tests

- valid PDF upload
- valid DOCX upload
- unsupported file upload
- empty file upload
- success response shape

Mock Gemini in tests for deterministic validation. Do not depend on live model calls in the test suite.

## Design Decisions

### Why upload-only input

Restricting Phase 1 to file upload keeps the interface narrow and aligns with the product workflow where
HR uploads actual JD documents. It also avoids carrying extra parsing branches before the core pipeline is stable.

### Why store both document and analysis

The original file is needed for traceability and potential re-processing. The extracted analysis is needed for
CV screening, later rubric refinement, and future interview planning.

### Why add `rubric_seed` in Phase 1

Simple JD extraction is not enough for objective CV screening. The system needs explicit priorities,
weights, evidence signals, and knockout rules so downstream evaluation does not rely on ad hoc prompt logic.

## Success Criteria

Phase 1 is successful when:

- a JD file can be uploaded through the backend API
- the original file is stored successfully
- Gemini returns a validated structured payload
- the payload includes bilingual HR-facing text and English schema keys
- the analysis can directly support downstream CV screening logic
