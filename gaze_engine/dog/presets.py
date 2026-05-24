"""
狗情绪预设 · 10 个
TODO: 按 pet_eye_engine_migration_plan.md 第四章填充
"""
from __future__ import annotations

from typing import Any

DOG_PRESETS: dict[str, dict[str, Any]] = {
    # "dog_alert_bark":       { ... },  # 警觉·吠
    # "dog_happy_wag":        { ... },  # 开心·摇尾
    # "dog_sad_puppy":        { ... },  # 委屈·幼犬眼
    # "dog_scared_tuck":      { ... },  # 恐惧·夹尾
    # "dog_angry_growl":      { ... },  # 愤怒·低吼
    # "dog_curious_cock":     { ... },  # 好奇·歪头
    # "dog_submissive_look":  { ... },  # 服从·回避
    # "dog_play_bow":         { ... },  # 邀玩·趴
    # "dog_guilty_side":      { ... },  # 心虚·偷瞄
    # "dog_content_sigh":     { ... },  # 满足·叹气
}


def dog_packet_from_preset(name: str) -> "SliderPacket":
    """狗预设名 → SliderPacket"""
    raise NotImplementedError("Dog presets not yet configured")