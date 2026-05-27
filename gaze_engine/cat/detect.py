"""
cat/detect.py · 猫专用检测模块

提供自动检测：
  1. ear_angle — 从面部 ROI 中的边缘方向估算猫耳角度
  2. infer_breed — 从照片推断猫品种（返回 breed_id + 置信度）

用法::
    from gaze_engine.cat.detect import estimate_cat_ear, infer_cat_breed

    ear = estimate_cat_ear(img, face_rect)        # → {"ear_angle": 0.0~1.0}
    breed = infer_cat_breed(img)                   # → {"breed_id": "...", "confidence": 0.0~1.0}
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
# 猫耳角度检测
# ═══════════════════════════════════════════════════════════

def estimate_cat_ear(
    img: np.ndarray,
    face_rect: tuple[int, int, int, int],
) -> dict[str, float]:
    """从面部 ROI 启发式估算猫耳角度。

    Args:
        img: BGR 原图
        face_rect: (x, y, w, h) 面部框

    Returns:
        {"ear_angle": float} — 0=飞机耳, 1=竖耳；检测失败返回空 dict
    """
    if not _HAS_CV2:
        return {}

    x, y, w, h = face_rect
    if w < 20 or h < 20:
        return {}

    # 耳区：面部框上部 45%，排除眼区
    ear_top = y
    ear_bot = y + int(h * 0.45)
    if ear_bot - ear_top < 10:
        return {}

    # 左右耳区（面部左右各 30%）
    left_ear = img[ear_top:ear_bot, x : x + int(w * 0.30)]
    right_ear = img[ear_top:ear_bot, x + int(w * 0.70) : x + w]

    def _score(roi: np.ndarray) -> float:
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
    angle = max(0.0, min(1.0, round(avg, 2)))
    return {"ear_angle": angle}


# ═══════════════════════════════════════════════════════════
# 猫品种自动推断（YOLOv8 + 映射表）
# ═══════════════════════════════════════════════════════════

# ImageNet 猫品种 class_id → 本系统 breed_id 映射表
# ImageNet 1000 分类中猫相关的类别
_CAT_IMAGENET_MAP: dict[int, str] = {
    281: "stray_cat",    # tabby cat → 田园猫
    282: "stray_cat",    # tiger cat → 田园猫
    283: "siamese_cat",  # Persian cat → 暹罗近似
    284: "siamese_cat",  # Siamese cat → 暹罗猫
    285: "british_cat",  # Egyptian cat → 英短近似
    286: "ragdoll_cat",  # cougar → 布偶近似
}

# 无 YOLOv8 时的兜底：凭 breed_matrix 风格特征匹配
_CAT_BREED_FALLBACKS = {
    "ragdoll_cat": {"keywords": ["布偶", "ragdoll", " blue eye", "colorpoint"]},
    "siamese_cat": {"keywords": ["暹罗", "siamese", "wedge", "blue eye"]},
    "british_cat": {"keywords": ["英短", "british shorthair", "round face", "orange eye"]},
    "stray_cat": {"keywords": []},  # 兜底
}

_DEFAULT_CAT_BREED = "stray_cat"


def infer_cat_breed(
    img: np.ndarray,
    yolo_model: Any = None,
) -> dict[str, Any]:
    """从照片推断猫品种。

    Args:
        img: BGR 原图
        yolo_model: 已加载的 YOLO 模型实例（可选），未传则用简单规则

    Returns:
        {
            "breed_id": "ragdoll_cat",
            "confidence": 0.85,
            "method": "yolov8" / "fallback",
            "needs_confirmation": False,    # True = 置信度低，需客户确认
        }
    """
    # ── L0: YOLOv8 推理 ──
    if yolo_model is not None:
        try:
            results = yolo_model(img, verbose=False)
            probs = results[0].probs
            if probs is not None:
                top5 = probs.top5  # 前 5 class_id
                confs = probs.top5conf.tolist()

                for cls_id, conf in zip(top5, confs):
                    if cls_id in _CAT_IMAGENET_MAP:
                        breed_id = _CAT_IMAGENET_MAP[cls_id]
                        needs = conf < 0.6
                        return {
                            "breed_id": breed_id,
                            "confidence": round(float(conf), 3),
                            "method": "yolov8",
                            "needs_confirmation": needs,
                        }

                # 检测到猫但未匹配到具体品种 → 用最高分猫品种
                raw_preds = [(c, probs.top5conf[i].item()) for i, c in enumerate(probs.top5)]
                cat_preds = [(cls_id, conf) for cls_id, conf in raw_preds if cls_id in _CAT_IMAGENET_MAP]
                if cat_preds:
                    cls_id, conf = max(cat_preds, key=lambda x: x[1])
                    return {
                        "breed_id": _CAT_IMAGENET_MAP.get(cls_id, _DEFAULT_CAT_BREED),
                        "confidence": round(float(conf), 3),
                        "method": "yolov8",
                        "needs_confirmation": conf < 0.6,
                    }
        except Exception:
            pass

    # ── L1: YOLOv8 不可用或失败 → 返回默认 ──
    return {
        "breed_id": _DEFAULT_CAT_BREED,
        "confidence": 0.0,
        "method": "fallback_default",
        "needs_confirmation": True,
    }