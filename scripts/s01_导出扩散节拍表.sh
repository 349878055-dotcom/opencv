#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=s01_env.sh
source "$ROOT/scripts/s01_env.sh"
PY="${VENV_PYTHON:-/home/jintao/ai_video/venv/bin/python}"
"$PY" -c "
import sys, json
sys.path.insert(0, '.')
from asset_lib import cmd_dir, resolve_sparse_json
from gaze_engine._shared.rhythm_compiler import build_metronome_text
src = resolve_sparse_json(prefer_baked=True)
if not src.is_file():
    print('缺少 02', file=sys.stderr)
    sys.exit(1)
sparse = json.loads(src.read_text(encoding='utf-8'))
species = sparse.get('species', 'human')
text = build_metronome_text(sparse, source_path=str(src), species=species)
out = cmd_dir() / '05_扩散节拍表.txt'
out.write_text(text, encoding='utf-8')
print(f'已写入: {out}')
print(f'  读取: {src} 物种: {species}')
"
echo "→ ${ECURSOR_GAZE_ROOT:-预设资产}/.../指令/05_扩散节拍表.txt"
