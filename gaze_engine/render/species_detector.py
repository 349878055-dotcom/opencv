#!/usr/bin/env python3
"""
species_detector.py · 从客户照片自动检测底膜模板参数

检测策略:

  人类 → MediaPipe Face Mesh (468 个面部 3D 关键点)
         精确定位眼角、瞳孔、眉峰、面部轮廓

用法::

    from gaze_engine.render.species_detector import (
        detect_human_face_mediapipe,
        detection_to_template_adjustments,
    )

    # 单张检测
    result = detect_human_face_mediapipe(img)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

# ── 路径 ──
_PKG = Path(__file__).resolve().parent.parent.parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

# ── MediaPipe（人类脸部检测，首选）──
_HAS_MP = False
_MP_LANDMARKER = None
try:
    import mediapipe as mp
    from mediapipe.tasks.python.vision.face_landmarker import (
        FaceLandmarker, FaceLandmarkerOptions,
    )
    from mediapipe.tasks.python.core.base_options import BaseOptions
    from mediapipe.tasks.python.vision.core.image import Image as MpImage

    # 查找预下载模型文件（tools/mediapipe_models/）
    _mp_model_path = str(_PKG / "tools" / "mediapipe_models" / "face_landmarker.task")
    if Path(_mp_model_path).is_file():
        _MP_LANDMARKER = FaceLandmarker.create_from_options(
            FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=_mp_model_path),
                num_faces=1,
                min_face_detection_confidence=0.5,
            )
        )
        _HAS_MP = True
except Exception:
    pass

# ── OpenCV（用于 MediaPipe 加载图片）──
_HAS_CV2 = False
try:
    import cv2

    _HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore


# ═══════════════════════════════════════════════════════════
# MediaPipe 人脸关键点索引
# ═══════════════════════════════════════════════════════════

# 左眼
LEFT_EYE_OUTER = 33  # 外眼角
LEFT_EYE_INNER = 133  # 内眼角
LEFT_EYE_TOP = 159  # 上眼睑
LEFT_EYE_BOTTOM = 145  # 下眼睑
LEFT_IRIS_CENTER = 468
LEFT_IRIS_RING = [469, 470, 471, 472]
LEFT_IRIS = [468, 469, 470, 471, 472]  # 中心 + 环

# 右眼
RIGHT_EYE_OUTER = 362
RIGHT_EYE_INNER = 263
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_IRIS_CENTER = 473
RIGHT_IRIS_RING = [474, 475, 476, 477]
RIGHT_IRIS = [473, 474, 475, 476, 477]  # 中心 + 环

# 眉毛
LEFT_BROW = [46, 53, 52, 65, 55, 70]  # 内→外
RIGHT_BROW = [276, 283, 282, 295, 285, 300]
LEFT_BROW_INNER = 46
LEFT_BROW_PEAK = 53
LEFT_BROW_OUTER = 55
RIGHT_BROW_INNER = 276
RIGHT_BROW_PEAK = 283
RIGHT_BROW_OUTER = 285

# 面部轮廓（用于面宽）
LEFT_TEMPLE = 234  # 左太阳穴
RIGHT_TEMPLE = 454  # 右太阳穴
CHIN = 152  # 下巴
FOREHEAD = 10  # 额头中点
NOSE_TIP = 1  # 鼻尖（鼻头最突出点）

# 耳朵附近
LEFT_EAR_APPROX = [172, 136, 150, 149]
RIGHT_EAR_APPROX = [377, 400, 379, 365]


# ═══════════════════════════════════════════════════════════
# 照片尺寸归一化基准
# ═══════════════════════════════════════════════════════════

# 渲染器默认值 (1024x1024 底图)
STANDARD_EYE_DIST = 350  # RIGHT_CX - LEFT_CX = 687 - 337
STANDARD_EYE_SIZE = 300  # 2 × EYE_W（1024 画布内外眼角距）
STANDARD_FACE_WIDTH = 400  # 标准面部宽度


# ═══════════════════════════════════════════════════════════
# 人类检测（MediaPipe Face Mesh）
# ═══════════════════════════════════════════════════════════

def detect_human_face_mediapipe(img: np.ndarray) -> dict[str, Any]:
    """用 MediaPipe Face Mesh 检测人脸，返回 468 个关键点的精确测量。

    Returns:
        {
            "face_rect": (x, y, w, h),        # 面部边界框
            "eyes": [(lx, ly), (rx, ry)],     # 左右眼中心
            "eye_distance": float,            # 眼距（像素）
            "avg_eye_size": float,            # 平均眼大小（限宽）
            "eye_aspect": float,              # 眼宽高比 (宽/高，>1 更圆)
            "eye_aspect_h_over_w": float,     # 合同口径：高/宽 (典型 0.25~0.35)
            "face_width": int,                # 面部宽度
            "left_eye_landmarks": [...],      # 左眼关键点
            "right_eye_landmarks": [...],     # 右眼关键点
            "left_brow_y": float,             # 左眉 Y 均值
            "right_brow_y": float,            # 右眉 Y 均值
            "confidence": float,              # 置信度 (landmark 密集度)
        }
    """
    if not _HAS_MP or _MP_LANDMARKER is None:
        return {"error": "MediaPipe 未安装或模型文件缺失，无法执行人脸检测"}

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]

    mp_img = MpImage(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    result = _MP_LANDMARKER.detect(mp_img)

    if not result or not result.face_landmarks:
        return {"error": "MediaPipe 未检测到人脸"}

    landmarks = result.face_landmarks[0]

    # 转换归一化坐标到像素
    def _px(idx: int) -> tuple[float, float]:
        lm = landmarks[idx]
        return lm.x * w, lm.y * h

    # ── 左右眼中心（取内外眼角中点） ──
    l_outer = _px(LEFT_EYE_OUTER)
    l_inner = _px(LEFT_EYE_INNER)
    r_outer = _px(RIGHT_EYE_OUTER)
    r_inner = _px(RIGHT_EYE_INNER)

    left_eye_cx = (l_outer[0] + l_inner[0]) / 2
    left_eye_cy = (l_outer[1] + l_inner[1]) / 2
    right_eye_cx = (r_outer[0] + r_inner[0]) / 2
    right_eye_cy = (r_outer[1] + r_inner[1]) / 2

    # ── 眼距 ──
    eye_dist = np.sqrt(
        (right_eye_cx - left_eye_cx) ** 2 + (right_eye_cy - left_eye_cy) ** 2
    )

    # ── 左眼宽高 ──
    l_top = _px(LEFT_EYE_TOP)
    l_bot = _px(LEFT_EYE_BOTTOM)
    left_eye_w = np.sqrt((l_inner[0] - l_outer[0]) ** 2 + (l_inner[1] - l_outer[1]) ** 2)
    left_eye_h = np.sqrt((l_top[0] - l_bot[0]) ** 2 + (l_top[1] - l_bot[1]) ** 2)

    # ── 右眼宽高 ──
    r_top = _px(RIGHT_EYE_TOP)
    r_bot = _px(RIGHT_EYE_BOTTOM)
    right_eye_w = np.sqrt((r_inner[0] - r_outer[0]) ** 2 + (r_inner[1] - r_outer[1]) ** 2)
    right_eye_h = np.sqrt((r_top[0] - r_bot[0]) ** 2 + (r_top[1] - r_bot[1]) ** 2)

    avg_eye_w = (left_eye_w + right_eye_w) / 2
    avg_eye_h = (left_eye_h + right_eye_h) / 2

    # ── 面部宽度 ──
    left_temple = _px(LEFT_TEMPLE)
    right_temple = _px(RIGHT_TEMPLE)
    face_w = right_temple[0] - left_temple[0]

    # ── 眼部宽高比（管线用 w/h；合同附录用 h/w）──
    aspect = avg_eye_w / max(avg_eye_h, 1)
    aspect_h_over_w = avg_eye_h / max(avg_eye_w, 1)

    # ── 眉毛位置 ──
    left_brow_ys = [_px(i)[1] for i in LEFT_BROW]
    right_brow_ys = [_px(i)[1] for i in RIGHT_BROW]

    # ── 虹膜中心（468/473）与半径（环点 469-472 / 474-477）──
    left_iris_cx, left_iris_cy = _px(LEFT_IRIS_CENTER)
    right_iris_cx, right_iris_cy = _px(RIGHT_IRIS_CENTER)

    # 虹膜中心相对眼角中点（眼中心）的偏移
    pupil_offset_lx = float(left_iris_cx - left_eye_cx)
    pupil_offset_ly = float(left_iris_cy - left_eye_cy)
    pupil_offset_rx = float(right_iris_cx - right_eye_cx)
    pupil_offset_ry = float(right_iris_cy - right_eye_cy)
    pupil_offset_l = float(np.hypot(pupil_offset_lx, pupil_offset_ly))
    pupil_offset_r = float(np.hypot(pupil_offset_rx, pupil_offset_ry))

    left_iris_r = float(np.mean([
        np.hypot(_px(i)[0] - left_iris_cx, _px(i)[1] - left_iris_cy)
        for i in LEFT_IRIS_RING
    ]))
    right_iris_r = float(np.mean([
        np.hypot(_px(i)[0] - right_iris_cx, _px(i)[1] - right_iris_cy)
        for i in RIGHT_IRIS_RING
    ]))
    avg_iris_radius = (left_iris_r + right_iris_r) * 0.5

    # ── 鼻尖（MediaPipe landmark 1）──
    nose_tip = _px(NOSE_TIP)

    # ── 面部边界框 ──
    all_x = [lm.x * w for lm in landmarks]
    all_y = [lm.y * h for lm in landmarks]
    fx, fy = min(all_x), min(all_y)
    fw = max(all_x) - fx
    fh = max(all_y) - fy

    return {
        "face_rect": (int(fx), int(fy), int(fw), int(fh)),
        "eyes": [
            (int(left_eye_cx), int(left_eye_cy)),
            (int(right_eye_cx), int(right_eye_cy)),
        ],
        "nose_tip": [round(float(nose_tip[0]), 2), round(float(nose_tip[1]), 2)],
        "eye_distance": float(eye_dist),
        "avg_eye_size": float(avg_eye_w),
        "avg_eye_height": float(avg_eye_h),
        "eye_aspect": float(aspect),
        "eye_aspect_h_over_w": float(aspect_h_over_w),
        "face_width": int(face_w),
        "pupil_offset_l": float(pupil_offset_l),
        "pupil_offset_r": float(pupil_offset_r),
        "pupil_offset_lx": pupil_offset_lx,
        "pupil_offset_ly": pupil_offset_ly,
        "pupil_offset_rx": pupil_offset_rx,
        "pupil_offset_ry": pupil_offset_ry,
        "left_iris_radius": left_iris_r,
        "right_iris_radius": right_iris_r,
        "avg_iris_radius": float(avg_iris_radius),
        "left_brow_y": float(np.mean(left_brow_ys)),
        "right_brow_y": float(np.mean(right_brow_ys)),
        # 眉线下沿（landmark 最大 Y = 靠近眼眶一侧，与底膜绿线对齐）
        "left_brow_y_lower": float(max(left_brow_ys)),
        "right_brow_y_lower": float(max(right_brow_ys)),
        "confidence": 0.95,
        "method": "mediapipe",
    }






# ═══════════════════════════════════════════════════════════
# 手动标定 → 模板调整参数
# ═══════════════════════════════════════════════════════════

def _clamp_template(v: float, lo: float = 0.5, hi: float = 1.5) -> float:
    return max(lo, min(hi, round(float(v), 2)))


def anchors_to_template_adjustments(
    anchors: dict[str, Any],
    img_width: int,
    img_height: int,
    species: str,
) -> dict[str, float]:
    """[DEPRECATED 2026-06] 从用户在照片上点击的锚点计算底膜模板参数。

    ╔══════════════════════════════════════════════════════════════╗
    ║  方向B：三点标定路径已于 2026-06 废弃。                     ║
    ║  真人管线改用 geometry_adapter._human_adjustments_strict() ║
    ║  (MediaPipe-only，无锚点歧义)。                            ║
    ║  此函数保留仅供历史参考，不再被任何调用点引用。             ║
    ╚══════════════════════════════════════════════════════════════╝

    必选锚点（照片像素坐标）::
        left_eye, right_eye, nose
    狗/猫可选::
        left_ear, right_ear — 能标就标；未标则耳朵参数由品种模板提供（不写入 adjustments）
    """
    import math

    def pt(key: str) -> tuple[float, float]:
        p = anchors.get(key)
        if not p or len(p) < 2:
            raise ValueError(f"缺少锚点: {key}")
        return float(p[0]), float(p[1])

    le = pt("left_eye")
    re = pt("right_eye")
    nose = pt("nose")

    eye_dist_px = math.hypot(re[0] - le[0], re[1] - le[1])
    if eye_dist_px < 5:
        raise ValueError("左右眼距离过小，请重新标点")

    mid_y = (le[1] + re[1]) / 2
    eye_nose_dy = nose[1] - mid_y

    # 用原图宽度归一化（避免高分辨率照片算出恒定 0.5）
    xs = [le[0], re[0], nose[0]]
    ys = [le[1], re[1], nose[1]]
    for k in ("left_ear", "right_ear"):
        if anchors.get(k):
            xs.append(float(anchors[k][0]))
            ys.append(float(anchors[k][1]))
    est_w = max(max(xs) - min(xs), 1.0) * 1.25
    est_h = max(max(ys) - min(ys), 1.0) * 1.35
    # 以面部宽度为归一化基准（避免高分辨率照片用全宽导致比例过小）
    # 原代码用 max(img_width, est_w) 总是选照片全宽（如 5600px），
    # 导致眼距/眼大小被低估到 0.73。改用 est_w 确保反映真实面部比例。
    _face_w = max(est_w, 100.0)   # 安全下限 100px
    _face_h = max(est_h, 100.0)
    ref_w = max(int(_face_w), 1)
    ref_h = max(int(_face_h), 1)

    # 正面照：眼距约占画面宽度 12%～22%，1.0 = 标准模板
    eye_dist_ratio = eye_dist_px / ref_w
    std_eye_dist_ratio = 0.16
    eye_distance_factor = eye_dist_ratio / std_eye_dist_ratio

    # 单眼宽度约为眼距的 20%～30%
    est_eye_w_px = eye_dist_px * 0.24
    eye_size_factor = (est_eye_w_px / ref_w) / 0.038

    adjustments: dict[str, float] = {
        "eye_distance": _clamp_template(eye_distance_factor),
        "eye_size": _clamp_template(eye_size_factor),
    }

    if eye_nose_dy > 0:
        ratio = eye_nose_dy / max(eye_dist_px, 1)
        adjustments["eye_vertical"] = _clamp_template(ratio / 0.62, 0.7, 1.35)


    return adjustments


# ═══════════════════════════════════════════════════════════
# 检测结果 → 模板调整参数
# ═══════════════════════════════════════════════════════════

def detection_to_template_adjustments(
    detection: dict[str, Any],
    species: str = "human",
    img: np.ndarray | None = None,
) -> dict[str, float]:
    """将检测结果映射为 SpeciesTemplate 调整参数（仅人类）。

    原理：
        以标准底膜为基准值，将照片检测到的眼距/眼大小等
        映射为比例因子（1.0 = 标准）。

    Args:
        detection: detect_human_face_mediapipe() 的返回结果
        species: 保留参数，仅支持 "human"
        img: 保留参数，不再使用
    """
    if "error" in detection:
        return {"error": detection["error"]}  # type: ignore

    detected_dist = detection["eye_distance"]
    detected_size = detection["avg_eye_size"]
    face_w = detection.get("face_width", STANDARD_FACE_WIDTH) or STANDARD_FACE_WIDTH

    # 归一化因子（抵消照片分辨率/拍摄距离的差异）
    scale_norm = STANDARD_FACE_WIDTH / max(face_w, 1)

    eye_distance_factor = (detected_dist * scale_norm) / STANDARD_EYE_DIST
    eye_size_factor = (detected_size * scale_norm) / STANDARD_EYE_SIZE

    adjustments: dict[str, float] = {
        "eye_distance": max(0.6, min(1.4, round(eye_distance_factor, 2))),
        "eye_size": max(0.6, min(1.4, round(eye_size_factor, 2))),
    }

    # 眼部宽高比（MediaPipe 专有）
    if "eye_aspect" in detection:
        aspect = detection["eye_aspect"]
        # 标准眼宽高比 ~2.0（杏仁形），大于 2.0 = 更圆
        adjustments["eye_aspect"] = max(0.7, min(1.3, round(aspect / 2.0, 2)))

    # ── 瞳孔大小（从虹膜半径 + 瞳孔偏移推算）──
    if "avg_iris_radius" in detection and "avg_eye_size" in detection:
        iris_r = float(detection["avg_iris_radius"])
        eye_w = float(detection["avg_eye_size"])
        if iris_r > 1 and eye_w > 2:
            # pupil_offset 之和估算瞳孔直径
            pupil_d = (
                abs(float(detection.get("pupil_offset_lx", 0)))
                + abs(float(detection.get("pupil_offset_ly", 0)))
                + abs(float(detection.get("pupil_offset_rx", 0)))
                + abs(float(detection.get("pupil_offset_ry", 0)))
            ) / 2.0
            if pupil_d <= 1.0:
                # 无 pupil_offset 时用 iris_r × 0.5 估算
                pupil_d = iris_r * 0.5
            pupil_ratio = pupil_d / eye_w
            STANDARD_PUPIL_RATIO = 16.0 / 150.0  # PUPIL_R_BASE=16 / EYE_W=150
            adjustments["pupil_size"] = max(
                0.4, min(2.0, round(pupil_ratio / STANDARD_PUPIL_RATIO, 2))
            )

    return adjustments


# ═══════════════════════════════════════════════════════════
# 单张照片检测（自动选择检测策略）
# ═══════════════════════════════════════════════════════════

def detect_from_photo(
    photo_path: str | Path,
    species: str = "human",
) -> dict[str, Any]:
    """从单张照片检测人脸（仅人类，MediaPipe）。

    Args:
        photo_path: 照片文件路径
        species: 保留参数，仅支持 "human"

    Returns:
        detection dict（含 "error" 表示失败）
    """
    if not _HAS_CV2:
        return {"error": "OpenCV 未安装"}

    img = cv2.imread(str(photo_path))
    if img is None:
        return {"error": f"无法读取照片: {photo_path}"}

    if not _HAS_MP or _MP_LANDMARKER is None:
        return {
            "error": (
                "MediaPipe 不可用：请安装 mediapipe 并确保 "
                "tools/mediapipe_models/face_landmarker.task 存在"
            ),
        }
    return detect_human_face_mediapipe(img)


def validate_three_points(
    anchors: dict[str, Any],
    img_width: int,
    img_height: int,
) -> dict[str, Any]:
    """[DEPRECATED 2026-06] 校验三点标定（左眼/右眼/鼻梁）的合理性。

    ╔══════════════════════════════════════════════════════════════╗
    ║  方向B：三点标定路径已于 2026-06 废弃，无调用者。          ║
    ╚══════════════════════════════════════════════════════════════╝

    检查项:
        1. 眼距最小阈值（≥ 图片宽度的 5%）
        2. 鼻尖在两眼下方（人类常规位置）
        3. 缩放因子在合理范围（0.5～2.0）

    Args:
        anchors: 锚点字典，含 left_eye / right_eye / nose
        img_width: 图片宽度（像素）
        img_height: 图片高度（像素）

    Returns:
        {
            "ok": True / False,
            "warnings": [str, ...],   # 非致命问题
            "errors": [str, ...],     # 致命问题（需重新标点）
            "eye_distance_px": float,
            "eye_distance_ratio": float,  # 眼距 / 图片宽度
            "nose_below_eyes": bool,
        }
    """
    import math

    result: dict[str, Any] = {
        "ok": True,
        "warnings": [],
        "errors": [],
        "eye_distance_px": 0.0,
        "eye_distance_ratio": 0.0,
        "nose_below_eyes": True,
    }

    def _get(key: str) -> tuple[float, float] | None:
        p = anchors.get(key)
        if not p or len(p) < 2:
            return None
        return float(p[0]), float(p[1])

    le = _get("left_eye")
    re = _get("right_eye")
    nose = _get("nose")

    # ── 必选锚点缺失 ──
    missing = []
    if le is None:
        missing.append("left_eye")
    if re is None:
        missing.append("right_eye")
    if nose is None:
        missing.append("nose")
    if missing:
        result["ok"] = False
        result["errors"].append(f"缺少必选锚点: {', '.join(missing)}")
        return result

    # ── 眼距检查 ──
    eye_dist = math.hypot(re[0] - le[0], re[1] - le[1])
    result["eye_distance_px"] = round(eye_dist, 1)

    ref_w = max(img_width, 1)
    eye_dist_ratio = eye_dist / ref_w
    result["eye_distance_ratio"] = round(eye_dist_ratio, 4)

    MIN_EYE_DIST_RATIO = 0.05  # 眼距至少占图片宽度 5%
    if eye_dist_ratio < MIN_EYE_DIST_RATIO:
        result["ok"] = False
        result["errors"].append(
            f"眼距过小 ({eye_dist_ratio:.2%} < {MIN_EYE_DIST_RATIO:.0%})，"
            "请确认左右眼标点是否正确"
        )
    elif eye_dist_ratio < 0.08:
        result["warnings"].append(
            f"眼距偏小 ({eye_dist_ratio:.2%})，可能为侧脸或儿童"
        )

    # ── 鼻尖位置检查 ──
    mid_eye_y = (le[1] + re[1]) / 2
    nose_below = nose[1] > mid_eye_y
    result["nose_below_eyes"] = nose_below

    if not nose_below:
        result["warnings"].append(
            "鼻尖在眼睛上方，请确认鼻梁标点是否正确"
        )

    # ── 鼻尖水平偏移检查（鼻尖不应偏离两眼中心太远）──
    mid_eye_x = (le[0] + re[0]) / 2
    nose_offset_ratio = abs(nose[0] - mid_eye_x) / max(eye_dist, 1)
    if nose_offset_ratio > 0.5:
        result["warnings"].append(
            f"鼻尖水平偏移较大 (偏移/眼距={nose_offset_ratio:.2f})，"
            "请确认鼻梁标点是否正确"
        )

    # ── 缩放因子预估 ──
    std_eye_dist_ratio = 0.16
    scale_factor = eye_dist_ratio / std_eye_dist_ratio
    if scale_factor < 0.5:
        result["warnings"].append(
            f"预估缩放因子过小 ({scale_factor:.2f})，可能影响渲染效果"
        )
    elif scale_factor > 2.0:
        result["warnings"].append(
            f"预估缩放因子过大 ({scale_factor:.2f})，可能影响渲染效果"
        )

    return result


# ═══════════════════════════════════════════════════════════
# 客户自动检测（全自动管线入口）
# ═══════════════════════════════════════════════════════════

def auto_detect_for_customer(
    customer_id: str,
    species: str | None = None,
) -> dict[str, Any]:
    """为客户自动检测底膜模板参数（全自动版，仅人类）。

    流程：查找照片 → MediaPipe 人脸检测 → 模板参数 → 自动保存

    Args:
        customer_id: 客户 ID（如 "C001"）
        species: 保留参数，仅支持 "human"

    Returns:
        {
            "ok": True / False,
            "photo": "photo_name.jpg",
            "species": "human",
            "detection": {...},
            "adjustments": {...},
            "saved_params": {...},
        }
    """
    from asset_lib import customer_ref_photos_dir
    from gaze_engine._shared.customer_db import update_template_params

    # ── 0. 查找照片 ──
    ref_dir = customer_ref_photos_dir(customer_id)
    if not ref_dir.is_dir():
        return {
            "ok": False,
            "error": f"客户 {customer_id} 参考素材目录不存在",
            "hint": f"请先上传照片到 {ref_dir}",
        }

    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    photos = sorted(
        p for p in ref_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS
    )
    if not photos:
        return {
            "ok": False,
            "error": f"客户 {customer_id} 参考素材目录为空",
            "hint": f"请先上传照片到 {ref_dir}",
        }

    photo_path = photos[0]

    # ── 1. 人脸检测 ──
    detection = detect_from_photo(photo_path, "human")
    if "error" in detection:
        return {
            "ok": False,
            "error": detection["error"],
            "photo": photo_path.name,
            "species": "human",
        }

    # ── 2. 计算模板调整参数 ──
    adjustments = detection_to_template_adjustments(detection, "human")

    # ── 3. 自动保存 ──
    saved = update_template_params(customer_id, adjustments)

    return {
        "ok": True,
        "photo": photo_path.name,
        "species": "human",
        "detection": {
            "eye_distance": detection.get("eye_distance", 0),
            "avg_eye_size": detection.get("avg_eye_size", 0),
            "eye_aspect": detection.get("eye_aspect", 0),
            "face_width": detection.get("face_width", 0),
            "confidence": detection.get("confidence", 0),
            "method": detection.get("method", "auto"),
        },
        "adjustments": adjustments,
        "saved_params": saved.get("params", {}) if saved else {},
    }


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="从客户照片自动检测底膜模板参数")
    ap.add_argument("--customer", help="客户 ID (如 C001)")
    ap.add_argument("--photo", help="照片路径（覆盖客户参考素材路径）")
    ap.add_argument("--species", default="human", choices=["human"])
    ap.add_argument("--save", action="store_true", help="将结果保存到客户资产库")
    ap.add_argument("--output", help="输出到 JSON 文件")
    args = ap.parse_args()

    if args.customer:
        # 全场自动模式
        result = auto_detect_for_customer(args.customer, args.species)
    elif args.photo:
        # 单张检测模式
        img = cv2.imread(args.photo)
        if img is None:
            print(f"[ERROR] 无法读取照片: {args.photo}", file=sys.stderr)
            return 1
        detection = detect_from_photo(args.photo, args.species)
        if "error" in detection:
            print(f"  ❌ 检测失败: {detection['error']}")
            adjustments = {"eye_distance": 1.0, "eye_size": 1.0}
        else:
            adjustments = detection_to_template_adjustments(detection, args.species, img=img)
        result = {
            "ok": "error" not in detection,
            "photo": args.photo,
            "detection": detection,
            "adjustments": adjustments,
        }
    else:
        print("[ERROR] 必须指定 --customer 或 --photo", file=sys.stderr)
        return 1

    print(f"  📸 照片: {result.get('photo', 'N/A')}")

    if not result.get("ok"):
        print(f"  ❌ 检测失败: {result.get('error', '未知错误')}")
        if "hint" in result:
            print(f"    提示: {result['hint']}")
        return 1

    det = result.get("detection", {})
    print(f"  ✅ 检测成功")
    print(f"     眼距: {det.get('eye_distance', 0):.1f}px")
    print(f"     眼睛大小: {det.get('avg_eye_size', 0):.1f}px")
    print(f"     面部宽度: {det.get('face_width', 0)}px")
    print(f"     方法: {det.get('method', 'N/A')}")

    adj = result.get("adjustments", {})
    print(f"  📐 模板调整参数:")
    for k, v in adj.items():
        print(f"     {k} = {v}")

    if args.save and args.customer and result.get("ok"):
        print(f"  💾 已保存到客户 {args.customer}")

    if args.output:
        out_path = Path(args.output)
        import json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  📄 输出已保存到: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())