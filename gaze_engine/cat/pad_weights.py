"""
猫 PAD 投影权重表 — 物种映射层

与人类的差异：
  - 去掉 eyebrow（猫无独立眉毛肌）
  - 加入 ear_left / ear_right（猫耳是核心情绪器官，取代眉毛的生态位）
  - pupil_scale 的 P 权重更高（猫瞳孔反应更敏感）
  - squint 的 P 权重更高（猫眯眼是重要的情感信号）
"""
from __future__ import annotations

from typing import Dict, Tuple

# 猫版 13 通道
CANONICAL_KEYS_CAT = [
    "pupil_x", "pupil_y", "blink",
    "ear_left", "ear_right",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# final_scale = Wp*P + Wa*A + Wd*D
CAT_PAD_WEIGHTS: Dict[str, Tuple[float, float, float]] = {
    "pupil_x":      (0.0,  0.50,  0.40),  # 同人类：高 A/D → 聚焦
    "pupil_y":      (0.0,  0.50,  0.40),  # 同人类
    "blink":        (0.0,  0.30,  0.10),  # 同人类
    # ── 猫耳取代人类 eyebrow 的生态位 ──
    "ear_left":     (0.05, 0.35,  0.25),  # 耳朵朝向：P 正 → 放松前竖；D 正 → 专注前倾
    "ear_right":    (0.05, 0.35,  0.25),  # 双耳对称
    # ── 瞳孔缩放：猫比人类敏感 ──
    "pupil_scale":  (0.20, 0.40,  0.30),  # P 从 0.10→0.20（猫瞳孔是情绪晴雨表）
    "iris_scale":   (0.10, 0.20,  0.10),
    "cornea_bulge": (0.0,  0.40,  0.30),
    # ── 眯眼：猫的重要情感信号 ──
    "squint":       (0.15, 0.35,  0.20),  # P 从 0.10→0.15（猫眯眼表达信任/满足）
    "brow_raise":   (0.10, 0.20, -0.20),  # 保留（猫有额肌，但幅度小）
    "lid_upper":    (0.0,  0.50,  0.40),  # 同人类
    "lid_lower":    (0.0,  0.30,  0.20),
    "eye_gloss":    (0.30, 0.10,  0.0),
}

# 猫基础 scale（中性值 0.30，与人类一致）
CAT_BASE_SCALE: Dict[str, float] = {k: 0.30 for k in CANONICAL_KEYS_CAT}