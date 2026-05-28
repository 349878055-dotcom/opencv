#!/usr/bin/env python3
"""
眼动先验核心 · 扫视动力学 + 盯住活劲 + 通道耦合

合同：合同/09_先验与质检/双质量标准_不要假不要平庸.md
"""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from typing import Any

from gaze_engine._shared.micro_jitter import apply_jitter_to_channels
from gaze_engine._shared.slider_schema import HoldSegment, SliderPacket, packet_to_compile_params

FRAME_COUNT_DEFAULT = 150
FPS_DEFAULT = 30
SACCADE_T0 = 12
SACCADE_T1 = 28
HOLD_T0 = 25
HOLD_T1 = 110


@dataclass(frozen=True)
class OculomotorPriorConfig:
    species: str = "human"
    zeta_range: tuple[float, float] = (0.72, 0.38)
    omega_range: tuple[float, float] = (9.0, 20.0)
    energy_in_scale: float = 0.88
    brow_lag_frames: int = 10
    lag_channels: tuple[str, ...] = ("eyebrow",)
    follow_channels: tuple[tuple[str, float], ...] = (
        ("pupil_scale", 0.08),
        ("squint", 0.06),
        ("iris_scale", 0.05),
    )
    saccade_channels: tuple[str, ...] = ("pupil_x", "pupil_y")
    jitter_profile: str = "cool_restrained"
    jitter_hz_bias: float = 0.0
    jitter_amp_bias: float = 0.0
    third_eyelid: bool = False
    third_eyelid_channel: str = "lid_lower"
    third_eyelid_peak: float = 0.18
    third_eyelid_center: int = 32
    env_var: str = "ECURSOR_HUMAN_PRIOR"


HUMAN_PRIOR_CONFIG = OculomotorPriorConfig(
    species="human",
    env_var="ECURSOR_HUMAN_PRIOR",
)

DOG_PRIOR_CONFIG = OculomotorPriorConfig(
    species="dog",
    zeta_range=(0.58, 0.42),
    omega_range=(11.0, 18.0),
    brow_lag_frames=8,
    lag_channels=("eyebrow", "brow_raise"),
    env_var="ECURSOR_DOG_PRIOR",
)

CAT_PRIOR_CONFIG = OculomotorPriorConfig(
    species="cat",
    zeta_range=(0.55, 0.38),
    omega_range=(14.0, 22.0),
    brow_lag_frames=8,
    lag_channels=("eyebrow", "brow_raise"),
    jitter_hz_bias=4.0,
    jitter_amp_bias=0.003,
    third_eyelid=True,
    env_var="ECURSOR_CAT_PRIOR",
)


@dataclass
class PriorReport:
    enabled: bool = True
    species: str = "human"
    speed: int = 50
    zeta: float = 0.55
    omega: float = 12.0
    saccade_window: tuple[int, int] = (SACCADE_T0, SACCADE_T1)
    overshoot_ratio_px: float = 0.0
    fixation_variance_px: float = 0.0
    brow_lag_frames: int = 10
    jitter: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "species": self.species,
            "speed": self.speed,
            "zeta": self.zeta,
            "omega": self.omega,
            "saccade_window": list(self.saccade_window),
            "overshoot_ratio_px": round(self.overshoot_ratio_px, 4),
            "fixation_variance_px": round(self.fixation_variance_px, 6),
            "brow_lag_frames": self.brow_lag_frames,
            "jitter": self.jitter,
            "issues": self.issues,
        }


def _lerp(a: float, b: float, t: float) -> float:
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t


def _intent(packet: SliderPacket, cfg: OculomotorPriorConfig) -> tuple[float, float, float, float, HoldSegment]:
    m = packet.macro
    params = packet_to_compile_params(packet)
    speed = m.speed / 100.0
    zeta = _lerp(cfg.zeta_range[0], cfg.zeta_range[1], speed)
    omega = _lerp(cfg.omega_range[0], cfg.omega_range[1], speed)
    energy = float(params["weight_scale"])
    if params["direction"] == "in":
        energy *= cfg.energy_in_scale
    return zeta, omega, energy, speed, packet.hold_seg


