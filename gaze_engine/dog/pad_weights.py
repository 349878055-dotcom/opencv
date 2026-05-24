"""
狗 PAD 投影权重表 — 物种映射层

与人类的差异：
  - 去掉 eyebrow 独立的眉毛控制 → 改为眉脊整体（狗眉运动幅度小于人）
  - 加入 ear_left / ear_right（狗耳也是核心情绪器官）
  - 整体 PAD 权重与人类差异小于猫（狗的面部解剖更接近人类）
"""
from __future__ import annotations

from typing import Dict, Tuple

# 狗版 13 通道
CANONICAL_KEYS_DOG = [
    "pupil_x", "pupil_y", "blink",
    "ear_left", "ear_right",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# final_scale = Wp*P + Wa*A + Wd*D
DOG_PAD_WEIGHTS: Dict[str, Tuple[float, float, float]] = {
    "pupil_x":      (0.0,  0.50,  0.40),  # 同人类
    "pupil_y":      (0.0,  0.50,  0.40),
    "blink":        (0.0,  0.30,  0.10),
    # ── 狗耳取代人类 eyebrow 的部分生态位 ──
    "ear_left":     (0.05, 0.30,  0.20),  # 狗耳权重略低于猫（狗还靠尾巴）
    "ear_right":    (0.05, 0.30,  0.20),
    "pupil_scale":  (0.10, 0.30,  0.20),  # 同人类（狗瞳孔反应不如猫明显）
    "iris_scale":   (0.10, 0.20,  0.10),
    "cornea_bulge": (0.0,  0.40,  0.30),
    "squint":       (0.10, 0.35,  0.20),  # 同人类（狗眯眼不如猫强烈）
    "brow_raise":   (0.10, 0.20, -0.20),  # 保留（狗有眉毛肌，幅度好于猫）
    "lid_upper":    (0.0,  0.50,  0.40),
    "lid_lower":    (0.0,  0.30,  0.20),
    "eye_gloss":    (0.30, 0.10,  0.0),
}

DOG_BASE_SCALE: Dict[str, float] = {k: 0.30 for k in CANONICAL_KEYS_DOG}