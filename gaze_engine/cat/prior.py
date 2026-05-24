"""
猫真人化先验 · 扫视动力学 + 第三眼睑 + 耳位耦合
TODO: 按 pet_eye_engine_migration_plan.md 第八章填充
"""
from __future__ import annotations

from typing import Any


def apply_cat_prior(
    channels: dict[str, list[float]],
    packet: Any,
) -> dict[str, list[float]]:
    """
    猫专用先验：
      - zeta=0.45, omega=18.0（过冲更大、更快）
      - 第三眼睑（内眦膜）短暂闭合
      - 瞳孔扫视时耳朵微转
    """
    # TODO: 实现猫扫视动力学
    raise NotImplementedError("Cat prior not yet implemented")