"""
狗平庸质检 · Q01-Q03 + blink 下限 + 通道解耦抽检

合同：合同/09_先验与质检/狗_先验与质检.md
"""
from __future__ import annotations

from gaze_engine._shared.pulse_quality_core import (
    DOG_QC_CONFIG,
    FRAME_COUNT_DEFAULT,
    PulseQualityMetrics,
    PulseQualityReport,
    fix_pulse_quality_core,
)
from gaze_engine._shared.slider_schema import SliderPacket

__all__ = [
    "DogPulseQualityReport",
    "PulseQualityMetrics",
    "PulseQualityReport",
    "fix_dog_pulse_quality",
]


class DogPulseQualityReport(PulseQualityReport):
    """狗 QC 报告（与 PulseQualityReport 同构，保留旧类名）。"""


def fix_dog_pulse_quality(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    max_rounds: int = 3,
) -> DogPulseQualityReport:
    """Q01-Q03 平庸三检 + blink 下限 + squint/pupil_scale 解耦抽检。"""
    out, rep = fix_pulse_quality_core(
        channels,
        packet,
        DOG_QC_CONFIG,
        frame_count=frame_count,
        max_rounds=max_rounds,
        species_blink=True,
    )
    channels.clear()
    channels.update(out)
    dog_rep = DogPulseQualityReport(
        enabled=rep.enabled,
        species=rep.species,
        fixes=rep.fixes,
        remaining=rep.remaining,
        metrics=rep.metrics,
    )
    return dog_rep
