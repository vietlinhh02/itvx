#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
session_id="${1:?interview session id is required}"
room_name="${2:?interview room name is required}"
opening_question="${3:?opening question is required}"
worker_token="${4:?livekit worker token is required}"

exec "$repo_root/backend/src/scripts/launch_interview_worker.sh" "$session_id" "$room_name" "$opening_question" "$worker_token"
