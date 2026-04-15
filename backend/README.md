# InterviewX Backend

Multi-Agent Interview Platform Backend built with FastAPI and SQLAlchemy.

## Development Setup

1. Install dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```

2. Run the development server:
   ```bash
   uvicorn src.main:app --reload
   ```

## Project Structure

- `api/` - API routes and endpoints
- `models/` - SQLAlchemy database models
- `schemas/` - Pydantic data models
- `services/` - Business logic services
- `agents/` - LangChain agent implementations
- `tests/` - Test suite
