#!/usr/bin/env bash
# 滑杆预设 → 能量包络 E(t) → 全量 → 烘焙定稿（不经稀疏关键帧）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=s01_env.sh
source "$ROOT/scripts/s01_env.sh"
PY="${VENV_PYTHON:-/home/jintao/ai_video/venv/bin/python}"

PRESET="${1:-施压·凝视}"
OUT="${ECURSOR_GAZE_ROOT}/指令/02_烘焙_真人律.json"
PACKET_JSON="$(mktemp)"
trap 'rm -f "$PACKET_JSON"' EXIT

"$PY" -c "
from gaze_engine.acting_pulse_presets import packet_from_acting_preset
import json, sys
p = packet_from_acting_preset(sys.argv[1])
open(sys.argv[2], 'w', encoding='utf-8').write(p.to_json())
" "$PRESET" "$PACKET_JSON"

"$PY" gaze_engine/delivery_pipeline.py --packet "$PACKET_JSON" -o "$OUT"

echo ""
echo "[OK] 烘焙定稿 → $OUT"
echo "  export ECURSOR_SPARSE_JSON=\"$OUT\""
echo "  ./scripts/s01_导出扩散节拍表.sh"
