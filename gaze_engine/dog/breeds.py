"""
狗品种配置 · 4 品种
TODO: 按 pet_eye_engine_migration_plan.md 第五章填充
"""
from __future__ import annotations

from typing import Any

BREEDS: dict[str, dict[str, Any]] = {
    # "golden":   { "label": "金毛 / 外向型",   "base_offset": {...}, "scale_factor": {...} },
    # "shepherd": { "label": "德牧 / 机警型",   "base_offset": {...}, "scale_factor": {...} },
    # "corgi":    { "label": "柯基 / 活泼型",   "base_offset": {...}, "scale_factor": {...} },
    # "shiba":    { "label": "柴犬 / 倔强型",   "base_offset": {...}, "scale_factor": {...} },
}


def get_dog_breed(breed_id: str) -> dict[str, Any]:
    """按 ID 获取品种配置"""
    breed = BREEDS.get(breed_id)
    if not breed:
        raise KeyError(f"未知狗品种: {breed_id}")
    return breed