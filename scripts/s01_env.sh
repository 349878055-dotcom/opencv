#!/usr/bin/env bash
# 输出当前人格包/情绪路径（供其它 s01 脚本 source）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
eval "$(ROOT="$ROOT" python3 <<'PY'
import os
import sys
from pathlib import Path

root = Path(os.environ["ROOT"])
sys.path.insert(0, str(root))
from asset_lib import (  # noqa: E402
    SPARSE_JSON,
    active_gaze_id,
    active_persona_id,
    gaze_root,
)

pairs = {
    "ECURSOR_PERSONA_PACK": active_persona_id(),
    "ECURSOR_GAZE_EMOTION": active_gaze_id(),
    "ECURSOR_GAZE_ROOT": str(gaze_root()),
    "ECURSOR_SPARSE_JSON": str(SPARSE_JSON),
}
for k, v in pairs.items():
    print(f'export {k}="{v}"')
PY
)"
