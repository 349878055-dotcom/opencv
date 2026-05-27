#!/usr/bin/env python3
"""
estimate_template_from_photo.py · 从客户照片估计底膜模板参数

用途:
  客户上传宠物/人脸照片后，用 OpenCV 检测面部关键点，
  自动估算底膜模板参数（眼距、眼大小、耳位等），
  保存到客户资产库。

用法:
  # 从客户参考素材目录检测(自动用第一张照片)
  python tools/03_工具脚本/estimate_template_from_photo.py --customer C001 --species dog

  # 指定照片路径
  python tools/03_工具脚本/estimate_template_from_photo.py --photo ./customer_photo.jpg --species cat

  # 强制更新并保存到客户库
  python tools/03_工具脚本/estimate_template_from_photo.py --customer C001 --save

依赖:
  opencv-python, numpy
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# ── 路径设置 ──
_PKG = Path(__file__).resolve().parent.parent.parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

try:
    import cv2
except ImportError:
    cv2 = None
    HAS_CV2 = False
else:
    HAS_CV2 = True


# ═══════════════════════════════════════════════════════════
# 人脸/宠物面部检测
# ═══════════════════════════════════════════════════════════

def _load_haar() -> tuple[Any, Any, Any | None]:
    """加载 OpenCV Haar cascade 分类器。

    Returns:
        (face_cascade, eye_cascade, pet_cascade_or_None)
    """
    cv2_data = cv2.data.haarcascades
    face_cascade = cv2.CascadeClassifier(cv2_data + "haarcascade_frontalface_default.xml")
    eye_cascade = cv2.CascadeClassifier(cv2_data + "haarcascade_eye.xml")
    # 猫狗没有标准的 Haar cascade, 尝试 secondary 分类器
    try:
        cat_cascade = cv2.CascadeClassifier(cv2_data + "haarcascade_frontalcatface_extended.xml")
    except Exception:
        cat_cascade = None
    return face_cascade, eye_cascade, cat_cascade


def detect_human_face(img: np.ndarray) -> dict[str, Any]:
    """检测人脸，返回面部和眼部的近似位置。

    Returns:
        { "face_rect": (x, y, w, h), "eyes": [(cx, cy), ...],
          "eye_distance": float, "face_width": int, "confidence": float }
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade, eye_cascade, _ = _load_haar()

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return {"error": "未检测到人脸"}

    # 取最大的人脸
    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray[y:y + h, x:x + w]

    eyes = eye_cascade.detectMultiScale(face_roi, 1.1, 3)
    if len(eyes) < 2:
        return {"error": f"检测到 {len(eyes)} 只眼睛，需要至少 2 只"}

    # 取最大的两只眼睛
    eyes_sorted = sorted(eyes, key=lambda e: e[2] * e[3], reverse=True)[:2]
    # 按 x 坐标排序: 左眼, 右眼
    eyes_sorted.sort(key=lambda e: e[0])

    eye_centers = []
    for (ex, ey, ew, eh) in eyes_sorted:
        cx = x + ex + ew // 2
        cy = y + ey + eh // 2
        eye_centers.append((cx, cy))

    left_eye, right_eye = eye_centers[0], eye_centers[1]
    eye_dist = np.sqrt((right_eye[0] - left_eye[0]) ** 2 +
                       (right_eye[1] - left_eye[1]) ** 2)

    # 估算眼睛大小（平均眼宽）
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


