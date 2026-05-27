"""
狗完整管线：SliderPacket → 12 通道全量帧 → 02 烘焙 →（可选）工程底膜 MP4

合同：contracts/06_架构/狗150帧全量编译合同_上篇.md（S0～S7）

  S1 resolve_pad → S2 build_energy_envelope → S4 channels_from_envelope
  → ear 注入 → S5 apply_breed_style → S6 apply_dog_prior → S7 fix_dog_pulse_quality
  → _make_dog_baked（1800 keyframes）
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PKG = Path(__file__).resolve().parent.parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from gaze_engine._shared.envelope_compile import (
    FRAME_COUNT_DEFAULT,
    FPS_DEFAULT,
    build_energy_envelope,
)
from gaze_engine.dog.envelope_compile import (
    channels_from_envelope,
    make_delivery_stub,
)
from gaze_engine._shared.channel_contract import validate_baked_delivery
from gaze_engine.dog.envelope_compile import DOG_CHANNELS
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine.dog.pad_weights import DOG_PAD_WEIGHTS, DOG_BASE_SCALE
from gaze_engine.dog.channel_adapter import inject_ear_into_channels


@dataclass
class DogPipelineReport:
    """狗管线执行报告"""
    enabled: bool = True
    emotion: str = ""
    frame_count: int = FRAME_COUNT_DEFAULT
    ear_injected: bool = False
    dog_prior_skipped: bool = True   # TODO: 等 apply_dog_prior 实现
    dog_quality_skipped: bool = True  # TODO: 等 fix_pulse_quality 实现
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "emotion": self.emotion,
            "frame_count": self.frame_count,
            "ear_injected": self.ear_injected,
            "dog_prior_skipped": self.dog_prior_skipped,
            "dog_quality_skipped": self.dog_quality_skipped,
            "issues": self.issues,
        }


def run_dog_pipeline(
    packet: SliderPacket,
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    fps: int = FPS_DEFAULT,
    P: float | None = None,
    A: float | None = None,
    D: float | None = None,
    narrative_action: str = "",
    breed_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, list[float]], DogPipelineReport]:
    """
    狗完整管线入口。

    Args:
        packet: SliderPacket（含 EarParams）
        frame_count: 帧数
        fps: 帧率
        P, A, D: PAD 值（None 则从 emotion 自动推导）

    Returns:
        (baked_dict, channels_dict, report)
    """
    from gaze_engine._shared.emotion_pad import resolve_pad

    pkt = packet.clamped()

    # ── 1. PAD 推导 ──
    if P is None or A is None or D is None:
        _P, _A, _D = resolve_pad(pkt)
        if P is None: P = _P
        if A is None: A = _A
        if D is None: D = _D

    # ── 2. 能量包络 → 12 通道（用狗 PAD 权重） ──
    envelope = build_energy_envelope(pkt, frame_count)
    channels = channels_from_envelope(
        pkt, envelope, P=P, A=A, D=D,
        frame_count=frame_count,
        canonical_keys=DOG_CHANNELS,
        pad_weights=DOG_PAD_WEIGHTS,
        base_scale=DOG_BASE_SCALE,
    )

    # ── 3. 注入 EarParams → eyebrow / brow_raise ──
    ear_injected = False
    if pkt.ear is not None:
        channels = inject_ear_into_channels(channels, pkt.ear)
        ear_injected = True

    # ── 3b. 品种 styled（不改 E(t)） ──
    style_applied = ""
    bid = (breed_id or "").strip()
    if bid and bid not in ("default",):
        from gaze_engine.dog.breeds import apply_breed_style

        channels = apply_breed_style(channels, bid)
        style_applied = bid

    # ── 4. 狗先验（叙事回头 → 扫视补偿） ──
    from gaze_engine.dog.prior import apply_dog_prior

    channels = apply_dog_prior(
        channels, pkt, narrative_action=narrative_action, frame_count=frame_count
    )

    # ── 5. 平庸质检（blink 下限等） ──
    from gaze_engine.dog.pulse_quality import fix_dog_pulse_quality

    pq = fix_dog_pulse_quality(channels, frame_count=frame_count)

    report = DogPipelineReport(
        emotion=pkt.emotion,
        frame_count=frame_count,
        ear_injected=ear_injected,
        dog_prior_skipped=False,
        dog_quality_skipped=False,
    )
    if pq.fixes:
        report.issues.extend(pq.fixes)

    baked = _make_dog_baked(
        pkt, channels, frame_count=frame_count, report=report,
        narrative_action=narrative_action,
        breed_id=style_applied,
    )

    return baked, channels, report


def _make_dog_baked(
    packet: SliderPacket,
    channels: dict[str, list[float]],
    *,
    frame_count: int = FRAME_COUNT_DEFAULT,
    report: DogPipelineReport | None = None,
    narrative_action: str = "",
    breed_id: str = "",
) -> dict[str, Any]:
    """组装狗版 02_烘焙_真人律.json 格式"""
    stub = make_delivery_stub(
        packet, channels, frame_count=frame_count, label=packet.emotion
    )

    # 用 channels 数据填充 channel_tracks 为稠密格式
    tracks: dict[str, dict[str, Any]] = {}
    phases = ["蓄力", "启动", "保持", "缓和"]
    # 简化版 phase 分配
    phase_map = {}
    for t in range(frame_count):
        if t < 14:
            phase_map[t] = "蓄力"
        elif t < 28:
            phase_map[t] = "启动"
        elif t < 110:
            phase_map[t] = "保持"
        else:
            phase_map[t] = "缓和"

    for key in DOG_CHANNELS:
        series = channels.get(key, [0.0] * frame_count)
        kfs = []
        for t in range(frame_count):
            kfs.append({
                "t": t,
                "v": round(series[t], 6),
                "phase": phase_map.get(t, "保持"),
                "easing": "linear",
            })
        tracks[key] = {"keyframes": kfs}

    baked = dict(stub)
    baked.update({
        "schema_version": "0.3-baked-dog",
        "_baked_dense": True,
        "revision": f"dog-pipeline:{packet.emotion}",
        "species": "dog",
        "channel_tracks": tracks,
        "energy_phases": phases,
        "dog_pipeline_report": report.to_dict() if report else {},
        "slider_packet": packet.to_dict(),
    })
    if narrative_action:
        baked["narrative_action"] = narrative_action
    if breed_id:
        baked["breed"] = breed_id
        baked["style_layer"] = "styled"
    else:
        baked["style_layer"] = "pulse"

    # 校验
    remaining = validate_baked_delivery(baked, DOG_CHANNELS, frame_count)
    if remaining:
        baked["_delivery_validation_remaining"] = remaining

    return baked


def render_dog_batch(
    baked_json_path: str | Path,
    out_dir: str | Path,
    *,
    fps: int = FPS_DEFAULT,
    skip_render: bool = False,
) -> Path:
    """
    狗工程底膜批量渲染。

    Args:
        baked_json_path: 02_烘焙_真人律.json 路径
        out_dir: 输出目录
        fps: 帧率
        skip_render: 是否跳过渲染（只生成 JSON）

    Returns:
        MP4 输出路径
    """
    from gaze_engine.dog.affine_renderer import DogAffineRenderer, OUTPUT_W, OUTPUT_H

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(Path(baked_json_path).read_text(encoding="utf-8"))
    ch_data = {}
    tracks = data.get("channel_tracks", {})
    for key in DOG_CHANNELS:
        kfs = tracks.get(key, {}).get("keyframes", [])
        ch_data[key] = [float(k["v"]) for k in kfs]

    frame_count = len(next(iter(ch_data.values())))
    mp4_path = out_dir / "engineering_base_dog.mp4"

    if skip_render:
        print(f"[跳过渲染] 仅输出 JSON → {baked_json_path}")
        return mp4_path

    renderer = DogAffineRenderer()
    frames_dir = out_dir / "_frames"
    frames_dir.mkdir(exist_ok=True)

    print(f"[狗底膜] 渲染 {frame_count} 帧 → {frames_dir}")
    for t in range(frame_count):
        frame = renderer.render_frame({k: v[t] for k, v in ch_data.items()})
        cv2_imwrite(str(frames_dir / f"frame_{t:04d}.png"), frame)

    # 使用 OpenCV VideoWriter 替代 ffmpeg
    import cv2
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(mp4_path), fourcc, fps, (OUTPUT_W, OUTPUT_H))

    for t in range(frame_count):
        frame_path = frames_dir / f"frame_{t:04d}.png"
        frame = cv2.imread(str(frame_path))
        if frame is not None:
            writer.write(frame)

    writer.release()
    print(f"[狗底膜] MP4 → {mp4_path}")

    # 清理临时帧
    import shutil
    shutil.rmtree(frames_dir)

    return mp4_path


def cv2_imwrite(path: str, img: Any) -> bool:
    """安全写入（延迟导入 cv2）"""
    import cv2
    return cv2.imwrite(path, img)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════
def main() -> int:
    import argparse
    from gaze_engine.dog.presets import dog_packet_from_preset

    ap = argparse.ArgumentParser(description="狗管线：预设 → 12通道 → 工程底膜")
    ap.add_argument("--preset", default="dog_sad_puppy", help="狗预设名")
    ap.add_argument("-o", "--out", default="/tmp/dog_pipeline", help="输出目录")
    ap.add_argument("--skip-render", action="store_true", help="跳过 OpenCV 渲染")
    args = ap.parse_args()

    pkt = dog_packet_from_preset(args.preset)
    print(f"[狗管线] 情绪: {pkt.emotion}")

    baked, channels, report = run_dog_pipeline(pkt)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 写 JSON
    json_path = out_dir / "02_烘焙_真人律.json"
    json_path.write_text(
        json.dumps(baked, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[狗管线] 烘焙 JSON → {json_path}")

    # 渲染工程底膜
    if not args.skip_render:
        mp4 = render_dog_batch(json_path, out_dir)
        print(f"[狗管线] 工程底膜 MP4 → {mp4}")

    print(f"[狗管线] ✅ 完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())