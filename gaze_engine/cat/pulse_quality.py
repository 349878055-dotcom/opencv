"""
猫平庸质检 · Q01 能量 / Q02 保持 / Q03 耳眼耦合

合同：合同/09_先验与质检/猫_先验与质检.md
"""
from __future__ import annotations

from gaze_engine._shared.pulse_quality_core import (
    CAT_QC_CONFIG,
    FRAME_COUNT_DEFAULT,
    PulseQualityMetrics,
    PulseQualityReport,
    fix_pulse_quality_core,
)
from gaze_engine._shared.slider_schema import SliderPacket

__all__ = [
    "CatPulseQualityReport",
    "PulseQualityMetrics",
    "PulseQualityReport",
    "fix_cat_pulse_quality",
]


class CatPulseQualityReport(PulseQualityReport):
    """猫 QC 报告。"""


def fix_cat_pulse_quality(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    max_rounds: int = 3,
) -> CatPulseQualityReport:
    """Q01-Q03 + blink 下限 + 通道解耦抽检。"""
    out, rep = fix_pulse_quality_core(
        channels,
        packet,
        CAT_QC_CONFIG,
        frame_count=frame_count,
        max_rounds=max_rounds,
        species_blink=True,
    )
    channels.clear()
    channels.update(out)
    return CatPulseQualityReport(
        enabled=rep.enabled,
        species=rep.species,
        fixes=rep.fixes,
        remaining=rep.remaining,
        metrics=rep.metrics,
    )
