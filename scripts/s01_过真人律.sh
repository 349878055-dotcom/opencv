#!/usr/bin/env bash
# 交付链：稀疏草稿 → Python 补针 → 真人默认律 → 烘焙 02 定稿
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=s01_env.sh
source "$ROOT/scripts/s01_env.sh"

SPARSE_IN="${1:-$ECURSOR_SPARSE_JSON}"
OUT="${2:-$ECURSOR_GAZE_ROOT/指令/02_烘焙_真人律.json}"
PACKET="${3:-}"

ARGS=(--sparse "$SPARSE_IN" -o "$OUT")
if [[ -n "$PACKET" ]]; then
  ARGS+=(--packet "$PACKET")
fi

exec python3 "$ROOT/gaze_engine/delivery_pipeline.py" "${ARGS[@]}"
