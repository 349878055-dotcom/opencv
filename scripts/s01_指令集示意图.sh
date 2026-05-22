#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
"$ROOT/scripts/s01_主验收示意图.sh"
"$ROOT/scripts/s01_参考十二通道.sh"
  # shellcheck source=s01_env.sh
  source "$ROOT/scripts/s01_env.sh"
  export ECURSOR_SPARSE_JSON
  echo "→ 预览/_指令关键点/（3D 参考，非主验收）"
fi
