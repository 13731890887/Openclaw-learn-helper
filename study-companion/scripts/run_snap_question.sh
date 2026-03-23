#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

source .venv/bin/activate
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

python study-companion/scripts/snap_question.py \
  --memory-mode auto \
  --max-width 1200 \
  --max-height 1200 \
  "$@"
