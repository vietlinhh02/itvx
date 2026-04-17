#!/usr/bin/env bash
set -euo pipefail

repo_root="/home/eddiesngu/Desktop/Dang/interviewx"

set -a
# shellcheck disable=SC1091
source "$repo_root/.env"
set +a

cd "$repo_root/worker"
BACKEND_CALLBACK_SECRET="${WORKER_CALLBACK_SECRET}" uv run python -m src.worker_server
