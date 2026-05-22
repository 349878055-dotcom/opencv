#!/usr/bin/env bash
# 标准主验收图（改 02 后只跑这个）：四通道 + 视线轨迹 + 红点稀疏点
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=s01_env.sh
source "$ROOT/scripts/s01_env.sh"
PY="${VENV_PYTHON:-/home/jintao/ai_video/venv/bin/python}"
"$PY" gaze_engine/preview_s01_instruction_schematic.py
echo "→ 资产库/…/示意图/主验收_指令集示意图.png"
echo "→ 资产库/…/预览/主验收_指令集示意图.png（副本）"
