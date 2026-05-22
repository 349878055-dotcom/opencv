#!/usr/bin/env python3
"""
滑杆 → 能量包络 E(t) → 12×150 全量通道（主出厂路径）。

不再依赖稀疏关键帧母版；操作台 SliderPacket 即编译输入。
"""
from __future__ import annotations

import math
from typing import Any

from gaze_engine.channel_contract import CANONICAL_KEYS
from gaze_engine.slider_schema import HoldSegment, SliderPacket

FRAME_COUNT_DEFAULT = 150
FPS_DEFAULT = 30

def _clamp01(u: float) -> float:
    return 0.0 if u <= 0.0 else 1.0 if u >= 1.0 else u

def _lerp(a: float, b: float, t: float) -> float:
    t = _clamp01(t)
    return a + (b - a) * t

def _smoothstep(u: float) -> float:
    u = _clamp01(u)
    return u * u * (3.0 - 2.0 * u)

def _timing(packet: SliderPacket, frame_count: int) -> dict[str, int]:
    m = packet.macro
    speed = m.speed / 100.0
    t_peak = int(round(_lerp(20, 14, speed)))
    t_settle = min(frame_count - 1, t_peak + int(round(_lerp(8, 4, speed))))
    t_hold0 = max(t_settle, 25)
    outro_fast = m.outro < 50
    t_hold1 = 92 if outro_fast else 110
    t_hold1 = min(frame_count - 2, t_hold1)
    return {
        "t_peak": t_peak,
        "t_settle": t_settle,
        "t_hold0": t_hold0,
        "t_hold1": t_hold1,
        "t_outro_end": frame_count - 1,
    }

def _peak_level(packet: SliderPacket) -> float:
    m = packet.macro
    power = m.power / 100.0
    push = m.push / 100.0
    outward = 0.78 + 0.45 * abs(push - 0.5)
    peak = 0.06 + 0.38 * power * outward
    if push < 0.35:
        peak = 0.04 + 0.26 * power
    return peak

def _hold_texture(
    u: float,
    hold: HoldSegment,
    *,
    tremble_amp: float,
) -> float:
    """u∈[0,1] 盯住段内；返回相对平顶的乘子。"""
    shape = hold.shape
    if shape == "flat":
        return 1.0
    if shape == "decay":
        return 1.0 - 0.55 * u
    if shape == "swell":
        return 1.0 + (hold.swell / 100.0) * 0.35 * math.sin(math.pi * u)
    if shape == "pulse":
        rate = max(1.0, hold.pulse_rate / 100.0 * 4.0)
        depth = 0.06 + (hold.pulse_depth / 100.0) * 0.20
        return 1.0 + depth * math.sin(2.0 * math.pi * rate * u)
    if shape == "tremble":
        rate = 6.0 + hold.pulse_rate / 100.0 * 10.0
        return 1.0 + tremble_amp * math.sin(2.0 * math.pi * rate * u)
    return 1.0

