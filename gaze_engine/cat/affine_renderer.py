"""
猫工程底膜渲染引擎 · CatEyeMesh
TODO: 按 pet_eye_engine_migration_plan.md 第三章填充 CatEyeMesh + 耳位渲染
"""
from __future__ import annotations

import numpy as np

CANONICAL_KEYS_CAT = [
    "pupil_x", "pupil_y", "blink",
    "ear_left", "ear_right",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]


class CatAffineRenderer:
    """猫工程底膜渲染器（TODO）"""

    def render_frame(self, channels: dict[str, float]) -> np.ndarray:
        """
        输出 RGB 三色分离（R=眼眶, G=耳位+眉, B=瞳孔）
        尺寸 690×361，匹配 Wan 扩散引擎输入
        """
        # TODO: 实现 CatEyeMesh 变形 + 竖椭圆瞳孔 + 耳位线
        raise NotImplementedError("CatAffineRenderer not yet implemented")