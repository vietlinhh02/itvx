#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
worker_root="$repo_root/worker"
env_file="${ENV_FILE:-$repo_root/.env}"
session_id="${1:?interview session id is required}"
room_name="${2:?interview room name is required}"
opening_question="${3:?opening question is required}"
worker_token="${4:?livekit worker token is required}"

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

worker_callback_secret="${WORKER_CALLBACK_SECRET:-$(derive_local_secret worker-callback)}"

export INTERVIEW_SESSION_ID="$session_id"
export INTERVIEW_ROOM_NAME="$room_name"
export OPENING_QUESTION="$opening_question"
export LIVEKIT_WORKER_TOKEN="$worker_token"

cd "$worker_root"
BACKEND_CALLBACK_SECRET="${BACKEND_CALLBACK_SECRET:-$worker_callback_secret}" uv run python -m src.agent
