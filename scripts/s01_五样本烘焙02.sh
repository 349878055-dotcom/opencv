#!/usr/bin/env bash
# SliderPacket 五样本 → 能量包络 → 全量 → 真人律 → 烘焙 02
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=s01_env.sh
source "$ROOT/scripts/s01_env.sh"
OUT="${1:-$ECURSOR_GAZE_ROOT/指令/脉冲样本_五连}"
exec python3 "$ROOT/gaze_engine/batch_presets.py" --batch-five --out-dir "$OUT"