def detect_cat_dog_face(img: np.ndarray) -> dict[str, Any]:
    """检测猫/狗面部（使用猫面部 Haar cascade + 简单假设）。

    Returns:
        与 detect_human_face 相同的返回结构
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade, eye_cascade, cat_cascade = _load_haar()

    # 尝试猫面部检测
    if cat_cascade is not None:
        faces = cat_cascade.detectMultiScale(gray, 1.05, 3)
    else:
        faces = face_cascade.detectMultiScale(gray, 1.3, 3)

    if len(faces) == 0:
        return {"error": "未检测到猫/狗面部"}

    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray[y:y + h, x:x + w]

    eyes = eye_cascade.detectMultiScale(face_roi, 1.1, 3)

    if len(eyes) < 2:
        # 如果眼睛检测不到，根据面部比例估算
        # 猫狗眼睛通常在面部上半部分的 1/3 ~ 1/2 处
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
    eye_dist = np.sqrt((right_eye[0] - left_eye[0]) ** 2 +
                       (right_eye[1] - left_eye[1]) ** 2)
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
# 检测结果 → 模板参数
# ═══════════════════════════════════════════════════════════

def detection_to_template_adjustments(
    detection: dict[str, Any],
    species: str,
) -> dict[str, float]:
    """将 OpenCV 检测结果转换为 SpeciesTemplate 调整参数。

    原理：
      以标准底膜的基准眼距 ~350px (1024x1024 坐标) 为参考，
      将检测到的眼距/眼大小映射为比例因子。
    """
    if "error" in detection:
        return {"error": detection["error"]}  # type: ignore

    # 标准眼距 (1024x1024 底图 & renderer 默认值)
    STANDARD_EYE_DIST = 350  # RIGHT_CX - LEFT_CX = 687 - 337
    STANDARD_EYE_SIZE = 64   # ~ 平均眼宽

    detected_dist = detection["eye_distance"]
    detected_size = detection["avg_eye_size"]

    # 照片可能在不同分辨率下，用 face_width 做归一化
    face_w = detection.get("face_width", 400)
    NORM_FACE_WIDTH = 400  # 假设标准检测距离下面部 ~400px

    # 归一化因子
    scale_norm = NORM_FACE_WIDTH / max(face_w, 1)

    # 调整: eye_distance > 1.0 = 眼距比标准宽
    eye_distance_factor = (detected_dist * scale_norm) / STANDARD_EYE_DIST
    eye_size_factor = (detected_size * scale_norm) / STANDARD_EYE_SIZE

    adjustments: dict[str, float] = {
        "eye_distance": max(0.6, min(1.4, round(eye_distance_factor, 2))),
        "eye_size": max(0.6, min(1.4, round(eye_size_factor, 2))),
    }

    # 猫: 默认竖瞳孔比
    if species == "cat":
        adjustments["pupil_slit_ratio"] = 1.5
        adjustments["ear_angle"] = 0.5

    # 狗: 默认耳下垂度
    if species == "dog":
        adjustments["ear_droop"] = 0.6

    return adjustments


# ═══════════════════════════════════════════════════════════
# 保存到客户资产库
# ═══════════════════════════════════════════════════════════

def save_to_customer(
    customer_id: str,
    species: str,
    adjustments: dict[str, float],
) -> dict[str, Any]:
    """将检测到的模板调整保存到客户资产库。"""
    from gaze_engine._shared.customer_db import update_template_params
    result = update_template_params(customer_id, adjustments)
    return result or {}


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="从客户照片估计底膜模板参数"
    )
    ap.add_argument("--customer", help="客户 ID (如 C001)")
    ap.add_argument("--photo", help="照片路径（覆盖客户参考素材路径）")
    ap.add_argument("--species", default="human",
                    choices=["human", "cat", "dog"])
    ap.add_argument("--save", action="store_true",
                    help="将估算结果保存到客户资产库")
    ap.add_argument("--output", help="将估算结果输出到 JSON 文件")
    args = ap.parse_args()

    if not HAS_CV2:
        print("[ERROR] opencv-python 未安装", file=sys.stderr)
        return 1

    # ── 确定照片路径 ──
    photo_path: Path | None = None
    if args.photo:
        photo_path = Path(args.photo)
    elif args.customer:
        from asset_lib import customer_ref_photos_dir
        ref_dir = customer_ref_photos_dir(args.customer)
        if ref_dir.is_dir():
            photos = sorted(ref_dir.iterdir())
            if photos:
                photo_path = photos[0]
                print(f"  📸 使用参考素材: {photo_path.name}")
    else:
        print("[ERROR] 必须指定 --photo 或 --customer", file=sys.stderr)
        return 1

    if photo_path is None or not photo_path.is_file():
        print(f"[ERROR] 照片不存在: {photo_path}", file=sys.stderr)
        return 1

    # ── 读取照片 ──
    img = cv2.imread(str(photo_path))
    if img is None:
        print(f"[ERROR] 无法读取照片: {photo_path}", file=sys.stderr)
        return 1
    print(f"  📷 照片尺寸: {img.shape[1]}x{img.shape[0]}")

    # ── 检测 ──
    if args.species == "human":
        detection = detect_human_face(img)
    else:
        detection = detect_cat_dog_face(img)

    if "error" in detection:
        print(f"  ❌ 检测失败: {detection['error']}")
        # 出问题时仍然提供保守的默认值
        adjustments = {"eye_distance": 1.0, "eye_size": 1.0}
        print(f"  ⚠️  使用默认值: {adjustments}")
    else:
        adjustments = detection_to_template_adjustments(detection, args.species)
        print(f"  ✅ 检测成功")
        print(f"     面部区域: {detection.get('face_rect')}")
        print(f"     眼距: {detection.get('eye_distance', 0):.1f}px")
        print(f"     眼睛大小: {detection.get('avg_eye_size', 0):.1f}px")
        print(f"     置信度: {detection.get('confidence', 0):.1f}")

    print(f"  📐 模板调整参数:")
    for k, v in adjustments.items():
        print(f"     {k} = {v}")

    # ── 保存 ──
    if args.save and args.customer:
        if "error" not in detection:
            saved = save_to_customer(args.customer, args.species, adjustments)
            print(f"  💾 已保存到客户 {args.customer}")
            print(f"     schema: {saved.get('schema', 'N/A')}")
        else:
            print(f"  ⏭️  跳过保存（检测失败）")

    # ── 输出文件 ──
    if args.output:
        out = {
            "photo": str(photo_path),
            "species": args.species,
            "detection": detection if "error" not in detection else {},
            "adjustments": adjustments,
            "customer_id": args.customer or "",
        }
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  📄 输出已保存到: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())