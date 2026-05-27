"""
风格/人格/品种动态合成 — 公共层

合同公式（不改 E(t)，只改 12 通道 pulse → styled）::

    styled[ch, t] = clamp01( base_offset[ch] + scale_factor[ch] × pulse[ch, t] )

人格（human）与品种（cat/dog）共用此函数；差异仅在 base/scale 数据来源。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaze_engine._shared.envelope_compile import clamp_to_safe_range

_PKG = Path(__file__).resolve().parents[2]
_STYLE_ROOT = _PKG / "预设资产" / "风格包"


def apply_style_offset(
    channels: dict[str, list[float]],
    base_offset: dict[str, float],
    scale_factor: dict[str, float],
    *,
    channel_keys: list[str] | None = None,
) -> dict[str, list[float]]:
    """pulse → styled；不改变序列长度（应为 150）。"""
    if not channels:
        return channels
    frame_count = len(next(iter(channels.values())))
    keys = channel_keys or sorted(set(channels) | set(base_offset) | set(scale_factor))
    out: dict[str, list[float]] = {}
    for ch in keys:
        series = channels.get(ch, [0.0] * frame_count)
        base = float(base_offset.get(ch, 0.5))
        scale = float(scale_factor.get(ch, 0.1))
        out[ch] = [
            clamp_to_safe_range(base + scale * float(v))
            for v in series[:frame_count]
        ]
    return out


def load_style_json(species: str, style_id: str) -> dict[str, Any] | None:
    """读 预设资产/风格包/{species}/{style_id}/style.json"""
    if not style_id or style_id in ("default", ""):
        return None
    path = _STYLE_ROOT / species / style_id / "style.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def style_offsets_from_dict(style: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    bo = {k: float(v) for k, v in (style.get("base_offset") or {}).items()}
    sf = {k: float(v) for k, v in (style.get("scale_factor") or {}).items()}
    return bo, sf


def apply_style_id(
    channels: dict[str, list[float]],
    species: str,
    style_id: str,
    *,
    channel_keys: list[str] | None = None,
) -> tuple[dict[str, list[float]], str]:
    """若 style_id 有效则叠 styled，否则原样返回。返回 (channels, applied_id)。"""
    raw = load_style_json(species, style_id)
    if raw is None:
        return channels, ""
    bo, sf = style_offsets_from_dict(raw)
    return apply_style_offset(channels, bo, sf, channel_keys=channel_keys), style_id
