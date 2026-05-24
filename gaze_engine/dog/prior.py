"""
狗真人化先验 · 扫视动力学 + 耳位耦合
TODO: 填充
"""
from __future__ import annotations

from typing import Any


def apply_dog_prior(
    channels: dict[str, list[float]],
    packet: Any,
) -> dict[str, list[float]]:
    """
    狗专用先验：
      - zeta=0.60, omega=14.0（过冲中等、稍慢）
      - 瞳孔扫视时耳朵跟随微转
    """
    raise NotImplementedError("Dog prior not yet implemented")