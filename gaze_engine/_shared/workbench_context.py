"""操作台上下文：自然语言、能量图补充说明、知识库、L1 附件（与 Comfy 节点 1/2 同步）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

F_WORKBENCH_CTX = "01_操作台上下文.json"

_DEFAULT_L1_ATTACH = {
    "title": "L1 滑杆禁区",
    "contract": "contracts/滑杆规范.md",
    "ui_script": "tools/packet_finalize_ui.js",
    "bounds_script": "tools/slider_forbidden_bounds.js",
    "note": "拖杆时浏览器内弹回；保存/出厂时 Python finalize_packet 写 02_滑杆_L1纠正.json",
}

def _cmd_dir() -> Path:
    from asset_lib import cmd_dir, ensure_dirs

    ensure_dirs()
    return cmd_dir()

def default_context(*, natural_language: str = "", prompt: str = "", knowledge_base: str = "") -> dict[str, Any]:
    return {
        "schema": "workbench-context-v1",
        "natural_language": natural_language or "",
        "prompt": prompt or "",
        "knowledge_base": knowledge_base or "",
        "l1_attachment": dict(_DEFAULT_L1_ATTACH),
    }

def context_path() -> Path:
    return _cmd_dir() / F_WORKBENCH_CTX

def read_workbench_context() -> dict[str, Any]:
    p = context_path()
    if not p.is_file():
        return default_context()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_context()
    if not isinstance(data, dict):
        return default_context()
    base = default_context()
    for k in ("natural_language", "knowledge_base", "energy_map_note", "last_slider_packet"):
        if k in data:
            base[k] = data[k]
    # 旧字段 prompt（曾误标为扩散 Prompt）
    if "energy_map_note" not in data and data.get("prompt"):
        base["energy_map_note"] = data["prompt"]
    if isinstance(data.get("l1_attachment"), dict):
        base["l1_attachment"] = {**base["l1_attachment"], **data["l1_attachment"]}
    return base

def write_workbench_context(
    *,
    natural_language: str | None = None,
    energy_map_note: str | None = None,
    knowledge_base: str | None = None,
    last_slider_packet: dict[str, Any] | None = None,
    merge: bool = True,
) -> Path:
    p = context_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    ctx = read_workbench_context() if merge else default_context()
    if natural_language is not None:
        ctx["natural_language"] = natural_language
    if energy_map_note is not None:
        ctx["energy_map_note"] = energy_map_note
        ctx.pop("prompt", None)
    if knowledge_base is not None:
        ctx["knowledge_base"] = knowledge_base
    if last_slider_packet is not None:
        ctx["last_slider_packet"] = last_slider_packet
    p.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tools_copy = Path(__file__).resolve().parent.parent / "tools" / F_WORKBENCH_CTX
    tools_copy.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    return p
