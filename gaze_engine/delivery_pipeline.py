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

from gaze_engine.channel_contract import validate_baked_delivery  # noqa: E402
from gaze_engine.human_prior import (  # noqa: E402
    FRAME_COUNT_DEFAULT,
    FPS_DEFAULT,
    PriorReport,
    apply_human_prior,
    dense_to_baked_sparse,
)
from gaze_engine.pulse_quality import PulseQualityReport, fix_pulse_quality  # noqa: E402
from gaze_engine.slider_schema import SliderPacket  # noqa: E402

_PIPELINE_DOC = "contracts/全量帧指令集规范.md · envelope-v1"

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
) -> tuple[dict[str, Any], dict[str, list[float]], PriorReport, PulseQualityReport]:
    draft = copy.deepcopy(context)
    pkt = packet or _packet_from_context(draft) or SliderPacket()
    from gaze_engine.packet_finalize import finalize_packet

    pkt, fin_rep = finalize_packet(pkt)
    if fin_rep.changed:
        draft["slider_packet"] = pkt.to_dict()
        prev = list(draft.get("_finalize_fixes") or [])
        prev.extend(fin_rep.fixes)
        draft["_finalize_fixes"] = prev

    if channels_precomputed is not None:
        channels = {k: list(v[:frame_count]) for k, v in channels_precomputed.items()}
    else:
        from gaze_engine.envelope_compile import channels_from_packet

        channels = channels_from_packet(pkt, frame_count)

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
    if draft.get("energy_envelope"):
        baked["energy_envelope"] = draft["energy_envelope"]
    baked["pulse_quality_report"] = pq_rep.to_dict()
    if pq_rep.fixes:
        baked["_pulse_quality_fix_log"] = pq_rep.fixes
    if pq_rep.remaining:
        baked["_pulse_quality_remaining"] = pq_rep.remaining

    remaining = validate_baked_delivery(baked, frame_count)
    if remaining:
        baked["_delivery_validation_remaining"] = remaining

    return baked, dense_out, rep, pq_rep

def run_delivery_from_packet(
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
) -> tuple[dict[str, Any], dict[str, list[float]], PriorReport, PulseQualityReport]:
    from gaze_engine.envelope_compile import channels_from_packet, make_delivery_stub

    channels = channels_from_packet(packet, frame_count)
    stub = make_delivery_stub(
        packet, channels, frame_count=frame_count, label=packet.emotion
    )
    return run_delivery(stub, packet, channels_precomputed=channels)

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
