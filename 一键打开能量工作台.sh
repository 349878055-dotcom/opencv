#!/usr/bin/env bash
# 双击运行：关旧服务 → 启动 serve_workbench (含照片上传+MediaPipe检测) → 打开浏览器
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
URL="http://127.0.0.1:8765/portal"
PORTAL_URL="$URL"
ROOT_URL="http://127.0.0.1:8765"
HEALTH="http://127.0.0.1:8765/health"
PORT=8765
LOG="${XDG_CACHE_HOME:-$HOME/.cache}/ecursor_workbench.log"

# 使用 venv 的 Python（含 mediapipe）
VENV_PY="${ROOT}/../venv/bin/python3"
if [ ! -x "$VENV_PY" ]; then
  VENV_PY="python3"
fi

mkdir -p "$(dirname "$LOG")"

_stop_port() {
  fuser -k "${PORT}/tcp" 2>/dev/null || true
  lsof -ti ":${PORT}" 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  pkill -f "workbench_backend.py" 2>/dev/null || true
  pkill -f "serve_workbench.py" 2>/dev/null || true
  sleep 0.8
}

_health_ok() {
  curl -sf --max-time 2 "$HEALTH" 2>/dev/null | "$VENV_PY" -c "
import sys, json
d = json.load(sys.stdin)
if not (d.get('ok') and d.get('version', 0) >= 13):
    raise SystemExit(1)
feats = d.get('portal_features') or []
if 'calibrate_preview' not in feats:
    raise SystemExit(1)
" 2>/dev/null
}

_start_server() {
  cd "$ROOT"
  export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
  nohup "$VENV_PY" "$ROOT/tools/01_工作台服务/serve_workbench.py" >>"$LOG" 2>&1 &
  local pid=$!
  for _ in $(seq 1 50); do
    if _health_ok; then
      echo "✅ 能量工作台 v13 已启动 (PID=$pid)"
      return 0
    fi
    sleep 0.3
  done
  echo "❌ 启动超时，查看日志: $LOG"
  tail -5 "$LOG"
  return 1
}

echo "⏳ 能量工作台 v13（自动 build · 标定线条预览 · 狗底膜）"
_stop_port
_start_server
xdg-open "$URL" 2>/dev/null || open "$URL" 2>/dev/null || true
echo "🔗 客户门户: $PORTAL_URL"
echo "🔗 内部工作台: $ROOT_URL"
echo "📋 日志: $LOG"
