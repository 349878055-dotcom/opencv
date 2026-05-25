"""
狗情绪预设 · 10 个（当前已实现: 委屈）
"""
from __future__ import annotations

from typing import Any

from gaze_engine._shared.slider_schema import EarParams, HoldSegment, MacroSliders, SliderPacket

DOG_PRESETS: dict[str, dict[str, Any]] = {
    "dog_sad_puppy": {
        "note": "委屈·幼犬眼：耳朵耷拉、眼湿润、慢眨眼",
        "macro": {"push": 15, "power": 26, "speed": 22, "steady": 62, "grip": 68, "outro": 22},
        "hold_seg": {"shape": "tremble", "pulse_rate": 18, "pulse_depth": 22, "swell": 8},
        "ear": {"left": [-0.6, -0.2], "right": [-0.6, -0.2]},
    },
}


def dog_packet_from_preset(name: str) -> SliderPacket:
    """狗预设名 → SliderPacket（含 EarParams）"""
    data = DOG_PRESETS.get(name)
    if not data:
        raise KeyError(f"未知狗预设: {name}，可选: {', '.join(DOG_PRESETS)}")
    ear = EarParams.from_preset_dict(data.get("ear") or {})
    return SliderPacket(
        emotion=name,
        style="default",
        macro=MacroSliders(**data["macro"]),  # type: ignore[arg-type]
        hold_seg=HoldSegment(**data["hold_seg"]),  # type: ignore[arg-type]
        ear=ear,
    ).clamped()