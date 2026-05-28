#!/usr/bin/env python3
"""狗 150 帧全量编译合同 · P0 结构验收（对应上篇 §5.1）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gaze_engine._shared.channel_contract import validate_baked_delivery
from gaze_engine._shared.envelope_compile import build_energy_envelope, export_envelope_series
from gaze_engine._shared.emotion_pad import resolve_pad
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine._shared.style_compose import apply_style_offset
from gaze_engine.dog.breeds import get_dog_breed
from gaze_engine.dog.dog_pipeline import run_dog_pipeline
from gaze_engine.dog.envelope_compile import DOG_CHANNELS, channels_from_envelope
from gaze_engine.dog.pad_weights import DOG_BASE_SCALE, DOG_PAD_WEIGHTS


def _load_packet(name: str = "委屈·幼犬眼") -> SliderPacket:
    p = ROOT / "预设资产" / "情绪包" / "dog" / f"{name}.json"
    return SliderPacket.from_dict(json.loads(p.read_text(encoding="utf-8")))


def verify_s2(pkt: SliderPacket) -> None:
    e = build_energy_envelope(pkt, 150)
    assert len(e) == 150, f"S2: envelope len {len(e)}"
    assert abs(e[-1]) < 0.02, f"S2: E[149]={e[-1]}"


def verify_s3_s4(pkt: SliderPacket) -> dict[str, list[float]]:
    P, A, D = resolve_pad(pkt)
    env = build_energy_envelope(pkt, 150)
    pulse = channels_from_envelope(
        pkt, env, P=P, A=A, D=D,
        frame_count=150,
        canonical_keys=DOG_CHANNELS,
        pad_weights=DOG_PAD_WEIGHTS,
        base_scale=DOG_BASE_SCALE,
    )
    assert set(pulse.keys()) == set(DOG_CHANNELS), "S4: channel keys"
    for ch in DOG_CHANNELS:
        assert len(pulse[ch]) == 150, f"S4: {ch} len"
    return pulse


def verify_s5(pulse: dict[str, list[float]], breed_id: str = "poodle_giant") -> None:
    cfg = get_dog_breed(breed_id)
    styled = apply_style_offset(
        pulse, cfg["base_offset"], cfg["scale_factor"], channel_keys=DOG_CHANNELS
    )
    for ch in DOG_CHANNELS:
        for t in range(150):
            expect = max(0.0, min(1.0, cfg["base_offset"][ch] + cfg["scale_factor"][ch] * pulse[ch][t]))
            assert abs(styled[ch][t] - expect) < 1e-5, f"S5: {ch}@{t}"


def verify_s7(name: str = "委屈·幼犬眼") -> None:
    pkt = _load_packet(name)
    baked, _, rep = run_dog_pipeline(pkt, breed_id="poodle_giant", narrative_action="回头看了一眼")
    rem = validate_baked_delivery(baked, DOG_CHANNELS, 150)
    assert not rem, f"S7: validation {rem}"
    assert baked.get("style_layer") == "styled"
    assert rep.dog_prior_skipped is False
    assert rep.dog_quality_skipped is False
    tracks = baked.get("channel_tracks") or {}
    n = sum(len(tracks.get(ch, {}).get("keyframes", [])) for ch in DOG_CHANNELS)
    assert n == 12 * 150, f"S7: keyframe count {n}"


def main() -> int:
    pkt = _load_packet()
    meta = export_envelope_series(pkt)
    print(f"[S2] peak={meta['peak_level']:.4f}")
    verify_s2(pkt)
    pulse = verify_s3_s4(pkt)
    verify_s5(pulse)
    verify_s7()
    print("OK: 狗150帧全量编译合同 P0 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
