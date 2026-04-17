#!/usr/bin/env bash
set -euo pipefail

repo_root="/home/eddiesngu/Desktop/Dang/interviewx"
session_id="${1:?interview session id is required}"
room_name="${2:?interview room name is required}"
opening_question="${3:?opening question is required}"
worker_token="${4:?livekit worker token is required}"

set -a
# shellcheck disable=SC1091
source "$repo_root/.env"
set +a

export INTERVIEW_SESSION_ID="$session_id"
export INTERVIEW_ROOM_NAME="$room_name"
export OPENING_QUESTION="$opening_question"
export LIVEKIT_WORKER_TOKEN="$worker_token"

cd "$repo_root/worker"
BACKEND_CALLBACK_SECRET="${WORKER_CALLBACK_SECRET}" uv run python -m src.agent
