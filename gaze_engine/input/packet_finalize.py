"""
SliderPacket 收口：滑杆禁区 L1（合同/滑杆规范.md §10 · slider_bounds.py）。

调用点：compile 前、delivery 前、apply_llm_delta 后；工作台 packet_finalize_ui.js。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from asset_lib import is_valid_preset, load_species_presets
from gaze_engine.input.control_surface import MACRO_IDS
from gaze_engine.input.slider_bounds import load_rules
from gaze_engine.input.slider_schema import SliderPacket

_RULES_PATH = Path(__file__).resolve().parent.parent / "runtime_data/slider_forbidden.json"


@dataclass
class FinalizeReport:
    fixes: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.fixes)


def _load_rules() -> dict[str, Any]:
    if not _RULES_PATH.is_file():
        return {}
    return json.loads(_RULES_PATH.read_text(encoding="utf-8"))


def _clamp_i(v: int | float, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(float(v)))))


def _preset_key(packet: SliderPacket) -> str | None:
    name = (packet.emotion or "").strip()
    if is_valid_preset("human", name):
        return name
    return None


def _get_macro(packet: SliderPacket, key: str) -> int:
    return int(getattr(packet.macro, key))


def _in_dead_zone(packet: SliderPacket, rules: dict[str, Any]) -> bool:
    dz = rules.get("dead_zone") or {}
    lo, hi = int(dz.get("macro_low", 42)), int(dz.get("macro_high", 58))
    if not dz.get("all_six_in_zone"):
        return False
    return all(lo <= _get_macro(packet, k) <= hi for k in MACRO_IDS)


def _reset_macro_to_preset(packet: SliderPacket, preset: str, rep: FinalizeReport) -> None:
    presets = load_species_presets("human") or {}
    center = (presets.get(preset) or {}).get("macro") or {}
    for k in MACRO_IDS:
        if k not in center:
            continue
        cur = _get_macro(packet, k)
        target = int(center[k])
        if cur != target:
            setattr(packet.macro, k, target)
            rep.fixes.append(f"G1路人中间带: {preset} macro.{k} {cur}→{target}")


def _apply_preset_box(packet: SliderPacket, preset: str, box: dict[str, Any], rep: FinalizeReport) -> None:
    presets = load_species_presets("human") or {}
    for k in MACRO_IDS:
        lo = int((box.get("macro_min") or {}).get(k, 0))
        hi = int((box.get("macro_max") or {}).get(k, 100))
        cur = _get_macro(packet, k)
        if cur < lo:
            setattr(packet.macro, k, lo)
            rep.fixes.append(f"{preset}: macro.{k} {cur}→{lo}（低于本戏下限）")
        elif cur > hi:
            setattr(packet.macro, k, hi)
            rep.fixes.append(f"{preset}: macro.{k} {cur}→{hi}（高于本戏上限）")

    h = packet.hold_seg
    allowed = box.get("allowed_shapes") or []
    if allowed and h.shape not in allowed:
        preset_data = presets.get(preset) or {}
        hold = preset_data.get("hold_seg") or {}
        default_shape = str(hold.get("shape") or allowed[0])
        old = h.shape
        h.shape = default_shape  # type: ignore[assignment]
        rep.fixes.append(f"{preset}: shape {old}→{default_shape}（本戏不允许）")

    for k in ("pulse_rate", "pulse_depth", "swell"):
        lo = int((box.get("hold_seg_min") or {}).get(k, 0))
        hi = int((box.get("hold_seg_max") or {}).get(k, 100))
        cur = int(getattr(h, k, 0))
        if cur < lo:
            setattr(h, k, lo)
            rep.fixes.append(f"{preset}: hold_seg.{k} {cur}→{lo}（低于本戏下限）")
        elif cur > hi:
            setattr(h, k, hi)
            rep.fixes.append(f"{preset}: hold_seg.{k} {cur}→{hi}（高于本戏上限）")


def finalize_packet(packet: SliderPacket) -> tuple[SliderPacket, FinalizeReport]:
    """收口主入口：禁区 + 死区 + 预设修正。"""
    rep = FinalizeReport()
    rules = _load_rules()
    preset = _preset_key(packet)
    if not preset:
        return packet, rep

    box = (rules.get("presets") or {}).get(preset)
    if box:
        _apply_preset_box(packet, preset, box, rep)

    if _in_dead_zone(packet, rules):
        _reset_macro_to_preset(packet, preset, rep)

    return packet, rep
