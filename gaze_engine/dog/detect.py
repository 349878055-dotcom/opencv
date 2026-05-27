"""
dog/detect.py · 狗专用检测模块

提供自动检测：
  1. ear_droop — 从面部 ROI 中的边缘方向估算狗耳下垂度
  2. infer_breed — 从照片推断狗品种（返回 breed_id + 置信度）

用法::
    from gaze_engine.dog.detect import estimate_dog_ear, infer_dog_breed

    ear = estimate_dog_ear(img, face_rect)        # → {"ear_droop": 0.0~1.0}
    breed = infer_dog_breed(img)                   # → {"breed_id": "...", "confidence": 0.0~1.0}
"""
from __future__ import annotations

from typing import Any

import numpy as np

_HAS_CV2 = False
try:
    import cv2

    _HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore


# ═══════════════════════════════════════════════════════════
# 狗耳下垂度检测
# ═══════════════════════════════════════════════════════════

def estimate_dog_ear(
    img: np.ndarray,
    face_rect: tuple[int, int, int, int],
) -> dict[str, float]:
    """从面部 ROI 启发式估算狗耳下垂度。

    Args:
        img: BGR 原图
        face_rect: (x, y, w, h) 面部框

    Returns:
        {"ear_droop": float} — 0=全竖立, 1=全下垂；检测失败返回空 dict
    """
    if not _HAS_CV2:
        return {}

    x, y, w, h = face_rect
    if w < 20 or h < 20:
        return {}

    # 耳区：面部框上部 45%
    ear_top = y
    ear_bot = y + int(h * 0.45)
    if ear_bot - ear_top < 10:
        return {}

    left_ear = img[ear_top:ear_bot, x : x + int(w * 0.30)]
    right_ear = img[ear_top:ear_bot, x + int(w * 0.70) : x + w]

    def _score(roi: np.ndarray) -> float:
        """垂直边缘占比。高分→竖耳，低分→垂耳。"""
        if roi.size == 0 or roi.shape[0] < 3 or roi.shape[1] < 3:
            return 0.5
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mx, my = np.abs(gx), np.abs(gy)
        total = np.sum(mx) + np.sum(my) + 1e-8
        if total < 1.0:
            return 0.5
        return float(np.sum(my) / total)

    avg = (_score(left_ear) + _score(right_ear)) / 2.0
    # 翻转：垂直边多 → 竖耳 → droop 低
    droop = 1.0 - avg
    droop = max(0.0, min(1.0, round(droop, 2)))
    return {"ear_droop": droop}


# ═══════════════════════════════════════════════════════════
# 狗品种自动推断（YOLOv8 + 映射表）
# ═══════════════════════════════════════════════════════════

# ImageNet 常见狗品种 → 本系统 breed_id 映射
# ImageNet 狗品种 ID 范围 151~268
_DOG_IMAGENET_MAP: dict[int, str] = {
    # 贵宾/卷毛类
    265: "poodle_giant",   # standard poodle
    266: "poodle_giant",   # miniature poodle
    267: "poodle_giant",   # toy poodle

    # 牧羊犬类（可扩展）
    232: "shepherd_dog",   # German shepherd
    233: "shepherd_dog",   # Doberman
    234: "shepherd_dog",   # golden retriever → 可映射

    # 小型犬
    158: "small_dog",      # Chihuahua
    168: "small_dog",      # Maltese
    184: "small_dog",      # Shih Tzu
    156: "small_dog",      # Pomeranian
}

# 默认兜底品种
_DEFAULT_DOG_BREED = "poodle_giant"


def infer_dog_breed(
    img: np.ndarray,
    yolo_model: Any = None,
) -> dict[str, Any]:
    """从照片推断狗品种。

    Args:
        img: BGR 原图
        yolo_model: 已加载的 YOLO 模型实例（可选）

    Returns:
        {
            "breed_id": "poodle_giant",
            "confidence": 0.85,
            "method": "yolov8" / "fallback",
            "needs_confirmation": False,
        }
    """
    # ── L0: YOLOv8 推理 ──
    if yolo_model is not None:
        try:
            results = yolo_model(img, verbose=False)
            probs = results[0].probs
            if probs is not None:
                top5 = probs.top5
                confs = probs.top5conf.tolist()

                # 先匹配已知品种
                for cls_id, conf in zip(top5, confs):
                    if cls_id in _DOG_IMAGENET_MAP:
                        breed_id = _DOG_IMAGENET_MAP[cls_id]
                        needs = conf < 0.55
                        return {
                            "breed_id": breed_id,
                            "confidence": round(float(conf), 3),
                            "method": "yolov8",
                            "needs_confirmation": needs,
                        }

                # 检测到狗但未精确匹配 → 按置信度最高的狗品种
                from gaze_engine.dog.breeds import list_dog_breeds
                known = list_dog_breeds()
                if known:
                    # 用第一个已知品种兜底
                    return {
                        "breed_id": known[0],
                        "confidence": 0.4,
                        "method": "yolov8_topdog",
                        "needs_confirmation": True,
                    }

                return {
                    "breed_id": _DEFAULT_DOG_BREED,
                    "confidence": 0.3,
                    "method": "yolov8_unknown",
                    "needs_confirmation": True,
                }
        except Exception:
            pass

    # ── L1: 无 YOLOv8 → 返回默认 ──
    return {
        "breed_id": _DEFAULT_DOG_BREED,
        "confidence": 0.0,
        "method": "fallback_default",
        "needs_confirmation": True,
    }