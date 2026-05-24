"""节点 1 默认 Prompt / 知识库 / 历史滑杆加载。"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gaze_engine._shared.pipeline_io import F_PACKET, cmd_dir
from gaze_engine._shared.slider_schema import SliderPacket

_PKG_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _PKG_ROOT / "prompts"

_PLACEHOLDER_PREFIXES = (
    "留空则用",
    "（留空",
    "留空=内置",
)

def _read_text(name: str) -> str:
    p = _PROMPTS_DIR / name
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return ""

def default_system_prompt_text() -> str:
    return _read_text("node1_system_prompt.txt")

def default_knowledge_base_text() -> str:
    return _read_text("node1_knowledge_base.txt")

def _is_placeholder(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return True
    return any(t.startswith(p) for p in _PLACEHOLDER_PREFIXES)

def resolve_knowledge_base(custom: str) -> str:
    t = (custom or "").strip()
    if t and not _is_placeholder(t):
        return t
    return default_knowledge_base_text()

def resolve_system_prompt_input(custom: str) -> str:
    """Comfy 框内容；留空/占位 → 用文件默认（llm_openai.resolve_node1_system_prompt 会再解析）。"""
    t = (custom or "").strip()
    if t and not _is_placeholder(t):
        return t
    return ""

def load_previous_slider_packet(out_dir: Path | None = None) -> SliderPacket | None:
    """上一轮 01_滑杆包.json，或上下文快照。"""
    base = out_dir or cmd_dir()
    pkt_path = base / F_PACKET
    if pkt_path.is_file():
        try:
            from gaze_engine._shared.workbench_io import read_slider_packet

            pkt, _ = read_slider_packet(str(pkt_path))
            return pkt.clamped()
        except Exception:
            pass
    try:
        from gaze_engine._shared.workbench_context import read_workbench_context

        snap = read_workbench_context().get("last_slider_packet")
        if isinstance(snap, dict) and snap.get("macro"):
            return SliderPacket.from_dict(snap)
    except Exception:
        pass
    return None

def format_previous_packet_for_llm(pkt: SliderPacket) -> str:
    p = pkt.clamped()
    body: dict[str, Any] = {
        "emotion_preset": p.emotion,
        "macro": asdict(p.macro),
        "hold_seg": asdict(p.hold_seg),
    }
    return json.dumps(body, ensure_ascii=False, indent=2)

def packet_to_context_snapshot(pkt: SliderPacket) -> dict[str, Any]:
    return pkt.clamped().to_dict()
