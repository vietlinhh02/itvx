#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run --project worker python -m src.agent
