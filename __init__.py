"""ecursor / jintao_node_eye：能量工作台（已脱离 ComfyUI，Web-only 模式）。"""
from __future__ import annotations

import os
from pathlib import Path

_here = Path(__file__).resolve().parent

def _load_local_env() -> None:
    """加载本目录 .env（仅补未设置的变量，勿提交 git）。"""
    env_path = _here / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val

_load_local_env()

# 启动工作台
#   cd tools && python3 serve_workbench.py
# 然后打开 http://127.0.0.1:8765/能量工作台.html

__all__ = []  # 无 ComfyUI 节点导出