def _infer_saccade_window(sparse: dict | None, frame_count: int) -> tuple[int, int]:
    if not sparse:
        return SACCADE_T0, SACCADE_T1
    tracks = sparse.get("channel_tracks") or {}
    px = tracks.get("pupil_x", {}).get("keyframes") or []
    t0, t1 = SACCADE_T0, SACCADE_T1
    for k in px:
        ph = str(k.get("phase", ""))
        t = int(k["t"])
        if ph == "启动" and t < 20:
            t0 = min(t0, max(0, t - 2))
        if ph in ("启动", "保持") and SACCADE_T0 <= t <= 35:
            t1 = max(t1, t)
    return max(0, t0), min(frame_count - 1, max(t0 + 3, t1))


def _rewrite_saccade_2nd_order(
    series: list[float],
    t0: int,
    t1: int,
    *,
    zeta: float,
    omega: float,
    fps: int = FPS_DEFAULT,
) -> list[float]:
    out = list(series)
    if t1 <= t0 + 1:
        return out
    target = out[t1]
    start = out[max(0, t0 - 1)]
    x, v = start, 0.0
    dt = 1.0 / fps
    wn = omega
    for t in range(t0, t1 + 1):
        err = target - x
        a = wn * wn * err - 2.0 * zeta * wn * v
        v += a * dt
        x += v * dt
        out[t] = x
    for t in range(t1 + 1, len(out)):
        if abs(out[t] - target) < abs(out[t] - x):
            break
        blend = 0.15
        out[t] = out[t] * (1 - blend) + target * blend
    return out


def _apply_saccade_dynamics(
    channels: dict[str, list[float]],
    *,
    zeta: float,
    omega: float,
    window: tuple[int, int],
    energy: float,
    cfg: OculomotorPriorConfig,
) -> None:
    t0, t1 = window
    for ch in cfg.saccade_channels:
        if ch not in channels:
            continue
        s = [v * energy for v in channels[ch]]
        channels[ch] = _rewrite_saccade_2nd_order(s, t0, t1, zeta=zeta, omega=omega)