def build_energy_envelope(
    packet: SliderPacket,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> list[float]:
    """主能量包络 E(t) ≥ 0；形状由 macro + hold_seg 决定。"""
    pkt = packet.clamped()
    m = pkt.macro
    hold = pkt.hold_seg
    tm = _timing(pkt, frame_count)
    peak = _peak_level(pkt)
    grip = m.grip / 100.0
    plateau = peak * _lerp(0.88, 1.0, grip)

    env = [0.0] * frame_count
    t_peak = tm["t_peak"]
    t_settle = tm["t_settle"]
    t_hold0 = tm["t_hold0"]
    t_hold1 = tm["t_hold1"]
    t_end = tm["t_outro_end"]

    for t in range(0, t_peak + 1):
        u = t / max(1, t_peak)
        env[t] = peak * _smoothstep(u)

    for t in range(t_peak + 1, t_settle + 1):
        u = (t - t_peak) / max(1, t_settle - t_peak)
        env[t] = peak + (plateau - peak) * _smoothstep(u)

    hold_len = max(1, t_hold1 - t_hold0)
    tremble_amp = 0.03 + hold.pulse_depth / 100.0 * 0.05
    for t in range(max(t_settle, t_hold0), t_hold1 + 1):
        u = (t - t_hold0) / hold_len
        env[t] = plateau * _hold_texture(u, hold, tremble_amp=tremble_amp)

    tail0 = env[t_hold1] if t_hold1 < frame_count else plateau
    outro_len = max(1, t_end - t_hold1)
    outro_fast = m.outro < 50
    for t in range(t_hold1 + 1, frame_count):
        u = (t - t_hold1) / outro_len
        if outro_fast:
            env[t] = tail0 * (1.0 - _smoothstep(u))
        else:
            env[t] = tail0 * (1.0 - 0.85 * u)

    return env

def _direction(packet: SliderPacket) -> tuple[float, float]:
    push = packet.macro.push / 100.0
    sign = 1.0 if push >= 0.5 else -1.0
    y_bias = -0.12 * sign if push >= 0.5 else -0.08
    return sign, y_bias

def channels_from_envelope(
    packet: SliderPacket,
    envelope: list[float],
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> dict[str, list[float]]:
    """E(t) → 12 轨全量（耦合分工；生理细节交给 human_prior）。"""
    pkt = packet.clamped()
    m = pkt.macro
    sign, y_bias = _direction(pkt)
    tm = _timing(pkt, frame_count)
    lag = int(round(_lerp(12, 6, m.speed / 100.0)))

    px = [sign * e for e in envelope]
    py = [y_bias * e + sign * 0.08 * e for e in envelope]

    # 眉：滞后跟随主能量
    eb = [0.0] * frame_count
    for t in range(frame_count):
        src = max(0, t - lag)
        eb[t] = 0.04 + 0.92 * abs(px[src])

    squint = [0.02 + 0.55 * abs(e) for e in envelope]
    p_scale = [0.02 + 0.22 * e for e in envelope]
    iris = [0.15 + 0.12 * e for e in envelope]
    bulge = [0.1 + 0.08 * e for e in envelope]
    lid_u = [0.05 + 0.35 * e for e in envelope]
    lid_l = [0.02 + 0.18 * e for e in envelope]
    brow_r = [0.02 + 0.15 * e for e in envelope]
    gloss = [0.2 + 0.25 * e for e in envelope]

    blink = [0.0] * frame_count
    t_blink = min(frame_count - 3, 86 + int(round(_lerp(2, -4, m.speed / 100.0))))
    for dt, v in ((0, 0.0), (1, 0.11), (2, 0.14), (3, 0.08), (4, 0.0)):
        t = t_blink + dt
        if 0 <= t < frame_count:
            blink[t] = v

    channels = {
        "pupil_x": px,
        "pupil_y": py,
        "blink": blink,
        "eyebrow": eb,
        "pupil_scale": p_scale,
        "iris_scale": iris,
        "cornea_bulge": bulge,
        "squint": squint,
        "brow_raise": brow_r,
        "lid_upper": lid_u,
        "lid_lower": lid_l,
        "eye_gloss": gloss,
    }
    return {k: channels[k] for k in CANONICAL_KEYS if k in channels}

def _apply_pulse_hold_coupling(
    packet: SliderPacket,
    channels: dict[str, list[float]],
    envelope: list[float],
    frame_count: int,
) -> None:
    """pulse 盯住段：眉/眯/瞳附加强耦合，增强表演力读出「放电」。"""
    if packet.hold_seg.shape != "pulse":
        return
    pkt = packet.clamped()
    sign, _ = _direction(pkt)
    tm = _timing(pkt, frame_count)
    t0, t1 = tm["t_hold0"], tm["t_hold1"]
    hold_len = max(1, t1 - t0)
    for t in range(max(0, t0), min(frame_count, t1 + 1)):
        u = (t - t0) / hold_len
        rip = _hold_texture(u, pkt.hold_seg, tremble_amp=0) - 1.0
        amp = envelope[t] if t < len(envelope) else 0.0
        channels["pupil_x"][t] += sign * rip * amp * 0.38
        channels["pupil_y"][t] += sign * rip * amp * 0.12
        channels["eyebrow"][t] += abs(rip) * amp * 0.32
        channels["squint"][t] += abs(rip) * amp * 0.20
        channels["pupil_scale"][t] += rip * amp * 0.14

def channels_from_packet(
    packet: SliderPacket,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> dict[str, list[float]]:
    env = build_energy_envelope(packet, frame_count)
    ch = channels_from_envelope(packet, env, frame_count)
    _apply_pulse_hold_coupling(packet, ch, env, frame_count)
    return ch

def export_envelope_series(
    packet: SliderPacket,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> dict[str, Any]:
    env = build_energy_envelope(packet, frame_count)
    tm = _timing(packet.clamped(), frame_count)
    return {
        "schema": "energy-envelope-v1",
        "frame_count": frame_count,
        "fps": FPS_DEFAULT,
        "peak_level": round(_peak_level(packet.clamped()), 5),
        "timing": tm,
        "envelope": [round(v, 6) for v in env],
    }

def make_delivery_stub(
    packet: SliderPacket,
    channels: dict[str, list[float]],
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    label: str = "",
) -> dict[str, Any]:
    """供 human_prior / 烘焙 用的轻量 02 上下文（非稀疏关键帧真值）。"""
    from gaze_engine.micro_jitter import default_micro_jitter_block

    pkt = packet.clamped()
    tm = _timing(pkt, frame_count)
    px = channels.get("pupil_x") or []
    t_peak = tm["t_peak"]
    t_settle = tm["t_settle"]

    profile = "cool_restrained"
    if pkt.hold_seg.shape == "tremble":
        profile = "agitated"
    elif pkt.macro.power < 35:
        profile = "tender"

    return {
        "_comment": "滑杆能量包络出厂；非手搓稀疏真值",
        "schema_version": "0.2-envelope-stub",
        "revision": f"envelope:{label or pkt.emotion}",
        "_compile_mode": "envelope-v1",
        "gaze_emotion_id": label or pkt.emotion,
        "mood": pkt.emotion,
        "energy_phases": ["蓄力", "启动", "保持", "缓和"],
        "controls_doc": "contracts/滑杆规范.md",
        "keys": list(CANONICAL_KEYS),
        "keys_active": list(CANONICAL_KEYS),
        "slider_packet": pkt.to_dict(),
        "energy_envelope": export_envelope_series(pkt, frame_count),
        "channel_tracks": {
            "pupil_x": {
                "keyframes": [
                    {"t": 0, "v": px[0] if px else 0.0, "phase": "蓄力"},
                    {"t": t_peak, "v": px[t_peak] if len(px) > t_peak else 0.0, "phase": "启动"},
                    {"t": t_settle, "v": px[t_settle] if len(px) > t_settle else 0.0, "phase": "启动"},
                    {
                        "t": tm["t_hold1"],
                        "v": px[min(tm["t_hold1"], len(px) - 1)] if px else 0.0,
                        "phase": "保持",
                    },
                    {
                        "t": frame_count - 1,
                        "v": px[-1] if px else 0.0,
                        "phase": "缓和",
                    },
                ]
            }
        },
        "micro_jitter": default_micro_jitter_block(profile),
    }
