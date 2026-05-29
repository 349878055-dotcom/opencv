"""
狗情绪预设 · 从 预设资产/情绪包/dog/ 加载（含子目录与别名）
"""
from __future__ import annotations

from gaze_engine._shared.slider_schema import SliderPacket

# 兼容旧 CLI 名 → 预设 id
_LEGACY_ALIASES: dict[str, str] = {
    "dog_sad_puppy": "委屈·幼犬眼",
    "委屈·幼犬眼": "委屈/变体3_迟疑试探",
}


def dog_packet_from_file(name: str) -> SliderPacket:
    """按 preset id 或别名加载 SliderPacket。"""
    from asset_lib import DOG_PRESETS_DIR, load_emotion_slider_packet

    preset_id = _LEGACY_ALIASES.get(name, name)
    pkt = load_emotion_slider_packet("dog", preset_id)
    if pkt is None:
        available = sorted(
            p.stem
            for p in DOG_PRESETS_DIR.rglob("*.json")
            if not p.name.startswith("_")
        )
        raise KeyError(f"未知狗预设: {name}，可选: {', '.join(available)}")
    return pkt


def dog_packet_from_preset(name: str) -> SliderPacket:
    """（兼容旧名）→ dog_packet_from_file"""
    return dog_packet_from_file(name)


# 供 registry 列举
DOG_PRESETS: dict[str, dict] = {
    "委屈/变体3_迟疑试探": {"alias": "dog_sad_puppy", "legacy": ["委屈·幼犬眼"]},
    "委屈·幼犬眼": {"alias": "dog_sad_puppy", "redirect": "委屈/变体3_迟疑试探"},
}
