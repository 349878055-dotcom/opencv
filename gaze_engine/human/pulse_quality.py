#!/usr/bin/env python3
"""
L3b 平庸检测 · 自动修正（合同/06_先验与质检/人_眼眉先验与平庸三检.md）

在 human_prior 之后、烘焙之前，对 Dense′ 检查并修正：
  Q01 能量不够 · Q02 保持段杂乱 · Q03 眉眼能量不纯
"""
from __future__ import annotations

from gaze_engine._shared.pulse_quality_core import (
    FRAME_COUNT_DEFAULT,
    HUMAN_QC_CONFIG,
    HOLD_T0,
    HOLD_T1,
    PulseQualityMetrics,
    PulseQualityReport,
    SACCADE_T0,
    SACCADE_T1,
    diagnose_dense as _diagnose_dense,
    fix_pulse_quality_core,
    measure_dense as _measure_dense,
    reference_targets,
)

__all__ = [
    "FRAME_COUNT_DEFAULT",
    "HOLD_T0",
    "HOLD_T1",
    "SACCADE_T0",
    "SACCADE_T1",
    "PulseQualityMetrics",
    "PulseQualityReport",
    "diagnose_dense",
    "fix_pulse_quality",
    "measure_dense",
    "reference_targets",
]


def measure_dense(channels, packet, *, frame_count: int = FRAME_COUNT_DEFAULT):
    return _measure_dense(channels, packet, HUMAN_QC_CONFIG, frame_count=frame_count)


def diagnose_dense(channels, packet, *, frame_count: int = FRAME_COUNT_DEFAULT):
    return _diagnose_dense(channels, packet, HUMAN_QC_CONFIG, frame_count=frame_count)


def fix_pulse_quality(
    channels,
    packet,
    sparse_draft=None,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    max_rounds: int = 3,
):
    _ = sparse_draft
    return fix_pulse_quality_core(
        channels,
        packet,
        HUMAN_QC_CONFIG,
        frame_count=frame_count,
        max_rounds=max_rounds,
        species_blink=False,
    )
