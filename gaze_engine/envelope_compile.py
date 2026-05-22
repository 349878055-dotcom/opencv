#!/usr/bin/env python3
"""
滑杆 → 能量包络 E(t) → PAD 动态投影 → 12×150 全量通道（主出厂路径）。

PAD 投影公式（每一帧）：
  final_scale[ch] = base_scale[ch] + P×Wp[ch] + A×Wa[ch] + D×Wd[ch]
  channel[t] = clamp01(final_scale[ch] × envelope[t])
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from gaze_engine.channel_contract import CANONICAL_KEYS
from gaze_engine.slider_schema import HoldSegment, SliderPacket
from gaze_engine.persona_compiler import clamp_to_safe_range

FRAME_COUNT_DEFAULT = 150
FPS_DEFAULT = 30


# ──────────────────────────────────────────────
# 硬编码 PAD 骨骼权重（审美铁律）
# ──────────────────────────────────────────────
# final_scale = Wp*P + Wa*A + Wd*D
# 每个通道三元组 (Wp, Wa, Wd)
_PAD_WEIGHTS: Dict[str, tuple[float, float, float]] = {
    "pupil_x":      (0.0,  0.50,  0.40),  # 高 A/D → 眼神向前聚焦（"迎"）
    "pupil_y":      (0.0,  0.50,  0.40),
    "blink":        (0.0,  0.30,  0.10),
    "eyebrow":      (0.0,  0.30, -0.35),  # D 负 → 负负得正 → 眉压下（"拒"）
    "pupil_scale":  (0.10, 0.30,  0.20),
    "iris_scale":   (0.10, 0.20,  0.10),
    "cornea_bulge": (0.0,  0.40,  0.30),
    "squint":       (0.10, 0.35,  0.20),
    "brow_raise":   (0.10, 0.20, -0.20),  # 低 D → 挑眉抬起
    "lid_upper":    (0.0,  0.50,  0.40),  # 高 A/D → 上眼睑紧张
    "lid_lower":    (0.0,  0.30,  0.20),
    "eye_gloss":    (0.30, 0.10,  0.0),   # 高 P → 湿润光泽
}

# 基础 scale（无 PAD 影响时的中性值）
_BASE_SCALE: Dict[str, float] = {k: 0.30 for k in CANONICAL_KEYS}


def _clamp01(u: float) -> float:
    return 0.0 if u <= 0.0 else 1.0 if u >= 1.0 else u


def _lerp(a: float, b: float, t: float) -> float:
    t = _clamp01(t)
    return a + (b - a) * t


def _smoothstep(u: float) -> float:
    u = _clamp01(u)
    return u * u * (3.0 - 2.0 * u)


def _compute_pad_scale(key: str, P: float, A: float, D: float) -> float:
    """PAD 动态投影：返回通道放大权重（≥0，不钳位上限让包络自然限制）。"""
    Wp, Wa, Wd = _PAD_WEIGHTS.get(key, (0.0, 0.3, 0.2))
    base = _BASE_SCALE.get(key, 0.30)
    s = base + P * Wp + A * Wa + D * Wd
    return max(0.0, s)


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


# ──────────────────────────────────────────────
# 核心：PAD 动态投影编译
# ──────────────────────────────────────────────


def channels_from_envelope(
    packet: SliderPacket,
    envelope: list[float],
    P: float = 0.0,
    A: float = 0.0,
    D: float = 0.0,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> dict[str, list[float]]:
    """E(t) × PAD → 12 轨全量（动态投影 + 微颤 + 安全钳位）。

    Args:
        packet:   滑杆包
        envelope: 能量包络序列 (150 帧)
        P:        愉悦度 [-1.0, 1.0]
        A:        激活度 [-1.0, 1.0]
        D:        控制度 [-1.0, 1.0]
        frame_count: 帧数 (默认 150)
    """
    # 钳位 PAD 到合法范围
    P = max(-1.0, min(1.0, P))
    A = max(-1.0, min(1.0, A))
    D = max(-1.0, min(1.0, D))

    pkt = packet.clamped()
    m = pkt.macro
    sign, y_bias = _direction(pkt)
    tm = _timing(pkt, frame_count)

    # ── D 轴驱动的眉滞后 ──
    # D < 0 (防御/羞涩) → 滞后变长；D ≥ 0 → 沿用 speed 驱动
    if D < 0.0:
        lag = max(2, int(round(-D * 12.0)))
    else:
        lag = int(round(_lerp(12, 6, m.speed / 100.0)))

    # ── 逐通道动态投影 scale ──
    pad_scale: Dict[str, float] = {}
    for key in CANONICAL_KEYS:
        pad_scale[key] = _compute_pad_scale(key, P, A, D)

    # ── 瞳孔方向（受 PAD 动态投影影响） ──
    # 高 A/D → 眼神聚焦幅度放大；高 P + 低 D → 收敛柔和
    px_scale = pad_scale["pupil_x"]
    py_scale = pad_scale["pupil_y"]
    px = [sign * e * px_scale for e in envelope]
    py = [(y_bias * e + sign * 0.08 * e) * py_scale for e in envelope]

    # ── 逐通道生成 ──
    result: Dict[str, list[float]] = {}

    for key in CANONICAL_KEYS:
        s = pad_scale[key]
        if key == "pupil_x":
            series = [clamp_to_safe_range(px[t]) for t in range(frame_count)]
        elif key == "pupil_y":
            series = [clamp_to_safe_range(py[t]) for t in range(frame_count)]
        elif key == "eyebrow":
            # 眉：D 驱动的滞后跟随
            series = [0.0] * frame_count
            for t in range(frame_count):
                src = max(0, t - lag)
                val = abs(px[src]) * s
                series[t] = clamp_to_safe_range(val)
        elif key == "blink":
            # 眨眼保留原逻辑
            series = [0.0] * frame_count
            t_blink = min(frame_count - 3, 86 + int(round(_lerp(2, -4, m.speed / 100.0))))
            for dt, v in ((0, 0.0), (1, 0.11 * s), (2, 0.14 * s), (3, 0.08 * s), (4, 0.0)):
                t = t_blink + dt
                if 0 <= t < frame_count:
                    series[t] = clamp_to_safe_range(v)
        else:
            # 通用：scale × envelope，直接钳位
            series = [clamp_to_safe_range(e * s) for e in envelope]
        result[key] = series

    # ── 注入生物微颤（micro_jitter） ──
    from gaze_engine.micro_jitter import (
        default_micro_jitter_block,
        resolve_jitter_config,
    )

    # 构建伪 sparse 字典让 jitter 可工作
    profile = "cool_restrained"
    if pkt.hold_seg.shape == "tremble":
        profile = "agitated"
    elif m.power < 35:
        profile = "tender"

    sparse_stub = {
        "micro_jitter": default_micro_jitter_block(profile),
        "gaze_emotion_id": pkt.emotion,
        "channel_tracks": {},
    }
    # 补齐 pupil_x 关键帧 phase 标签
    tm2 = tm
    sparse_stub["channel_tracks"]["pupil_x"] = {
        "keyframes": [
            {"t": 0, "phase": "蓄力"},
            {"t": tm2["t_peak"], "phase": "启动"},
            {"t": tm2["t_hold0"], "phase": "保持"},
            {"t": tm2["t_hold1"], "phase": "缓和"},
        ]
    }

    jitter_cfg = resolve_jitter_config(sparse_stub, frame_count, FPS_DEFAULT)
    if jitter_cfg.get("enabled"):
        from gaze_engine.micro_jitter import apply_jitter_to_series

        for ch in jitter_cfg.get("channels", []):
            if ch in result:
                result[ch] = apply_jitter_to_series(result[ch], jitter_cfg, ch)

    # ── 最终安全钳位（二次保险） ──
    for key in CANONICAL_KEYS:
        result[key] = [clamp_to_safe_range(v) for v in result[key]]

    # ── 防御校验 ──
    assert set(result.keys()) == set(CANONICAL_KEYS), (
        f"输出缺少通道: {set(CANONICAL_KEYS) - set(result.keys())}"
    )
    return result


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
        channels["pupil_x"][t] = clamp_to_safe_range(
            channels["pupil_x"][t] + sign * rip * amp * 0.38
        )
        channels["pupil_y"][t] = clamp_to_safe_range(
            channels["pupil_y"][t] + sign * rip * amp * 0.12
        )
        channels["eyebrow"][t] = clamp_to_safe_range(
            channels["eyebrow"][t] + abs(rip) * amp * 0.32
        )
        channels["squint"][t] = clamp_to_safe_range(
            channels["squint"][t] + abs(rip) * amp * 0.20
        )
        channels["pupil_scale"][t] = clamp_to_safe_range(
            channels["pupil_scale"][t] + rip * amp * 0.14
        )


def channels_from_packet(
    packet: SliderPacket,
    frame_count: int = FRAME_COUNT_DEFAULT,
    P: float = 0.0,
    A: float = 0.0,
    D: float = 0.0,
) -> dict[str, list[float]]:
    """完整管线：包络 → PAD 投影 → 脉冲耦合。

    PAD 默认 (0,0,0) = 中性情感，仅靠滑杆驱动。
    """
    env = build_energy_envelope(packet, frame_count)
    ch = channels_from_envelope(packet, env, P, A, D, frame_count)
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
