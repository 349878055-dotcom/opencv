#!/usr/bin/env python3
"""
滑杆 → 能量包络 E(t) — 纯数学层，物种无关。

保留函数均为纯数学计算，不包含任何人类/猫/狗的生理假设。
物种专属的通道映射（eyebrow 滞后处理、pulse 耦合等）放在各物种的 envelope_compile.py。

PAD 投影公式（每一帧，由 species 专用层调用 compute_pad_scale）：
  final_scale[ch] = base_scale[ch] + P×Wp[ch] + A×Wa[ch] + D×Wd[ch]
  channel[t] = clamp01(final_scale[ch] × envelope[t])
"""
from __future__ import annotations

import math
from typing import Any, Dict

from gaze_engine._shared.slider_schema import HoldSegment, SliderPacket

FRAME_COUNT_DEFAULT = 150
FPS_DEFAULT = 30


def _clamp01(u: float) -> float:
    return 0.0 if u <= 0.0 else 1.0 if u >= 1.0 else u


def clamp_to_safe_range(value: float) -> float:
    """将单个数值强制钳位到 [0.0, 1.0]。

    所有物种共用 — 最后一层保险：
      - 防止通道编译后数值越界
      - 防止扩散引擎读取到非法浮点数
    """
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def _lerp(a: float, b: float, t: float) -> float:
    t = _clamp01(t)
    return a + (b - a) * t


def _smoothstep(u: float) -> float:
    u = _clamp01(u)
    return u * u * (3.0 - 2.0 * u)


def compute_pad_scale(
    key: str,
    P: float,
    A: float,
    D: float,
    pad_weights: dict[str, tuple[float, float, float]] | None = None,
    base_scale: dict[str, float] | None = None,
) -> float:
    """PAD 动态投影：返回通道放大权重（≥0）。

    Args:
        key: 通道名
        P, A, D: PAD 情绪维度
        pad_weights: 物种专用 PAD 权重表
        base_scale: 物种专用基础 scale
    """
    _PAD_DEFAULT: dict[str, tuple[float, float, float]] = {}
    _BASE_DEFAULT: dict[str, float] = {}
    pw = pad_weights if pad_weights is not None else _PAD_DEFAULT
    bs = base_scale if base_scale is not None else _BASE_DEFAULT
    Wp, Wa, Wd = pw.get(key, (0.0, 0.3, 0.2))
    base = bs.get(key, 0.30)
    s = base + P * Wp + A * Wa + D * Wd
    return max(0.0, s)


# 别名：旧名向后兼容
_compute_pad_scale = compute_pad_scale


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


def _hold_texture(u: float, hold: HoldSegment, *, tremble_amp: float) -> float:
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
