#!/usr/bin/env python3
"""
L3b 平庸检测 · 自动修正（contracts/眼眉真人默认律.md §6.4）

在 human_prior 之后、烘焙之前，对 Dense′ 检查并修正：
  Q01 能量不够 · Q02 保持段杂乱 · Q03 眉眼能量不纯

理论锚：拉班 Effort（力/时/流/空）+ Beat 起停收 + 眉眼分工。
"""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from typing import Any

from gaze_engine.human_prior import HOLD_T0, HOLD_T1, SACCADE_T0, SACCADE_T1
from gaze_engine.slider_schema import HoldSegment, SliderPacket

FRAME_COUNT_DEFAULT = 150

# 主能量轴 + 从属通道（缩放时一起抬，避免只剩眼动）
ENERGY_CHANNELS = (
    "pupil_x",
    "pupil_y",
    "eyebrow",
    "squint",
    "pupil_scale",
    "iris_scale",
    "lid_upper",
    "lid_lower",
)

BLINK_PRESERVE = frozenset({"blink", "eye_gloss"})

@dataclass
class PulseQualityMetrics:
    peak_px: float = 0.0
    range_px: float = 0.0
    saccade_slope: float = 0.0
    hold_std_px: float = 0.0
    hold_spike_rate: float = 0.0
    brow_lag_frames: int = 0
    energy_ratio: float = 0.0
    energy_score: float = 0.0
    clarity_score: float = 0.0
    noise_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "peak_px": round(self.peak_px, 5),
            "range_px": round(self.range_px, 5),
            "saccade_slope": round(self.saccade_slope, 5),
            "hold_std_px": round(self.hold_std_px, 6),
            "hold_spike_rate": round(self.hold_spike_rate, 4),
            "brow_lag_frames": self.brow_lag_frames,
            "energy_ratio": round(self.energy_ratio, 4),
            "energy_score": round(self.energy_score, 3),
            "clarity_score": round(self.clarity_score, 3),
            "noise_score": round(self.noise_score, 3),
        }

@dataclass
class PulseQualityReport:
    enabled: bool = True
    fixes: list[str] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)
    metrics: PulseQualityMetrics = field(default_factory=PulseQualityMetrics)

    @property
    def changed(self) -> bool:
        return bool(self.fixes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "fixes": self.fixes,
            "remaining": self.remaining,
            "metrics": self.metrics.to_dict(),
        }

