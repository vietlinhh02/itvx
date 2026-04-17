# Background JD Analysis and CV Screening Design

## Goal

Move JD analysis and CV screening off the request path so uploads return immediately, while a background worker processes AI tasks and updates resource state in the database.

## Problem

Today both flows run synchronously inside the API request:

- `POST /api/v1/jd/analyze`
- `POST /api/v1/cv/screen`

That keeps the HTTP request open while the backend stores files, calls AI models, writes records, and builds the final response. The result is slow requests, poor UX, and fragile behavior for long-running tasks.

## Decision

Use a database-backed job queue with a separate worker process.

The API will validate input, create resource records in `processing` state, enqueue a background job, and return `202 Accepted` immediately. A worker process will poll queued jobs, run the existing JD analysis or CV screening logic, and update both the job row and the resource row when work finishes.

## Why this approach

### Chosen approach: DB-backed jobs + worker poller

This approach fits the current codebase well.

- The project already uses the database as the main source of truth.
- It avoids adding Redis, Celery, or other infrastructure now.
- Jobs survive API restarts because they are persisted in the database.
- It supports retries, failure states, and inspection later.

### Rejected approach: in-process background tasks

FastAPI `BackgroundTasks` or `asyncio.create_task()` would be simpler, but they are not durable. If the API process restarts, jobs can be lost. That is a bad fit for AI work and uploaded files.

### Rejected approach: external queue now

A Redis or Celery stack is a valid long-term option, but it adds infrastructure and operational cost that the project does not need yet.

## Architecture

### API layer

The API request path will do only short, deterministic work:

1. Validate file type and content.
2. Store the uploaded file.
3. Create the resource row with `status="processing"`.
4. Create a `background_job` row.
5. Return `202 Accepted` with both the job id and the resource id.

The API will no longer call the AI extractor or screening model directly.

### Worker layer

A separate worker process will:

1. Poll the `background_jobs` table.
2. Claim one queued job safely.
3. Run the matching service logic.
4. Update the job status and resource status.
5. Persist either the completed result or the failure message.

### Read layer

The frontend will use two read paths:

- poll `GET /api/v1/jobs/{job_id}` to track background progress
- fetch `GET /api/v1/jd/{jd_id}` or `GET /api/v1/cv/screenings/{screening_id}` after completion

## Data model

Add a new `background_jobs` table.

### Fields

- `id`
- `job_type`
  - `jd_analysis`
  - `cv_screening`
- `status`
  - `queued`
  - `running`
  - `completed`
  - `failed`
- `resource_type`
  - `jd_document`
  - `candidate_screening`
- `resource_id`
- `payload`
- `error_message`
- `started_at`
- `completed_at`
- `created_at`
- `updated_at`

### Payload shape

The payload should contain only the inputs the worker needs to continue processing without depending on request memory.

For JD analysis, payload should include:

- `jd_id`
- `file_name`
- `mime_type`
- `storage_path`

For CV screening, payload should include:

- `screening_id`
- `jd_id`
- `candidate_document_id`
- `candidate_profile_id` if already created
- `file_name`
- `mime_type`
- `storage_path`

## Resource state rules

### JD document

`jd_documents.status` should support:

- `processing`
- `completed`
- `failed`

### Candidate screening

CV screening needs an explicit persisted status as well. The current model stores result payload but does not expose a persisted screening status field. Add one so the worker can mark progress directly.

`candidate_screenings.status` should support:

- `processing`
- `completed`
- `failed`

This change keeps the resource state explicit and avoids deriving status indirectly from payload presence.

## API behavior

### `POST /api/v1/jd/analyze`

New behavior:

1. Validate upload.
2. Store file.
3. Create `jd_document(status="processing")`.
4. Create `background_job(job_type="jd_analysis")`.
5. Return `202 Accepted`.

Response shape:

```json
{
  "job_id": "job-uuid",
  "jd_id": "jd-uuid",
  "file_name": "backend-engineer.pdf",
  "status": "processing"
}
```

### `POST /api/v1/cv/screen`

New behavior:

1. Validate upload.
2. Verify the referenced JD exists and is ready.
3. Store candidate file.
4. Create candidate document and extracted-profile placeholder strategy required by the worker design.
5. Create `candidate_screening(status="processing")`.
6. Create `background_job(job_type="cv_screening")`.
7. Return `202 Accepted`.

