#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
backend_root="$repo_root/backend"
env_file="${ENV_FILE:-$repo_root/.env}"

derive_local_secret() {
  python3 - "$repo_root" "$1" <<'PY'
import hashlib
import sys

repo_root = sys.argv[1]
purpose = sys.argv[2]
print(hashlib.sha256(f"interviewx:{purpose}:{repo_root}".encode()).hexdigest())
PY
}

if [[ -f "$env_file" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$env_file"
  set +a
fi

required_env=(
  LIVEKIT_URL
  LIVEKIT_API_KEY
  LIVEKIT_API_SECRET
  GEMINI_API_KEY
)

for name in "${required_env[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required environment variable: %s\n' "$name" >&2
    exit 1
  fi
done

worker_callback_secret="${WORKER_CALLBACK_SECRET:-$(derive_local_secret worker-callback)}"

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
  cd "$backend_root"
  APP_ENV=local WORKER_CALLBACK_SECRET="$worker_callback_secret" uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
) &
api_pid=$!

(
  cd "$backend_root"
  APP_ENV=local WORKER_CALLBACK_SECRET="$worker_callback_secret" uv run python -m src.scripts.run_background_jobs
) &
job_worker_pid=$!

wait "$api_pid" "$job_worker_pid"
