#!/usr/bin/env python3
"""人类眼眉先验 · 全量 12×150 后处理（合同/06_先验与质检/人_眼眉先验与平庸三检.md）。"""
from __future__ import annotations

import copy
from typing import Any

from gaze_engine.human.envelope_compile import HUMAN_CHANNELS
from gaze_engine._shared.micro_jitter import _phase_at_each_frame
from gaze_engine._shared.oculomotor_prior import (
    FPS_DEFAULT,
    FRAME_COUNT_DEFAULT,
    HOLD_T0,
    HOLD_T1,
    HUMAN_PRIOR_CONFIG,
    SACCADE_T0,
    SACCADE_T1,
    PriorReport,
    apply_oculomotor_prior,
)
from gaze_engine._shared.slider_schema import SliderPacket

BLINK_PRESERVE = frozenset({"blink"})

__all__ = [
    "BLINK_PRESERVE",
    "FRAME_COUNT_DEFAULT",
    "FPS_DEFAULT",
    "HOLD_T0",
    "HOLD_T1",
    "PriorReport",
    "SACCADE_T0",
    "SACCADE_T1",
    "apply_human_prior",
    "dense_to_baked_sparse",
]


def apply_human_prior(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    sparse_draft: dict | None = None,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    fps: int = FPS_DEFAULT,
) -> tuple[dict[str, list[float]], PriorReport]:
    """全量曲线真人化；返回新 channels 与验收报告。"""
    return apply_oculomotor_prior(
        channels,
        packet,
        HUMAN_PRIOR_CONFIG,
        sparse_draft,
        frame_count=frame_count,
        fps=fps,
    )


def dense_to_baked_sparse(
    sparse_draft: dict,
    channels: dict[str, list[float]],
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    prior_report: PriorReport | None = None,
) -> dict[str, Any]:
    """全量定稿 → 逐帧关键帧 02（定稿直出，不再二次插值猜真人感）。"""
    draft = copy.deepcopy(sparse_draft)
    phases = _phase_at_each_frame(draft, frame_count)
    old_tracks = draft.get("channel_tracks") or {}
    keys = list(draft.get("keys") or HUMAN_CHANNELS)
    tracks: dict[str, Any] = {}

    for ch in keys:
        if ch in BLINK_PRESERVE and ch in old_tracks and old_tracks[ch].get("keyframes"):
            tracks[ch] = copy.deepcopy(old_tracks[ch])
            continue
        series = channels.get(ch)
        if not series:
            tracks[ch] = {"role": old_tracks.get(ch, {}).get("role", ""), "keyframes": []}
            continue
        kfs = []
        for t in range(frame_count):
            kfs.append(
                {
                    "t": t,
                    "v": round(float(series[t]), 6),
                    "phase": phases[t],
                    "easing": "linear",
                }
            )
        tracks[ch] = {
            "role": old_tracks.get(ch, {}).get("role", ""),
            "keyframes": kfs,
        }

    draft["channel_tracks"] = tracks
    draft["schema_version"] = "0.2-baked-human-prior"
    draft["_baked_dense"] = True
    draft["frame_count"] = frame_count
    draft["fps"] = draft.get("fps") or FPS_DEFAULT
    if prior_report:
        draft["human_prior_report"] = prior_report.to_dict()
    jitter = (prior_report.jitter if prior_report else {}) or {}
    if jitter.get("enabled"):
        draft["micro_jitter"] = {
            "enabled": False,
            "_note": "颤动已烘焙进逐帧关键帧",
        }
    draft["_comment"] = "Python 补针 + 真人默认律定稿"
    return draft
