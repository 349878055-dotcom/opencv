"""补针后微颤：按戏段(phase)自动叠噪声，频率/幅度可分段配置。"""
from __future__ import annotations

import hashlib
import math
import os
from typing import Any

ENERGY_PHASES = ("蓄力", "启动", "保持", "缓和")

# 情绪 profile → 默认「保持段」参数（by_phase 未写时用）
JITTER_PROFILES: dict[str, dict[str, float]] = {
    "cool_restrained": {"hz": 14.0, "amplitude": 0.010},
    "施压瞬间凝视": {"hz": 14.0, "amplitude": 0.011},
    "agitated": {"hz": 22.0, "amplitude": 0.018},
    "tender": {"hz": 10.0, "amplitude": 0.008},
    "default": {"hz": 16.0, "amplitude": 0.012},
}

# profile → 四段戏默认微颤（启动/蓄力一般为 0，避免盖住过冲）
PHASE_JITTER_BY_PROFILE: dict[str, dict[str, dict[str, float]]] = {
    "cool_restrained": {
        "蓄力": {"hz": 0, "amplitude": 0},
        "启动": {"hz": 0, "amplitude": 0},
        "保持": {"hz": 14, "amplitude": 0.011},
        "缓和": {"hz": 9, "amplitude": 0.006},
    },
    "agitated": {
        "蓄力": {"hz": 6, "amplitude": 0.004},
        "启动": {"hz": 0, "amplitude": 0},
        "保持": {"hz": 22, "amplitude": 0.016},
        "缓和": {"hz": 12, "amplitude": 0.010},
    },
    "tender": {
        "蓄力": {"hz": 0, "amplitude": 0},
        "启动": {"hz": 0, "amplitude": 0},
        "保持": {"hz": 10, "amplitude": 0.008},
        "缓和": {"hz": 7, "amplitude": 0.005},
    },
}

GAZE_CHANNELS = ("pupil_x", "pupil_y")

def default_micro_jitter_block(profile: str = "cool_restrained") -> dict[str, Any]:
    """新建 02 时的初始化块：补针阶段按 by_phase 自动叠噪（不手写每帧）。"""
    preset = PHASE_JITTER_BY_PROFILE.get(
        profile, PHASE_JITTER_BY_PROFILE["cool_restrained"]
    )
    return {
        "enabled": True,
        "profile": profile,
        "channels": list(GAZE_CHANNELS),
        "by_phase": {ph: dict(preset.get(ph, {"hz": 0, "amplitude": 0})) for ph in ENERGY_PHASES},
    }

def ensure_micro_jitter_init(sparse: dict) -> tuple[dict[str, Any], bool]:
    """缺省时注入 micro_jitter；返回 (sparse, 是否新写入)。"""
    block = sparse.get("micro_jitter")
    if isinstance(block, dict) and block.get("by_phase"):
        return sparse, False
    profile = str(
        (block or {}).get("profile")
        or sparse.get("profile_hint")
        or sparse.get("gaze_emotion_id")
        or "cool_restrained"
    )
    out = dict(sparse)
    out["micro_jitter"] = default_micro_jitter_block(profile)
    return out, True

def _enabled() -> bool:
    return os.environ.get("ECURSOR_MICRO_JITTER", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )

def _seed_from_sparse(sparse: dict) -> int:
    raw = (
        sparse.get("gaze_emotion_id")
        or sparse.get("template_id")
        or sparse.get("mood")
        or "ecursor"
    )
    h = hashlib.md5(str(raw).encode("utf-8")).hexdigest()
    return int(h[:8], 16)

def _phase_at_each_frame(sparse: dict, frame_count: int) -> list[str]:
    """用 pupil_x 关键帧上的 phase 标签，铺到每一帧。"""
    tracks = sparse.get("channel_tracks") or {}
    ref = tracks.get("pupil_x", {}).get("keyframes") or []
    if not ref:
        return ["保持"] * frame_count
    kfs = sorted(ref, key=lambda k: int(k["t"]))
    phases: list[str] = []
    seg_i = 0
    cur = str(kfs[0].get("phase") or "蓄力")
    for t in range(frame_count):
        while seg_i + 1 < len(kfs) and t >= int(kfs[seg_i + 1]["t"]):
            seg_i += 1
            cur = str(kfs[seg_i].get("phase") or cur)
        phases.append(cur if cur in ENERGY_PHASES else "保持")
    return phases

def _resolve_by_phase(
    block: dict,
    profile: str,
    base_hz: float,
    base_amp: float,
) -> dict[str, dict[str, float]]:
    """合并 02.micro_jitter.by_phase 与 profile 预设。"""
    preset = dict(PHASE_JITTER_BY_PROFILE.get(profile, PHASE_JITTER_BY_PROFILE["cool_restrained"]))
    custom = block.get("by_phase") or {}
    out: dict[str, dict[str, float]] = {}
    for ph in ENERGY_PHASES:
        row = dict(preset.get(ph, {"hz": 0, "amplitude": 0}))
        if ph in custom and isinstance(custom[ph], dict):
            row.update(custom[ph])
        # 仅写了顶层 hz/amplitude 时：落到「保持」段
        if ph == "保持" and "hz" not in (custom.get(ph) or {}) and block.get("hz") is not None:
            row["hz"] = float(block.get("hz", base_hz))
        if ph == "保持" and "amplitude" not in (custom.get(ph) or {}) and block.get("amplitude") is not None:
            row["amplitude"] = float(block.get("amplitude", base_amp))
        out[ph] = {
            "hz": float(row.get("hz", 0)),
            "amplitude": float(row.get("amplitude", row.get("amplitude_json", 0))),
        }
    return out

