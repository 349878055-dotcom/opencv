#!/usr/bin/env bash
# 一张图快验：E(t) + 四通道全量（04 或从 02 即时算）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=s01_env.sh
source "$ROOT/scripts/s01_env.sh"
PY="${VENV_PYTHON:-python3}"
OPEN_IT=0
[[ "${1:-}" == "--open" ]] && OPEN_IT=1
ARGS=()
[[ "$OPEN_IT" == 1 ]] && ARGS+=(--open)
OUT="$("$PY" gaze_engine/preview_dense04_quick.py "${ARGS[@]}")"
echo "预览副本 → $ECURSOR_GAZE_ROOT/预览/快验_04全量.png"
echo "看图：一眼 E(t) 是否对 + 眉/眼/眯 是否随能量动（死平=编译有问题）"
