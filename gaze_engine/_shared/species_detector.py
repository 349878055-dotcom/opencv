#!/usr/bin/env python3
"""
species_detector.py · 从客户照片自动检测底膜模板参数

检测策略:

  人类 → MediaPipe Face Mesh (468 个面部 3D 关键点)
         精确定位眼角、瞳孔、眉峰、面部轮廓

  猫/狗 → OpenCV Haar Cascade (面部区域检测 + 眼睛检测)
          MediaPipe 不支持宠物，用传统方法兜底

用法::

    from gaze_engine._shared.species_detector import (
        detect_human_face_mediapipe,
        detect_cat_dog_face,
        detection_to_template_adjustments,
        auto_detect_for_customer,
    )

    # 自动检测并保存
    result = auto_detect_for_customer("C001")
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
try:
    import mediapipe as mp

    _mp_face_mesh = mp.solutions.face_mesh
    _mp_drawing = mp.solutions.drawing_utils
    _HAS_MP = True
except ImportError:
    pass

# ── OpenCV（猫狗兜底，也用于 MediaPipe 加载图片）──
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
LEFT_IRIS = [468, 469, 470, 471]  # 瞳孔周围点

# 右眼
RIGHT_EYE_OUTER = 362
RIGHT_EYE_INNER = 263
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_IRIS = [472, 473, 474, 475]

# 眉毛
LEFT_BROW = [46, 53, 52, 65, 55, 70]  # 内→外
RIGHT_BROW = [276, 283, 282, 295, 285, 300]

# 面部轮廓（用于面宽）
LEFT_TEMPLE = 234  # 左太阳穴
RIGHT_TEMPLE = 454  # 右太阳穴
CHIN = 152  # 下巴
FOREHEAD = 10  # 额头中点

# 耳朵附近（猫狗耳朵关键点不存在，这里仅做人脸近似）
LEFT_EAR_APPROX = [172, 136, 150, 149]
RIGHT_EAR_APPROX = [377, 400, 379, 365]


# ═══════════════════════════════════════════════════════════
# 照片尺寸归一化基准
# ═══════════════════════════════════════════════════════════

# 渲染器默认值 (1024x1024 底图)
STANDARD_EYE_DIST = 350  # RIGHT_CX - LEFT_CX = 687 - 337
STANDARD_EYE_SIZE = 64  # 平均眼宽（像素）
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
            "eye_aspect": float,              # 眼宽高比 (宽/高)
            "face_width": int,                # 面部宽度
            "left_eye_landmarks": [...],      # 左眼关键点
            "right_eye_landmarks": [...],     # 右眼关键点
            "left_brow_y": float,             # 左眉 Y 均值
            "right_brow_y": float,            # 右眉 Y 均值
            "confidence": float,              # 置信度 (landmark 密集度)
        }
    """
    if not _HAS_MP:
        return {"error": "MediaPipe 未安装，无法执行人脸检测"}

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]

    with _mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,  # 启用瞳孔关键点
        min_detection_confidence=0.5,
    ) as face_mesh:
        results = face_mesh.process(img_rgb)

    if not results or not results.multi_face_landmarks:
        return {"error": "MediaPipe 未检测到人脸"}

    landmarks = results.multi_face_landmarks[0].landmark

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

    # ── 眼部宽高比（>1 = 更圆眼）──
    aspect = avg_eye_w / max(avg_eye_h, 1)

    # ── 眉毛位置 ──
    left_brow_ys = [_px(i)[1] for i in LEFT_BROW]
    right_brow_ys = [_px(i)[1] for i in RIGHT_BROW]

    # ── 瞳孔位置 ──
    left_iris_cx = np.mean([_px(i)[0] for i in LEFT_IRIS])
    left_iris_cy = np.mean([_px(i)[1] for i in LEFT_IRIS])
    right_iris_cx = np.mean([_px(i)[0] for i in RIGHT_IRIS])
    right_iris_cy = np.mean([_px(i)[1] for i in RIGHT_IRIS])

    # 瞳孔偏移量（相对于眼中心）
    pupil_offset_l = np.sqrt(
        (left_iris_cx - left_eye_cx) ** 2 + (left_iris_cy - left_eye_cy) ** 2
    )
    pupil_offset_r = np.sqrt(
        (right_iris_cx - right_eye_cx) ** 2 + (right_iris_cy - right_eye_cy) ** 2
    )

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
        "eye_distance": float(eye_dist),
        "avg_eye_size": float(avg_eye_w),
        "avg_eye_height": float(avg_eye_h),
        "eye_aspect": float(aspect),
        "face_width": int(face_w),
        "pupil_offset_l": float(pupil_offset_l),
        "pupil_offset_r": float(pupil_offset_r),
        "left_brow_y": float(np.mean(left_brow_ys)),
        "right_brow_y": float(np.mean(right_brow_ys)),
        "confidence": 0.95,
        "method": "mediapipe",
    }


