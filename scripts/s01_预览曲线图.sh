#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=s01_env.sh
source "$ROOT/scripts/s01_env.sh"
python3 gaze_engine/preview_s01_curves.py
