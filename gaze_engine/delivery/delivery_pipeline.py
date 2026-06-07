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

from gaze_engine.input.channel_contract import validate_baked_delivery  # noqa: E402
from gaze_engine.prior_qc.human_prior import (  # noqa: E402
    FRAME_COUNT_DEFAULT,
    FPS_DEFAULT,
    PriorReport,
    apply_human_prior,
    dense_to_baked_sparse,
)
from gaze_engine.prior_qc.pulse_quality import PulseQualityReport, fix_pulse_quality  # noqa: E402
from gaze_engine.input.slider_schema import SliderPacket  # noqa: E402

from gaze_engine.envelope.emotion_pad import resolve_pad  # noqa: E402

_PIPELINE_DOC = "合同/04_通道编译/01_十二通道与全量帧格式.md · envelope-v1"


def _emotion_pad(emotion: str, packet: SliderPacket | None = None) -> tuple[float, float, float]:
    """按情绪名查找 PAD；packet 含 pad 块时优先读资产。"""
    if packet is not None:
        return resolve_pad(packet)
    from asset_lib import load_emotion_pad

    t = load_emotion_pad("human", emotion)
    if t is not None:
        return t
    return (0.0, 0.0, 0.0)

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
    from gaze_engine.input.packet_finalize import finalize_packet

    pkt, fin_rep = finalize_packet(pkt)
    if fin_rep.changed:
        draft["slider_packet"] = pkt.to_dict()
        prev = list(draft.get("_finalize_fixes") or [])
        prev.extend(fin_rep.fixes)
        draft["_finalize_fixes"] = prev

    if channels_precomputed is not None:
        channels = {k: list(v[:frame_count]) for k, v in channels_precomputed.items()}
    else:
        from gaze_engine.envelope.envelope_compile import channels_from_packet

        P, A, D = _emotion_pad(pkt.emotion, pkt)
        channels = channels_from_packet(pkt, frame_count, P=P, A=A, D=D)

    sid = (style_id or pkt.style or "").strip()
    if sid and sid not in ("default",):
        from gaze_engine.style.persona_compiler import apply_persona_style

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

    from gaze_engine.envelope.envelope_compile import HUMAN_CHANNELS
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
    from gaze_engine.envelope.envelope_compile import channels_from_packet, make_delivery_stub

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


def run_species_delivery(
    packet: SliderPacket,
    species: str = "human",
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    narrative_action: str = "",
    breed_id: str = "",
    style_id: str = "",
) -> tuple[dict[str, Any], dict[str, list[float]], Any, Any]:
    """人类专属交付管线（已移除 cat/dog 路由）。"""
    sid = (style_id or "").strip()
    baked, dense, rep, pq = run_delivery_from_packet(
        packet, frame_count=frame_count, style_id=sid
    )
    baked.setdefault("species", "human")
    return baked, dense, rep, pq


