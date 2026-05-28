"""
猫情绪预设 · 12 个（代码回退）+ 预设资产 JSON（真源，含 pad）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaze_engine._shared.slider_schema import EarParams, HoldSegment, MacroSliders, SliderPacket

CAT_PRESETS: dict[str, dict[str, Any]] = {
    "cat_alarm_stare": {
        "note": "竖耳、瞳孔收缩、眼不眨",
        "macro": {"push": 82, "power": 88, "speed": 90, "steady": 94, "grip": 90, "outro": 28},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
        "ear": {"left": [0.9, 0.1], "right": [0.9, 0.1]},
    },
    "cat_hunt_fixate": {
        "note": "狩猎锁定、伏低、瞳孔放大",
        "macro": {"push": 88, "power": 92, "speed": 72, "steady": 98, "grip": 96, "outro": 12},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
        "ear": {"left": [0.6, 0.3], "right": [0.6, 0.3]},
    },
    "cat_startle_fluff": {
        "note": "飞机耳、瞳孔炸开、快速眨眼",
        "macro": {"push": 38, "power": 68, "speed": 96, "steady": 48, "grip": 32, "outro": 14},
        "hold_seg": {"shape": "tremble", "pulse_rate": 28, "pulse_depth": 36, "swell": 0},
        "ear": {"left": [-0.9, -0.5], "right": [-0.9, -0.5]},
    },
    "cat_curious_tilt": {
        "note": "歪头、竖耳、瞳孔放大",
        "macro": {"push": 58, "power": 42, "speed": 48, "steady": 52, "grip": 62, "outro": 42},
        "hold_seg": {"shape": "swell", "pulse_rate": 22, "pulse_depth": 18, "swell": 38},
        "ear": {"left": [0.8, 0.2], "right": [0.3, -0.2]},
    },
    "cat_cuddle_squint": {
        "note": "慢眨眼、半眯眼、耳朵放松",
        "macro": {"push": 62, "power": 32, "speed": 20, "steady": 72, "grip": 82, "outro": 72},
        "hold_seg": {"shape": "pulse", "pulse_rate": 32, "pulse_depth": 18, "swell": 18},
        "ear": {"left": [0.3, 0.0], "right": [0.3, 0.0]},
    },
    "cat_content_bliss": {
        "note": "眯眼成线、瞳孔缩小、慢眨",
        "macro": {"push": 42, "power": 18, "speed": 12, "steady": 68, "grip": 76, "outro": 72},
        "hold_seg": {"shape": "tremble", "pulse_rate": 8, "pulse_depth": 6, "swell": 0},
        "ear": {"left": [0.2, 0.0], "right": [0.2, 0.0]},
    },
    "cat_annoyed_swish": {
        "note": "耳朵背过去、半眯眼",
        "macro": {"push": 52, "power": 48, "speed": 38, "steady": 58, "grip": 52, "outro": 28},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
        "ear": {"left": [-0.3, -0.6], "right": [-0.3, -0.6]},
    },
    "cat_scared_flatten": {
        "note": "全飞机耳、瞳孔放大、快速眨眼",
        "macro": {"push": 22, "power": 58, "speed": 88, "steady": 38, "grip": 28, "outro": 18},
        "hold_seg": {"shape": "tremble", "pulse_rate": 32, "pulse_depth": 38, "swell": 0},
        "ear": {"left": [-1.0, -0.6], "right": [-1.0, -0.6]},
    },
    "cat_sad_whimper": {
        "note": "耳朵耷拉、眼湿润、慢眨眼",
        "macro": {"push": 15, "power": 26, "speed": 22, "steady": 62, "grip": 68, "outro": 22},
        "hold_seg": {"shape": "tremble", "pulse_rate": 18, "pulse_depth": 22, "swell": 8},
        "ear": {"left": [-0.6, -0.2], "right": [-0.6, -0.2]},
    },
    "cat_angry_hiss": {
        "note": "飞机耳、瞳孔缩成线、怒视",
        "macro": {"push": 92, "power": 94, "speed": 78, "steady": 86, "grip": 88, "outro": 22},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
        "ear": {"left": [-0.8, 0.2], "right": [-0.8, 0.2]},
    },
    "cat_sleepy_droop": {
        "note": "眼皮下垂、瞳孔放大、慢眨眼",
        "macro": {"push": 12, "power": 12, "speed": 10, "steady": 48, "grip": 22, "outro": 58},
        "hold_seg": {"shape": "decay", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
        "ear": {"left": [-0.2, -0.1], "right": [-0.2, -0.1]},
    },
    "cat_play_pounce": {
        "note": "瞳孔放大、耳朵前竖、快速扫视",
        "macro": {"push": 68, "power": 62, "speed": 82, "steady": 44, "grip": 48, "outro": 18},
        "hold_seg": {"shape": "pulse", "pulse_rate": 42, "pulse_depth": 38, "swell": 28},
        "ear": {"left": [0.8, 0.4], "right": [0.8, 0.4]},
    },
}

CAT_PRESET_GROUPS: tuple[dict[str, Any], ...] = (
    {"label": "警觉 · 攻击", "keys": ["cat_alarm_stare", "cat_hunt_fixate", "cat_angry_hiss"]},
    {"label": "恐惧 · 退缩", "keys": ["cat_startle_fluff", "cat_scared_flatten", "cat_sad_whimper"]},
    {"label": "亲昵 · 放松", "keys": ["cat_cuddle_squint", "cat_content_bliss", "cat_sleepy_droop"]},
    {"label": "好奇 · 玩耍", "keys": ["cat_curious_tilt", "cat_play_pounce", "cat_annoyed_swish"]},
)


def _presets_dir() -> Path:
    from asset_lib import CAT_PRESETS_DIR

    return CAT_PRESETS_DIR


def cat_packet_from_file(name: str) -> SliderPacket:
    """按预设文件名（不含 .json）或 emotion id 加载 SliderPacket。"""
    from gaze_engine._shared.emotion_pad import ensure_pad_on_packet

    presets_dir = _presets_dir()
    candidates = [presets_dir / f"{name}.json"]
    if not candidates[0].is_file():
        for f in presets_dir.glob("*.json"):
            if f.name.startswith("_"):
                continue
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if raw.get("emotion") == name or raw.get("label") == name:
                candidates = [f]
                break
    path = candidates[0]
    if not path.is_file():
        available = sorted(
            p.stem for p in presets_dir.glob("*.json") if not p.name.startswith("_")
        )
        raise KeyError(f"未知猫预设: {name}，可选: {', '.join(available)}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    pkt = SliderPacket.from_dict(raw)
    if not pkt.emotion or pkt.emotion == "s01_pressure":
        pkt.emotion = str(raw.get("emotion") or name)
    return ensure_pad_on_packet(pkt, "cat")


def cat_packet_from_preset(name: str) -> SliderPacket:
    """猫预设名 → SliderPacket（优先 JSON 资产，回退代码表）"""
    from gaze_engine._shared.emotion_pad import ensure_pad_on_packet

    try:
        return cat_packet_from_file(name)
    except KeyError:
        pass
    data = CAT_PRESETS.get(name)
    if not data:
        raise KeyError(f"未知猫预设: {name}，可选: {', '.join(CAT_PRESETS)}")
    ear = EarParams.from_preset_dict(data.get("ear") or {})
    pkt = SliderPacket(
        emotion=name,
        style="default",
        macro=MacroSliders(**data["macro"]),  # type: ignore[arg-type]
        hold_seg=HoldSegment(**data["hold_seg"]),  # type: ignore[arg-type]
        ear=ear,
    ).clamped()
    return ensure_pad_on_packet(pkt, "cat")