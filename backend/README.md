# InterviewX Backend

Multi-Agent Interview Platform Backend built with FastAPI and SQLAlchemy.

## Development Setup

1. Install dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```

2. Start PostgreSQL with Docker Compose:
   ```bash
   docker compose up -d postgres
   ```

3. Run the development server locally with uv:
   ```bash
   uvicorn src.main:app --reload
   ```

## JD Analysis

The backend exposes `POST /api/v1/jd/analyze` for upload-only JD analysis.

Supported files:

- PDF
- DOCX

Relevant environment variables:

- `GEMINI_API_KEY`
- `GEMINI_MODEL` for overriding the default Gemini model
- `JD_UPLOAD_DIR` for overriding where uploaded JD files are stored
- `JD_MAX_UPLOAD_SIZE_BYTES` for overriding the upload size limit

## CV Screening

The backend exposes `POST /api/v1/cv/screen` for one-CV screening against an existing analyzed JD.

Supported files:

- PDF
- DOCX

Required request fields:

- `jd_id`
- `file`

Relevant environment variables:

- `CV_UPLOAD_DIR`
- `CV_MAX_UPLOAD_SIZE_BYTES`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

## Project Structure

- `api/` - API routes and endpoints
- `models/` - SQLAlchemy database models
- `schemas/` - Pydantic data models
- `services/` - Business logic services
- `agents/` - LangChain agent implementations
- `tests/` - Test suite
