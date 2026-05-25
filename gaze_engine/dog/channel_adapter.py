"""
狗通道适配器 · 将 EarParams（-1~1）映射为标准 12 通道（0~1）

与猫版 [cat/channel_adapter.py](gaze_engine/cat/channel_adapter.py) 对称，
区别：狗版 brow_raise 保留给眉脊（狗有眉毛肌），不作为第二耳通道。
"""
from __future__ import annotations

from typing import Dict, List

from gaze_engine._shared.slider_schema import EarParams


def ear_to_channel_values(ear: EarParams) -> Dict[str, float]:
    """
    将 EarParams（-1~1 范围）映射为 eyebrow / brow_raise 的 [0, 1] 基线值。

    狗版映射规则：
      - eyebrow  ← 左耳角度 left_angle: -1=全耷拉(垂耳)→0,  1=全竖立(立耳)→1
      - brow_raise ← 右耳角度 right_angle（狗有眉脊，保留独立语义）
      （left_offset / right_offset 保留给后续"耳尖微颤"扩展）
    """
    return {
        "eyebrow": (ear.left_angle + 1.0) / 2.0,
        "brow_raise": (ear.right_angle + 1.0) / 2.0,
    }


def inject_ear_into_channels(
    channels: Dict[str, List[float]],
    ear: EarParams,
) -> Dict[str, List[float]]:
    """
    将 EarParams 注入编译后的 12 通道，覆盖 eyebrow / brow_raise。

    调用时机：在 compile_to_channels() 之后、affine_renderer 之前。

    Args:
        channels: compile_to_channels() 的输出，12 键 × 150 帧
        ear: 来自 SliderPacket 的耳参数（-1~1 范围）

    Returns:
        覆盖耳通道后的同一 dict（原地修改 + 返回引用）
    """
    vals = ear_to_channel_values(ear)
    frame_count = len(next(iter(channels.values())))

    channels["eyebrow"] = [vals["eyebrow"]] * frame_count
    channels["brow_raise"] = [vals["brow_raise"]] * frame_count

    return channels