def _enabled() -> bool:
    return os.environ.get("ECURSOR_PULSE_QUALITY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )

def reference_targets(packet: SliderPacket) -> dict[str, float]:
    """由 SliderPacket 推出该戏的期望能量（相对阈值，非绝对真值）。"""
    p = packet.clamped()
    m = p.macro
    h = p.hold_seg
    power = m.power / 100.0
    speed = m.speed / 100.0
    push = m.push / 100.0
    steady = m.steady / 100.0

    outward = 0.75 + 0.5 * abs(push - 0.5)
    peak = 0.07 + 0.40 * power * outward
    if push < 0.35:
        peak = 0.05 + 0.28 * power

    hold_std_lo = 0.002 + 0.012 * power * (1.0 - 0.25 * steady)
    hold_std_hi = 0.045 + 0.08 * power
    if h.shape == "flat":
        hold_spike_max = 0.10 + 0.04 * (1.0 - steady)
    elif h.shape in ("pulse", "swell"):
        hold_spike_max = 0.35
    elif h.shape == "tremble":
        hold_spike_max = 0.55
    else:
        hold_spike_max = 0.22

    floor_ratio = 0.45 if power < 0.35 else 0.58
    return {
        "peak_min": peak * floor_ratio,
        "peak_target": peak,
        "range_min": peak * 1.15,
        "saccade_slope_min": 0.012 + 0.09 * speed,
        "hold_std_lo": hold_std_lo,
        "hold_std_hi": hold_std_hi,
        "hold_spike_max": hold_spike_max,
        "brow_lag_min": 5.0,
    }

def _series_stats(px: list[float], t0: int, t1: int) -> tuple[float, float]:
    seg = px[max(0, t0) : min(len(px), t1 + 1)]
    if not seg:
        return 0.0, 0.0
    mean = sum(seg) / len(seg)
    var = sum((x - mean) ** 2 for x in seg) / len(seg)
    return mean, var**0.5

def _max_abs_slope(px: list[float], t0: int, t1: int) -> float:
    seg = px[max(0, t0) : min(len(px), t1 + 1)]
    if len(seg) < 2:
        return 0.0
    return max(abs(seg[i + 1] - seg[i]) for i in range(len(seg) - 1))

def _hold_spike_rate(px: list[float], t0: int, t1: int) -> float:
    """盯住段大幅跳变占比（微颤不算乱；只抓异常尖刺）。"""
    seg = px[max(0, t0) : min(len(px), t1 + 1)]
    if len(seg) < 4:
        return 0.0
    diffs = [abs(seg[i + 1] - seg[i]) for i in range(len(seg) - 1)]
    med = sorted(diffs)[len(diffs) // 2]
    thresh = max(med * 5.0, 0.012)
    spikes = sum(1 for d in diffs if d > thresh)
    return spikes / len(diffs)

def _brow_lag_frames(px: list[float], eb: list[float]) -> int:
    if not px or not eb:
        return 99
    eye_on = next((i for i, v in enumerate(px) if i >= 8 and abs(v) > 0.05), 0)
    if not eye_on:
        return 99
    brow_peak = max(range(len(eb)), key=lambda i: abs(eb[i]), default=0)
    return brow_peak - eye_on

def measure_dense(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> tuple[PulseQualityMetrics, dict[str, float]]:
    targets = reference_targets(packet)
    px = channels.get("pupil_x") or [0.0] * frame_count
    eb = channels.get("eyebrow") or []

    peak = max(abs(v) for v in px) if px else 0.0
    rng = (max(px) - min(px)) if px else 0.0
    slope = _max_abs_slope(px, SACCADE_T0, SACCADE_T1)
    _, hold_std = _series_stats(px, HOLD_T0, HOLD_T1)
    spike = _hold_spike_rate(px, HOLD_T0, HOLD_T1)
    lag = _brow_lag_frames(px, eb)

    peak_tgt = max(targets["peak_target"], 1e-6)
    energy_ratio = peak / peak_tgt
    energy_score = min(1.0, energy_ratio / 0.58)
    clarity_score = 1.0 if lag >= targets["brow_lag_min"] else max(0.0, lag / targets["brow_lag_min"])
    if targets["hold_std_lo"] <= hold_std <= targets["hold_std_hi"]:
        noise_score = 1.0
    elif hold_std < targets["hold_std_lo"]:
        noise_score = hold_std / max(targets["hold_std_lo"], 1e-8)
    elif spike > targets["hold_spike_max"]:
        noise_score = max(0.0, 1.0 - (spike - targets["hold_spike_max"]) / 0.35)
    else:
        noise_score = 0.85

    m = PulseQualityMetrics(
        peak_px=peak,
        range_px=rng,
        saccade_slope=slope,
        hold_std_px=hold_std,
        hold_spike_rate=spike,
        brow_lag_frames=lag,
        energy_ratio=energy_ratio,
        energy_score=energy_score,
        clarity_score=clarity_score,
        noise_score=noise_score,
    )
    return m, targets

def diagnose_dense(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> list[str]:
    m, targets = measure_dense(channels, packet, frame_count=frame_count)
    power = packet.clamped().macro.power
    issues: list[str] = []
    if m.peak_px < targets["peak_min"]:
        issues.append("Q01: 能量不够（峰弱）")
    if m.range_px < targets["range_min"] * 0.85 and m.peak_px < targets["peak_min"]:
        issues.append("Q01: 能量不够（动态范围小）")
    if (
        m.saccade_slope < targets["saccade_slope_min"] * 0.72
        and m.peak_px < targets["peak_min"]
        and power >= 35
    ):
        issues.append("Q01: 能量不够（起势弱）")
    if m.hold_std_px < targets["hold_std_lo"] * 0.65 and m.peak_px < targets["peak_min"]:
        issues.append("Q01: 能量不够（盯住段瘪）")

    shape = packet.clamped().hold_seg.shape
    if shape in ("flat", "decay") and m.hold_spike_rate > targets["hold_spike_max"]:
        issues.append("Q02: 保持段杂乱（异常尖刺过多）")
    if shape == "flat" and m.hold_std_px > targets["hold_std_hi"] * 1.35:
        issues.append("Q02: 保持段杂乱（起伏过大）")

    if m.brow_lag_frames < int(targets["brow_lag_min"]):
        issues.append("Q03: 能量不纯（眉峰不晚于眼）")
    return issues

def _scale_energy_channels(
    channels: dict[str, list[float]],
    scale: float,
    *,
    frame_count: int,
) -> None:
    scale = max(1.0, min(1.42, scale))
    for ch in ENERGY_CHANNELS:
        if ch not in channels:
            continue
        s = channels[ch]
        channels[ch] = [v * scale for v in s[:frame_count]]

def _fix_q01_energy(
    channels: dict[str, list[float]],
    targets: dict[str, float],
    log: PulseQualityReport,
    *,
    frame_count: int,
) -> bool:
    px = channels.get("pupil_x") or []
    if not px:
        return False
    peak = max(abs(v) for v in px)
    need_peak = targets["peak_min"]
    rng = max(px) - min(px)
    slope = _max_abs_slope(px, SACCADE_T0, SACCADE_T1)
    _, hold_std = _series_stats(px, HOLD_T0, HOLD_T1)

    scales = [1.0]
    peak_ok = peak >= targets["peak_target"] * 0.88
    if peak < need_peak:
        scales.append(need_peak / max(peak, 1e-6))
    if not peak_ok and rng < targets["range_min"] * 0.85:
        scales.append((targets["range_min"] * 0.92) / max(rng, 1e-6))
    if not peak_ok and slope < targets["saccade_slope_min"] * 0.72:
        scales.append((targets["saccade_slope_min"] * 0.85) / max(slope, 1e-6))
    if not peak_ok and hold_std < targets["hold_std_lo"] * 0.65:
        scales.append((targets["hold_std_lo"] * 0.75) / max(hold_std, 1e-8))

    scale = min(1.42, max(scales))
    if scale <= 1.02:
        return False
    _scale_energy_channels(channels, scale, frame_count=frame_count)
    log.fixes.append(
        f"Q01: 抬升主能量 ×{scale:.3f}（峰 {peak:.4f}、range {rng:.4f}、起势 {slope:.4f}）"
    )
    return True

def _moving_average(series: list[float], t0: int, t1: int, radius: int = 2) -> list[float]:
    out = list(series)
    n = len(out)
    for t in range(max(0, t0), min(n, t1 + 1)):
        acc: list[float] = []
        for j in range(t - radius, t + radius + 1):
            if 0 <= j < n:
                acc.append(series[j])
        out[t] = sum(acc) / len(acc)
    return out

def _fix_q02_chaotic_hold(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    targets: dict[str, float],
    log: PulseQualityReport,
) -> bool:
    shape = packet.clamped().hold_seg.shape
    if shape not in ("flat", "decay"):
        return False
    px = channels.get("pupil_x") or []
    if not px:
        return False
    spike = _hold_spike_rate(px, HOLD_T0, HOLD_T1)
    _, hold_std = _series_stats(px, HOLD_T0, HOLD_T1)
    if spike <= targets["hold_spike_max"] and hold_std <= targets["hold_std_hi"] * 1.35:
        return False
    for ch in ("pupil_x", "pupil_y"):
        if ch in channels:
            channels[ch] = _moving_average(channels[ch], HOLD_T0, HOLD_T1, radius=2)
    log.fixes.append(
        f"Q02: 盯住段轻平滑（shape={shape}，spike={spike:.3f}→≤{targets['hold_spike_max']:.3f}）"
    )
    return True

def _shift_series(series: list[float], lag: int, t0: int, t1: int) -> list[float]:
    out = list(series)
    n = len(out)
    for t in range(min(n - 1, t1), max(t0, lag) - 1, -1):
        out[t] = out[t - lag]
    return out

def _fix_q03_ensemble(
    channels: dict[str, list[float]],
    targets: dict[str, float],
    log: PulseQualityReport,
) -> bool:
    px = channels.get("pupil_x") or []
    eb = channels.get("eyebrow") or []
    if not px or not eb:
        return False
    lag = _brow_lag_frames(px, eb)
    need = int(targets["brow_lag_min"])
    if lag >= need:
        return False
    shift = min(12, max(need - lag, 3))
    channels["eyebrow"] = _shift_series(eb, shift, HOLD_T0 // 2, HOLD_T1)
    log.fixes.append(f"Q03: 眉峰延后 {shift} 帧（原 lag={lag} 帧）")
    return True

def fix_pulse_quality(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    sparse_draft: dict | None = None,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    max_rounds: int = 3,
) -> tuple[dict[str, list[float]], PulseQualityReport]:
    """全量 Dense′ 平庸修正；返回新 channels 与修正日记。"""
    _ = sparse_draft
    report = PulseQualityReport(enabled=_enabled())
    if not report.enabled:
        report.metrics, _ = measure_dense(channels, packet, frame_count=frame_count)
        return channels, report

    out = {k: list(v[:frame_count]) for k, v in channels.items()}
    for _round in range(max_rounds):
        issues = diagnose_dense(out, packet, frame_count=frame_count)
        if not issues:
            break
        _, targets = measure_dense(out, packet, frame_count=frame_count)
        changed = False
        if any(i.startswith("Q01") for i in issues):
            changed |= _fix_q01_energy(out, targets, report, frame_count=frame_count)
        if any(i.startswith("Q02") for i in issues):
            changed |= _fix_q02_chaotic_hold(out, packet, targets, report)
        if any(i.startswith("Q03") for i in issues):
            changed |= _fix_q03_ensemble(out, targets, report)
        if not changed:
            break

    report.metrics, _ = measure_dense(out, packet, frame_count=frame_count)
    report.remaining = diagnose_dense(out, packet, frame_count=frame_count)
    return out, report
