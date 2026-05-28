"""
狗真人化先验 · 扫视动力学 + 耳位耦合 + 叙事动作（回头等）

合同：合同/09_先验与质检/狗_先验与质检.md
"""
from __future__ import annotations

from typing import Any

from gaze_engine._shared.envelope_compile import clamp_to_safe_range
from gaze_engine._shared.oculomotor_prior import (
    DOG_PRIOR_CONFIG,
    FRAME_COUNT_DEFAULT,
    PriorReport,
    apply_oculomotor_prior,
)
from gaze_engine._shared.slider_schema import SliderPacket


def _glance_back_keywords(text: str) -> bool:
    t = (text or "").strip()
    return any(k in t for k in ("回头", "回看", "再看", "扭头", "侧目", "瞥"))


def _apply_glance_back_saccade(
    channels: dict[str, list[float]],
    frame_count: int,
) -> None:
    """叙事含「回头」：启动段 pupil_x 扫视 + 耳位微跟。"""
    px = channels.get("pupil_x") or []
    py = channels.get("pupil_y") or []
    eb = channels.get("eyebrow") or []
    br = channels.get("brow_raise") or []
    if not px:
        return

    t_start, t_end = 12, min(52, frame_count - 1)
    span = max(1, t_end - t_start)
    for t in range(t_start, t_end + 1):
        u = (t - t_start) / span
        sweep = u * u * (3.0 - 2.0 * u)
        px[t] = clamp_to_safe_range(px[t] + sweep * 0.24)
        py[t] = clamp_to_safe_range(py[t] + sweep * 0.06)
        if eb:
            eb[t] = clamp_to_safe_range(eb[t] + sweep * 0.04)
        if br:
            br[t] = clamp_to_safe_range(br[t] + sweep * 0.03)

    hold_from = min(55, frame_count - 1)
    hold_to = min(105, frame_count - 1)
    for t in range(hold_from, hold_to + 1):
        px[t] = clamp_to_safe_range(px[t] + 0.18)
        if eb:
            eb[t] = clamp_to_safe_range(eb[t] + 0.03)
        if br:
            br[t] = clamp_to_safe_range(br[t] + 0.02)


def apply_dog_prior(
    channels: dict[str, list[float]],
    packet: SliderPacket | Any,
    *,
    narrative_action: str = "",
    frame_count: int = FRAME_COUNT_DEFAULT,
    sparse_draft: dict | None = None,
) -> tuple[dict[str, list[float]], PriorReport]:
    """
    狗专用先验（envelope 编译之后、质检之前）：
      - 通用眼动动力学（过冲/微颤/耳眼延迟）
      - 叙事「回头」→ pupil 扫视 + 耳位微跟
    """
    pkt = packet if isinstance(packet, SliderPacket) else SliderPacket()
    sparse = dict(sparse_draft or {})
    sparse["_compile_mode"] = "envelope-v1"
    out, report = apply_oculomotor_prior(
        channels, pkt, DOG_PRIOR_CONFIG, sparse, frame_count=frame_count
    )
    action = narrative_action or getattr(packet, "emotion", "") or ""
    if _glance_back_keywords(action):
        _apply_glance_back_saccade(out, frame_count)
        report.issues.append("叙事：回头扫视已叠加")
    return out, report