Response shape:

```json
{
  "job_id": "job-uuid",
  "screening_id": "screening-uuid",
  "jd_id": "jd-uuid",
  "file_name": "candidate.pdf",
  "status": "processing"
}
```

### `GET /api/v1/jobs/{job_id}`

Add a new status endpoint for polling.

Response shape:

```json
{
  "job_id": "job-uuid",
  "job_type": "cv_screening",
  "status": "running",
  "resource_type": "candidate_screening",
  "resource_id": "screening-uuid",
  "error_message": null,
  "started_at": "2026-04-16T14:00:00Z",
  "completed_at": null
}
```

When complete, the frontend can redirect or refetch the final resource by `resource_id`.

## Worker behavior

### Job claiming

The worker must claim jobs safely so two workers do not process the same row.

Use a database-safe claim pattern, such as:

- select one queued row ordered by `created_at`
- update it to `running`
- set `started_at`
- commit before doing AI work

The exact locking strategy should follow what the project database supports cleanly.

### JD analysis execution

The worker should:

1. Load the queued job.
2. Load the referenced JD document.
3. Run JD extraction.
4. Write the `jd_analyses` row.
5. Set document `status="completed"`.
6. Set job `status="completed"` and `completed_at`.

On failure:

- set document `status="failed"`
- set job `status="failed"`
- store `error_message`

### CV screening execution

The worker should:

1. Load the queued job.
2. Load the referenced JD analysis and candidate file.
3. Extract or load the candidate profile, depending on the final enqueue design.
4. Run screening.
5. Persist screening payload.
6. Set screening `status="completed"`.
7. Set candidate document `status="completed"` if that document tracks screening lifecycle.
8. Set job `status="completed"`.

On failure:

- set screening `status="failed"`
- set job `status="failed"`
- store `error_message`

## Service boundaries

### JD service

Split the current JD flow into two responsibilities:

- **enqueue path**: create file, document row, and background job
- **worker path**: perform extraction and finalize DB state

### CV screening service

Split the current CV flow the same way:

- **enqueue path**: validate request, persist upload state, create screening row, enqueue job
- **worker path**: perform extraction and screening, then finalize result state

The existing synchronous methods contain most of the business logic already. The implementation should extract reusable inner methods instead of duplicating logic.

## Frontend behavior

### Upload UX

After upload:

- show immediate `processing` state
- store both `job_id` and `resource_id`
- poll job status endpoint

### Completion UX

When a job reaches `completed`:

- JD flow: open or refresh the JD detail page using `jd_id`
- CV flow: open or refresh the screening detail page using `screening_id`

### Failure UX

When a job reaches `failed`:

- show the failure state in the UI
- display a short error message
- offer retry from the upload screen or resource screen

## Error handling

The system should fail explicitly.

- request validation errors stay synchronous and return `4xx`
- background execution errors become persisted job failures
- resource records should never remain stuck in `processing` after a handled failure

Worker errors should be stored with enough context to debug the failing stage, but the API should expose a concise user-facing message.

## Testing

### Backend tests

Add tests for:

- JD enqueue API returns `202` and creates a job row
- CV enqueue API returns `202` and creates a job row
- worker completes JD jobs and updates status correctly
- worker completes CV screening jobs and updates status correctly
- worker failure updates both job and resource to `failed`
- job status endpoint returns the expected state transitions

### Frontend tests

Add tests for:

- upload flow enters `processing`
- polling transitions to `completed`
- polling transitions to `failed`
- navigation uses returned `resource_id`

## Migration impact

This change requires schema changes.

- add `background_jobs` table
- add persisted status field to `candidate_screenings`
- update any response schemas that currently assume synchronous completion

The implementation should keep old read endpoints working for completed records while changing write endpoints to async behavior.

## Scope boundaries

This design does not include:

- retries with exponential backoff
- job priority queues
- job cancellation
- Redis or Celery integration
- multi-tenant scheduling logic

Those can come later if needed.

## Success criteria

The design is successful when:

- JD upload returns quickly with `202`, `job_id`, and `jd_id`
- CV upload returns quickly with `202`, `job_id`, and `screening_id`
- AI work runs in a background worker, not in the API request
- completed records remain readable through existing detail endpoints
- failed jobs are visible and do not leave resources stuck in `processing`
