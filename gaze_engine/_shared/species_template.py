"""
species_template.py · 物种底膜模板参数

定义每个物种的可调底膜几何参数（"低膜"），实现：

  物种标准模板 → 品种偏移 → 客户调整 → 最终渲染常量

用法::

    from gaze_engine._shared.species_template import (
        species_default_template,
        adjust_template_for_breed,
        apply_customer_adjustments,
    )

    # 获取物种默认模板
    base = species_default_template("dog")

    # 叠加品种偏移（可选）
    bred = adjust_template_for_breed(base, "poodle_giant")

    # 叠加上一次保存的客户调整
    final = apply_customer_adjustments(bred, customer_adjustments_dict)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

__all__ = [
    "SpeciesTemplate",
    "species_default_template",
    "adjust_template_for_breed",
    "apply_customer_adjustments",
    "breed_template_ear_params",
    "template_to_renderer_constants",
    "ADJUSTABLE_PARAMS_HUMAN",
    "ADJUSTABLE_PARAMS_CAT",
    "ADJUSTABLE_PARAMS_DOG",
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

ADJUSTABLE_PARAMS_CAT = ADJUSTABLE_PARAMS_HUMAN + [
    "ear_size",          # 耳朵大小
    "ear_angle",         # 耳朵角度 (0=飞机耳, 1=竖耳)
    "ear_position_x",    # 耳位水平偏移
    "ear_position_y",    # 耳位垂直偏移
    "pupil_slit_ratio",  # 瞳孔竖椭圆比 (>1 = 更竖)
]

ADJUSTABLE_PARAMS_DOG = ADJUSTABLE_PARAMS_HUMAN + [
    "ear_size",          # 耳朵大小
    "ear_droop",         # 耳朵下垂度 (0=全竖立, 1=全垂)
    "ear_position_x",    # 耳位水平偏移
    "ear_position_y",    # 耳位垂直偏移
]


# ──────────────────────────────────────────────────────────
# 底膜模板数据类
# ──────────────────────────────────────────────────────────

@dataclass
class SpeciesTemplate:
    """物种底膜模板 — 渲染器用几何参数（缩放比，1.0 = 标准）

    所有字段都是比例因子，乘到 species 默认常量上得到最终值。
    """

    # ── 眼位（眼距、眼高） ──
    eye_distance: float = 1.0   # 两眼间距比例
    eye_vertical: float = 1.0   # 眼位垂直位置比例
    eye_size: float = 1.0       # 单眼大小比例
    eye_aspect: float = 1.0     # 眼睑高度比例 (>1 = 更圆眼)

    # ── 瞳孔/虹膜 ──
    pupil_size: float = 1.0     # 瞳孔半径比例
    iris_size: float = 1.0      # 虹膜半径比例

    # ── 耳位（猫/狗） ──
    ear_size: float = 1.0       # 耳朵大小比例
    ear_angle: float = 0.5      # 猫: 耳朵角度 (0=飞机耳, 1=竖耳)
    ear_droop: float = 0.5      # 狗: 耳朵下垂度 (0=全竖, 1=全垂)
    ear_position_x: float = 1.0 # 耳位水平偏移比例
    ear_position_y: float = 1.0 # 耳位垂直偏移比例

    # ── 猫专有 ──
    pupil_slit_ratio: float = 1.5  # 瞳孔竖椭圆比 (猫: >1)

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
    """获取物种的标准默认模板（全 1.0 = 标准几何）。"""
    t = SpeciesTemplate()
    if species == "cat":
        # 猫: 默认竖瞳孔
        t.pupil_slit_ratio = 1.5
        # 猫: 耳朵默认半竖
        t.ear_angle = 0.5
    elif species == "dog":
        # 狗: 耳朵默认半垂（贵宾犬风格）
        t.ear_droop = 0.6
        # 狗: 瞳孔比人稍大
        t.iris_size = 1.15
    elif species == "human":
        # 人类无特殊
        pass
    return t


def adjust_template_for_breed(
    template: SpeciesTemplate,
    species: str,
    breed_id: str | None,
) -> SpeciesTemplate:
    """叠加品种风格的几何偏移（从 breed_matrix.json 读取）。

    品种矩阵中的 base_offset 部分影响模板参数：
      - pupil_scale → pupil_size
      - iris_scale  → iris_size
      - eyebrow     → ear_angle (猫) / ear_droop (狗)
    """
    if not breed_id:
        return template

    try:
        if species == "cat":
            from gaze_engine.cat.breeds import get_cat_breed
            cfg = get_cat_breed(breed_id)
        elif species == "dog":
            from gaze_engine.dog.breeds import get_dog_breed
            cfg = get_dog_breed(breed_id)
        else:
            return template
    except (KeyError, ImportError):
        return template

    offset = cfg.get("base_offset", {})
    scales = cfg.get("template_scales") or {}
    t = SpeciesTemplate.from_dict(template.to_dict())

    # 映射 breed_matrix.base_offset → 模板参数
    if "pupil_scale" in offset:
        # base_offset 中心在 0.5, 映射到 [0.8, 1.2]
        t.pupil_size = 0.8 + offset["pupil_scale"] * 0.8
    if "iris_scale" in offset:
        t.iris_size = 0.8 + offset["iris_scale"] * 0.8
    if species == "cat" and "eyebrow" in offset:
        # 猫耳角度: eyebrow 越低 (0) → 飞机耳, 越高 (1) → 竖耳
        t.ear_angle = offset["eyebrow"]
    if species == "dog" and "eyebrow" in offset:
        # 狗耳下垂度: eyebrow 越低 (0) → 全垂, 越高 (1) → 全竖
        t.ear_droop = 1.0 - offset["eyebrow"]

    # 品种眼型乘数（相对狗默认 1.0，可被客户标定继续乘）
    for k, v in scales.items():
        if k.startswith("_") or not isinstance(v, (int, float)):
            continue
        if hasattr(t, k):
            setattr(t, k, float(getattr(t, k)) * float(v))

    return t


def breed_template_ear_params(species: str, breed_id: str | None) -> dict[str, float]:
    """未标耳尖时，从物种默认 + 品种偏移取耳朵相关参数。"""
    t = adjust_template_for_breed(species_default_template(species), species, breed_id or None)
    if species == "dog":
        keys = ("ear_droop", "ear_size", "ear_position_x", "ear_position_y")
    elif species == "cat":
        keys = ("ear_angle", "ear_size", "ear_position_x", "ear_position_y")
    else:
        return {}
    return {k: float(getattr(t, k)) for k in keys}


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


# ──────────────────────────────────────────────────────────
# 模板 → 渲染器常量的工具函数
# ──────────────────────────────────────────────────────────

_RENDERER_CONSTANTS: dict[str, dict[str, Any]] = {
    "human": {
        "LEFT_CX": 337, "LEFT_CY": 325,
        "RIGHT_CX": 687, "RIGHT_CY": 325,
        "EYE_W": 150,
        "UPPER_PEAK": 45, "LOWER_BOT": 38,
        "PUPIL_R_BASE": 16, "IRIS_R_BASE": 44,
        "BLINK_DROP": 40, "SQUINT_LIFT": 25,
        "LID_UPPER_DROP": 15, "LID_LOWER_LIFT": 10,
        "BROW_DOWN": 30, "BROW_RAISE_AMP": 25,
        "PUPIL_X_RANGE": 80, "PUPIL_Y_RANGE": 40,
        "IRIS_SCALE_RANGE": 1.3, "PUPIL_SCALE_RANGE": 1.5,
        "EYELID_THICK": 7, "BROW_THICK": 12, "PUPIL_THICK": 2,
        "BROW_INNER_OFF": (-130, -90),
        "BROW_PEAK_OFF": (0, -115),
        "BROW_OUTER_OFF": (130, -90),
    },
    "dog": {
        "LEFT_CX": 337, "LEFT_CY": 325,
        "RIGHT_CX": 687, "RIGHT_CY": 325,
        "EYE_W": 150,
        "UPPER_PEAK": 38, "LOWER_BOT": 32,
        "PUPIL_R_BASE": 18, "IRIS_R_BASE": 28,
        "BLINK_DROP": 38, "SQUINT_LIFT": 22,
        "LID_UPPER_DROP": 12, "LID_LOWER_LIFT": 8,
        "BROW_DOWN": 25, "BROW_RAISE_AMP": 20,
        "BROW_INNER_OFF": (-110, -80),
        "BROW_PEAK_OFF": (0, -100),
        "BROW_OUTER_OFF": (110, -80),
        "PUPIL_X_RANGE": 80, "PUPIL_Y_RANGE": 40,
        "IRIS_SCALE_RANGE": 1.4, "PUPIL_SCALE_RANGE": 1.6,
        "EYELID_THICK": 7, "BROW_THICK": 10, "PUPIL_THICK": 2,
        "EAR_THICK": 10,
        "EAR_DROOP": 0.6,
        # 相对各自眼中心的耳控制点（右耳勿用绝对坐标）
        "EAR_LEFT_BASE": [(-50, -140), (20, -155), (90, -130)],
        "EAR_RIGHT_BASE": [(50, -140), (120, -155), (190, -130)],
    },
    "cat": {
        "LEFT_CX": 337, "LEFT_CY": 325,
        "RIGHT_CX": 687, "RIGHT_CY": 325,
        "EYE_W": 140,           # 猫眼更圆/更宽
        "UPPER_PEAK": 40,       # 猫眼更圆
        "LOWER_BOT": 34,
        "PUPIL_R_BASE": 8,      # 猫瞳孔可缩更小
        "IRIS_R_BASE": 36,      # 猫虹膜更大
        "BLINK_DROP": 35,
        "SQUINT_LIFT": 20,
        "LID_UPPER_DROP": 12,
        "LID_LOWER_LIFT": 8,
        "BROW_DOWN": 20,
        "BROW_RAISE_AMP": 18,
        "BROW_INNER_OFF": (-120, -85),
        "BROW_PEAK_OFF": (0, -108),
        "BROW_OUTER_OFF": (120, -85),
        "PUPIL_X_RANGE": 70,
        "PUPIL_Y_RANGE": 35,
        "IRIS_SCALE_RANGE": 1.2,
        "PUPIL_SCALE_RANGE": 1.8,  # 猫瞳孔缩放范围更大
        "EYELID_THICK": 6,
        "BROW_THICK": 8,
        "PUPIL_THICK": 2,
        "EAR_THICK": 10,
        "EAR_DROOP": 0.3,      # 猫默认耳角度 (0=飞机耳, 1=竖耳)
        "PUPIL_SLIT_RATIO": 1.5,  # 猫瞳孔竖椭圆比
        # 猫耳默认控制点 (尖三角形，竖耳风格)
        "EAR_LEFT_BASE": [(-55, -130), (-5, -165), (45, -120)],
        "EAR_RIGHT_BASE": [(615, -130), (665, -165), (715, -120)],
    },
}


def template_to_renderer_constants(
    species: str,
    template: SpeciesTemplate | None = None,
    breed_id: str | None = None,
) -> dict[str, Any]:
    """将模板参数合并到物种渲染器常量中。

    Args:
        species: "human" / "cat" / "dog"
        template: 模板参数，None 则使用标准默认

    Returns:
        可直接解包到渲染器 __init__ 的常量 dict
    """
    base = dict(_RENDERER_CONSTANTS.get(species, _RENDERER_CONSTANTS["human"]))

    # 品种耳/眉结构（先于客户标定乘数，且绝不覆盖 EYE_W 等）
    if species == "dog" and breed_id:
        from gaze_engine.dog.breeds import apply_breed_structure
        base = apply_breed_structure(base, breed_id)

    if template is None:
        template = species_default_template(species)

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
    base["EYE_W"] = max(60, int(base["EYE_W"] * t.eye_size))

    # ── 眼睑高度 (eye_aspect) ──
    base["UPPER_PEAK"] = max(10, int(base["UPPER_PEAK"] * t.eye_aspect))
    base["LOWER_BOT"] = max(8, int(base["LOWER_BOT"] * t.eye_aspect))

    # ── 瞳孔/虹膜 ──
    base["PUPIL_R_BASE"] = max(2, int(base["PUPIL_R_BASE"] * t.pupil_size))
    base["IRIS_R_BASE"] = max(4, int(base["IRIS_R_BASE"] * t.iris_size))

    # ── 耳下垂度/角度 ──
    if "EAR_DROOP" in base:
        if species == "cat":
            base["EAR_DROOP"] = min(1.0, max(0.0, t.ear_angle))
        elif species == "dog":
            base["EAR_DROOP"] = min(1.0, max(0.0, t.ear_droop))

    # ── 猫竖瞳孔比 ──
    if species == "cat" and "PUPIL_SLIT_RATIO" in base:
        base["PUPIL_SLIT_RATIO"] = max(1.0, t.pupil_slit_ratio)

    _adjust_ear_constants(base, t)

    return base


# 参数中文名（门户对比表）
PARAM_LABELS: dict[str, str] = {
    "eye_distance": "眼距",
    "eye_vertical": "眼位高低",
    "eye_size": "眼睛大小",
    "eye_aspect": "眼睑形状",
    "pupil_size": "瞳孔大小",
    "iris_size": "虹膜大小",
    "ear_droop": "垂耳程度",
    "ear_angle": "耳朵角度",
    "ear_size": "耳朵大小",
    "ear_position_x": "耳位左右",
    "ear_position_y": "耳位上下",
    "pupil_slit_ratio": "竖瞳比例",
}


def breed_baseline_template(species: str, breed_id: str | None) -> SpeciesTemplate:
    """物种默认 + 品种偏移（不含客户照片标定）。"""
    return adjust_template_for_breed(species_default_template(species), species, breed_id or None)


def diff_template_params(
    before: SpeciesTemplate,
    after: SpeciesTemplate,
    species: str,
) -> list[dict[str, Any]]:
    """对比两个模板，返回标定引起的微调项。"""
    keys = {
        "dog": ADJUSTABLE_PARAMS_DOG,
        "cat": ADJUSTABLE_PARAMS_CAT,
        "human": ADJUSTABLE_PARAMS_HUMAN,
    }.get(species, ADJUSTABLE_PARAMS_HUMAN)
    rows: list[dict[str, Any]] = []
    for k in keys:
        bv = float(getattr(before, k))
        av = float(getattr(after, k))
        if abs(av - bv) < 0.015:
            continue
        delta = av - bv
        if k == "eye_vertical":
            hint = "上移" if delta > 0 else "下移"
        elif k in ("eye_distance", "eye_size", "iris_size", "pupil_size", "ear_size"):
            hint = "相对品种基准偏宽" if delta > 0 else "相对品种基准偏窄"
        elif k == "ear_droop":
            hint = "更垂" if delta > 0 else "更立"
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


def _adjust_ear_constants(base: dict, t: SpeciesTemplate) -> None:
    """根据模板参数调整耳朵控制点。"""
    for ear_key in ("EAR_LEFT_BASE", "EAR_RIGHT_BASE"):
        if ear_key not in base:
            continue
        pts = list(base[ear_key])
        adjusted = []
        for (x, y) in pts:
            new_x = int(x * t.ear_position_x)
            new_y = int(y * t.ear_position_y)
            adjusted.append((new_x, new_y))
        base[ear_key] = adjusted


# ── 快速自检 ──
if __name__ == "__main__":
    for sp in ("human", "cat", "dog"):
        tmpl = species_default_template(sp)
        consts = template_to_renderer_constants(sp, tmpl)
        print(f"\n=== {sp} ===")
        print(f"  LEFT_CX={consts['LEFT_CX']} RIGHT_CX={consts['RIGHT_CX']}")
        print(f"  EYE_W={consts['EYE_W']} UPPER_PEAK={consts['UPPER_PEAK']}")
        print(f"  PUPIL_R={consts['PUPIL_R_BASE']} IRIS_R={consts['IRIS_R_BASE']}")
        if "EAR_LEFT_BASE" in consts:
            print(f"  EAR_LEFT={consts['EAR_LEFT_BASE']}")