#!/usr/bin/env bash
# 加载 OpenAI 密钥（供 Comfy 前1 节点 ChatGPT）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ECURSOR_ENV_FILE:-$ROOT/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
  echo "[OK] 已加载 $ENV_FILE"
else
  echo "未找到 $ENV_FILE"
  echo "请复制: cp .env.example .env  并编辑 OPENAI_API_KEY=..."
  echo "或: export OPENAI_API_KEY='sk-proj-...'"
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY 为空" >&2
  exit 1
fi
echo "OPENAI_API_KEY 已设置（长度 ${#OPENAI_API_KEY}）"
echo "模型: ${ECURSOR_OPENAI_MODEL:-gpt-4o-mini}"
echo ""
echo "从本终端启动 ComfyUI 时才会带上密钥，例如:"
echo "  source $ROOT/scripts/s01_设置OpenAI密钥.sh && cd ~/ai_video/ComfyUI && python main.py"
