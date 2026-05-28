"""
猫真人化先验 · 扫视动力学 + 第三眼睑 + 耳位耦合

合同：合同/09_先验与质检/猫_先验与质检.md
"""
from __future__ import annotations

from gaze_engine._shared.oculomotor_prior import (
    CAT_PRIOR_CONFIG,
    FRAME_COUNT_DEFAULT,
    PriorReport,
    apply_oculomotor_prior,
)
from gaze_engine._shared.slider_schema import SliderPacket


def apply_cat_prior(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    sparse_draft: dict | None = None,
) -> tuple[dict[str, list[float]], PriorReport]:
    """
    猫专用先验：
      - ζ/ω 更欠阻尼（过冲更大、更快）
      - 第三眼睑（内眦膜）短暂闭合
      - 瞳孔扫视时耳位（eyebrow/brow_raise）延迟耦合
    """
    sparse = dict(sparse_draft or {})
    sparse["_compile_mode"] = "envelope-v1"
    return apply_oculomotor_prior(
        channels, packet, CAT_PRIOR_CONFIG, sparse, frame_count=frame_count
    )
