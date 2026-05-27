"""
狗物种 — 专属通道编译。

与人类版的区别：
  - 去掉 eyebrow 滞后逻辑（狗的 eyebrow 通道 = 耳位，由 channel_adapter 处理）
  - 去掉 _apply_pulse_hold_coupling（人类特有生理耦合）
  - channels_from_packet 内部自动调用 channel_adapter 注入耳位
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# 狗 12 通道定义（渲染管线接口标准）
DOG_CHANNELS = [
    "pupil_x", "pupil_y", "blink", "eyebrow",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# ── 狗物种微颤动偏置 ──
# 社交动物生理：巩膜暴露多 → 保持段抖动幅度更大，频率稍低
_DOG_JITTER_BIAS = {"hz": -2.0, "amplitude": 0.006}

# 通道增益 / 相位滞后 — 解耦「整脸同步拉伸」
_DOG_CHANNEL_GAIN: dict[str, float] = {
    "pupil_scale": 0.82,
    "iris_scale": 0.71,
    "cornea_bulge": 0.58,
    "squint": 1.10,
    "brow_raise": 0.68,
    "lid_upper": 1.08,
    "lid_lower": 0.76,
    "eye_gloss": 0.42,
}

_DOG_CHANNEL_LAG: dict[str, int] = {
    "pupil_scale": 0,
    "iris_scale": 3,
    "cornea_bulge": 6,
    "squint": 2,
    "brow_raise": 4,
    "lid_upper": 2,
    "lid_lower": 5,
    "eye_gloss": 7,
}


def _sample_lagged(envelope: list[float], t: int, lag: int) -> float:
    src = max(0, t - lag)
    return envelope[src] if src < len(envelope) else 0.0


def _dog_blink_series(
    packet: SliderPacket,
    frame_count: int,
    scale: float,
    tm: dict[str, int],
) -> list[float]:
    """多点位眨眼：启动 / 保持段转折 / 缓和前（委屈+tremble 加强）。"""
    series = [0.0] * frame_count
    hs = packet.hold_seg
    hold_len = max(1, tm["t_hold1"] - tm["t_hold0"])

    anchors = [
        tm["t_peak"] + 1,
        tm["t_hold0"] + int(hold_len * 0.28),
        tm["t_hold0"] + int(hold_len * 0.52),
        min(frame_count - 6, tm["t_hold1"] - 8),
    ]
    if hs.shape == "tremble":
        anchors.append(tm["t_hold0"] + int(hold_len * 0.72))

    peak = 0.13 * scale
    emo = packet.emotion or ""
    if any(k in emo for k in ("委屈", "可怜", "渴望")):
        peak = 0.17 * scale
    if hs.shape == "tremble":
        peak *= 1.12

    for t0 in sorted(set(anchors)):
        if t0 < 3 or t0 >= frame_count - 4:
            continue
        for dt, frac in ((0, 0.0), (1, 0.72), (2, 1.0), (3, 0.58), (4, 0.0)):
            t = t0 + dt
            if 0 <= t < frame_count:
                v = clamp_to_safe_range(peak * frac)
                series[t] = max(series[t], v)
    return series


def _apply_moist_sad_baseline(
    channels: dict[str, list[float]],
    packet: SliderPacket,
    frame_count: int,
    tm: dict[str, int],
) -> None:
    """委屈类：保持段半阖眼睑 + 湿润高光基线。"""
    emo = packet.emotion or ""
    if not any(k in emo for k in ("委屈", "可怜", "渴望")):
        return
    t0, t1 = tm["t_hold0"], tm["t_hold1"]
    for t in range(max(0, t0), min(frame_count, t1 + 1)):
        u = (t - t0) / max(1, t1 - t0)
        droop = 0.07 + 0.05 * u
        channels["squint"][t] = clamp_to_safe_range(channels["squint"][t] + droop)
        channels["lid_upper"][t] = clamp_to_safe_range(channels["lid_upper"][t] + droop * 0.85)
        channels["lid_lower"][t] = clamp_to_safe_range(channels["lid_lower"][t] + droop * 0.35)
        channels["eye_gloss"][t] = clamp_to_safe_range(channels["eye_gloss"][t] + 0.04 + 0.05 * u)


def _apply_tremble_hold_coupling(
    packet: SliderPacket,
    channels: dict[str, list[float]],
    envelope: list[float],
    frame_count: int,
    tm: dict[str, int],
) -> None:
    """tremble 保持段：各通道不同幅度微颤，避免同步。"""
    if packet.hold_seg.shape != "tremble":
        return
    from gaze_engine._shared.envelope_compile import _hold_texture

    t0, t1 = tm["t_hold0"], tm["t_hold1"]
    hold_len = max(1, t1 - t0)
    for t in range(max(0, t0), min(frame_count, t1 + 1)):
        u = (t - t0) / hold_len
        rip = _hold_texture(u, packet.hold_seg, tremble_amp=1.0) - 1.0
        amp = envelope[t] if t < len(envelope) else 0.0
        channels["pupil_y"][t] = clamp_to_safe_range(
            channels["pupil_y"][t] + rip * amp * 0.09
        )
        channels["squint"][t] = clamp_to_safe_range(
            channels["squint"][t] + abs(rip) * amp * 0.14
        )
        channels["pupil_scale"][t] = clamp_to_safe_range(
            channels["pupil_scale"][t] + rip * amp * 0.07
        )
        channels["iris_scale"][t] = clamp_to_safe_range(
            channels["iris_scale"][t] + rip * amp * 0.04
        )
        channels["lid_lower"][t] = clamp_to_safe_range(
            channels["lid_lower"][t] + abs(rip) * amp * 0.06
        )
        channels["eye_gloss"][t] = clamp_to_safe_range(
            channels["eye_gloss"][t] + abs(rip) * amp * 0.03
        )

def _dog_jitter_block(profile: str = "cool_restrained") -> dict:
    """狗微颤动块：在共享预设上叠加狗生理偏置。"""
    from gaze_engine._shared.micro_jitter import default_micro_jitter_block
    block = default_micro_jitter_block(profile)
    for ph, vals in block["by_phase"].items():
        if vals["hz"] > 0:
            vals["hz"] = round(vals["hz"] + _DOG_JITTER_BIAS["hz"], 1)
        if vals["amplitude"] > 0:
            vals["amplitude"] = round(vals["amplitude"] + _DOG_JITTER_BIAS["amplitude"], 5)
    return block

from gaze_engine._shared.envelope_compile import (
    FRAME_COUNT_DEFAULT,
    FPS_DEFAULT,
    _direction,
    _lerp,
    _timing,
    build_energy_envelope,
    compute_pad_scale,
)
from gaze_engine._shared.envelope_compile import clamp_to_safe_range
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine.dog.channel_adapter import inject_ear_into_channels
from gaze_engine.dog.pad_weights import DOG_BASE_SCALE, DOG_PAD_WEIGHTS


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
    """E(t) × PAD → 狗 12 轨全量（不含人类 eyebrow 滞后，耳位由 channel_adapter 注入）。

    Args:
        packet:   滑杆包
        envelope: 能量包络序列 (150 帧)
        P:        愉悦度 [-1.0, 1.0]
        A:        激活度 [-1.0, 1.0]
        D:        控制度 [-1.0, 1.0]
        frame_count: 帧数 (默认 150)
        canonical_keys: 物种通道列表（默认 12 通道）
        pad_weights:    物种 PAD 权重表（默认狗）
        base_scale:     物种基础 scale（默认狗）
    """
    if canonical_keys is None:
        canonical_keys = DOG_CHANNELS
    if pad_weights is None:
        pad_weights = DOG_PAD_WEIGHTS  # type: ignore[arg-type]
    if base_scale is None:
        base_scale = DOG_BASE_SCALE  # type: ignore[arg-type]
    P = max(-1.0, min(1.0, P))
    A = max(-1.0, min(1.0, A))
    D = max(-1.0, min(1.0, D))

    pkt = packet.clamped()
    m = pkt.macro
    sign, y_bias = _direction(pkt)
    tm = _timing(pkt, frame_count)

    pad_scale: Dict[str, float] = {}
    for key in canonical_keys:
        pad_scale[key] = compute_pad_scale(key, P, A, D, pad_weights, base_scale)

    px_scale = pad_scale["pupil_x"]
    py_scale = pad_scale["pupil_y"]
    px = [sign * e * px_scale for e in envelope]
    py = [(y_bias * e + sign * 0.08 * e) * py_scale for e in envelope]

    blink_series = _dog_blink_series(pkt, frame_count, pad_scale["blink"], tm)

    result: Dict[str, list[float]] = {}

    for key in canonical_keys:
        s = pad_scale[key]
        if key == "pupil_x":
            series = [clamp_to_safe_range(px[t]) for t in range(frame_count)]
        elif key == "pupil_y":
            series = [clamp_to_safe_range(py[t]) for t in range(frame_count)]
        elif key == "blink":
            series = list(blink_series)
        elif key in _DOG_CHANNEL_GAIN:
            gain = _DOG_CHANNEL_GAIN[key]
            lag = _DOG_CHANNEL_LAG.get(key, 0)
            series = [
                clamp_to_safe_range(_sample_lagged(envelope, t, lag) * s * gain)
                for t in range(frame_count)
            ]
        else:
            series = [clamp_to_safe_range(e * s) for e in envelope]
        result[key] = series

    _apply_tremble_hold_coupling(pkt, result, envelope, frame_count, tm)
    _apply_moist_sad_baseline(result, pkt, frame_count, tm)

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
        "micro_jitter": _dog_jitter_block(profile),
        "gaze_emotion_id": pkt.emotion,
        "channel_tracks": {},
    }
    tm = _timing(pkt, frame_count)
    sparse_stub["channel_tracks"]["pupil_x"] = {
        "keyframes": [
            {"t": 0, "phase": "蓄力"},
            {"t": tm["t_peak"], "phase": "启动"},
            {"t": tm["t_hold0"], "phase": "保持"},
            {"t": tm["t_hold1"], "phase": "缓和"},
        ]
    }

    jitter_cfg = resolve_jitter_config(sparse_stub, frame_count, FPS_DEFAULT)
    if jitter_cfg.get("enabled"):
        for ch in jitter_cfg.get("channels", []):
            if ch in result:
                result[ch] = apply_jitter_to_series(result[ch], jitter_cfg, ch)

    for key in canonical_keys:
        result[key] = [clamp_to_safe_range(v) for v in result[key]]

    assert set(result.keys()) == set(canonical_keys), (
        f"输出缺少通道: {set(canonical_keys) - set(result.keys())}"
    )
    return result


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
    """狗完整管线：包络 → PAD 投影 → 耳位注入。"""
    env = build_energy_envelope(packet, frame_count)
    ch = channels_from_envelope(packet, env, P, A, D, frame_count,
                                canonical_keys, pad_weights, base_scale)
    # 狗的 eyebrow/brow_raise 由 EarParams 注入替换
    if packet.ear is not None:
        ch = inject_ear_into_channels(ch, packet.ear)
    return ch


def make_delivery_stub(
    packet: SliderPacket,
    channels: dict[str, list[float]],
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    label: str = "",
) -> dict[str, Any]:
    """狗 02 上下文 stub。"""

    pkt = packet.clamped()
    tm = _timing(pkt, frame_count)
    px = channels.get("pupil_x") or []

    profile = "cool_restrained"
    if pkt.hold_seg.shape == "tremble":
        profile = "agitated"
    elif pkt.macro.power < 35:
        profile = "tender"

    return {
        "_comment": "狗版—滑杆能量包络出厂",
        "schema_version": "0.3-dog-envelope-stub",
        "revision": f"dog-envelope:{label or pkt.emotion}",
        "_compile_mode": "envelope-v1-dog",
        "gaze_emotion_id": label or pkt.emotion,
        "mood": pkt.emotion,
        "energy_phases": ["蓄力", "启动", "保持", "缓和"],
        "controls_doc": "contracts/滑杆规范.md",
        "keys": list(DOG_CHANNELS),
        "keys_active": list(DOG_CHANNELS),
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
                    {"t": tm["t_peak"], "v": px[tm["t_peak"]] if len(px) > tm["t_peak"] else 0.0, "phase": "启动"},
                    {"t": tm["t_settle"], "v": px[tm["t_settle"]] if len(px) > tm["t_settle"] else 0.0, "phase": "启动"},
                    {"t": tm["t_hold1"], "v": px[min(tm["t_hold1"], len(px) - 1)] if px else 0.0, "phase": "保持"},
                    {"t": frame_count - 1, "v": px[-1] if px else 0.0, "phase": "缓和"},
                ]
            }
        },
        "micro_jitter": _dog_jitter_block(profile),
    }