def write_delivery_json(baked: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
# MediaPipe → 中间画布 → OpenCV 线条图（端到端，跳过文件 I/O）
# ═══════════════════════════════════════════════════════════════

def mediapipe_to_opencv_lines(
    photo_path: str | Path,
    *,
    img_width: int = 0,
    img_height: int = 0,
    anchor_mode: str = "eye_center",
) -> dict:
    """一步到位：MediaPipe 检测 → 1024 标准画布 → OpenCV 线条图。

    将原始真人照片通过完整管线（检测→几何适配→模板合成→
    空间标定→画布渲染）直接输出 OpenCV 线条图，跳过中间文件保存。

    Args:
        photo_path: 真人照片路径（支持 jpg/png）
        img_width: 照片宽度（0 则自动读取）
        img_height: 照片高度（0 则自动读取）
        anchor_mode: 锚点模式 "eye_center"（默认）| "outer_canthus"

    Returns:
        dict 包含:
            - "membrane_bgr": (H,W,3) uint8 — OpenCV 线条图
                R=眼眶(红), G=眉毛(绿), B=虹膜+瞳孔(蓝)
            - "photo_aligned": (H,W,3) uint8 — 经仿射对齐的照片
            - "overlay": (H,W,3) uint8 — 线条叠加照片的预览
            - "adjustments": MediaPipe 推导的模板调整参数
            - "render_baseline": 瞳孔静息 + 眉位基线
            - "spatial_calibration": 空间标定数据 dict
            - "notes": 处理日志

    Raises:
        FileNotFoundError: 照片不存在
        RuntimeError: MediaPipe 检测失败或几何适配失败
        ValueError: 缺少必要数据
    """
    import cv2
    import numpy as np

    photo_path = Path(photo_path)
    if not photo_path.is_file():
        raise FileNotFoundError(f"照片不存在: {photo_path}")

    from gaze_engine.render.geometry_adapter import (
        adapt_geometry, apply_render_baseline,
    )
    from gaze_engine.render.species_template import (
        species_default_template, apply_customer_adjustments,
        sanitize_human_spatial_adjustments, template_for_spatial_render,
        template_to_renderer_constants,
    )
    from gaze_engine.render.spatial_calibration import compute_spatial_calibration
    from gaze_engine.render.affine_renderer import (
        AffineRenderer, CANONICAL_KEYS,
    )

    # ── ① MediaPipe 检测 + 几何适配 ──
    geo = adapt_geometry(species="human", photo_path=photo_path)
    if geo.method == "failed":
        raise RuntimeError(f"几何适配失败: {'; '.join(geo.notes)}")
    if not geo.anchors:
        raise RuntimeError("MediaPipe 未产出锚点数据")
    if not geo.render_baseline:
        raise RuntimeError("MediaPipe 未产出 render_baseline（瞳孔静息/眉位缺失）")

    # ── ② 模板合成：SpeciesTemplate → 渲染器常量 ──
    _base_tpl = species_default_template("human")
    _adj = sanitize_human_spatial_adjustments(geo.adjustments)
    _adj_tpl = apply_customer_adjustments(_base_tpl, _adj)
    _spatial_tpl = template_for_spatial_render(_adj_tpl, "human")
    constants = apply_render_baseline(
        template_to_renderer_constants("human", _spatial_tpl),
        geo.render_baseline,
    )

    # ── ③ 空间标定：3 点仿射（模型 1024 → 照片空间）──
    img = cv2.imread(str(photo_path))
    if img is None:
        raise RuntimeError(f"无法读取照片: {photo_path}")
    if img_width <= 0 or img_height <= 0:
        img_height, img_width = img.shape[:2]
    spatial_cal = compute_spatial_calibration(
        geo.anchors, img_width, img_height, constants,
        anchor_mode=anchor_mode,
    )

    # ── ④ 中间画布渲染（1024×1024 → warpAffine 投影）──
    renderer = AffineRenderer(constants, spatial_calibration=spatial_cal)
    neutral = {k: 0.0 for k in CANONICAL_KEYS}
    membrane_bgr = renderer.render_frame(neutral)  # (OUTPUT_H, OUTPUT_W, 3)

    # ── ⑤ 照片仿射对齐（与底膜共用同一矩阵）──
    canvas = spatial_cal.warp_photo(img)

    # ── ⑥ 叠加预览（RGB 分通道着色）──
    overlay = np.zeros_like(membrane_bgr, dtype=np.uint8)
    overlay[membrane_bgr[:, :, 2] > 0] = (0, 0, 255)   # R=红（眼眶）
    overlay[membrane_bgr[:, :, 1] > 0] = (0, 255, 0)   # G=绿（眉毛）
    overlay[membrane_bgr[:, :, 0] > 0] = (255, 0, 0)   # B=蓝（虹膜+瞳孔）
    combined = cv2.addWeighted(canvas, 0.5, overlay, 0.5, 0)

    return {
        "membrane_bgr": membrane_bgr,
        "photo_aligned": canvas,
        "overlay": combined,
        "adjustments": geo.adjustments,
        "render_baseline": geo.render_baseline,
        "spatial_calibration": spatial_cal.to_dict(),
        "notes": geo.notes,
    }


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
