"""
猫物种 — 专属通道编译。

与人类版的区别：
  - 去掉 eyebrow 滞后（猫无独立眉毛肌，eyebrow 通道 = 耳位）
  - 使用猫 PAD 权重（CAT_PAD_WEIGHTS，含 ear_left/ear_right 权重）
  - 通道编译后自动调用 channel_adapter 注入耳位
"""
from __future__ import annotations

from typing import Any, Dict

# 猫 12 通道定义（渲染管线接口标准）
# 注意：猫内部用 13 通道（ear_left/ear_right 代替 eyebrow），
# 但 channel_adapter 映射回标准 12 通道的 eyebrow/brow_raise 槽位
CAT_CHANNELS = [
    "pupil_x", "pupil_y", "blink", "eyebrow",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# ── 猫物种微颤动偏置 ──
# 捕猎者生理：微扫视频率更高（警觉态基线更高）
_CAT_JITTER_BIAS = {"hz": 4.0, "amplitude": 0.003}

def _cat_jitter_block(profile: str = "cool_restrained") -> dict:
    """猫微颤动块：在共享预设上叠加猫生理偏置。"""
    from gaze_engine._shared.micro_jitter import default_micro_jitter_block
    block = default_micro_jitter_block(profile)
    for ph, vals in block["by_phase"].items():
        if vals["hz"] > 0:
            vals["hz"] = round(vals["hz"] + _CAT_JITTER_BIAS["hz"], 1)
        if vals["amplitude"] > 0:
            vals["amplitude"] = round(vals["amplitude"] + _CAT_JITTER_BIAS["amplitude"], 5)
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
from gaze_engine.cat.channel_adapter import inject_ear_into_channels
from gaze_engine.cat.pad_weights import CAT_BASE_SCALE, CAT_PAD_WEIGHTS


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
    """E(t) × PAD → 猫 12 轨全量（耳位由 channel_adapter 注入）。"""
    if canonical_keys is None:
        canonical_keys = CAT_CHANNELS
    if pad_weights is None:
        pad_weights = CAT_PAD_WEIGHTS  # type: ignore[arg-type]
    if base_scale is None:
        base_scale = CAT_BASE_SCALE  # type: ignore[arg-type]
    P = max(-1.0, min(1.0, P))
    A = max(-1.0, min(1.0, A))
    D = max(-1.0, min(1.0, D))

    pkt = packet.clamped()
    m = pkt.macro
    sign, y_bias = _direction(pkt)

    pad_scale: Dict[str, float] = {}
    for key in canonical_keys:
        pad_scale[key] = compute_pad_scale(key, P, A, D, pad_weights, base_scale)

    px_scale = pad_scale["pupil_x"]
    py_scale = pad_scale["pupil_y"]
    px = [sign * e * px_scale for e in envelope]
    py = [(y_bias * e + sign * 0.08 * e) * py_scale for e in envelope]

    result: Dict[str, list[float]] = {}

    for key in canonical_keys:
        s = pad_scale[key]
        if key == "pupil_x":
            series = [clamp_to_safe_range(px[t]) for t in range(frame_count)]
        elif key == "pupil_y":
            series = [clamp_to_safe_range(py[t]) for t in range(frame_count)]
        elif key == "blink":
            series = [0.0] * frame_count
            t_blink = min(frame_count - 3, 86 + int(round(_lerp(2, -4, m.speed / 100.0))))
            for dt, v in ((0, 0.0), (1, 0.11 * s), (2, 0.14 * s), (3, 0.08 * s), (4, 0.0)):
                t = t_blink + dt
                if 0 <= t < frame_count:
                    series[t] = clamp_to_safe_range(v)
        else:
            # ⭐ 所有其他通道统一用 scale × envelope
            # 猫 eyebrow/brow_raise 由 channel_adapter 注入耳位覆盖
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
        "micro_jitter": _cat_jitter_block(profile),
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
    """猫完整管线：包络 → PAD 投影 → 耳位注入。"""
    env = build_energy_envelope(packet, frame_count)
    ch = channels_from_envelope(packet, env, P, A, D, frame_count,
                                canonical_keys, pad_weights, base_scale)
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
    """猫 02 上下文 stub。"""

    pkt = packet.clamped()
    tm = _timing(pkt, frame_count)
    px = channels.get("pupil_x") or []

    profile = "cool_restrained"
    if pkt.hold_seg.shape == "tremble":
        profile = "agitated"
    elif pkt.macro.power < 35:
        profile = "tender"

    return {
        "_comment": "猫版—滑杆能量包络出厂",
        "schema_version": "0.3-cat-envelope-stub",
        "revision": f"cat-envelope:{label or pkt.emotion}",
        "_compile_mode": "envelope-v1-cat",
        "gaze_emotion_id": label or pkt.emotion,
        "mood": pkt.emotion,
        "energy_phases": ["蓄力", "启动", "保持", "缓和"],
        "controls_doc": "合同/滑杆规范.md",
        "keys": list(CAT_CHANNELS),
        "keys_active": list(CAT_CHANNELS),
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
        "micro_jitter": _cat_jitter_block(profile),
    }