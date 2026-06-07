"""
species_template.py · 人类底膜模板参数

定义人类的可调底膜几何参数（"低膜"），实现：

  标准模板 → 客户调整 → 最终渲染常量

用法::

    from gaze_engine.render.species_template import (
        species_default_template,
        apply_customer_adjustments,
    )

    # 获取人类默认模板
    base = species_default_template("human")

    # 叠加上一次保存的客户调整
    final = apply_customer_adjustments(base, customer_adjustments_dict)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

__all__ = [
    "SpeciesTemplate",
    "species_default_template",
    "apply_customer_adjustments",
    "template_to_renderer_constants",
    "sanitize_human_spatial_adjustments",
    "template_for_spatial_render",
    "ADJUSTABLE_PARAMS_HUMAN",
    "HUMAN_SPATIAL_TEMPLATE_KEYS",
]


# ──────────────────────────────────────────────────────────
# 可调参数清单（供 UI 滑杆和 OpenCV 检测使用）
# ──────────────────────────────────────────────────────────

ADJUSTABLE_PARAMS_HUMAN = [
    "eye_distance",      # 眼距
    "eye_vertical",      # 眼位垂直
    "eye_size",          # 眼睛大小
    "eye_aspect",        # 眼睛宽高比 (>1 = 更圆)
    "pupil_size",        # 瞳孔大小
    "iris_size",         # 虹膜大小
]

# 空间仿射承担眼距/眼位；形状参数只管眼宽/眼形
HUMAN_SPATIAL_TEMPLATE_KEYS = frozenset({
    "eye_distance", "eye_vertical",
})


# ──────────────────────────────────────────────────────────
# 底膜模板数据类
# ──────────────────────────────────────────────────────────

@dataclass
class SpeciesTemplate:
    """人类底膜模板 — 渲染器用几何参数（缩放比，1.0 = 标准）

    所有字段都是比例因子，乘到人类默认常量上得到最终值。
    """

    # ── 眼位（眼距、眼高） ──
    eye_distance: float = 1.0   # 两眼间距比例
    eye_vertical: float = 1.0   # 眼位垂直位置比例
    eye_size: float = 1.0       # 单眼大小比例
    eye_aspect: float = 1.0     # 眼睑高度比例 (>1 = 更圆眼)

    # ── 瞳孔/虹膜 ──
    pupil_size: float = 1.0     # 瞳孔半径比例
    iris_size: float = 1.0      # 虹膜半径比例

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpeciesTemplate:
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: float(v) for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# ──────────────────────────────────────────────────────────
# 物种默认模板
# ──────────────────────────────────────────────────────────

def species_default_template(species: str) -> SpeciesTemplate:
    """获取人类标准默认模板。

    仅从预设资产 JSON（species_default.json）读取作为唯一真源。
    不设硬编码回退，JSON 不存在或格式错误时抛 FileNotFoundError / ValueError。
    """
    from asset_lib import species_membrane_default_path

    path: Path = species_membrane_default_path(species)
    if not path.exists():
        raise FileNotFoundError(
            f"预设底膜 JSON 不存在: {path} —— "
            f"请确认 预设资产/底膜包/species_default.json 存在且内容正确"
        )

    with open(path, encoding="utf-8") as f:
        data: dict = json.load(f)

    params: dict = data.get("template_params", {})
    if not params:
        raise ValueError(
            f"预设底膜 JSON 缺少 template_params 字段: {path}"
        )

    return SpeciesTemplate.from_dict(params)


def adjust_template_for_breed(
    template: SpeciesTemplate,
    species: str,
    breed_id: str | None,
) -> SpeciesTemplate:
    """（保留函数签名兼容性，人类无品种概念，原样返回。）"""
    return template


def apply_customer_adjustments(
    template: SpeciesTemplate,
    adjustments: dict[str, float] | None,
) -> SpeciesTemplate:
    """叠加客户照片检测/手动调整的参数。"""
    if not adjustments:
        return template
    t = SpeciesTemplate.from_dict(template.to_dict())
    valid_keys = set(SpeciesTemplate.__dataclass_fields__.keys())
    for k, v in adjustments.items():
        if k in valid_keys and isinstance(v, (int, float)):
            setattr(t, k, float(v))
    return t


def sanitize_human_spatial_adjustments(
    adjustments: dict[str, float] | None,
) -> dict[str, float]:
    """人类标定 adjustments：眼距/眼位由 spatial_calibration 承担。"""
    if not adjustments:
        return {}
    return {
        k: float(v) for k, v in adjustments.items()
        if k not in HUMAN_SPATIAL_TEMPLATE_KEYS and isinstance(v, (int, float))
    }


def template_for_spatial_render(
    template: SpeciesTemplate,
    species: str,
    breed_id: str | None = None,
) -> SpeciesTemplate:
    """空间仿射渲染前：眼距/眼位回退基准，避免与仿射矩阵冲突。"""
    base = species_default_template("human")
    t = SpeciesTemplate.from_dict(template.to_dict())
    t.eye_distance = base.eye_distance
    t.eye_vertical = base.eye_vertical
    return t


# ──────────────────────────────────────────────────────────
# 模板 → 渲染器常量的工具函数
# ──────────────────────────────────────────────────────────

# 人类标准模型常量（1024×1024 画布基准，供 template_to_renderer_constants 推导使用）
_HUMAN_STANDARD_CONSTANTS: dict[str, Any] = {
    "LEFT_CX": 337, "LEFT_CY": 325,
    "RIGHT_CX": 687, "RIGHT_CY": 325,
    "EYE_W": 150,
    # ⚠️ 以下参数由 template_to_renderer_constants 推导：
    #   UPPER_PEAK        = std_eye_h × 0.55
    #   LOWER_BOT         = std_eye_h × 0.45
    #   PUPIL_R_BASE      = EYE_W × 16/150
    #   IRIS_R_BASE       = EYE_W × 44/150
    #   BLINK_DROP        = UPPER_PEAK
    #   SQUINT_LIFT       = LOWER_BOT
    #   BROW_DOWN/RAISE   = UPPER_PEAK
    #   BROW_INNER/PEAK/OUTER → render_baseline 注入
}

# 标准人类底膜：单眼宽高比 = EYE_W / 眼睑总高 = 150 / 83 ≈ 1.807
# 眼睑总高 = UPPER_PEAK(45) + LOWER_BOT(38) = 83（标准模型解剖值）
_HUMAN_STANDARD_EYE_ASPECT = 150 / 83

_RENDERER_CONSTANTS: dict[str, dict[str, Any]] = {
    "human": {
        # 画布坐标（标准模型基准，template_to_renderer_constants 中由 template 缩放）
        "LEFT_CX": 337, "LEFT_CY": 325,
        "RIGHT_CX": 687, "RIGHT_CY": 325,
        "EYE_W": 150,
        # ⚠️ 以下几何参数不再设默认值，必须从 template + render_baseline 推导：
        #   UPPER_PEAK/LOWER_BOT   → template.eye_size × template.eye_aspect
        #   PUPIL_R_BASE           → template.pupil_size（由 MediaPipe 检测）
        #   IRIS_R_BASE            → template.iris_size
        #   BLINK_DROP/SQUINT_LIFT → template.eye_aspect 推导
        #   BROW_INNER/PEAK/OUTER  → render_baseline（apply_render_baseline 注入）
        #   BROW_DOWN/RAISE_AMP    → template 推导
        # 渲染样式常量（非几何检测，可保留默认值）
        "LID_UPPER_DROP": 15, "LID_LOWER_LIFT": 10,
        "PUPIL_X_RANGE": 80, "PUPIL_Y_RANGE": 40,
        "IRIS_SCALE_RANGE": 1.3, "PUPIL_SCALE_RANGE": 1.5,
        "EYELID_THICK": 7, "BROW_THICK": 12, "PUPIL_THICK": 2,
    },
}


def template_to_renderer_constants(
    species: str,
    template: SpeciesTemplate | None = None,
    breed_id: str | None = None,
) -> dict[str, Any]:
    """将模板参数合并到人类渲染器常量中。

    Args:
        species: "human"（其他值回退到 human）
        template: 模板参数，None 则使用标准默认

    Returns:
        可直接解包到渲染器 __init__ 的常量 dict
    """
    base = dict(_RENDERER_CONSTANTS["human"])

    if template is None:
        template = species_default_template("human")

    t = template

    # ── 眼位 —— 以左右眼中心点间距为基准 ──
    left_cx = base["LEFT_CX"]
    right_cx = base["RIGHT_CX"]
    center_x = (left_cx + right_cx) / 2
    half_dist = (right_cx - left_cx) / 2

    new_half = half_dist * t.eye_distance
    base["LEFT_CX"] = int(center_x - new_half)
    base["RIGHT_CX"] = int(center_x + new_half)

    # 眼位垂直
    cy = base["LEFT_CY"]
    base["LEFT_CY"] = int(cy * t.eye_vertical)
    base["RIGHT_CY"] = int(cy * t.eye_vertical)

    # ── 眼睛大小 ──
    base["EYE_W"] = max(22, int(base["EYE_W"] * t.eye_size))

    # ── 从标准模型解剖 + template 推导几何参数（无硬编码默认值）──
    _std_eye_h = base["EYE_W"] / _HUMAN_STANDARD_EYE_ASPECT

    # 合同 §4.2：UPPER_PEAK = eye_height × 0.55, LOWER_BOT = eye_height × 0.45
    base["UPPER_PEAK"] = max(10, int(_std_eye_h * 0.55 * t.eye_aspect))
    base["LOWER_BOT"] = max(8, int(_std_eye_h * 0.45 * t.eye_aspect))

    # 瞳孔/虹膜半径 = 标准解剖比例 × 对应缩放因子
    base["PUPIL_R_BASE"] = max(2, int(base["EYE_W"] * (16 / 150) * t.pupil_size))
    base["IRIS_R_BASE"] = max(4, int(base["EYE_W"] * (44 / 150) * t.iris_size))

    # 安全钳制：虹膜 ≤ 眼宽×0.55，瞳孔 ≤ 虹膜×0.48
    base["IRIS_R_BASE"] = min(base["IRIS_R_BASE"], max(4, int(base["EYE_W"] * 0.55)))
    base["PUPIL_R_BASE"] = min(base["PUPIL_R_BASE"], max(2, int(base["IRIS_R_BASE"] * 0.48)))

    # BLINK_DROP / SQUINT_LIFT 与眼睑高度成正比
    base["BLINK_DROP"] = max(12, int(_std_eye_h * 0.55 * t.eye_aspect))
    base["SQUINT_LIFT"] = max(6, int(_std_eye_h * 0.45 * t.eye_aspect))

    # BROW_DOWN / BROW_RAISE_AMP 与眼睑高度成正比
    base["BROW_DOWN"] = max(10, int(_std_eye_h * 0.55 * t.eye_aspect))
    base["BROW_RAISE_AMP"] = max(10, int(_std_eye_h * 0.55 * t.eye_aspect))

    return base


# 参数中文名（门户对比表）
PARAM_LABELS: dict[str, str] = {
    "eye_distance": "眼距",
    "eye_vertical": "眼位高低",
    "eye_size": "眼睛大小",
    "eye_aspect": "眼睑形状",
    "pupil_size": "瞳孔大小",
    "iris_size": "虹膜大小",
}


def breed_baseline_template(species: str, breed_id: str | None) -> SpeciesTemplate:
    """人类无品种概念，直接返回物种默认模板（从 JSON 读取）。"""
    return species_default_template(species)


def diff_template_params(
    before: SpeciesTemplate,
    after: SpeciesTemplate,
    species: str,
) -> list[dict[str, Any]]:
    """对比两个模板，返回标定引起的微调项。"""
    keys = ADJUSTABLE_PARAMS_HUMAN
    rows: list[dict[str, Any]] = []
    for k in keys:
        bv = float(getattr(before, k))
        av = float(getattr(after, k))
        if abs(av - bv) < 0.015:
            continue
        delta = av - bv
        if k == "eye_vertical":
            hint = "上移" if delta > 0 else "下移"
        elif k in ("eye_distance", "eye_size", "iris_size", "pupil_size"):
            hint = "偏宽" if delta > 0 else "偏窄"
        else:
            hint = "增加" if delta > 0 else "减少"
        rows.append({
            "key": k,
            "label": PARAM_LABELS.get(k, k),
            "before": round(bv, 2),
            "after": round(av, 2),
            "delta": round(delta, 2),
            "hint": hint,
        })
    return rows


# ── 快速自检 ──
if __name__ == "__main__":
    tmpl = species_default_template("human")
    consts = template_to_renderer_constants("human", tmpl)
    print(f"LEFT_CX={consts['LEFT_CX']} RIGHT_CX={consts['RIGHT_CX']}")
    print(f"EYE_W={consts['EYE_W']} UPPER_PEAK={consts['UPPER_PEAK']}")
    print(f"PUPIL_R={consts['PUPIL_R_BASE']} IRIS_R={consts['IRIS_R_BASE']}")