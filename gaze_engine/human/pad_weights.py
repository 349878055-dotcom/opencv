"""
人类 PAD 投影权重表（原硬编码在 envelope_compile.py）
"""
from __future__ import annotations

from typing import Dict, Tuple

from gaze_engine._shared.channel_contract import CANONICAL_KEYS

# final_scale = Wp*P + Wa*A + Wd*D
# 每个通道三元组 (Wp, Wa, Wd)
HUMAN_PAD_WEIGHTS: Dict[str, Tuple[float, float, float]] = {
    "pupil_x":      (0.0,  0.50,  0.40),  # 高 A/D → 眼神向前聚焦（"迎"）
    "pupil_y":      (0.0,  0.50,  0.40),
    "blink":        (0.0,  0.30,  0.10),
    "eyebrow":      (0.0,  0.30, -0.35),  # D 负 → 负负得正 → 眉压下（"拒"）
    "pupil_scale":  (0.10, 0.30,  0.20),
    "iris_scale":   (0.10, 0.20,  0.10),
    "cornea_bulge": (0.0,  0.40,  0.30),
    "squint":       (0.10, 0.35,  0.20),
    "brow_raise":   (0.10, 0.20, -0.20),  # 低 D → 挑眉抬起
    "lid_upper":    (0.0,  0.50,  0.40),  # 高 A/D → 上眼睑紧张
    "lid_lower":    (0.0,  0.30,  0.20),
    "eye_gloss":    (0.30, 0.10,  0.0),   # 高 P → 湿润光泽
}

# 基础 scale（无 PAD 影响时的中性值）
HUMAN_BASE_SCALE: Dict[str, float] = {k: 0.30 for k in CANONICAL_KEYS}