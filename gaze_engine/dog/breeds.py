"""
狗品种配置 · 从 dog/breed_matrix.json 读取品种风格
"""
from __future__ import annotations

import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MATRIX_PATH = os.path.join(_THIS_DIR, "breed_matrix.json")

# 只写入渲染常量的品种结构项（耳/眉控制点），禁止覆盖 EYE_W 等客户可标定项
_BREED_STRUCTURE_KEYS = frozenset({
    "BROW_INNER_OFF", "BROW_PEAK_OFF", "BROW_OUTER_OFF",
    "EAR_LEFT_BASE", "EAR_RIGHT_BASE",
})

_cache: dict[str, Any] | None = None


def _load_matrix() -> dict[str, Any]:
    global _cache
    if _cache is None:
        with open(_MATRIX_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        _cache = raw.get("breed_personas") or {}
    return _cache


def get_dog_breed(breed_id: str) -> dict:
    """按 ID 获取品种配置（读 dog/breed_matrix.json）"""
    matrix = _load_matrix()
    if breed_id not in matrix:
        raise KeyError(f"未知狗品种 '{breed_id}'，可用选项: {list(matrix.keys())}")
    entry = matrix[breed_id]
    # 兼容旧字段 template_geometry
    structure = dict(entry.get("template_structure") or {})
    legacy = entry.get("template_geometry") or {}
    if not structure and legacy:
        structure = {
            k: legacy[k]
            for k in _BREED_STRUCTURE_KEYS
            if k in legacy
        }
    return {
        "label": entry.get("label", breed_id),
        "reference": entry.get("_reference", ""),
        "base_offset": dict(entry["base_offset"]),
        "scale_factor": dict(entry["scale_factor"]),
        "template_scales": dict(entry.get("template_scales") or {}),
        "template_structure": structure,
    }


def apply_breed_template_scales(template_params: dict[str, float], breed_id: str) -> dict[str, float]:
    """品种相对狗默认的乘数（eye_size 等），乘到已有模板参数上。"""
    try:
        cfg = get_dog_breed(breed_id)
    except KeyError:
        return template_params
    scales = cfg.get("template_scales") or {}
    out = dict(template_params)
    for k, v in scales.items():
        if k.startswith("_") or not isinstance(v, (int, float)):
            continue
        if k in out:
            out[k] = float(out[k]) * float(v)
        else:
            out[k] = float(v)
    return out


def apply_breed_structure(constants: dict[str, Any], breed_id: str) -> dict[str, Any]:
    """仅叠加品种耳/眉结构控制点（在客户标定乘数之前写入 base constants）。"""
    try:
        cfg = get_dog_breed(breed_id)
    except KeyError:
        return constants
    geo = dict(cfg.get("template_structure") or {})
    left_ear = geo.get("EAR_LEFT_BASE")
    if left_ear:
        geo.setdefault(
            "EAR_RIGHT_BASE",
            [[-float(p[0]), float(p[1])] for p in left_ear],
        )
    out = dict(constants)
    for k, v in geo.items():
        if k.startswith("_") or k not in _BREED_STRUCTURE_KEYS:
            continue
        if k in ("BROW_INNER_OFF", "BROW_PEAK_OFF", "BROW_OUTER_OFF"):
            out[k] = tuple(v)
        elif k in ("EAR_LEFT_BASE", "EAR_RIGHT_BASE"):
            out[k] = [tuple(p) for p in v]
    out["BREED_ID"] = breed_id
    out["BREED_LABEL"] = cfg.get("label", breed_id)
    out["BREED_REFERENCE"] = cfg.get("reference", "")
    return out


def apply_breed_geometry(constants: dict[str, Any], breed_id: str) -> dict[str, Any]:
    """兼容旧调用：等同 apply_breed_structure。"""
    return apply_breed_structure(constants, breed_id)


def list_dog_breeds() -> list[str]:
    """列出所有狗品种 ID"""
    return list(_load_matrix().keys())


def apply_breed_style(
    channels: dict[str, list[float]],
    breed_id: str,
) -> dict[str, list[float]]:
    """品种动态偏置：styled = base + scale × pulse（不改 E(t)）。"""
    if not breed_id or breed_id in ("default", ""):
        return channels
    from gaze_engine.dog.envelope_compile import DOG_CHANNELS
    from gaze_engine._shared.style_compose import apply_style_offset

    cfg = get_dog_breed(breed_id)
    return apply_style_offset(
        channels,
        cfg["base_offset"],
        cfg["scale_factor"],
        channel_keys=DOG_CHANNELS,
    )
