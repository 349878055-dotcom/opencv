#!/usr/bin/env python3
"""眼眉真人默认律 · 全量 12×150 后处理（contracts/眼眉真人默认律.md）。"""
from __future__ import annotations

import copy
import math
import os
from dataclasses import dataclass, field
from typing import Any

from gaze_engine.channel_contract import CANONICAL_KEYS
from gaze_engine.micro_jitter import (
    _phase_at_each_frame,
    apply_jitter_to_channels,
)
from gaze_engine.slider_schema import HoldSegment, SliderPacket, packet_to_compile_params

FRAME_COUNT_DEFAULT = 150
FPS_DEFAULT = 30
SACCADE_T0 = 12
SACCADE_T1 = 28
HOLD_T0 = 25
HOLD_T1 = 110
BLINK_PRESERVE = frozenset({"blink"})

@dataclass
class PriorReport:
    enabled: bool = True
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

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _intent(packet: SliderPacket) -> tuple[float, float, float, float, HoldSegment]:
    m = packet.macro
    params = packet_to_compile_params(packet)
    speed = m.speed / 100.0
    zeta = _lerp(0.72, 0.38, speed)
    omega = _lerp(9.0, 20.0, speed)
    energy = float(params["weight_scale"])
    if params["direction"] == "in":
        energy *= 0.88
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
    """欠阻尼二阶系统趋向段末目标，自然产生过冲。"""
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
) -> None:
    t0, t1 = window
    for ch in ("pupil_x", "pupil_y"):
        if ch not in channels:
            continue
        s = [v * energy for v in channels[ch]]
        channels[ch] = _rewrite_saccade_2nd_order(s, t0, t1, zeta=zeta, omega=omega)

def _apply_hold_shape_on_channels(
    channels: dict[str, list[float]],
    hold: HoldSegment,
    frame_count: int,
) -> None:
    shape = hold.shape
    if shape == "decay":
        for ch in ("pupil_x", "pupil_y", "eyebrow", "pupil_scale", "squint"):
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

def _couple_eyebrow_lag(
    channels: dict[str, list[float]],
    lag: int,
    frame_count: int,
) -> None:
    if "pupil_x" not in channels or "eyebrow" not in channels:
        return
    px = channels["pupil_x"]
    eb = list(channels["eyebrow"])
    scale = 0.35
    for t in range(frame_count):
        src = max(0, t - lag)
        delta = abs(px[t] - px[max(0, t - 1)])
        eb[t] = eb[t] + scale * abs(px[src]) * 0.15 + delta * 0.4
    channels["eyebrow"] = eb

    energy = max(abs(v) for v in px) if px else 0.0
    for ch, mul in (
        ("pupil_scale", 0.08),
        ("squint", 0.06),
        ("iris_scale", 0.05),
    ):
        if ch not in channels:
            continue
        s = channels[ch]
        for t in range(HOLD_T0, min(HOLD_T1, frame_count)):
            s[t] = s[t] + energy * mul * 0.2

def _jitter_block_for_packet(packet: SliderPacket) -> dict[str, Any]:
    hold = packet.hold_seg
    shape = hold.shape
    if shape == "tremble":
        hz, amp, profile = 10.0 + hold.pulse_rate / 100.0 * 18.0, 0.007 + hold.pulse_depth / 100.0 * 0.016, "agitated"
    elif shape == "pulse":
        hz, amp, profile = 8.0 + hold.pulse_rate / 100.0 * 14.0, 0.005 + hold.pulse_depth / 100.0 * 0.012, "cool_restrained"
    elif shape == "decay":
        hz, amp, profile = 6.0, 0.004, "tender"
    else:
        hz, amp, profile = 14.0, 0.009 + (100 - packet.macro.steady) / 100.0 * 0.004, "cool_restrained"
    m = packet.macro
    if m.power < 25:
        amp *= 0.85
    if m.steady > 80:
        amp *= 0.75
    return {
        "enabled": True,
        "profile": profile,
        "channels": ["pupil_x", "pupil_y"],
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
    frame_count: int,
    fps: int,
) -> dict[str, Any]:
    sparse_j = copy.deepcopy(sparse)
    sparse_j["micro_jitter"] = _jitter_block_for_packet(packet)
    out, cfg = apply_jitter_to_channels(channels, sparse_j, frame_count, fps)
    channels.clear()
    channels.update(out)
    return cfg

