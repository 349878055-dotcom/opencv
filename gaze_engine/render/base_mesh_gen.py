#!/usr/bin/env python3
"""
base_mesh_gen.py — 最终封装版

修改：
  1. 上下眼睑合并为一个封闭环 (isClosed=True)
  2. 删除黑色瞳孔，虹膜=纯蓝实心圆
  3. 所有线条厚度统一 8px
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

try:
    import cv2
except ImportError:
    raise

W, H = 1024, 1024

RED   = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE  = (255, 0, 0)
BLACK = (0, 0, 0)

LEFT_CX, LEFT_CY   = 337, 325
RIGHT_CX, RIGHT_CY = 687, 325

EYE_HALF_W = 150
UPPER_PEAK = 45
LOWER_BOT  = 45

IRIS_R = 22

BROW_OFFSET = 95
BROW_HALF_W = 130
BROW_PEAK_H = 20

THICK = 8  # 统一厚度


def _eye_ring(cx, cy, steps=40):
    """生成上下眼睑合并的闭合环"""
    pts = []
    # 上眼睑（从左到右）
    for i in range(steps + 1):
        t = i / steps
        x = int(cx - EYE_HALF_W + 2 * EYE_HALF_W * t)
        y_offset = UPPER_PEAK * (1 - (2*t - 1)**2)
        y = int(cy - y_offset)
        pts.append((x, y))
    # 下眼睑（从右到左，保证连续）
    for i in range(steps + 1):
        t = i / steps
        x = int(cx + EYE_HALF_W - 2 * EYE_HALF_W * t)
        y_offset = LOWER_BOT * (1 - (2*t - 1)**2) * 0.85
        y = int(cy + y_offset)
        pts.append((x, y))
    return np.array(pts, np.int32)


def generate() -> np.ndarray:
    img = np.full((H, W, 3), BLACK, dtype=np.uint8)

    for cx, cy, side in [(LEFT_CX, LEFT_CY, -1), (RIGHT_CX, RIGHT_CY, 1)]:
        # ── 1. 上下眼睑封闭环 ──
        ring = _eye_ring(cx, cy)
        cv2.polylines(img, [ring], True, RED, THICK, cv2.LINE_AA)

        # ── 2. 虹膜（纯蓝实心，无瞳孔） ──
        cv2.circle(img, (cx, cy), IRIS_R, BLUE, -1, cv2.LINE_AA)

        # ── 4. 眉毛 ──
        brow_cy = cy - BROW_OFFSET
        if side == -1:
            brow_pts = np.array([
                (cx - BROW_HALF_W, brow_cy + 8),
                (cx - 20, brow_cy - BROW_PEAK_H),
                (cx + BROW_HALF_W - 20, brow_cy + 5),
            ], np.int32)
        else:
            brow_pts = np.array([
                (cx + BROW_HALF_W, brow_cy + 8),
                (cx + 20, brow_cy - BROW_PEAK_H),
                (cx - BROW_HALF_W + 20, brow_cy + 5),
            ], np.int32)
        cv2.polylines(img, [brow_pts], False, GREEN, THICK, cv2.LINE_AA)

    return img


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "render" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "eyelid_raw.png"

    print("最终封装底模 ...")
    img = generate()
    cv2.imwrite(str(out_path), img)

    for name, color in [("红(眼睑)", RED), ("绿(眉毛)", GREEN), ("蓝(虹膜)", BLUE)]:
        mask = np.all(img == color, axis=2)
        print(f"  {name}: {mask.sum()}px")
    print(f"  纯黑背景: {np.all(img == BLACK, axis=2).sum()}px")
    print(f"已保存: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())