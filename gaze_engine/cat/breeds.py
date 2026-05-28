"""
猫品种配置
真源：预设资产/风格包/cat/{id}/style.json；回退 cat/breed_matrix.json
"""
from __future__ import annotations

import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MATRIX_PATH = os.path.join(_THIS_DIR, "breed_matrix.json")

_cache: dict[str, Any] | None = None


def _load_matrix() -> dict[str, Any]:
    global _cache
    if _cache is None:
        with open(_MATRIX_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        _cache = raw.get("breed_personas") or {}
    return _cache


def get_cat_breed(breed_id: str) -> dict:
    """按 ID 获取品种配置（读 cat/breed_matrix.json）"""
    matrix = _load_matrix()
    if breed_id not in matrix:
        raise KeyError(f"未知猫品种 '{breed_id}'，可用选项: {list(matrix.keys())}")
    entry = matrix[breed_id]
    return {
        "label": entry.get("label", breed_id),
        "base_offset": dict(entry["base_offset"]),
        "scale_factor": dict(entry["scale_factor"]),
    }


def list_cat_breeds() -> list[str]:
    """列出所有猫品种 ID"""
    return list(_load_matrix().keys())


def apply_breed_style(
    channels: dict[str, list[float]],
    breed_id: str,
) -> dict[str, list[float]]:
    """品种动态偏置：styled = base + scale × pulse（不改 E(t)）。"""
    if not breed_id or breed_id in ("default", ""):
        return channels
    from gaze_engine.cat.envelope_compile import CAT_CHANNELS
    from gaze_engine._shared.style_compose import (
        apply_style_offset,
        load_style_json,
        style_offsets_from_dict,
    )

    raw = load_style_json("cat", breed_id)
    if raw is not None:
        bo, sf = style_offsets_from_dict(raw)
    else:
        cfg = get_cat_breed(breed_id)
        bo, sf = cfg["base_offset"], cfg["scale_factor"]
    return apply_style_offset(channels, bo, sf, channel_keys=CAT_CHANNELS)