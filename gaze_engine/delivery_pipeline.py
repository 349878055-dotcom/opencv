#!/usr/bin/env python3
"""
交付链：SliderPacket → 能量包络 E(t) → 全量 12×150 → 真人律 → 平庸修正 → 烘焙 02
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

_PKG = Path(__file__).resolve().parent.parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from gaze_engine._shared.channel_contract import validate_baked_delivery  # noqa: E402
from gaze_engine.human.human_prior import (  # noqa: E402
    FRAME_COUNT_DEFAULT,
    FPS_DEFAULT,
    PriorReport,
    apply_human_prior,
    dense_to_baked_sparse,
)
from gaze_engine.human.pulse_quality import PulseQualityReport, fix_pulse_quality  # noqa: E402
from gaze_engine._shared.slider_schema import SliderPacket  # noqa: E402

from gaze_engine._shared.emotion_pad import EMOTION_PAD, resolve_pad  # noqa: E402

_PIPELINE_DOC = "合同/全量帧指令集规范.md · envelope-v1"


def _emotion_pad(emotion: str, packet: SliderPacket | None = None) -> tuple[float, float, float]:
    """按情绪名查找 PAD；packet 含 pad 块时优先读资产。"""
    if packet is not None:
        return resolve_pad(packet)
    return EMOTION_PAD.get(emotion, (0.0, 0.0, 0.0))

def _packet_from_context(context: dict) -> SliderPacket | None:
    block = context.get("slider_packet")
    if isinstance(block, dict) and block.get("schema") == "slider-packet-v1":
        return SliderPacket.from_dict(block)
    return None

def run_delivery(
    context: dict[str, Any],
    packet: SliderPacket | None = None,
    *,
    channels_precomputed: dict[str, list[float]] | None = None,
    frame_count: int = FRAME_COUNT_DEFAULT,
    fps: int = FPS_DEFAULT,
    skip_human_prior: bool = False,
    style_id: str = "",
) -> tuple[dict[str, Any], dict[str, list[float]], PriorReport, PulseQualityReport]:
    draft = copy.deepcopy(context)
    pkt = packet or _packet_from_context(draft) or SliderPacket()
    from gaze_engine._shared.packet_finalize import finalize_packet

    pkt, fin_rep = finalize_packet(pkt)
    if fin_rep.changed:
        draft["slider_packet"] = pkt.to_dict()
        prev = list(draft.get("_finalize_fixes") or [])
        prev.extend(fin_rep.fixes)
        draft["_finalize_fixes"] = prev

    if channels_precomputed is not None:
        channels = {k: list(v[:frame_count]) for k, v in channels_precomputed.items()}
    else:
        from gaze_engine.human.envelope_compile import channels_from_packet

        P, A, D = _emotion_pad(pkt.emotion, pkt)
        channels = channels_from_packet(pkt, frame_count, P=P, A=A, D=D)

    sid = (style_id or pkt.style or "").strip()
    if sid and sid not in ("default",):
        from gaze_engine.human.persona_compiler import apply_persona_style

        channels = apply_persona_style(channels, sid)

    if skip_human_prior:
        rep = PriorReport(enabled=False)
        dense_out = channels
    else:
        dense_out, rep = apply_human_prior(
            channels, pkt, draft, frame_count=frame_count, fps=fps
        )

    dense_out, pq_rep = fix_pulse_quality(
        dense_out, pkt, draft, frame_count=frame_count
    )

    baked = dense_to_baked_sparse(
        draft, dense_out, frame_count=frame_count, prior_report=rep
    )
    baked["slider_packet"] = pkt.to_dict()
    baked["delivery_pipeline"] = _PIPELINE_DOC
    baked["_compile_mode"] = "envelope-v1"
    if sid and sid not in ("default",):
        baked["persona"] = sid
        baked["style_layer"] = "styled"
    else:
        baked["style_layer"] = "pulse"
    if draft.get("energy_envelope"):
        baked["energy_envelope"] = draft["energy_envelope"]
    baked["pulse_quality_report"] = pq_rep.to_dict()
    if pq_rep.fixes:
        baked["_pulse_quality_fix_log"] = pq_rep.fixes
    if pq_rep.remaining:
        baked["_pulse_quality_remaining"] = pq_rep.remaining

    from gaze_engine.human.envelope_compile import HUMAN_CHANNELS
    remaining = validate_baked_delivery(baked, HUMAN_CHANNELS, frame_count)
    if remaining:
        baked["_delivery_validation_remaining"] = remaining

    return baked, dense_out, rep, pq_rep

def run_delivery_from_packet(
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    P: float | None = None,
    A: float | None = None,
    D: float | None = None,
    style_id: str = "",
) -> tuple[dict[str, Any], dict[str, list[float]], PriorReport, PulseQualityReport]:
    from gaze_engine.human.envelope_compile import channels_from_packet, make_delivery_stub

    if P is None or A is None or D is None:
        _P, _A, _D = resolve_pad(packet)
        if P is None: P = _P
        if A is None: A = _A
        if D is None: D = _D
    channels = channels_from_packet(packet, frame_count, P=P, A=A, D=D)
    stub = make_delivery_stub(
        packet, channels, frame_count=frame_count, label=packet.emotion
    )
    sid = (style_id or packet.style or "").strip()
    return run_delivery(stub, packet, channels_precomputed=channels, style_id=sid)


def _make_species_baked(
    packet: SliderPacket,
    channels: dict[str, list[float]],
    *,
    species: str,
    channel_keys: list[str],
    frame_count: int = FRAME_COUNT_DEFAULT,
    schema_version: str,
    report: dict | None = None,
    breed_id: str = "",
) -> dict[str, Any]:
    """狗/猫共用：channels → 02_烘焙 JSON（含稠密 channel_tracks）。"""
    from gaze_engine.dog.envelope_compile import make_delivery_stub as dog_stub
    from gaze_engine.cat.envelope_compile import make_delivery_stub as cat_stub

    if species == "cat":
        stub = cat_stub(packet, channels, frame_count=frame_count, label=packet.emotion)
    else:
        stub = dog_stub(packet, channels, frame_count=frame_count, label=packet.emotion)

    phases = ["蓄力", "启动", "保持", "缓和"]
    phase_map: dict[int, str] = {}
    for t in range(frame_count):
        if t < 14:
            phase_map[t] = "蓄力"
        elif t < 28:
            phase_map[t] = "启动"
        elif t < 110:
            phase_map[t] = "保持"
        else:
            phase_map[t] = "缓和"

    tracks: dict[str, dict[str, Any]] = {}
    for key in channel_keys:
        series = channels.get(key, [0.0] * frame_count)
        tracks[key] = {
            "keyframes": [
                {
                    "t": t,
                    "v": round(float(series[t]), 6),
                    "phase": phase_map.get(t, "保持"),
                    "easing": "linear",
                }
                for t in range(frame_count)
            ]
        }

    baked = dict(stub)
    baked.update({
        "schema_version": schema_version,
        "_baked_dense": True,
        "revision": f"{species}-pipeline:{packet.emotion}",
        "species": species,
        "channel_tracks": tracks,
        "energy_phases": phases,
        "slider_packet": packet.to_dict(),
    })
    if breed_id:
        baked["breed"] = breed_id
        baked["style_layer"] = "styled"
    elif species in ("dog", "cat"):
        baked["style_layer"] = "pulse"
    if report:
        baked[f"{species}_pipeline_report"] = report
    if isinstance(report, dict):
        if report.get("prior_report"):
            baked[f"{species}_prior_report"] = report["prior_report"]
        if report.get("pulse_quality_report"):
            baked["pulse_quality_report"] = report["pulse_quality_report"]
            if report["pulse_quality_report"].get("fixes"):
                baked["_pulse_quality_fix_log"] = report["pulse_quality_report"]["fixes"]
            if report["pulse_quality_report"].get("remaining"):
                baked["_pulse_quality_remaining"] = report["pulse_quality_report"]["remaining"]

    from gaze_engine._shared.channel_contract import validate_baked_delivery
    remaining = validate_baked_delivery(baked, channel_keys, frame_count)
    if remaining:
        baked["_delivery_validation_remaining"] = remaining
    return baked


def run_cat_pipeline(
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    breed_id: str = "",
) -> tuple[dict[str, Any], dict[str, list[float]], dict[str, Any]]:
    """猫完整管线（与 dog_pipeline 对称）。"""
    from gaze_engine._shared.envelope_compile import build_energy_envelope
    from gaze_engine.cat.envelope_compile import (
        CAT_CHANNELS,
        channels_from_envelope,
        channels_from_packet,
    )
    from gaze_engine.cat.pad_weights import CAT_BASE_SCALE, CAT_PAD_WEIGHTS

    pkt = packet.clamped()
    if pkt.ear is not None:
        channels = channels_from_packet(pkt, frame_count)
        ear_injected = True
    else:
        P, A, D = _emotion_pad(pkt.emotion, pkt)
        envelope = build_energy_envelope(pkt, frame_count)
        channels = channels_from_envelope(
            pkt, envelope, P=P, A=A, D=D,
            frame_count=frame_count,
            canonical_keys=CAT_CHANNELS,
            pad_weights=CAT_PAD_WEIGHTS,
            base_scale=CAT_BASE_SCALE,
        )
        ear_injected = False

    bid = (breed_id or "").strip()
    if bid and bid not in ("default",):
        from gaze_engine.cat.breeds import apply_breed_style

        channels = apply_breed_style(channels, bid)

    from gaze_engine.cat.prior import apply_cat_prior
    from gaze_engine.cat.pulse_quality import fix_cat_pulse_quality

    channels, prior_rep = apply_cat_prior(channels, pkt, frame_count=frame_count)
    pq = fix_cat_pulse_quality(channels, pkt, frame_count=frame_count)

    issues: list[str] = []
    issues.extend(prior_rep.issues)
    issues.extend(pq.fixes)
    issues.extend(pq.remaining)

    report = {
        "enabled": True,
        "emotion": pkt.emotion,
        "frame_count": frame_count,
        "ear_injected": ear_injected,
        "breed": bid or None,
        "style_layer": "styled" if bid else "pulse",
        "cat_prior_skipped": not prior_rep.enabled,
        "cat_quality_skipped": not pq.enabled,
        "prior_report": prior_rep.to_dict(),
        "pulse_quality_report": pq.to_dict(),
        "issues": issues,
    }
    baked = _make_species_baked(
        pkt, channels,
        species="cat",
        channel_keys=CAT_CHANNELS,
        frame_count=frame_count,
        schema_version="0.3-baked-cat",
        report=report,
        breed_id=bid,
    )
    return baked, channels, report


def run_species_delivery(
    packet: SliderPacket,
    species: str = "human",
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    narrative_action: str = "",
    breed_id: str = "",
    style_id: str = "",
) -> tuple[dict[str, Any], dict[str, list[float]], Any, Any]:
    """按物种路由：human → 真人律；dog/cat → 各自管线。"""
    sp = (species or "human").strip().lower()
    sid = (style_id or breed_id or "").strip()
    if sp == "dog":
        from gaze_engine.dog.dog_pipeline import run_dog_pipeline
        baked, dense, rep = run_dog_pipeline(
            packet,
            frame_count=frame_count,
            narrative_action=narrative_action,
            breed_id=sid or None,
        )
        return baked, dense, rep, rep
    if sp == "cat":
        baked, dense, rep = run_cat_pipeline(
            packet, frame_count=frame_count, breed_id=sid
        )
        return baked, dense, rep, rep
    baked, dense, rep, pq = run_delivery_from_packet(
        packet, frame_count=frame_count, style_id=sid
    )
    baked.setdefault("species", "human")
    return baked, dense, rep, pq


def write_delivery_json(baked: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    import argparse

    from asset_lib import ensure_dirs

    ap = argparse.ArgumentParser(description="滑杆包络 → 真人律 → 烘焙 02")
    ap.add_argument("--packet", required=True, help="SliderPacket JSON")
    ap.add_argument("-o", "--output", required=True, help="烘焙定稿 02 路径")
    ap.add_argument("--no-prior", action="store_true")
    args = ap.parse_args()

    ensure_dirs()
    packet = SliderPacket.from_dict(
        json.loads(Path(args.packet).read_text(encoding="utf-8"))
    )
    baked, _, rep, pq = run_delivery_from_packet(packet)
    write_delivery_json(baked, Path(args.output))
    print(f"[OK] 烘焙定稿 → {args.output}")
    print(f"  human_prior: enabled={rep.enabled}")
    if pq.fixes:
        for line in pq.fixes:
            print(f"  [平庸修正] {line}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
