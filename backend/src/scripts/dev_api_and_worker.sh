#!/usr/bin/env bash
set -euo pipefail

repo_root="/home/eddiesngu/Desktop/Dang/interviewx"
if [[ -f "$repo_root/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$repo_root/.env"
  set +a
fi

required_env=(
  LIVEKIT_URL
  LIVEKIT_API_KEY
  LIVEKIT_API_SECRET
  GEMINI_API_KEY
  WORKER_CALLBACK_SECRET
)

for name in "${required_env[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required environment variable: %s\n' "$name" >&2
    exit 1
  fi
done

cleanup() {
  if [[ -n "${api_pid:-}" ]]; then
    kill "$api_pid" 2>/dev/null || true
  fi
  if [[ -n "${job_worker_pid:-}" ]]; then
    kill "$job_worker_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

(
  cd "/home/eddiesngu/Desktop/Dang/interviewx/backend"
  APP_ENV=local uv run python - <<'PY'
import logging

import uvicorn

logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

uvicorn.run("src.main:app", host="0.0.0.0", port=8000, log_level="info")
PY
) &
api_pid=$!

(
  cd "/home/eddiesngu/Desktop/Dang/interviewx/backend"
  APP_ENV=local uv run python - <<'PY'
import logging

from src.scripts.run_background_jobs import main

logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

main_logger = logging.getLogger("src.scripts.run_background_jobs")
main_logger.setLevel(logging.INFO)

import asyncio
asyncio.run(main())
PY
) &
job_worker_pid=$!

wait "$api_pid" "$job_worker_pid"
