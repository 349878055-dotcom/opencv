#!/usr/bin/env bash
# 双击运行：关旧服务 → 启动新版 → 打开浏览器（5 帧关键帧版）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
URL="http://127.0.0.1:8765/能量工作台.html"
HEALTH="http://127.0.0.1:8765/health"
PORT=8765
LOG="${XDG_CACHE_HOME:-$HOME/.cache}/ecursor_workbench.log"

mkdir -p "$(dirname "$LOG")"

_stop_port() {
  fuser -k "${PORT}/tcp" 2>/dev/null || true
  lsof -ti ":${PORT}" 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  pkill -f "serve_workbench.py" 2>/dev/null || true
  pkill -f stream_daemon 2>/dev/null || true
  pkill -f run_pipeline 2>/dev/null || true
  sleep 0.8
}

_health_ok() {
  curl -sf --max-time 2 "$HEALTH" 2>/dev/null | grep -q '"version": 8'
}

_start_server() {
  cd "$ROOT/tools"
  export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
  nohup python3 serve_workbench.py >>"$LOG" 2>&1 &
  for _ in $(seq 1 50); do
    if _health_ok; then
      return 0
    fi
    sleep 0.2
  done
  echo "启动失败，请看日志: $LOG" >&2
  tail -n 15 "$LOG" >&2 2>/dev/null || true
  return 1
}

_open_browser() {
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$URL" >/dev/null 2>&1 &
  else
    echo "请打开: $URL"
  fi
}

# 清理旧缓存
rm -rf "$ROOT/tools/preview_cache/live_frames" 2>/dev/null || true
rm -f "$ROOT/tools/preview_cache/live_replay.json" 2>/dev/null || true
rm -f "$ROOT/tools/preview_cache/live_viewport_status.json" 2>/dev/null || true

_stop_port
if ! _start_server; then
  echo "失败。若端口仍被占: fuser -k 8765/tcp" >&2
  exit 1
fi
echo "OK 工作台 v8（5 帧关键帧）: $URL"
_open_browser
