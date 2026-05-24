"""
猫情绪预设 · 12 个
TODO: 按 pet_eye_engine_migration_plan.md 第四章填充具体参数
"""
from __future__ import annotations

from typing import Any

from gaze_engine._shared.slider_schema import SliderPacket

CAT_PRESETS: dict[str, dict[str, Any]] = {
    # "cat_alarm_stare": { ... },    # 警觉·盯
    # "cat_hunt_fixate": { ... },    # 狩猎·锁定
    # "cat_startle_fluff": { ... },  # 惊吓·炸毛
    # "cat_curious_tilt": { ... },   # 好奇·歪头
    # "cat_cuddle_squint": { ... },  # 撒娇·眯眼
    # "cat_content_bliss": { ... },  # 满足·飘然
    # "cat_annoyed_swish": { ... },  # 不耐烦·甩尾
    # "cat_scared_flatten": { ... }, # 恐惧·贴地
    # "cat_sad_whimper": { ... },    # 委屈·呜咽
    # "cat_angry_hiss": { ... },     # 愤怒·哈气
    # "cat_sleepy_droop": { ... },   # 困倦·迷离
    # "cat_play_pounce": { ... },    # 玩耍·扑击
}

CAT_PRESET_GROUPS: tuple[dict[str, Any], ...] = (
    {"label": "警觉 · 攻击", "keys": ["cat_alarm_stare", "cat_hunt_fixate", "cat_angry_hiss"]},
    {"label": "恐惧 · 退缩", "keys": ["cat_startle_fluff", "cat_scared_flatten", "cat_sad_whimper"]},
    {"label": "亲昵 · 放松", "keys": ["cat_cuddle_squint", "cat_content_bliss", "cat_sleepy_droop"]},
    {"label": "好奇 · 玩耍", "keys": ["cat_curious_tilt", "cat_play_pounce", "cat_annoyed_swish"]},
)


def cat_packet_from_preset(name: str) -> SliderPacket:
    """猫预设名 → SliderPacket（含 EarParams）"""
    data = CAT_PRESETS.get(name)
    if not data:
        raise KeyError(f"未知猫预设: {name}")
    # TODO: 解析 data 中的 macro / hold_seg / ear 字段
    raise NotImplementedError("Presets not yet configured")