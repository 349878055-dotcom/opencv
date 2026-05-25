"""
猫工程底膜渲染引擎 · CatEyeMesh
TODO: 按 pet_eye_engine_migration_plan.md 第三章填充 CatEyeMesh + 耳位渲染

通道映射（猫语境下，标准 12 通道的语义）：
  - eyebrow   → 左耳位（0=飞机耳耷拉, 1=竖耳警惕）
  - brow_raise → 右耳位 / 耳尖微颤（好奇/受惊时高频小幅度）

OpenCV 渲染时按以下分组处理：
  - R 通道 = 眼眶 (lid_upper, lid_lower, blink, squint)
  - G 通道 = 耳位线 (eyebrow, brow_raise)
  - B 通道 = 瞳孔 (pupil_x, pupil_y, pupil_scale, iris_scale)
"""
from __future__ import annotations

import numpy as np

from gaze_engine._shared.channel_contract import CANONICAL_KEYS


class CatAffineRenderer:
    """猫工程底膜渲染器（TODO）"""

    def render_frame(self, channels: dict[str, float]) -> np.ndarray:
        """
        输出 RGB 三色分离（R=眼眶, G=耳位+眉, B=瞳孔）
        尺寸 690×361，匹配 Wan 扩散引擎输入

        Args:
            channels: 严格包含 CANONICAL_KEYS 全部 12 个键的 dict
        """
        # TODO: 实现 CatEyeMesh 变形 + 竖椭圆瞳孔 + 耳位线
        raise NotImplementedError("CatAffineRenderer not yet implemented")