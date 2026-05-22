"""ecursor / jintao_node_eye：ComfyUI 自定义节点（Comfy 用 importlib 加载，禁止相对导入）。"""
from __future__ import annotations

import importlib.util
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
_spec = importlib.util.spec_from_file_location(
    "jintao_node_eye_nodes_v1", _here / "nodes_v1.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load nodes_v1.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

NODE_CLASS_MAPPINGS = dict(_mod.NODE_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS = dict(
    getattr(_mod, "NODE_DISPLAY_NAME_MAPPINGS", {})
)

# ComfyUI 加载 web/js/*.js，为多行 STRING 补中文标签
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
