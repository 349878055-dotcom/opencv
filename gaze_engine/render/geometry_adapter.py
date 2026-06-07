"""geometry_adapter · MediaPipe 检测 → 底膜几何适配（人类 · fail-fast）

人类标定唯一路径：
  1. MediaPipe Face Landmarker 检测
  2. 换算公式 → SpeciesTemplate adjustments + render_baseline
  3. 任一步失败 → method=failed，明确报错（无 OpenCV/手标兜底）

用法::

    from gaze_engine.render.geometry_adapter import adapt_geometry

    result = adapt_geometry(species="human", photo_path=ref_photo)
    if result.method == "failed":
        raise RuntimeError(result.notes[-1])
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import cv2
    import numpy as np

    _HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    _HAS_CV2 = False

from gaze_engine.render.species_detector import (
    STANDARD_EYE_DIST,
    STANDARD_EYE_SIZE,
    detect_from_photo,
)
from gaze_engine.render.species_template import (
    species_default_template,
)

_HUMAN_SHAPE_KEYS = frozenset({
    "eye_size", "eye_aspect",
    "pupil_size", "iris_size",
})

_STANDARD_EYE_ASPECT = 2.0  # 宽/高，与 detection_to_template_adjustments 一致

# 人类标准底膜常量（按依赖顺序排列，勿调换行序）
_HUMAN_STANDARD_EYE_W = 150          # 单眼画布宽度
_HUMAN_STANDARD_IRIS_R = 44          # 虹膜半径
_HUMAN_STANDARD_PUPIL_R = 16         # 瞳孔半径
_HUMAN_STANDARD_TOTAL_EYE_H = 83     # 眼睑总高: UPPER(45) + LOWER(38)
# 双眼总宽 / 单眼高 ≈ 300/83 ≈ 3.61
_HUMAN_STANDARD_ASPECT = (2 * _HUMAN_STANDARD_EYE_W) / _HUMAN_STANDARD_TOTAL_EYE_H
_HUMAN_STANDARD_BROW_PEAK = 115.0    # 眉峰高度
_HUMAN_MODEL_BROW_PEAK = 115.0
_HUMAN_MODEL_BROW_INNER_RATIO = 90.0 / 115.0  # 内/外眉点相对眉峰高度


@dataclass
class GeometryAdaptResult:
    """几何适配器输出。"""

    anchors: dict[str, list[float]]
    adjustments: dict[str, float]
    confidence: float
    method: str
    auto_filled: bool
    notes: list[str] = field(default_factory=list)
    detection: dict[str, Any] = field(default_factory=dict)
    """原始检测数据（MediaPipe / Haar 返回的全部字段）。"""
    raw_adjustments: dict[str, float] = field(default_factory=dict)
    """过滤前的原始调整参数（MediaPipe 检测直接推算，三点标定路径已于 2026-06 移除）。"""
    render_baseline: dict[str, Any] = field(default_factory=dict)
    """人类渲染基线：瞳孔静息偏移、眉位比例（不进 SpeciesTemplate）。"""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp(v: float, lo: float = 0.5, hi: float = 1.5) -> float:
    return max(lo, min(hi, round(float(v), 3)))


def _required_anchors(anchors: dict[str, Any]) -> bool:
    for k in ("left_eye", "right_eye", "nose"):
        p = anchors.get(k)
        if not p or len(p) < 2:
            return False
    return True


def _auto_anchors_from_detection(
    detection: dict[str, Any],
    img_width: int,
    img_height: int,
    species: str = "human",
) -> dict[str, list[float]]:
    """检测框 → 眼/鼻锚点（像素坐标）。"""
    eyes = detection.get("eyes") or []
    if len(eyes) < 2:
        return {}

    le = (float(eyes[0][0]), float(eyes[0][1]))
    re = (float(eyes[1][0]), float(eyes[1][1]))
    eye_dist = math.hypot(re[0] - le[0], re[1] - le[1])
    if eye_dist < 5:
        return {}

    mid_x = (le[0] + re[0]) * 0.5
    mid_y = (le[1] + re[1]) * 0.5

    nose_tip = detection.get("nose_tip")
    if nose_tip and len(nose_tip) >= 2:
        nose_x, nose_y = float(nose_tip[0]), float(nose_tip[1])
    else:
        nose_y = mid_y + eye_dist * 0.62
        nose_x = mid_x

    return {
        "left_eye": [round(le[0], 2), round(le[1], 2)],
        "right_eye": [round(re[0], 2), round(re[1], 2)],
        "nose": [round(nose_x, 2), round(nose_y, 2)],
    }


def _human_eye_aspect_from_detection(detection: dict[str, Any]) -> float | None:
    """人类眼睑形状：标准宽高比 / 真人宽高比。"""
    det_w = float(detection.get("avg_eye_size") or 0)
    det_h = float(detection.get("avg_eye_height") or 0)
    if det_h <= 2 or det_w <= 2:
        asp = detection.get("eye_aspect")
        if asp and float(asp) > 0.5:
            detected_aspect = float(asp)
        else:
            return None
    else:
        detected_aspect = det_w / det_h
    if detected_aspect < 0.5:
        return None
    return max(0.6, min(1.4, round(_HUMAN_STANDARD_ASPECT / detected_aspect, 3)))


def _human_iris_size_from_detection(detection: dict[str, Any]) -> float | None:
    """真人虹膜半径 / 眼宽 → 相对标准 IRIS_R/EYE_W。"""
    iris_r = float(detection.get("avg_iris_radius") or 0)
    eye_w = float(detection.get("avg_eye_size") or 0)
    if iris_r <= 1 or eye_w <= 2:
        return None
    photo_ratio = iris_r / eye_w
    model_ratio = _HUMAN_STANDARD_IRIS_R / _HUMAN_STANDARD_EYE_W
    return max(0.55, min(1.45, round(photo_ratio / model_ratio, 3)))


def _human_pupil_size_from_detection(detection: dict[str, Any]) -> float | None:
    """从 MediaPipe 检测结果计算瞳孔缩放因子。

    从 pupil_offset 估算瞳孔直径，换算为相对标准 PUPIL_R/EYE_W 的比例。
    无兜底 — pupil_offset 全缺失直接报错。
    """
    eye_w = float(detection.get("avg_eye_size") or 0)
    iris_r = float(detection.get("avg_iris_radius") or 0)
    if eye_w <= 2:
        raise ValueError(f"Cannot compute pupil_size: avg_eye_size={eye_w}")
    if iris_r <= 1:
        raise ValueError(f"Cannot compute pupil_size: avg_iris_radius={iris_r}")

    # 四个瞳孔偏移量之和估算瞳孔直径
    offsets = [
        detection.get(k, 0)
        for k in ("pupil_offset_lx", "pupil_offset_ly",
                  "pupil_offset_rx", "pupil_offset_ry")
    ]
    pupil_d = sum(abs(float(v)) for v in offsets if v) / 2.0

    # 无兜底 — pupil_offset 全缺失/为零直接报错
    if pupil_d <= 1.0:
        raise ValueError(
            f"MediaPipe pupil_offset all zero/missing: pupil_d={pupil_d:.2f}. "
            "Cannot compute pupil_size without iris center offset landmarks."
        )

    pupil_ratio = pupil_d / eye_w
    # 标准瞳孔比 = 16 / 150
    model_ratio = _HUMAN_STANDARD_PUPIL_R / _HUMAN_STANDARD_EYE_W
    return max(0.4, min(2.0, round(pupil_ratio / model_ratio, 3)))


def _human_render_baseline_from_detection(
    detection: dict[str, Any],
    *,
    eye_size: float = 1.0,
) -> dict[str, Any]:
    """MediaPipe → 瞳孔静息偏移（模型像素）与眉位垂直比例。"""
    eye_w = float(detection.get("avg_eye_size") or 0)
    if eye_w <= 2:
        return {}

    # avg_eye_size 已是内外眼角全宽；_HUMAN_STANDARD_EYE_W 也是单眼全宽(EYE_W)
    model_eye_w = _HUMAN_STANDARD_EYE_W * max(eye_size, 0.5)
    photo_eye_w = eye_w
    scale = model_eye_w / photo_eye_w

    baseline: dict[str, Any] = {}
    max_rx = model_eye_w * 0.32
    max_ry = model_eye_w * 0.28
    for side, kx, ky in (
        ("left", "pupil_offset_lx", "pupil_offset_ly"),
        ("right", "pupil_offset_rx", "pupil_offset_ry"),
    ):
        if kx in detection and ky in detection:
            dx = max(-max_rx, min(max_rx, float(detection[kx]) * scale))
            dy = max(-max_ry, min(max_ry, float(detection[ky]) * scale))
            baseline[f"pupil_rest_{side}"] = [round(dx, 2), round(dy, 2)]

    eyes = detection.get("eyes") or []
    if len(eyes) >= 2:
        for side, eye_y, brow_lower_key in (
            ("left", float(eyes[0][1]), "left_brow_y_lower"),
            ("right", float(eyes[1][1]), "right_brow_y_lower"),
        ):
            brow_lower = detection.get(brow_lower_key)
            if brow_lower is None:
                brow_lower = detection.get(
                    "left_brow_y" if side == "left" else "right_brow_y"
                )
            if brow_lower is None:
                raise ValueError(
                    f"MediaPipe brow detection failed for {side} eye: "
                    "brow_lower landmark not found"
                )
            # 眼中心到眉线下沿（像素）→ 模型空间眉峰 Y（负=向上）
            photo_gap = eye_y - float(brow_lower)
            if photo_gap < 25:
                raise ValueError(
                    f"MediaPipe brow detection unreliable for {side} eye: "
                    f"photo_gap={photo_gap:.1f}px < 25px. "
                    "Please use a photo with visible eyebrows and normal expression."
                )
            peak_dy = -int(round(photo_gap * scale))
            peak_dy = max(-int(model_eye_w * 1.6), min(-18, peak_dy))
            inner_dy = int(round(peak_dy * _HUMAN_MODEL_BROW_INNER_RATIO))
            # 两眼共用「内负外正」：内眼角侧为负 X，外眼角侧为正 X
            brow_span = int(round(130 * max(eye_size, 0.5)))
            baseline[f"brow_{side}"] = {
                "inner": (-brow_span, inner_dy),
                "peak": (0, peak_dy),
                "outer": (brow_span, inner_dy),
            }

    return baseline


def apply_render_baseline(
    constants: dict[str, Any],
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    """将标定基线并入渲染器常量（眉位比例、瞳孔静息偏移）。"""
    if not baseline:
        return constants
    out = dict(constants)
    for side in ("left", "right"):
        brow = baseline.get(f"brow_{side}")
        if not isinstance(brow, dict):
            continue
        tag = side.upper()
        for part in ("inner", "peak", "outer"):
            pt = brow.get(part)
            if pt and len(pt) >= 2:
                out[f"BROW_{tag}_{part.upper()}_OFF"] = (
                    int(pt[0]), int(pt[1]),
                )
    for side in ("left", "right"):
        rest = baseline.get(f"pupil_rest_{side}")
        if rest and len(rest) >= 2:
            out[f"PUPIL_REST_{side.upper()}"] = (
                int(round(float(rest[0]))),
                int(round(float(rest[1]))),
            )
    return out


def _aspect_to_template_multiplier(raw_aspect: float) -> float:
    """检测宽/高 → SpeciesTemplate.eye_aspect 乘数。"""
    return _clamp(raw_aspect / _STANDARD_EYE_ASPECT, 0.75, 1.35)


def _eye_aspect_from_detection(detection: dict[str, Any]) -> float | None:
    """全脸检测眼框 → eye_aspect。"""
    asp = detection.get("eye_aspect")
    if asp and float(asp) > 0.5:
        return _aspect_to_template_multiplier(float(asp))
    ew = detection.get("avg_eye_size")
    eh = detection.get("avg_eye_height")
    if ew and eh and float(eh) > 1:
        return _aspect_to_template_multiplier(float(ew) / float(eh))
    return None


def _eye_aspect_from_photo(
    img: Any,
    anchors: dict[str, Any],
    *,
    face_rect: tuple[int, int, int, int] | None = None,
) -> float | None:
    """眼中心附近 + 可选整脸 ROI：Haar 眼框 → eye_aspect。"""
    if not _HAS_CV2 or cv2 is None or np is None:
        return None
    le = anchors.get("left_eye")
    re = anchors.get("right_eye")
    if not le or not re:
        return None

    eye_dist = math.hypot(float(re[0]) - float(le[0]), float(re[1]) - float(le[1]))
    if eye_dist < 5:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    aspects: list[float] = []

    def _scan_roi(x0: int, y0: int, x1: int, y1: int) -> None:
        roi = gray[y0:y1, x0:x1]
        if roi.size == 0 or roi.shape[0] < 8 or roi.shape[1] < 8:
            return
        boxes = cascade.detectMultiScale(roi, 1.05, 2, minSize=(12, 12))
        for (_, _, ew, eh) in boxes:
            if eh >= 3 and ew >= 3:
                aspects.append(float(ew) / float(eh))

    if face_rect and len(face_rect) >= 4:
        fx, fy, fw, fh = face_rect[:4]
        x0 = max(int(fx), 0)
        y0 = max(int(fy), 0)
        x1 = min(int(fx + fw), gray.shape[1])
        y1 = min(int(fy + int(fh * 0.55)), gray.shape[0])
        _scan_roi(x0, y0, x1, y1)

    radius = max(int(eye_dist * 0.28), 40)
    for pt in (le, re):
        cx, cy = int(pt[0]), int(pt[1])
        _scan_roi(
            max(cx - radius, 0), max(cy - radius, 0),
            min(cx + radius, gray.shape[1]), min(cy + radius, gray.shape[0]),
        )

    if not aspects:
        return None
    return _aspect_to_template_multiplier(float(np.median(aspects)))


def _geometry_fail(
    *,
    notes: list[str],
    msg: str,
    detection: dict[str, Any] | None = None,
) -> GeometryAdaptResult:
    return GeometryAdaptResult(
        anchors={},
        adjustments={},
        confidence=0.0,
        method="failed",
        auto_filled=False,
        notes=notes + [msg],
        detection=detection or {},
    )


def _anchors_from_mediapipe(detection: dict[str, Any]) -> dict[str, list[float]]:
    eyes = detection.get("eyes") or []
    nose = detection.get("nose_tip")
    if len(eyes) < 2:
        raise ValueError("MediaPipe 缺少双眼中心")
    if not nose or len(nose) < 2:
        raise ValueError("MediaPipe 缺少鼻尖 landmark")
    return {
        "left_eye": [round(float(eyes[0][0]), 2), round(float(eyes[0][1]), 2)],
        "right_eye": [round(float(eyes[1][0]), 2), round(float(eyes[1][1]), 2)],
        "nose": [round(float(nose[0]), 2), round(float(nose[1]), 2)],
    }


def _require_mediapipe_field(
    detection: dict[str, Any],
    key: str,
    *,
    min_value: float | None = None,
) -> float:
    if key not in detection:
        raise ValueError(f"MediaPipe 检测缺少字段: {key}")
    val = float(detection[key])
    if min_value is not None and val < min_value:
        raise ValueError(f"MediaPipe 字段 {key}={val} 无效（要求 ≥ {min_value}）")
    return val


def _human_adjustments_strict(detection: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
    """MediaPipe 测量 → 底膜旋钮（缺字段即抛错）。

    方向 A（2026-06）：绝对映射到 1024 画布。
    旧公式 ratio/ratio 将模型大眼比例（85.7%）当基准，
    导致真实人眼（~45%）被压缩到 0.52。新公式直接映射：
        scale_1024 = 模型眼距 / 照片眼距
        mapped_eye_w = 照片眼宽 × scale_1024
        eye_size = mapped_eye_w / 模型单眼宽(150)
    """
    det_eye_dist = _require_mediapipe_field(detection, "eye_distance", min_value=5)
    det_eye_size = _require_mediapipe_field(detection, "avg_eye_size", min_value=2)
    det_eye_height = _require_mediapipe_field(detection, "avg_eye_height", min_value=2)
    _require_mediapipe_field(detection, "avg_iris_radius", min_value=1)

    # 照片眼宽 → 1024 画布空间
    scale_1024 = STANDARD_EYE_DIST / det_eye_dist
    mapped_eye_w = det_eye_size * scale_1024
    model_eye_w = STANDARD_EYE_SIZE / 2  # 150px = EYE_W（单眼）
    eye_size_factor = mapped_eye_w / model_eye_w
    if not (0.35 <= eye_size_factor <= 1.8):
        raise ValueError(
            f"眼宽/眼距比超出合理范围: {eye_size_factor:.3f} "
            f"(mapped={mapped_eye_w:.1f}, model={model_eye_w})"
        )

    aspect_adj = _human_eye_aspect_from_detection(detection)
    if aspect_adj is None:
        raise ValueError(
            f"眼睑形状换算失败: avg_eye_size={det_eye_size}, avg_eye_height={det_eye_height}"
        )

    iris_adj = _human_iris_size_from_detection(detection)
    if iris_adj is None:
        raise ValueError("虹膜大小换算失败: avg_iris_radius 或 avg_eye_size 无效")

    # ── 瞳孔大小（新增 2026-06：从 MediaPipe pupil_offset 推算）──
    pupil_adj = _human_pupil_size_from_detection(detection)
    if pupil_adj is None:
        raise ValueError("瞳孔大小推算失败: avg_iris_radius 或 avg_eye_size 无效")

    notes = [
        f"eye_size=mapped_1024 ({mapped_eye_w:.1f}px/{model_eye_w}px)→{eye_size_factor:.2f}",
        f"eye_aspect=standard/detected ({_HUMAN_STANDARD_ASPECT:.2f}/"
        f"{det_eye_size/det_eye_height:.2f})→{aspect_adj}",
        f"iris_size→{iris_adj}",
        f"pupil_size→{pupil_adj}",
    ]
    return {
        "eye_size": round(eye_size_factor, 2),
        "eye_aspect": aspect_adj,
        "iris_size": iris_adj,
        "pupil_size": pupil_adj,
    }, notes


def _human_render_baseline_strict(
    detection: dict[str, Any],
    *,
    eye_size: float,
) -> tuple[dict[str, Any], list[str]]:
    """MediaPipe → 瞳孔静息 + 眉位（缺字段即抛错）。"""
    baseline = _human_render_baseline_from_detection(detection, eye_size=eye_size)
    notes: list[str] = []

    for side in ("left", "right"):
        if f"pupil_rest_{side}" not in baseline:
            raise ValueError(f"MediaPipe 瞳孔静息偏移缺失: {side}")
        if f"brow_{side}" not in baseline:
            raise ValueError(f"MediaPipe 眉位基线缺失: {side}")

    _require_mediapipe_field(detection, "pupil_offset_lx")
    _require_mediapipe_field(detection, "pupil_offset_ly")
    _require_mediapipe_field(detection, "pupil_offset_rx")
    _require_mediapipe_field(detection, "pupil_offset_ry")
    _require_mediapipe_field(detection, "left_brow_y_lower", min_value=1)
    _require_mediapipe_field(detection, "right_brow_y_lower", min_value=1)

    notes.append("render_baseline: pupil_rest×2 + brow×2")
    return baseline, notes


def _adapt_geometry_human(
    *,
    photo_path: Path,
    img_width: int = 0,
    img_height: int = 0,
) -> GeometryAdaptResult:
    """人类：MediaPipe-only，失败即报错。"""
    notes: list[str] = ["人类标定路径: MediaPipe-only"]

    if not _HAS_CV2:
        return _geometry_fail(notes=notes, msg="OpenCV 未安装，无法读取照片")

    if not photo_path.is_file():
        return _geometry_fail(notes=notes, msg=f"照片不存在: {photo_path}")

    img = cv2.imread(str(photo_path))
    if img is None:
        return _geometry_fail(notes=notes, msg=f"无法读取照片: {photo_path}")

    img_height, img_width = img.shape[:2]
    detection = detect_from_photo(photo_path, "human")

    if detection.get("error"):
        return _geometry_fail(
            notes=notes,
            msg=f"MediaPipe 检测失败: {detection['error']}",
            detection=detection,
        )

    if detection.get("method") != "mediapipe":
        return _geometry_fail(
            notes=notes,
            msg=f"检测方法非法: {detection.get('method')}（仅允许 mediapipe）",
            detection=detection,
        )

    try:
        anchors = _anchors_from_mediapipe(detection)
        adjustments, adj_notes = _human_adjustments_strict(detection)
        render_baseline, base_notes = _human_render_baseline_strict(
            detection, eye_size=adjustments["eye_size"],
        )
    except ValueError as e:
        return _geometry_fail(notes=notes, msg=str(e), detection=detection)

    notes.extend(adj_notes)
    notes.extend(base_notes)
    notes.append("锚点: 左眼/右眼/鼻尖 ← MediaPipe landmark")

    return GeometryAdaptResult(
        anchors=anchors,
        adjustments=adjustments,
        confidence=float(detection.get("confidence") or 0.95),
        method="mediapipe",
        auto_filled=True,
        notes=notes,
        detection=detection,
        raw_adjustments=dict(adjustments),
        render_baseline=render_baseline,
    )


def _filter_shape_adjustments(species: str, raw: dict[str, float]) -> dict[str, float]:
    keys = {
        "dog": _DOG_SHAPE_KEYS,
        "cat": _CAT_SHAPE_KEYS,
        "human": _HUMAN_SHAPE_KEYS,
    }.get(species, _HUMAN_SHAPE_KEYS)
    out: dict[str, float] = {}
    for k, v in raw.items():
        if k in keys and isinstance(v, (int, float)):
            out[k] = float(v)
    return out


def adapt_geometry(
    *,
    species: str,
    breed_id: str = "",
    img_width: int = 0,
    img_height: int = 0,
    anchors: dict[str, Any] | None = None,
    photo_path: str | Path | None = None,
) -> GeometryAdaptResult:
    """几何适配：人类仅 MediaPipe + 换算公式，失败即 method=failed。"""
    sp = (species or "human").strip().lower()

    if sp != "human":
        return _geometry_fail(
            notes=[f"物种 {sp} 未启用（门户仅人类）"],
            msg="仅支持 species=human",
        )

    if anchors:
        return _geometry_fail(
            notes=["人类标定拒绝手传 anchors"],
            msg="不支持手动标点，请仅上传照片由 MediaPipe 自动检测",
        )

    if not photo_path:
        return _geometry_fail(
            notes=["人类标定缺少 photo_path"],
            msg="必须提供参考照片路径",
        )

    return _adapt_geometry_human(
        photo_path=Path(photo_path),
        img_width=img_width,
        img_height=img_height,
    )


def shape_adjustment_diff(
    species: str,
    breed_id: str,
    adjustments: dict[str, float],
) -> list[dict[str, Any]]:
    """标定对比表：品种基准 vs 适配后形状参数（portal 用 before/after/delta）。"""
    from gaze_engine.render.species_template import PARAM_LABELS

    base = breed_baseline_template(species, breed_id or None)
    if species == "human":
        base = species_default_template("human")
    rows: list[dict[str, Any]] = []
    for k, av in adjustments.items():
        if not hasattr(base, k):
            continue
        bv = float(getattr(base, k))
        avf = float(av)
        if abs(avf - bv) < 0.015:
            continue
        delta = avf - bv
        if k == "eye_vertical":
            hint = "上移" if delta > 0 else "下移"
        elif k == "eye_aspect":
            hint = "更圆" if delta > 0 else "更扁"
        elif k == "ear_droop":
            hint = "更垂" if delta > 0 else "更立"
        else:
            hint = "增加" if delta > 0 else "减少"
        rows.append({
            "key": k,
            "label": PARAM_LABELS.get(k, k),
            "before": round(bv, 3),
            "after": round(avf, 3),
            "delta": round(delta, 3),
            "hint": hint,
        })
    return rows
