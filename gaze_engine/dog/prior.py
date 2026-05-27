"""
狗真人化先验 · 扫视动力学 + 耳位耦合 + 叙事动作（回头等）
"""
from __future__ import annotations

from typing import Any

from gaze_engine._shared.envelope_compile import clamp_to_safe_range


def _glance_back_keywords(text: str) -> bool:
    t = (text or "").strip()
    return any(k in t for k in ("回头", "回看", "再看", "扭头", "侧目", "瞥"))


def _apply_glance_back_saccade(
    channels: dict[str, list[float]],
    frame_count: int,
) -> None:
    """叙事含「回头」：启动段 pupil_x 扫视 + 耳位微跟（无独立 head 通道时的补偿）。"""
    px = channels.get("pupil_x") or []
    py = channels.get("pupil_y") or []
    eb = channels.get("eyebrow") or []
    if not px:
        return

    t_start, t_end = 12, min(52, frame_count - 1)
    span = max(1, t_end - t_start)
    for t in range(t_start, t_end + 1):
        u = (t - t_start) / span
        # 平滑扫视：先外后稳
        sweep = u * u * (3.0 - 2.0 * u)
        px[t] = clamp_to_safe_range(px[t] + sweep * 0.24)
        py[t] = clamp_to_safe_range(py[t] + sweep * 0.06)
        if eb:
            eb[t] = clamp_to_safe_range(eb[t] + sweep * 0.04)

    hold_from = min(55, frame_count - 1)
    hold_to = min(105, frame_count - 1)
    for t in range(hold_from, hold_to + 1):
        px[t] = clamp_to_safe_range(px[t] + 0.18)
        if eb:
            eb[t] = clamp_to_safe_range(eb[t] + 0.03)


def apply_dog_prior(
    channels: dict[str, list[float]],
    packet: Any,
    *,
    narrative_action: str = "",
    frame_count: int = 150,
) -> dict[str, list[float]]:
    """
    狗专用先验（在 envelope 编译之后、质检之前）：
      - 叙事「回头」→ pupil_x 扫视 + 耳位微跟
      - 保持 eyebrow 由 EarParams 注入的值，仅叠加小幅跟随
    """
    action = narrative_action or getattr(packet, "emotion", "") or ""
    if _glance_back_keywords(action):
        _apply_glance_back_saccade(channels, frame_count)
    return channels
