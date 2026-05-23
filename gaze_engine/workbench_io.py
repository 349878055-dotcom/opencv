"""操作台 ↔ 资产库：SliderPacket 读写路径。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from gaze_engine.slider_schema import SliderPacket

_PKG_ROOT = Path(__file__).resolve().parent.parent
_TOOLS_PACKET = _PKG_ROOT / "tools" / "slider_packet.json"
F_PACKET = "01_滑杆包.json"

def slider_packet_path() -> Path:
    from asset_lib import cmd_dir, ensure_dirs

    ensure_dirs()
    return cmd_dir() / F_PACKET

def write_slider_packet(packet: SliderPacket) -> Path:
    p = slider_packet_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = packet.to_dict()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _TOOLS_PACKET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, _TOOLS_PACKET)
    return p

def read_slider_packet(path: str | None = None) -> tuple[SliderPacket, Path]:
    p = Path(path.strip().strip('"')) if path and path.strip() else slider_packet_path()
    if not p.is_file() and _TOOLS_PACKET.is_file():
        p = _TOOLS_PACKET
    if not p.is_file():
        raise FileNotFoundError(f"找不到滑杆包: {p}（请先在操作台保存）")
    pkt = SliderPacket.from_dict(json.loads(p.read_text(encoding="utf-8")))
    return pkt, p

def finalize_and_write_l1(packet: SliderPacket | None = None) -> Path:
    """操作台出厂：L1 finalize → 02_滑杆_L1纠正.json（Comfy ② 包络读此文件）。"""
    from asset_lib import cmd_dir, ensure_dirs
    from gaze_engine.packet_finalize import finalize_packet
    from gaze_engine.pipeline_io import F_PACKET_L1, write_packet

    ensure_dirs()
    pkt = packet
    if pkt is None:
        pkt, _ = read_slider_packet()
    pkt2, _ = finalize_packet(pkt)
    out = cmd_dir() / F_PACKET_L1
    write_packet(pkt2, out)
    return out
