"""
狗品种配置 · 数据已迁移至 _shared/persona_matrix.json → breed_personas
通过 persona_compiler.get_persona(breed_id) 读取
"""
from __future__ import annotations

from gaze_engine._shared.persona_compiler import get_persona, list_persona_ids


def get_dog_breed(breed_id: str) -> dict:
    """按 ID 获取品种配置（委托 persona_compiler）"""
    p = get_persona(breed_id)
    return {
        "label": p.label,
        "base_offset": dict(p.base_offset),
        "scale_factor": dict(p.scale_factor),
    }


def list_dog_breeds() -> list[str]:
    """列出所有狗品种 ID"""
    return [pid for pid in list_persona_ids() if pid.endswith("_dog")]