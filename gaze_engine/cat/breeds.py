"""
猫品种配置 · 4 品种
TODO: 按 pet_eye_engine_migration_plan.md 第五章填充 breed_personas
"""
from __future__ import annotations

from typing import Any

BREEDS: dict[str, dict[str, Any]] = {
    # "ragdoll":  { "label": "布偶猫 / 温顺型", "base_offset": {...}, "scale_factor": {...} },
    # "siamese":  { "label": "暹罗猫 / 高冷型", "base_offset": {...}, "scale_factor": {...} },
    # "stray":    { "label": "田园猫 / 机敏型", "base_offset": {...}, "scale_factor": {...} },
    # "british":  { "label": "英短 / 憨厚型",   "base_offset": {...}, "scale_factor": {...} },
}


def get_cat_breed(breed_id: str) -> dict[str, Any]:
    """按 ID 获取品种配置"""
    breed = BREEDS.get(breed_id)
    if not breed:
        raise KeyError(f"未知猫品种: {breed_id}")
    return breed