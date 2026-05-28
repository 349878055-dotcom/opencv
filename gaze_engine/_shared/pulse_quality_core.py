#!/usr/bin/env python3
"""
平庸三检核心 · Q01 能量 / Q02 保持 / Q03 主次延迟

合同：合同/09_先验与质检/双质量标准_不要假不要平庸.md
"""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from typing import Any

from gaze_engine._shared.slider_schema import HoldSegment, SliderPacket

FRAME_COUNT_DEFAULT = 150
SACCADE_T0 = 12
SACCADE_T1 = 28
HOLD_T0 = 25
HOLD_T1 = 110


@dataclass(frozen=True)
class PulseQualityConfig:
    species: str = "human"
    energy_channels: tuple[str, ...] = (
        "pupil_x",
        "pupil_y",
        "eyebrow",
        "squint",
        "pupil_scale",
        "iris_scale",
        "lid_upper",
        "lid_lower",
    )
    lag_channels: tuple[str, ...] = ("eyebrow",)
    primary_channel: str = "pupil_x"
    brow_lag_min: float = 5.0
    max_energy_scale: float = 1.42
    env_var: str = "ECURSOR_PULSE_QUALITY"
    blink_channel: str = "blink"
    blink_peak_min: float = 0.05
    blink_anchors: tuple[int, ...] = (49, 91, 132)
    decouple_pairs: tuple[tuple[str, str], ...] = ()


HUMAN_QC_CONFIG = PulseQualityConfig(
    species="human",
    env_var="ECURSOR_PULSE_QUALITY",
)

DOG_QC_CONFIG = PulseQualityConfig(
    species="dog",
    energy_channels=(
        "pupil_x",
        "pupil_y",
        "eyebrow",
        "brow_raise",
        "squint",
        "pupil_scale",
        "iris_scale",
        "lid_upper",
        "lid_lower",
    ),
    lag_channels=("eyebrow", "brow_raise"),
    decouple_pairs=(("squint", "pupil_scale"),),
)

CAT_QC_CONFIG = PulseQualityConfig(
    species="cat",
    energy_channels=(
        "pupil_x",
        "pupil_y",
        "eyebrow",
        "brow_raise",
        "squint",
        "pupil_scale",
        "iris_scale",
        "lid_upper",
        "lid_lower",
    ),
    lag_channels=("eyebrow", "brow_raise"),
    brow_lag_min=6.0,
    decouple_pairs=(("squint", "pupil_scale"),),
)


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
    species: str = "human"
    fixes: list[str] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)
    metrics: PulseQualityMetrics = field(default_factory=PulseQualityMetrics)

    @property
    def changed(self) -> bool:
        return bool(self.fixes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "species": self.species,
            "fixes": self.fixes,
            "remaining": self.remaining,
            "metrics": self.metrics.to_dict(),
        }


