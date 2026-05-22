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

# 情绪 → PAD 三维向量映射（LLM / 预设自动分配）
# 值域 [-1.0, 1.0]，分别对应 P(愉悦度), A(激活度), D(控制度)
EMOTION_PAD: dict[str, tuple[float, float, float]] = {
    "魅惑·勾人": (0.6,  0.3, -0.4),
    "施压·凝视": (-0.2, 0.7,  0.6),
    "冷压·决心": (-0.3, 0.6,  0.8),
    "威慑·一瞬": (0.0,  0.8,  0.5),
    "怒视·压人": (-0.5, 0.8,  0.7),
    "鄙夷·冷瞥": (-0.4, 0.3,  0.5),
    "可怜·委屈": (-0.2, 0.2, -0.5),
    "要哭未哭":  (-0.3, 0.3, -0.6),
    "崩溃·泄劲": (-0.6, 0.5, -0.7),
    "哀求·仰望": (0.1,  0.2, -0.6),
    "惊惧·一怔": (-0.4, 0.7, -0.3),
    "空竭·死心": (-0.7, 0.1, -0.2),
    "纯甜·含情": (0.8,  0.2,  0.1),
    "媚杀·一眼": (0.5,  0.4,  0.0),
    "若即若离":   (0.3,  0.1, -0.1),
    "打量·玩味": (0.2,  0.3,  0.2),
}


def _emotion_pad(emotion: str) -> tuple[float, float, float]:
    """按情绪名查找 PAD 值；未找到时返回中性 (0,0,0)。"""
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

        P, A, D = _emotion_pad(pkt.emotion)
        channels = channels_from_packet(pkt, frame_count, P=P, A=A, D=D)

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
    P: float | None = None,
    A: float | None = None,
    D: float | None = None,
) -> tuple[dict[str, Any], dict[str, list[float]], PriorReport, PulseQualityReport]:
    from gaze_engine.envelope_compile import channels_from_packet, make_delivery_stub

    if P is None or A is None or D is None:
        _P, _A, _D = _emotion_pad(packet.emotion)
        if P is None: P = _P
        if A is None: A = _A
        if D is None: D = _D
    channels = channels_from_packet(packet, frame_count, P=P, A=A, D=D)
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
