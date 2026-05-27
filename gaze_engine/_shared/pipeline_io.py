"""Comfy 节点间：各阶段 JSON 读写（与能量工作台段名一致）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaze_engine._shared.slider_schema import SliderPacket

F_NL = "01_自然语言.txt"
F_SYSTEM_PROMPT = "01_系统Prompt.txt"
F_CONSULT = "01_咨询回复.txt"
F_PACKET = "01_滑杆包.json"
F_PACKET_L1 = "02_滑杆_L1纠正.json"
F_ENVELOPE = "03_能量包络.json"
F_DENSE_ENV = "04_全量_包络展开.json"
F_DENSE_PRIOR = "05_全量_真人律.json"
F_DENSE_QUALITY = "06_全量_平庸纠正.json"
F_BAKED = "02_烘焙_真人律.json"
F_CONTEXT = "04_交付上下文.json"

def cmd_dir() -> Path:
    from asset_lib import cmd_dir as d, ensure_dirs

    ensure_dirs()
    return d()

def _write(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path.resolve())

def read_packet(path: str = "") -> tuple[SliderPacket, Path]:
    from gaze_engine._shared.workbench_io import read_slider_packet

    return read_slider_packet(path or None)

def write_packet(packet: SliderPacket, path: Path | None = None) -> str:
    from gaze_engine._shared.workbench_io import write_slider_packet

    if path is None:
        return str(write_slider_packet(packet).resolve())
    return _write(path, packet.to_dict())

def write_envelope(packet: SliderPacket, path: Path | None = None) -> str:
    from gaze_engine._shared.envelope_compile import export_envelope_series

    p = path or cmd_dir() / F_ENVELOPE
    return _write(p, export_envelope_series(packet))

def write_dense(
    channels: dict[str, list[float]],
    *,
    packet: SliderPacket,
    stub: dict[str, Any] | None = None,
    path: Path | None = None,
) -> str:
    p = path or cmd_dir() / F_DENSE_ENV
    body: dict[str, Any] = {
        "schema": "dense-12x150",
        "frame_count": 150,
        "fps": 30,
        "channels": {k: [round(float(x), 6) for x in v] for k, v in channels.items()},
        "slider_packet": packet.to_dict(),
    }
    if stub is not None:
        body["delivery_context"] = stub
    return _write(p, body)

def read_dense(path: str) -> tuple[dict[str, list[float]], SliderPacket, dict[str, Any]]:
    p = Path(path.strip().strip('"')).resolve()
    d = json.loads(p.read_text(encoding="utf-8"))
    ch = d.get("channels") or {}
    channels = {k: list(v) for k, v in ch.items()}
    pkt = SliderPacket.from_dict(d.get("slider_packet") or {})
    ctx = d.get("delivery_context") or {}
    return channels, pkt, ctx

def write_context(stub: dict[str, Any], path: Path | None = None) -> str:
    p = path or cmd_dir() / F_CONTEXT
    return _write(p, stub)

def read_context(path: str = "") -> dict[str, Any]:
    p = Path(path.strip().strip('"')) if path.strip() else cmd_dir() / F_CONTEXT
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
