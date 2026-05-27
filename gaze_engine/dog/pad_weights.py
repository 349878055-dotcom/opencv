"""
狗 PAD 投影权重表 — 物种映射层（标准 12 通道版）

与人类的差异：
  - eyebrow → 狗耳位（0=全耷拉·垂耳, 1=全竖立·立耳）
  - brow_raise → 狗眉脊微动（狗有眉毛肌，保留活性）
  - 狗瞳孔反应不如猫明显，但比人敏感
"""
from __future__ import annotations

from typing import Dict, Tuple

from gaze_engine.dog.envelope_compile import DOG_CHANNELS

# final_scale = base + P×Wp + A×Wa + D×Wd
DOG_PAD_WEIGHTS: Dict[str, Tuple[float, float, float]] = {
    "pupil_x":      (0.0,  0.50,  0.40),
    "pupil_y":      (0.0,  0.50,  0.40),
    "blink":        (0.0,  0.30,  0.10),
    "eyebrow":      (0.05, 0.30,  0.20),
    "pupil_scale":  (0.10, 0.30,  0.20),
    "iris_scale":   (0.10, 0.20,  0.10),
    "cornea_bulge": (0.0,  0.40,  0.30),
    "squint":       (0.10, 0.35,  0.20),
    "brow_raise":   (0.10, 0.20, -0.20),
    "lid_upper":    (0.0,  0.50,  0.40),
    "lid_lower":    (0.0,  0.30,  0.20),
    "eye_gloss":    (0.30, 0.10,  0.0),
}

# 各通道独立 base，避免 e×s 全通道数值重合
DOG_BASE_SCALE: Dict[str, float] = {
    "pupil_x":      0.36,
    "pupil_y":      0.33,
    "blink":        0.48,
    "eyebrow":      0.28,
    "pupil_scale":  0.24,
    "iris_scale":   0.19,
    "cornea_bulge": 0.14,
    "squint":       0.31,
    "brow_raise":   0.22,
    "lid_upper":    0.37,
    "lid_lower":    0.25,
    "eye_gloss":    0.11,
}

assert set(DOG_BASE_SCALE.keys()) == set(DOG_CHANNELS)
