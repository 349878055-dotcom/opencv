"""
SliderPacket 收口：滑杆禁区 L1（contracts/滑杆规范.md §10 · slider_bounds.py）。

调用点：compile 前、delivery 前、apply_llm_delta 后；工作台 packet_finalize_ui.js。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gaze_engine.control_surface import PRESETS as ACTING_PULSE_PRESETS, MACRO_IDS
from gaze_engine.slider_bounds import load_rules
from gaze_engine.slider_schema import SliderPacket

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
    if name in ACTING_PULSE_PRESETS:
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
    center = (ACTING_PULSE_PRESETS[preset].get("macro") or {})
    for k in MACRO_IDS:
        if k not in center:
            continue
        cur = _get_macro(packet, k)
        target = int(center[k])
        if cur != target:
            setattr(packet.macro, k, target)
            rep.fixes.append(f"G1路人中间带: {preset} macro.{k} {cur}→{target}")

def _apply_preset_box(packet: SliderPacket, preset: str, box: dict[str, Any], rep: FinalizeReport) -> None:
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
        default_shape = str((ACTING_PULSE_PRESETS[preset].get("hold_seg") or {}).get("shape") or allowed[0])
        old = h.shape
        h.shape = default_shape  # type: ignore[assignment]
        rep.fixes.append(f"{preset}: shape {old}→{default_shape}（本戏不允许）")

    for k in ("pulse_rate", "pulse_depth", "swell"):
        lo = int((box.get("hold_seg_min") or {}).get(k, 0))
        hi = int((box.get("hold_seg_max") or {}).get(k, 100))
        cur = int(getattr(h, k))
        if cur < lo:
            setattr(h, k, lo)
            rep.fixes.append(f"{preset}: hold_seg.{k} {cur}→{lo}")
        elif cur > hi:
            setattr(h, k, hi)
            rep.fixes.append(f"{preset}: hold_seg.{k} {cur}→{hi}")

def _match_when(packet: SliderPacket, when: dict[str, Any]) -> bool:
    h = packet.hold_seg
    m = packet.macro
    checks = [
        ("hold_seg.shape", lambda s: h.shape == s),
        ("hold_seg.shape_not", lambda s: h.shape != s),
        ("hold_seg.pulse_rate_min", lambda n: h.pulse_rate >= int(n)),
        ("hold_seg.pulse_rate_max", lambda n: h.pulse_rate <= int(n)),
        ("hold_seg.pulse_depth_min", lambda n: h.pulse_depth >= int(n)),
        ("macro.speed_min", lambda n: m.speed >= int(n)),
        ("macro.speed_max", lambda n: m.speed <= int(n)),
        ("macro.power_min", lambda n: m.power >= int(n)),
        ("macro.power_max", lambda n: m.power <= int(n)),
        ("macro.steady_min", lambda n: m.steady >= int(n)),
        ("macro.steady_max", lambda n: m.steady <= int(n)),
        ("macro.grip_min", lambda n: m.grip >= int(n)),
        ("macro.grip_max", lambda n: m.grip <= int(n)),
        ("macro.push_min", lambda n: m.push >= int(n)),
        ("macro.push_max", lambda n: m.push <= int(n)),
        ("macro.outro_min", lambda n: m.outro >= int(n)),
        ("macro.outro_max", lambda n: m.outro <= int(n)),
    ]
    for key, pred in checks:
        if key in when and not pred(when[key]):
            return False
    return True

def _apply_global_fixes(
    packet: SliderPacket,
    rules: dict[str, Any],
    preset: str | None,
    rep: FinalizeReport,
) -> None:
    box = (rules.get("presets") or {}).get(preset or "") or {}

    for rule in rules.get("global_fixes") or []:
        if rule.get("dead_zone"):
            continue
        when = rule.get("when") or {}
        if not _match_when(packet, when):
            continue
        rid = str(rule.get("id") or "fix")

        for key, val in (rule.get("set") or {}).items():
            if not key.startswith("hold_seg."):
                continue
            f = key.split(".", 1)[1]
            old = getattr(packet.hold_seg, f)
            if f == "shape":
                packet.hold_seg.shape = val  # type: ignore[assignment]
            else:
                setattr(packet.hold_seg, f, _clamp_i(val))
            rep.fixes.append(f"{rid}: {key} {old}→{getattr(packet.hold_seg, f)}")

        for key, val in (rule.get("set_macro_min") or {}).items():
            floor = _clamp_i(val)
            if key in (box.get("macro_min") or {}):
                floor = max(floor, int(box["macro_min"][key]))
            cur = _get_macro(packet, key)
            if cur < floor:
                setattr(packet.macro, key, floor)
                rep.fixes.append(f"{rid}: macro.{key} {cur}→{floor}")

        for key, val in (rule.get("set_macro_max") or {}).items():
            ceil = _clamp_i(val)
            if key in (box.get("macro_max") or {}):
                ceil = min(ceil, int(box["macro_max"][key]))
            cur = _get_macro(packet, key)
            if cur > ceil:
                setattr(packet.macro, key, ceil)
                rep.fixes.append(f"{rid}: macro.{key} {cur}→{ceil}")

def finalize_packet(packet: SliderPacket) -> tuple[SliderPacket, FinalizeReport]:
    """滑杆禁区收口：本戏数值盒 → 全剧种硬禁区 → 路人中间带。"""
    p = packet.clamped()
    rep = FinalizeReport()
    rules = load_rules()
    preset = _preset_key(p)

    if preset:
        box = (rules.get("presets") or {}).get(preset)
        if box:
            _apply_preset_box(p, preset, box, rep)

    _apply_global_fixes(p, rules, preset, rep)

    if preset and _in_dead_zone(p, rules):
        _reset_macro_to_preset(p, preset, rep)

    return p.clamped(), rep
