#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
worker_root="$repo_root/worker"
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

worker_callback_secret="${WORKER_CALLBACK_SECRET:-$(derive_local_secret worker-callback)}"

cd "$worker_root"
BACKEND_CALLBACK_SECRET="${BACKEND_CALLBACK_SECRET:-$worker_callback_secret}" uv run python -m src.worker_server