def _apply_hold_shape_on_channels(
    channels: dict[str, list[float]],
    hold: HoldSegment,
    frame_count: int,
    cfg: OculomotorPriorConfig,
) -> None:
    shape = hold.shape
    shape_channels = list(cfg.saccade_channels) + list(cfg.lag_channels) + ["pupil_scale", "squint"]
    if shape == "decay":
        for ch in shape_channels:
            if ch not in channels:
                continue
            s = channels[ch]
            base = s[max(0, HOLD_T0 - 1)]
            for t in range(HOLD_T0, min(HOLD_T1 + 1, frame_count)):
                frac = (t - HOLD_T0) / max(1, HOLD_T1 - HOLD_T0)
                s[t] = base + (s[t] - base) * (1.0 - 0.55 * frac)
    elif shape == "swell":
        sw = hold.swell / 100.0
        mid = 58
        if "eyebrow" in channels:
            s = channels["eyebrow"]
            s[mid] = s[mid] + 0.12 * sw
        if "pupil_scale" in channels:
            channels["pupil_scale"][mid] = channels["pupil_scale"][mid] + 0.08 * sw
    elif shape == "pulse":
        depth = 0.03 + (hold.pulse_depth / 100.0) * 0.10
        n = max(2, min(5, 2 + hold.pulse_rate // 22))
        t0, t1 = 38, 95
        step = max(1, (t1 - t0) // (n + 1))
        for ch in ("pupil_x", "squint"):
            if ch not in channels:
                continue
            s = channels[ch]
            for i in range(1, n + 1):
                t = t0 + step * i
                if t >= frame_count:
                    break
                sign = 1.0 if i % 2 else -1.0
                s[t] = s[t] + sign * depth


def _couple_lag_channels(
    channels: dict[str, list[float]],
    lag: int,
    frame_count: int,
    cfg: OculomotorPriorConfig,
) -> None:
    px = channels.get("pupil_x")
    if not px:
        return
    scale = 0.35
    for lag_name in cfg.lag_channels:
        if lag_name not in channels:
            continue
        sec = list(channels[lag_name])
        for t in range(frame_count):
            src = max(0, t - lag)
            delta = abs(px[t] - px[max(0, t - 1)])
            sec[t] = sec[t] + scale * abs(px[src]) * 0.15 + delta * 0.4
        channels[lag_name] = sec

    energy = max(abs(v) for v in px) if px else 0.0
    for ch, mul in cfg.follow_channels:
        if ch not in channels:
            continue
        s = channels[ch]
        for t in range(HOLD_T0, min(HOLD_T1, frame_count)):
            s[t] = s[t] + energy * mul * 0.2


def _jitter_block_for_packet(packet: SliderPacket, cfg: OculomotorPriorConfig) -> dict[str, Any]:
    hold = packet.hold_seg
    shape = hold.shape
    if shape == "tremble":
        hz, amp, profile = 10.0 + hold.pulse_rate / 100.0 * 18.0, 0.007 + hold.pulse_depth / 100.0 * 0.016, "agitated"
    elif shape == "pulse":
        hz, amp, profile = 8.0 + hold.pulse_rate / 100.0 * 14.0, 0.005 + hold.pulse_depth / 100.0 * 0.012, "cool_restrained"
    elif shape == "decay":
        hz, amp, profile = 6.0, 0.004, "tender"
    else:
        hz, amp, profile = 14.0, 0.009 + (100 - packet.macro.steady) / 100.0 * 0.004, cfg.jitter_profile
    m = packet.macro
    if m.power < 25:
        amp *= 0.85
    if m.steady > 80:
        amp *= 0.75
    hz += cfg.jitter_hz_bias
    amp += cfg.jitter_amp_bias
    return {
        "enabled": True,
        "profile": profile,
        "channels": list(cfg.saccade_channels),
        "by_phase": {
            "蓄力": {"hz": 0, "amplitude": 0},
            "启动": {"hz": 0, "amplitude": 0},
            "保持": {"hz": round(hz, 2), "amplitude": round(amp, 4)},
            "缓和": {"hz": round(hz * 0.65, 2), "amplitude": round(amp * 0.55, 4)},
        },
    }


def _apply_fixation_jitter(
    channels: dict[str, list[float]],
    sparse: dict,
    packet: SliderPacket,
    cfg: OculomotorPriorConfig,
    frame_count: int,
    fps: int,
) -> dict[str, Any]:
    sparse_j = copy.deepcopy(sparse)
    sparse_j["micro_jitter"] = _jitter_block_for_packet(packet, cfg)
    out, jitter_cfg = apply_jitter_to_channels(channels, sparse_j, frame_count, fps)
    channels.clear()
    channels.update(out)
    return jitter_cfg if isinstance(jitter_cfg, dict) else {}


def _apply_third_eyelid(
    channels: dict[str, list[float]],
    cfg: OculomotorPriorConfig,
    frame_count: int,
) -> None:
    if not cfg.third_eyelid:
        return
    ch = cfg.third_eyelid_channel
    if ch not in channels:
        return
    from gaze_engine._shared.envelope_compile import clamp_to_safe_range

    s = channels[ch]
    c = cfg.third_eyelid_center
    for dt, v in ((-2, 0.06), (-1, 0.12), (0, cfg.third_eyelid_peak), (1, 0.10), (2, 0.04)):
        t = c + dt
        if 0 <= t < frame_count:
            s[t] = clamp_to_safe_range(max(s[t], v))


def validate_dense_channels(
    channels: dict[str, list[float]],
    *,
    saccade_window: tuple[int, int],
    lag_channels: tuple[str, ...],
) -> list[str]:
    issues: list[str] = []
    px = channels.get("pupil_x") or []
    if len(px) < 30:
        return issues
    t0, t1 = saccade_window
    seg = px[t0 : t1 + 1]
    if len(seg) >= 3:
        peak_v = max(seg, key=abs)
        peak_i = seg.index(peak_v)
        if peak_i < len(seg) - 1:
            settle = seg[-1]
            if abs(peak_v) > 0.05 and abs(settle) >= abs(peak_v) * 0.92:
                if abs(peak_v) > 0.08:
                    issues.append("负向：pupil_x 扫视段缺少过冲后回弹")
    hold = px[HOLD_T0:HOLD_T1]
    if hold:
        mean = sum(hold) / len(hold)
        var = sum((x - mean) ** 2 for x in hold) / len(hold)
        if var < 1e-8:
            issues.append("负向：盯住段过平（无活劲）")
    if px:
        eye_on = next((i for i, v in enumerate(px) if i >= 10 and abs(v) > 0.06), 0)
        for lag_name in lag_channels:
            sec = channels.get(lag_name) or []
            if not sec or not eye_on:
                continue
            sec_peak = max(range(len(sec)), key=lambda i: abs(sec[i]), default=0)
            if sec_peak < eye_on + 5:
                issues.append(f"负向：{lag_name} 峰不晚于眼动")
    return issues


def apply_oculomotor_prior(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    cfg: OculomotorPriorConfig,
    sparse_draft: dict | None = None,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    fps: int = FPS_DEFAULT,
) -> tuple[dict[str, list[float]], PriorReport]:
    if os.environ.get(cfg.env_var, "1").strip().lower() in ("0", "false", "no", "off"):
        return channels, PriorReport(enabled=False, species=cfg.species)

    out = {k: list(v) for k, v in channels.items()}
    zeta, omega, energy, _speed, hold = _intent(packet, cfg)
    window = _infer_saccade_window(sparse_draft, frame_count)

    _apply_saccade_dynamics(out, zeta=zeta, omega=omega, window=window, energy=energy, cfg=cfg)
    if str((sparse_draft or {}).get("_compile_mode") or "") != "envelope-v1":
        _apply_hold_shape_on_channels(out, hold, frame_count, cfg)
    _couple_lag_channels(out, lag=cfg.brow_lag_frames, frame_count=frame_count, cfg=cfg)
    _apply_third_eyelid(out, cfg, frame_count)

    sparse_stub = copy.deepcopy(sparse_draft or {"channel_tracks": {}})
    sparse_stub["slider_packet"] = packet.to_dict()
    jitter_cfg = _apply_fixation_jitter(out, sparse_stub, packet, cfg, frame_count, fps)

    if packet.macro.outro < 50:
        end_t = 100
        for ch in out:
            s = out[ch]
            for t in range(end_t, frame_count):
                s[t] = s[t] * (1.0 - (t - end_t) / max(1, frame_count - end_t))

    report = PriorReport(
        species=cfg.species,
        speed=packet.macro.speed,
        zeta=zeta,
        omega=omega,
        saccade_window=window,
        brow_lag_frames=cfg.brow_lag_frames,
        jitter=jitter_cfg,
    )
    px = out.get("pupil_x", [])
    if px and window[1] > window[0]:
        seg = px[window[0] : window[1] + 1]
        peak, settle = max(seg, key=abs), seg[-1]
        if abs(settle) > 1e-6:
            report.overshoot_ratio_px = abs(peak) / abs(settle) - 1.0
    hold_seg = px[HOLD_T0:HOLD_T1] if px else []
    if hold_seg:
        m = sum(hold_seg) / len(hold_seg)
        report.fixation_variance_px = sum((x - m) ** 2 for x in hold_seg) / len(hold_seg)
    report.issues = validate_dense_channels(
        out, saccade_window=window, lag_channels=cfg.lag_channels
    )
    return out, report