def _infer_hold_window(sparse: dict, frame_count: int) -> tuple[int, int]:
    """盯住段：启动段回弹后 → 缓和段之前（与 phase 标签可错开）。"""
    tracks = sparse.get("channel_tracks") or {}
    px = tracks.get("pupil_x", {}).get("keyframes") or []
    if not px:
        return 25, min(frame_count - 1, 110)
    rebound_t = 23
    for k in px:
        if k.get("phase") == "启动":
            rebound_t = max(rebound_t, int(k["t"]))
    ease_ts = [int(k["t"]) for k in px if k.get("phase") == "缓和"]
    end = (min(ease_ts) - 1) if ease_ts else min(frame_count - 1, 110)
    start = rebound_t + 2
    start = max(0, min(start, frame_count - 2))
    end = max(start + 1, min(end, frame_count - 1))
    return start, end

def _build_jitter_segments(
    sparse: dict,
    frame_count: int,
    phase_at: list[str],
    by_phase: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    """补针噪声段：盯住窗=保持参数；缓和段=缓和参数；蓄力/启动=0。"""
    segs: list[dict[str, Any]] = []
    hold_s, hold_e = _infer_hold_window(sparse, frame_count)
    p_hold = by_phase.get("保持", {"hz": 0, "amplitude": 0})
    if float(p_hold.get("hz", 0)) > 0 and float(p_hold.get("amplitude", 0)) > 0:
        segs.append(
            {
                "phase": "保持",
                "start": hold_s,
                "end": hold_e,
                "hz": float(p_hold["hz"]),
                "amplitude": float(p_hold["amplitude"]),
            }
        )
    ease_start = next((i for i, ph in enumerate(phase_at) if ph == "缓和"), frame_count)
    p_ease = by_phase.get("缓和", {"hz": 0, "amplitude": 0})
    if ease_start < frame_count and float(p_ease.get("amplitude", 0)) > 0:
        segs.append(
            {
                "phase": "缓和",
                "start": ease_start,
                "end": frame_count - 1,
                "hz": float(p_ease.get("hz", 0)),
                "amplitude": float(p_ease["amplitude"]),
            }
        )
    return segs

def _params_at_frame(t: int, cfg: dict[str, Any]) -> tuple[float, float]:
    for seg in cfg.get("segments") or []:
        if int(seg["start"]) <= t <= int(seg["end"]):
            return float(seg["hz"]), float(seg["amplitude"])
    return 0.0, 0.0

def resolve_jitter_config(
    sparse: dict,
    frame_count: int = 150,
    fps: int = 30,
) -> dict[str, Any]:
    block = sparse.get("micro_jitter") or {}
    if block.get("enabled") is False:
        return {"enabled": False}
    if not _enabled():
        return {"enabled": False}

    profile = str(
        block.get("profile")
        or sparse.get("profile_hint")
        or sparse.get("gaze_emotion_id")
        or "default"
    )
    base = dict(JITTER_PROFILES.get(profile, JITTER_PROFILES["default"]))
    base_hz = float(block.get("hz", base["hz"]))
    base_amp = float(block.get("amplitude", block.get("amplitude_json", base["amplitude"])))

    by_phase = _resolve_by_phase(block, profile, base_hz, base_amp)
    phase_at = _phase_at_each_frame(sparse, frame_count)
    segments = _build_jitter_segments(sparse, frame_count, phase_at, by_phase)
    channels = list(block.get("channels") or GAZE_CHANNELS)

    return {
        "enabled": True,
        "profile": profile,
        "fps": fps,
        "frame_count": frame_count,
        "channels": [c for c in channels if c in GAZE_CHANNELS],
        "seed": int(block.get("seed", _seed_from_sparse(sparse))),
        "by_phase": by_phase,
        "phase_at_frame": phase_at,
        "segments": segments,
        # 兼容旧日志
        "hz": base_hz,
        "amplitude": base_amp,
    }

def jitter_offset_at(
    t: int,
    hz: float,
    amp: float,
    cfg: dict[str, Any],
    channel: str,
    phase_mul: float = 1.0,
) -> float:
    if hz <= 0 or amp <= 0:
        return 0.0
    fps = float(cfg["fps"])
    seed = int(cfg["seed"])
    ch = 0.7 if channel == "pupil_x" else 1.3
    a = 2.0 * math.pi * hz * phase_mul * t / fps
    w1 = math.sin(a + seed % 97 + ch)
    w2 = 0.35 * math.sin(2.3 * a + (seed >> 3) % 53 + ch * 2.1)
    return amp * (w1 + w2)

def apply_jitter_to_series(
    series: list[float],
    cfg: dict[str, Any],
    channel: str,
) -> list[float]:
    if not cfg.get("enabled"):
        return series
    out = list(series)
    phase_mul = 1.0 if channel == "pupil_x" else 1.08
    for t in range(len(out)):
        hz, amp = _params_at_frame(t, cfg)
        out[t] += jitter_offset_at(t, hz, amp, cfg, channel, phase_mul)
    return out

def apply_jitter_to_channels(
    channels: dict[str, list[float]],
    sparse: dict,
    frame_count: int,
    fps: int = 30,
) -> tuple[dict[str, list[float]], dict[str, Any]]:
    cfg = resolve_jitter_config(sparse, frame_count, fps)
    if not cfg.get("enabled"):
        return channels, cfg
    out = dict(channels)
    for ch in cfg["channels"]:
        if ch in out:
            out[ch] = apply_jitter_to_series(out[ch], cfg, ch)
    return out, cfg

