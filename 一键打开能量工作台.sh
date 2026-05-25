#!/usr/bin/env bash
# 双击运行：关旧服务 → 启动 FastAPI 版 → 打开浏览器
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
URL="http://127.0.0.1:8765"
HEALTH="http://127.0.0.1:8765/health"
PORT=8765
LOG="${XDG_CACHE_HOME:-$HOME/.cache}/ecursor_workbench.log"

mkdir -p "$(dirname "$LOG")"

_stop_port() {
  fuser -k "${PORT}/tcp" 2>/dev/null || true
  lsof -ti ":${PORT}" 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  pkill -f "workbench_backend.py" 2>/dev/null || true
  pkill -f "serve_workbench.py" 2>/dev/null || true
  sleep 0.8
}

_health_ok() {
  curl -sf --max-time 2 "$HEALTH" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('ok') and d.get('version',0)>=12 else 1)" 2>/dev/null
}

_start_server() {
  cd "$ROOT/tools/01_工作台服务"
  export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
  nohup python3 -m uvicorn workbench_backend:app --host 0.0.0.0 --port "$PORT" --no-access-log >>"$LOG" 2>&1 &
  local pid=$!
  for _ in $(seq 1 50); do
    if _health_ok; then
      echo "✅ 能量工作台 v12（FastAPI）已启动 (PID=$pid)"
      return 0
    fi
    sleep 0.3
  done
  echo "❌ 启动超时，查看日志: $LOG"
  tail -5 "$LOG"
  return 1
}

echo "⏳ 能量工作台 v12（FastAPI · 已脱离 ComfyUI）"
_stop_port
_start_server
xdg-open "$URL" 2>/dev/null || open "$URL" 2>/dev/null || true
echo "🔗 $URL"
echo "📋 日志: $LOG"