def validate_dense_channels(
    channels: dict[str, list[float]],
    *,
    saccade_window: tuple[int, int],
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
            if abs(peak_v) > 0.05 and abs(settle) < abs(peak_v) * 0.92:
                pass
            elif abs(peak_v) > 0.08:
                issues.append("负向：pupil_x 扫视段缺少过冲后回弹")
    hold = px[HOLD_T0:HOLD_T1]
    if hold:
        mean = sum(hold) / len(hold)
        var = sum((x - mean) ** 2 for x in hold) / len(hold)
        if var < 1e-8:
            issues.append("负向：盯住段过平（无活劲）")
    eb = channels.get("eyebrow") or []
    if px and eb:
        eye_on = next((i for i, v in enumerate(px) if i >= 10 and abs(v) > 0.06), 0)
        brow_peak = max(range(len(eb)), key=lambda i: abs(eb[i]), default=0)
        if eye_on and brow_peak < eye_on + 5:
            issues.append("负向：眉峰不晚于眼动")
    return issues

def apply_human_prior(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    sparse_draft: dict | None = None,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    fps: int = FPS_DEFAULT,
) -> tuple[dict[str, list[float]], PriorReport]:
    """全量曲线真人化；返回新 channels 与验收报告。"""
    if os.environ.get("ECURSOR_HUMAN_PRIOR", "1").strip().lower() in ("0", "false", "no", "off"):
        return channels, PriorReport(enabled=False)

    out = {k: list(v) for k, v in channels.items()}
    zeta, omega, energy, _speed, hold = _intent(packet)
    window = _infer_saccade_window(sparse_draft, frame_count)

    _apply_saccade_dynamics(out, zeta=zeta, omega=omega, window=window, energy=energy)
    if str(sparse_draft.get("_compile_mode") or "") != "envelope-v1":
        _apply_hold_shape_on_channels(out, hold, frame_count)
    _couple_eyebrow_lag(out, lag=10, frame_count=frame_count)

    sparse_stub = sparse_draft or {"channel_tracks": {}}
    sparse_stub = copy.deepcopy(sparse_stub)
    sparse_stub["slider_packet"] = packet.to_dict()
    jitter_cfg = _apply_fixation_jitter(out, sparse_stub, packet, frame_count, fps)

    # 收尾：outro 快则 t>100 衰减
    if packet.macro.outro < 50:
        end_t = 100
        for ch in out:
            s = out[ch]
            for t in range(end_t, frame_count):
                s[t] = s[t] * (1.0 - (t - end_t) / max(1, frame_count - end_t))

    report = PriorReport(
        speed=packet.macro.speed,
        zeta=zeta,
        omega=omega,
        saccade_window=window,
        jitter=jitter_cfg if isinstance(jitter_cfg, dict) else {},
    )
    px = out.get("pupil_x", [])
    if px and window[1] > window[0]:
        seg = px[window[0] : window[1] + 1]
        peak, settle = max(seg, key=abs), seg[-1]
        if abs(settle) > 1e-6:
            report.overshoot_ratio_px = abs(peak) / abs(settle) - 1.0
    hold = px[HOLD_T0:HOLD_T1] if px else []
    if hold:
        m = sum(hold) / len(hold)
        report.fixation_variance_px = sum((x - m) ** 2 for x in hold) / len(hold)
    report.issues = validate_dense_channels(out, saccade_window=window)
    return out, report

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
    keys = list(draft.get("keys") or CANONICAL_KEYS)
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

def main() -> int:
    import argparse
    import json
    import sys
    from pathlib import Path

    _pkg = Path(__file__).resolve().parent.parent
    if str(_pkg) not in sys.path:
        sys.path.insert(0, str(_pkg))

    from gaze_engine.delivery_pipeline import run_delivery  # noqa: E402

    ap = argparse.ArgumentParser(description="稀疏 02 + SliderPacket → 烘焙定稿 02")
    ap.add_argument("--sparse", required=True)
    ap.add_argument("--packet", default="")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    sparse = json.loads(Path(args.sparse).read_text(encoding="utf-8"))
    packet = None
    if args.packet:
        packet = SliderPacket.from_dict(
            json.loads(Path(args.packet).read_text(encoding="utf-8"))
        )
    from gaze_engine.delivery_pipeline import run_delivery_from_packet

    baked, _dense, rep, _pq = run_delivery_from_packet(packet)
    Path(args.output).write_text(
        json.dumps(baked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
    if rep.issues:
        print("[审]", "; ".join(rep.issues))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