# ═══════════════════════════════════════════════════════════
# 猫狗检测（OpenCV Haar Cascade，兜底方案）
# ═══════════════════════════════════════════════════════════

def _load_haar() -> tuple[Any, Any, Any | None]:
    """加载 OpenCV Haar cascade 分类器。"""
    cv2_data = cv2.data.haarcascades
    face_cascade = cv2.CascadeClassifier(cv2_data + "haarcascade_frontalface_default.xml")
    eye_cascade = cv2.CascadeClassifier(cv2_data + "haarcascade_eye.xml")
    try:
        cat_cascade = cv2.CascadeClassifier(cv2_data + "haarcascade_frontalcatface_extended.xml")
    except Exception:
        cat_cascade = None
    return face_cascade, eye_cascade, cat_cascade


def detect_cat_dog_face(img: np.ndarray) -> dict[str, Any]:
    """用 OpenCV Haar Cascade 检测猫/狗面部。

    Returns:
        {
            "face_rect": (x, y, w, h),
            "eyes": [(cx, cy), ...],
            "eye_distance": float,
            "avg_eye_size": float,
            "face_width": int,
            "confidence": float,
        }
    """
    if not _HAS_CV2:
        return {"error": "OpenCV 未安装，无法执行猫狗面部检测"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade, eye_cascade, cat_cascade = _load_haar()

    # 猫面部检测（如果有专用分类器）
    if cat_cascade is not None:
        faces = cat_cascade.detectMultiScale(gray, 1.05, 3)
        if len(faces) == 0:
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    else:
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return {"error": "未检测到猫/狗面部"}

    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray[y : y + h, x : x + w]

    eyes = eye_cascade.detectMultiScale(face_roi, 1.1, 3)

    if len(eyes) < 2:
        # 眼睛检测不到，根据面部比例估算
        eye_y = y + int(h * 0.35)
        left_eye_x = x + int(w * 0.25)
        right_eye_x = x + int(w * 0.75)
        eye_size = int(w * 0.08)
        return {
            "face_rect": (int(x), int(y), int(w), int(h)),
            "eyes": [(left_eye_x, eye_y), (right_eye_x, eye_y)],
            "eye_distance": float(right_eye_x - left_eye_x),
            "avg_eye_size": float(eye_size),
            "face_width": int(w),
            "confidence": 0.5,
            "note": "眼睛检测失败，使用面部比例估算",
        }

    eyes_sorted = sorted(eyes, key=lambda e: e[2] * e[3], reverse=True)[:2]
    eyes_sorted.sort(key=lambda e: e[0])

    eye_centers = []
    for (ex, ey, ew, eh) in eyes_sorted:
        cx = x + ex + ew // 2
        cy = y + ey + eh // 2
        eye_centers.append((cx, cy))

    left_eye, right_eye = eye_centers[0], eye_centers[1]
    eye_dist = np.sqrt(
        (right_eye[0] - left_eye[0]) ** 2 + (right_eye[1] - left_eye[1]) ** 2
    )
    eye_sizes = [e[2] for e in eyes_sorted]
    avg_eye_size = np.mean(eye_sizes)

    return {
        "face_rect": (int(x), int(y), int(w), int(h)),
        "eyes": [(int(cx), int(cy)) for cx, cy in eye_centers],
        "eye_distance": float(eye_dist),
        "avg_eye_size": float(avg_eye_size),
        "face_width": int(w),
        "confidence": float(len(faces)),
    }


# ═══════════════════════════════════════════════════════════
# 物种 + 品种自动推断（YOLOv8）
# ═══════════════════════════════════════════════════════════

_HAS_YOLO = False
_yolo_model: Any = None

def _get_yolo_model():
    """延迟加载 YOLOv8 分类模型。"""
    global _HAS_YOLO, _yolo_model
    if not _HAS_YOLO and _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO("yolov8n-cls.pt")  # ~6MB 分类模型
            _HAS_YOLO = True
        except Exception:
            _HAS_YOLO = False
    return _yolo_model if _HAS_YOLO else None


def _infer_species_and_breed(
    img: np.ndarray,
    known_species: str | None = None,
) -> dict[str, Any]:
    """从照片自动推断物种和品种。

    Args:
        img: BGR 原图
        known_species: 已知物种（可选），传入则跳过物种分类

    Returns:
        {
            "species": "cat" / "dog" / "human",
            "breed_id": "poodle_giant" / "",
            "confidence": 0.85,
            "needs_confirmation": False,
            "method": "yolov8" / "haar_cascade" / "fallback_default",
        }
    """
    yolo = _get_yolo_model()

    # ── L0: 用 YOLOv8 做物种 + 品种推断 ──
    if yolo is not None:
        try:
            results = yolo(img, verbose=False)
            probs = results[0].probs
            if probs is not None:
                top1 = probs.top1
                conf = probs.top1conf.item()

                # ImageNet 物种判定
                if 151 <= top1 <= 268:           # 狗品种 (ImageNet 151~268)
                    species = "dog"
                    breed_result = _infer_dog_breed_yolo(yolo, img, probs)
                    return {
                        "species": species,
                        "breed_id": breed_result["breed_id"],
                        "confidence": round(float(conf), 3),
                        "needs_confirmation": conf < 0.6,
                        "method": "yolov8",
                    }
                elif 281 <= top1 <= 286:         # 猫品种 (ImageNet 281~286)
                    species = "cat"
                    breed_result = _infer_cat_breed_yolo(yolo, img, probs)
                    return {
                        "species": species,
                        "breed_id": breed_result["breed_id"],
                        "confidence": round(float(conf), 3),
                        "needs_confirmation": conf < 0.6,
                        "method": "yolov8",
                    }
                elif top1 in (0, 1, 2, 3, 4, 5):  # 人物类
                    return {
                        "species": "human",
                        "breed_id": "",
                        "confidence": round(float(conf), 3),
                        "needs_confirmation": False,
                        "method": "yolov8",
                    }
        except Exception:
            pass

    # ── L1: Haar Cascade 降级物种检测（仅区分人脸 vs 猫狗）──
    if _HAS_CV2:
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            cat_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalcatface_extended.xml")

            cat_faces = cat_cascade.detectMultiScale(gray, 1.05, 3)
            if len(cat_faces) > 0:
                from gaze_engine.cat.breeds import list_cat_breeds
                cats = list_cat_breeds()
                return {
                    "species": "cat",
                    "breed_id": cats[0] if cats else "stray_cat",
                    "confidence": 0.5,
                    "needs_confirmation": True,
                    "method": "haar_cascade",
                }

            human_faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            if len(human_faces) > 0:
                return {
                    "species": "human",
                    "breed_id": "",
                    "confidence": 0.6,
                    "needs_confirmation": False,
                    "method": "haar_cascade",
                }
        except Exception:
            pass

    # ── L2: 全失败，用已知物种兜底 ──
    if known_species:
        return {
            "species": known_species,
            "breed_id": "",
            "confidence": 0.0,
            "needs_confirmation": True,
            "method": "fallback_known",
        }

    return {
        "species": "human",
        "breed_id": "",
        "confidence": 0.0,
        "needs_confirmation": True,
        "method": "fallback_default",
    }


def _infer_dog_breed_yolo(yolo: Any, img: np.ndarray, probs: Any) -> dict[str, Any]:
    """用 YOLOv8 从推理结果推断狗品种。"""
    from gaze_engine.dog.detect import infer_dog_breed
    return infer_dog_breed(img, yolo_model=yolo)


def _infer_cat_breed_yolo(yolo: Any, img: np.ndarray, probs: Any) -> dict[str, Any]:
    """用 YOLOv8 从推理结果推断猫品种。"""
    from gaze_engine.cat.detect import infer_cat_breed
    return infer_cat_breed(img, yolo_model=yolo)


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
    """从用户在照片上点击的锚点计算底膜模板参数。

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
    ref_w = max(int(img_width or 0), int(est_w), 1)
    ref_h = max(int(img_height or 0), int(est_h), 1)

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

    if species == "dog":
        le_ear = anchors.get("left_ear")
        re_ear = anchors.get("right_ear")
        if le_ear and re_ear and len(le_ear) >= 2 and len(re_ear) >= 2:
            avg_ear_y = (float(le_ear[1]) + float(re_ear[1])) / 2
            droop_raw = (avg_ear_y - mid_y) / max(eye_dist_px, 1)
            adjustments["ear_droop"] = max(0.0, min(1.0, round((droop_raw - 0.15) / 1.0, 2)))
    elif species == "cat":
        adjustments["pupil_slit_ratio"] = 1.5
        le_ear = anchors.get("left_ear")
        re_ear = anchors.get("right_ear")
        if le_ear and re_ear and len(le_ear) >= 2 and len(re_ear) >= 2:
            avg_ear_y = (float(le_ear[1]) + float(re_ear[1])) / 2
            lift = (mid_y - avg_ear_y) / max(eye_dist_px, 1)
            adjustments["ear_angle"] = max(0.0, min(1.0, round(0.5 + lift * 0.4, 2)))

    return adjustments


# ═══════════════════════════════════════════════════════════
# 检测结果 → 模板调整参数
# ═══════════════════════════════════════════════════════════

def detection_to_template_adjustments(
    detection: dict[str, Any],
    species: str,
    img: np.ndarray | None = None,
) -> dict[str, float]:
    """将检测结果映射为 SpeciesTemplate 调整参数。

    原理：
        以标准底膜为基准值，将照片检测到的眼距/眼大小等
        映射为比例因子（1.0 = 标准）。

    Args:
        detection: detect_from_photo() 的返回结果
        species: "human" / "cat" / "dog"
        img: 原始图片（可选），传入则启用耳部启发式检测
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

    # ── 猫: 竖瞳孔 + 耳角度检测（置信度门控，委托 cat/detect.py）──
    if species == "cat":
        adjustments["pupil_slit_ratio"] = 1.5

        face_rect = detection.get("face_rect")
        confidence = detection.get("confidence", 0.0)
        ear_estimated: dict[str, float] = {}
        if img is not None and face_rect and confidence >= 0.5:
            try:
                from gaze_engine.cat.detect import estimate_cat_ear
                ear_estimated = estimate_cat_ear(img, face_rect)
            except Exception:
                ear_estimated = {}
        if ear_estimated:
            adjustments.update(ear_estimated)
        # else: L1 Fallback → 不写入，让品种偏移生效

    # ── 狗: 耳下垂度检测（置信度门控，委托 dog/detect.py）──
    if species == "dog":
        face_rect = detection.get("face_rect")
        confidence = detection.get("confidence", 0.0)
        ear_estimated = {}
        if img is not None and face_rect and confidence >= 0.5:
            try:
                from gaze_engine.dog.detect import estimate_dog_ear
                ear_estimated = estimate_dog_ear(img, face_rect)
            except Exception:
                ear_estimated = {}
        if ear_estimated:
            adjustments.update(ear_estimated)
        # else: L1 Fallback → 不写入，让品种偏移生效

    return adjustments


# ═══════════════════════════════════════════════════════════
# 单张照片检测（自动选择检测策略）
# ═══════════════════════════════════════════════════════════

def detect_from_photo(
    photo_path: str | Path,
    species: str,
) -> dict[str, Any]:
    """从单张照片检测面部，自动选择检测策略。

    Args:
        photo_path: 照片文件路径
        species: "human" / "cat" / "dog"

    Returns:
        detection dict（含 "error" 表示失败）
    """
    if not _HAS_CV2:
        return {"error": "OpenCV 未安装"}

    img = cv2.imread(str(photo_path))
    if img is None:
        return {"error": f"无法读取照片: {photo_path}"}

    if species == "human":
        if _HAS_MP:
            return detect_human_face_mediapipe(img)
        else:
            # 降级到 OpenCV Haar
            face_cascade, eye_cascade, _ = _load_haar()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            if len(faces) == 0:
                return {"error": "未检测到人脸"}
            (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
            eyes = eye_cascade.detectMultiScale(gray[y : y + h, x : x + w], 1.1, 3)
            if len(eyes) < 2:
                return {"error": f"检测到 {len(eyes)} 只眼睛"}
            eyes_sorted = sorted(eyes, key=lambda e: e[2] * e[3], reverse=True)[:2]
            eyes_sorted.sort(key=lambda e: e[0])
            eye_centers = []
            for (ex, ey, ew, eh) in eyes_sorted:
                cx = x + ex + ew // 2
                cy = y + ey + eh // 2
                eye_centers.append((cx, cy))
            left_eye, right_eye = eye_centers[0], eye_centers[1]
            eye_dist = np.sqrt(
                (right_eye[0] - left_eye[0]) ** 2 + (right_eye[1] - left_eye[1]) ** 2
            )
            eye_sizes = [e[2] for e in eyes_sorted]
            return {
                "face_rect": (int(x), int(y), int(w), int(h)),
                "eyes": [(int(cx), int(cy)) for cx, cy in eye_centers],
                "eye_distance": float(eye_dist),
                "avg_eye_size": float(np.mean(eye_sizes)),
                "face_width": int(w),
                "confidence": 0.7,
                "method": "opencv_haar",
            }
    else:
        return detect_cat_dog_face(img)


# ═══════════════════════════════════════════════════════════
# 客户自动检测（全自动管线入口）
# ═══════════════════════════════════════════════════════════

def auto_detect_for_customer(
    customer_id: str,
    species: str | None = None,
) -> dict[str, Any]:
    """为客户自动检测底膜模板参数（全自动版）。

    ## 自动检测流程

    L0: 从照片自动推断物种（猫/狗/人）+ 品种（YOLOv8 / Haar 降级）
        - 置信度高（≥0.6）→ 静默写入客户信息
        - 置信度低（<0.6）→ 标记 needs_confirmation，供 UI 提示
    L1: 面部检测（MediaPipe：人类 / OpenCV：猫狗）
    L2: 耳位启发式检测（仅猫狗，委托 cat/detect.py / dog/detect.py）
    L3: 全自动保存到客户资产库

    Args:
        customer_id: 客户 ID（如 "C001"）
        species: 物种覆盖（传入则跳过 L0 物种推断）

    Returns:
        {
            "ok": True / False,
            "photo": "photo_name.jpg",
            "species": "dog",                    # 推断的物种
            "breed_id": "poodle_giant",          # 推断的品种
            "needs_confirmation": False,         # 置信度过低需客户确认
            "detection": {...},
            "adjustments": {...},
            "saved_params": {...},
        }
    """
    from asset_lib import customer_ref_photos_dir
    from gaze_engine._shared.customer_db import (
        get_customer,
        get_customer_species_and_breed,
        update_customer,
        update_template_params,
    )

    # 品种存在性校验函数（确保识别的品种在 breed_matrix 中有定义）
    def _breed_exists(species: str, breed_id: str) -> bool:
        if not breed_id:
            return False
        try:
            if species == "cat":
                from gaze_engine.cat.breeds import get_cat_breed
                get_cat_breed(breed_id)
            elif species == "dog":
                from gaze_engine.dog.breeds import get_dog_breed
                get_dog_breed(breed_id)
            else:
                return False
            return True
        except (KeyError, ImportError):
            return False

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

    # ── 1. 加载原图（一次性，供后续所有检测复用）──
    if not _HAS_CV2:
        return {"ok": False, "error": "OpenCV 未安装"}
    img = cv2.imread(str(photo_path))
    if img is None:
        return {"ok": False, "error": f"无法读取照片: {photo_path}", "photo": photo_path.name}

    # ── 2. 自动推断物种 + 品种 ──
    species_infer: dict[str, Any] = {"species": species or "human", "breed_id": "", "needs_confirmation": False}
    if species is None:
        # 无人工指定 → 用 YOLOv8/Haar 自动推断
        known_species, known_breed = get_customer_species_and_breed(customer_id)
        species_infer = _infer_species_and_breed(img, known_species=known_species)
    else:
        species_infer["species"] = species

    detected_species = species_infer["species"]
    detected_breed = species_infer.get("breed_id", "")

    # ── 3. 如果推断出品种且存在于 breed_matrix，写回客户信息 ──
    if detected_breed and not species_infer.get("needs_confirmation", False):
        if _breed_exists(detected_species, detected_breed):
            update_customer(customer_id, preferred_species=detected_species, breed=detected_breed)

    # ── 4. 面部检测 ──
    detection = detect_from_photo(photo_path, detected_species)
    if "error" in detection:
        return {
            "ok": False,
            "error": detection["error"],
            "photo": photo_path.name,
            "species": detected_species,
            "breed_id": detected_breed,
            "needs_confirmation": species_infer.get("needs_confirmation", False),
        }

    # ── 5. 计算模板调整参数（含耳位检测）──
    adjustments = detection_to_template_adjustments(
        detection, detected_species,
        img=img if detected_species in ("cat", "dog") else None,
    )

    # ── 6. 自动保存 ──
    saved = update_template_params(customer_id, adjustments)

    return {
        "ok": True,
        "photo": photo_path.name,
        "species": detected_species,
        "breed_id": detected_breed,
        "needs_confirmation": species_infer.get("needs_confirmation", False),
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
    ap.add_argument("--species", default="human", choices=["human", "cat", "dog"])
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
            # 传递原图用于耳部启发式检测
            ear_img = img if args.species in ("cat", "dog") else None
            adjustments = detection_to_template_adjustments(detection, args.species, img=ear_img)
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