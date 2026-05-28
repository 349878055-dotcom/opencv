"""
人类物种 — 专属通道编译。

从 _shared/envelope_compile.py 拆分而来，含人类特有的：
  - eyebrow 滞后跟随（D 轴驱动）
  - pulse 盯住段耦合（eyebrow/squint/pupil_scale）
  - 人类 12 通道默认配置
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# 人类 12 通道定义（渲染管线接口标准）
HUMAN_CHANNELS = [
    "pupil_x", "pupil_y", "blink", "eyebrow",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# ── 人类物种微颤动偏置 ──
# 人类为基准物种，偏置为零（生理基线）
_HUMAN_JITTER_BIAS = {"hz": 0.0, "amplitude": 0.0}

def _human_jitter_block(profile: str = "cool_restrained") -> dict:
    """人类微颤动块：直接使用共享预设（人类是生理基线）。"""
    from gaze_engine._shared.micro_jitter import default_micro_jitter_block
    return default_micro_jitter_block(profile)

from gaze_engine._shared.envelope_compile import (
    FRAME_COUNT_DEFAULT,
    FPS_DEFAULT,
    _direction,
    _hold_texture,
    _lerp,
    _timing,
    build_energy_envelope,
    compute_pad_scale,
)
from gaze_engine._shared.envelope_compile import clamp_to_safe_range
from gaze_engine._shared.slider_schema import HoldSegment, SliderPacket
from gaze_engine.human.pad_weights import HUMAN_BASE_SCALE, HUMAN_PAD_WEIGHTS


def channels_from_envelope(
    packet: SliderPacket,
    envelope: list[float],
    P: float = 0.0,
    A: float = 0.0,
    D: float = 0.0,
    frame_count: int = FRAME_COUNT_DEFAULT,
    canonical_keys: list[str] | None = None,
    pad_weights: dict[str, tuple[float, float, float]] | None = None,
    base_scale: dict[str, float] | None = None,
) -> dict[str, list[float]]:
    """E(t) × PAD → 人类 12 轨全量（含人类特有的 eyebrow 滞后 + 微颤）。

    Args:
        packet:   滑杆包
        envelope: 能量包络序列 (150 帧)
        P:        愉悦度 [-1.0, 1.0]
        A:        激活度 [-1.0, 1.0]
        D:        控制度 [-1.0, 1.0]
        frame_count: 帧数 (默认 150)
        canonical_keys: 物种通道列表（默认人类 12 通道）
        pad_weights:    物种 PAD 权重表（默认人类）
        base_scale:     物种基础 scale（默认人类）
    """
    if canonical_keys is None:
        canonical_keys = HUMAN_CHANNELS
    if pad_weights is None:
        pad_weights = HUMAN_PAD_WEIGHTS  # type: ignore[arg-type]
    if base_scale is None:
        base_scale = HUMAN_BASE_SCALE  # type: ignore[arg-type]
    # 钳位 PAD 到合法范围
    P = max(-1.0, min(1.0, P))
    A = max(-1.0, min(1.0, A))
    D = max(-1.0, min(1.0, D))

    pkt = packet.clamped()
    m = pkt.macro
    sign, y_bias = _direction(pkt)
    tm = _timing(pkt, frame_count)

    # ── D 轴驱动的眉滞后（人类特有） ──
    # D < 0（防御/羞涩）→ 滞后变长；D ≥ 0 → 沿用 speed 驱动
    if D < 0.0:
        lag = max(2, int(round(-D * 12.0)))
    else:
        lag = int(round(_lerp(12, 6, m.speed / 100.0)))

    # ── 逐通道动态投影 scale ──
    pad_scale: Dict[str, float] = {}
    for key in canonical_keys:
        pad_scale[key] = compute_pad_scale(key, P, A, D, pad_weights, base_scale)

    # ── 瞳孔方向（受 PAD 动态投影影响） ──
    px_scale = pad_scale["pupil_x"]
    py_scale = pad_scale["pupil_y"]
    px = [sign * e * px_scale for e in envelope]
    py = [(y_bias * e + sign * 0.08 * e) * py_scale for e in envelope]

    # ── 逐通道生成 ──
    result: Dict[str, list[float]] = {}

    for key in canonical_keys:
        s = pad_scale[key]
        if key == "pupil_x":
            series = [clamp_to_safe_range(px[t]) for t in range(frame_count)]
        elif key == "pupil_y":
            series = [clamp_to_safe_range(py[t]) for t in range(frame_count)]
        elif key == "eyebrow":
            # 人类特有：眉；D 驱动的滞后跟随
            series = [0.0] * frame_count
            for t in range(frame_count):
                src = max(0, t - lag)
                val = abs(px[src]) * s
                series[t] = clamp_to_safe_range(val)
        elif key == "blink":
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
    from gaze_engine._shared.micro_jitter import (
        apply_jitter_to_series,
        resolve_jitter_config,
    )

    profile = "cool_restrained"
    if pkt.hold_seg.shape == "tremble":
        profile = "agitated"
    elif m.power < 35:
        profile = "tender"

    sparse_stub = {
        "micro_jitter": _human_jitter_block(profile),
        "gaze_emotion_id": pkt.emotion,
        "channel_tracks": {},
    }
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
        for ch in jitter_cfg.get("channels", []):
            if ch in result:
                result[ch] = apply_jitter_to_series(result[ch], jitter_cfg, ch)

    # ── 最终安全钳位（二次保险） ──
    for key in canonical_keys:
        result[key] = [clamp_to_safe_range(v) for v in result[key]]

    # ── 防御校验 ──
    assert set(result.keys()) == set(canonical_keys), (
        f"输出缺少通道: {set(canonical_keys) - set(result.keys())}"
    )
    return result


def _apply_pulse_hold_coupling(
    packet: SliderPacket,
    channels: dict[str, list[float]],
    envelope: list[float],
    frame_count: int,
) -> None:
    """人类特有：pulse 盯住段 — 眉/眯/瞳附加强耦合。"""
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
    canonical_keys: list[str] | None = None,
    pad_weights: dict[str, tuple[float, float, float]] | None = None,
    base_scale: dict[str, float] | None = None,
) -> dict[str, list[float]]:
    """人类完整管线：包络 → PAD 投影 → 脉冲耦合。"""
    env = build_energy_envelope(packet, frame_count)
    ch = channels_from_envelope(packet, env, P, A, D, frame_count,
                                canonical_keys, pad_weights, base_scale)
    _apply_pulse_hold_coupling(packet, ch, env, frame_count)
    return ch


def make_delivery_stub(
    packet: SliderPacket,
    channels: dict[str, list[float]],
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    label: str = "",
) -> dict[str, Any]:
    """人类 02 上下文 stub（for human_prior / 烘焙）。"""

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
        "controls_doc": "合同/滑杆规范.md",
        "keys": list(HUMAN_CHANNELS),
        "keys_active": list(HUMAN_CHANNELS),
        "slider_packet": pkt.to_dict(),
        "energy_envelope": {
            "schema": "energy-envelope-v1",
            "frame_count": frame_count,
            "fps": FPS_DEFAULT,
            "peak_level": round(max(px) if px else 0.0, 5),
            "timing": tm,
        },
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
        "micro_jitter": _human_jitter_block(profile),
    }