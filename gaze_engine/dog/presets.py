"""
狗情绪预设 · 从 预设资产/预设情绪包/dog/*.json 加载
"""
from __future__ import annotations

import json
from pathlib import Path

from gaze_engine._shared.slider_schema import EarParams, HoldSegment, MacroSliders, SliderPacket

# 兼容旧 CLI 名 → 文件预设名
_LEGACY_ALIASES: dict[str, str] = {
    "dog_sad_puppy": "委屈·幼犬眼",
}


def _presets_dir() -> Path:
    from asset_lib import DOG_PRESETS_DIR

    return DOG_PRESETS_DIR


def dog_packet_from_file(name: str) -> SliderPacket:
    """按预设文件名（不含 .json）加载 SliderPacket，含 EarParams。"""
    resolved = _LEGACY_ALIASES.get(name, name)
    path = _presets_dir() / f"{resolved}.json"
    if not path.is_file():
        available = sorted(
            p.stem for p in _presets_dir().glob("*.json") if not p.name.startswith("_")
        )
        raise KeyError(f"未知狗预设: {name}，可选: {', '.join(available)}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    ear_raw = raw.get("ear")
    ear = EarParams.from_preset_dict(ear_raw) if ear_raw else None
    return SliderPacket(
        emotion=str(raw.get("emotion") or resolved),
        style=str(raw.get("style") or "default"),
        macro=MacroSliders(**raw["macro"]),  # type: ignore[arg-type]
        hold_seg=HoldSegment(**raw["hold_seg"]),  # type: ignore[arg-type]
        ear=ear,
    ).clamped()


def dog_packet_from_preset(name: str) -> SliderPacket:
    """（兼容旧名）→ dog_packet_from_file"""
    return dog_packet_from_file(name)


# 供 registry 列举
DOG_PRESETS: dict[str, dict] = {
    "委屈·幼犬眼": {"alias": "dog_sad_puppy"},
}