def _enabled(cfg: PulseQualityConfig) -> bool:
    return os.environ.get(cfg.env_var, "1").strip().lower() not in (
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
    seg = px[max(0, t0) : min(len(px), t1 + 1)]
    if len(seg) < 4:
        return 0.0
    diffs = [abs(seg[i + 1] - seg[i]) for i in range(len(seg) - 1)]
    med = sorted(diffs)[len(diffs) // 2]
    thresh = max(med * 5.0, 0.012)
    spikes = sum(1 for d in diffs if d > thresh)
    return spikes / len(diffs)


def _lag_frames(
    px: list[float],
    secondary: list[float],
    *,
    onset_threshold: float = 0.05,
) -> int:
    if not px or not secondary:
        return 99
    eye_on = next((i for i, v in enumerate(px) if i >= 8 and abs(v) > onset_threshold), 0)
    if not eye_on:
        return 99
    sec_peak = max(range(len(secondary)), key=lambda i: abs(secondary[i]), default=0)
    return sec_peak - eye_on


def _min_lag_frames(
    px: list[float],
    channels: dict[str, list[float]],
    lag_names: tuple[str, ...],
) -> int:
    lags = [_lag_frames(px, channels[name]) for name in lag_names if channels.get(name)]
    return min(lags) if lags else 99


def measure_dense(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    cfg: PulseQualityConfig,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> tuple[PulseQualityMetrics, dict[str, float]]:
    targets = reference_targets(packet)
    targets["brow_lag_min"] = cfg.brow_lag_min
    px = channels.get(cfg.primary_channel) or [0.0] * frame_count

    peak = max(abs(v) for v in px) if px else 0.0
    rng = (max(px) - min(px)) if px else 0.0
    slope = _max_abs_slope(px, SACCADE_T0, SACCADE_T1)
    _, hold_std = _series_stats(px, HOLD_T0, HOLD_T1)
    spike = _hold_spike_rate(px, HOLD_T0, HOLD_T1)
    lag = _min_lag_frames(px, channels, cfg.lag_channels)

    peak_tgt = max(targets["peak_target"], 1e-6)
    energy_ratio = peak / peak_tgt
    energy_score = min(1.0, energy_ratio / 0.58)
    clarity_score = (
        1.0 if lag >= targets["brow_lag_min"] else max(0.0, lag / targets["brow_lag_min"])
    )
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
    cfg: PulseQualityConfig,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> list[str]:
    m, targets = measure_dense(channels, packet, cfg, frame_count=frame_count)
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
        lag_label = "/".join(cfg.lag_channels)
        issues.append(f"Q03: 能量不纯（{lag_label} 峰不晚于眼）")
    return issues


def _scale_energy_channels(
    channels: dict[str, list[float]],
    scale: float,
    cfg: PulseQualityConfig,
    *,
    frame_count: int,
) -> None:
    scale = max(1.0, min(cfg.max_energy_scale, scale))
    for ch in cfg.energy_channels:
        if ch not in channels:
            continue
        s = channels[ch]
        channels[ch] = [v * scale for v in s[:frame_count]]


def _fix_q01_energy(
    channels: dict[str, list[float]],
    targets: dict[str, float],
    cfg: PulseQualityConfig,
    log: PulseQualityReport,
    *,
    frame_count: int,
) -> bool:
    px = channels.get(cfg.primary_channel) or []
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

    scale = min(cfg.max_energy_scale, max(scales))
    if scale <= 1.02:
        return False
    _scale_energy_channels(channels, scale, cfg, frame_count=frame_count)
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
    cfg: PulseQualityConfig,
    log: PulseQualityReport,
) -> bool:
    shape = packet.clamped().hold_seg.shape
    if shape not in ("flat", "decay"):
        return False
    px = channels.get(cfg.primary_channel) or []
    if not px:
        return False
    spike = _hold_spike_rate(px, HOLD_T0, HOLD_T1)
    _, hold_std = _series_stats(px, HOLD_T0, HOLD_T1)
    if spike <= targets["hold_spike_max"] and hold_std <= targets["hold_std_hi"] * 1.35:
        return False
    for ch in (cfg.primary_channel, "pupil_y"):
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
    cfg: PulseQualityConfig,
    log: PulseQualityReport,
) -> bool:
    px = channels.get(cfg.primary_channel) or []
    if not px:
        return False
    lag = _min_lag_frames(px, channels, cfg.lag_channels)
    need = int(targets["brow_lag_min"])
    if lag >= need:
        return False
    shift = min(12, max(need - lag, 3))
    for name in cfg.lag_channels:
        sec = channels.get(name)
        if not sec:
            continue
        channels[name] = _shift_series(sec, shift, HOLD_T0 // 2, HOLD_T1)
    lag_label = "/".join(cfg.lag_channels)
    log.fixes.append(f"Q03: {lag_label} 延后 {shift} 帧（原 lag={lag} 帧）")
    return True


def _fix_blink_floor(
    channels: dict[str, list[float]],
    cfg: PulseQualityConfig,
    log: PulseQualityReport,
    *,
    frame_count: int,
) -> bool:
    from gaze_engine._shared.envelope_compile import clamp_to_safe_range

    blink = channels.get(cfg.blink_channel) or [0.0] * frame_count
    peak = max(blink) if blink else 0.0
    nonzero = sum(1 for v in blink if v > 0.01)
    if peak >= cfg.blink_peak_min and nonzero >= 2:
        return False
    for t0 in cfg.blink_anchors:
        if t0 < 2 or t0 >= frame_count - 3:
            continue
        for dt, v in ((1, 0.10), (2, 0.14), (3, 0.07)):
            t = t0 + dt
            if 0 <= t < frame_count:
                blink[t] = max(blink[t], clamp_to_safe_range(v))
    channels[cfg.blink_channel] = blink
    log.fixes.append(f"blink补脉冲(peak={peak:.3f}→{max(blink):.3f})")
    return True


def _check_decouple_pairs(
    channels: dict[str, list[float]],
    cfg: PulseQualityConfig,
    log: PulseQualityReport,
    *,
    frame_count: int,
) -> None:
    for a, b in cfg.decouple_pairs:
        sa = channels.get(a) or []
        sb = channels.get(b) or []
        if not sa or not sb or len(sa) != len(sb):
            continue
        same = sum(1 for x, y in zip(sa, sb) if abs(x - y) < 1e-6)
        if same > frame_count * 0.85:
            log.fixes.append(f"{a}/{b}高度重合(需检查 envelope_compile)")


def fix_pulse_quality_core(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    cfg: PulseQualityConfig,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    max_rounds: int = 3,
    species_blink: bool = False,
) -> tuple[dict[str, list[float]], PulseQualityReport]:
    """全量 Dense′ 平庸修正；返回新 channels 与修正日记。"""
    report = PulseQualityReport(enabled=_enabled(cfg), species=cfg.species)
    if not report.enabled:
        report.metrics, _ = measure_dense(channels, packet, cfg, frame_count=frame_count)
        return channels, report

    out = {k: list(v[:frame_count]) for k, v in channels.items()}
    for _round in range(max_rounds):
        issues = diagnose_dense(out, packet, cfg, frame_count=frame_count)
        if not issues:
            break
        _, targets = measure_dense(out, packet, cfg, frame_count=frame_count)
        changed = False
        if any(i.startswith("Q01") for i in issues):
            changed |= _fix_q01_energy(out, targets, cfg, report, frame_count=frame_count)
        if any(i.startswith("Q02") for i in issues):
            changed |= _fix_q02_chaotic_hold(out, packet, targets, cfg, report)
        if any(i.startswith("Q03") for i in issues):
            changed |= _fix_q03_ensemble(out, targets, cfg, report)
        if not changed:
            break

    if species_blink:
        _fix_blink_floor(out, cfg, report, frame_count=frame_count)
    _check_decouple_pairs(out, cfg, report, frame_count=frame_count)

    report.metrics, _ = measure_dense(out, packet, cfg, frame_count=frame_count)
    report.remaining = diagnose_dense(out, packet, cfg, frame_count=frame_count)
    return out, report
