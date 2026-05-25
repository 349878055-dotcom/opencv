#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=s01_env.sh
source "$ROOT/scripts/s01_env.sh"
PY="${VENV_PYTHON:-/home/jintao/ai_video/venv/bin/python}"
"$PY" gaze_engine/export_diffusion_metronome.py
echo "→ ${ECURSOR_GAZE_ROOT:-预设资产}/.../指令/05_扩散节拍表.txt"
