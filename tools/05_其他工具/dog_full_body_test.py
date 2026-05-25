#!/usr/bin/env python3
"""
狗管线测试 · Wan 资产打包

合同《眼眉指令集_全局情绪节奏主钟》规定：
  OpenCV 只输出三色几何控制图（工程底膜），
  全身动作由 Wan 扩散引擎从参考图 + 控制网格 + 节奏说明书生成。

输出:
  dog_eye_control_mesh.mp4  — 标准 RGB 工程底膜（690×361）← 喂给 Wan
  02_烘焙_真人律.json        — 全量帧数据（12 通道 × 150 帧）
  05_扩散节拍表.txt          — 节奏说明书（自然语言版）
  04_给视频生成的Prompt.txt  — Wan 扩散 Prompt
  dog_visualized.png         — 单帧示意图（关键帧 + 通道曲线）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None
    print("⚠️ OpenCV 未安装，工程底膜渲染将跳过")

# ── 路径 ──
_PKG = Path(__file__).resolve().parent.parent.parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from gaze_engine._shared.channel_contract import CANONICAL_KEYS, CHANNEL_LABELS_ZH, DIFFUSION_HINTS
from gaze_engine._shared.rhythm_compiler import build_metronome_text
from gaze_engine.dog.dog_pipeline import run_dog_pipeline
from gaze_engine.dog.presets import dog_packet_from_preset

FPS = 30
FRAME_COUNT = 150


def build_dog_test_assets(
    preset_name: str = "dog_sad_puppy",
    out_dir: str | Path = "/tmp/dog_test",
    *,
    natural_language: str = "狗子被关进笼子里面的委屈样子",
    skip_render: bool = False,
) -> dict[str, Any]:
    """
    构建狗测试资产（Wan 可消费格式）。

    Returns:
        { 输出文件路径字典 }
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"🐶 狗管线测试 — Wan 资产打包")
    print(f"   预设: {preset_name}")
    print(f"   NL: {natural_language}")
    print(f"   输出: {out_dir}")
    print("=" * 60)

    # ── 1. 狗预设 → 全量帧（12 通道 × 150） ──
    print(f"\n[1/5] 编译 12 通道全量帧...")
    pkt = dog_packet_from_preset(preset_name)
    baked, channels, report = run_dog_pipeline(pkt)

    # ── 2. 写 02_烘焙_真人律.json（Wan 消费格式） ──
    print(f"[2/5] 写烘焙 JSON...")
    json_path = out_dir / "02_烘焙_真人律.json"
    json_path.write_text(
        json.dumps(baked, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"   → {json_path}")

    # ── 3. 写 05_扩散节拍表.txt（节奏说明书） ──
    print(f"[3/5] 写节奏说明书...")
    metronome_text = build_metronome_text(baked, species="dog")
    metronome_path = out_dir / "05_扩散节拍表.txt"
    metronome_path.write_text(metronome_text, encoding="utf-8")
    print(f"   → {metronome_path}")

    # ── 4. 渲染工程底膜（RGB 三色分离，只控制眉眼耳） ──
    # 合同规定：R=眼眶, G=耳廓+眉脊, B=瞳孔 — 这才是 OpenCV 该做的事
    mesh_path = out_dir / "dog_eye_control_mesh.mp4"
    if not skip_render and cv2 is not None:
        print(f"[4/5] 渲染工程底膜（RGB 三色分离）...")
        from gaze_engine.dog.dog_pipeline import render_dog_batch
        render_dog_batch(json_path, out_dir)
        default_mp4 = out_dir / "engineering_base_dog.mp4"
        if default_mp4.exists():
            default_mp4.rename(mesh_path)
        print(f"   → {mesh_path}")
    else:
        print(f"[4/5] ⏭ 跳过工程底膜渲染")
        mesh_path = None

    # ── 5. 写 Wan Prompt（扩散引擎提示词） ──
    print(f"[5/5] 写 Wan 扩散 Prompt...")
    prompt_path = out_dir / "04_给视频生成的Prompt.txt"
    prompt = _build_wan_prompt(
        preset_name, natural_language,
        report, channels,
        metronome_text,
    )
    prompt_path.write_text(prompt, encoding="utf-8")
    print(f"   → {prompt_path}")

    # ── 可视化关键帧示意图 ──
    viz_path = out_dir / "dog_visualized.png"
    if not skip_render and cv2 is not None:
        _draw_keyframe_viz(channels, str(viz_path))

    result = {
        "preset": preset_name,
        "natural_language": natural_language,
        "baked_json": str(json_path),
        "metronome_txt": str(metronome_path),
        "eye_mesh_video": str(mesh_path) if mesh_path else None,
        "wan_prompt": str(prompt_path),
        "report": report.to_dict(),
        "species": "dog",
        "frame_count": FRAME_COUNT,
        "fps": FPS,
    }

    print("\n" + "=" * 60)
    print("✅ 狗管线测试完成！Wan 资产输出：")
    for k, v in result.items():
        if v is not None and not isinstance(v, dict):
            print(f"   {k}: {v}")
    print("=" * 60)
    print(f"\n   使用 Wan 生成视频：")
    print(f"     参考图: dog_sad_frame.png（根目录）")
    print(f"     控制网格: {mesh_path}")
    print(f"     Prompt: {prompt_path}")
    print(f"     节奏说明书: {metronome_path}")

    return result


def _build_wan_prompt(
    preset: str,
    nl: str,
    report: Any,
    channels: dict[str, list[float]],
    metronome_text: str,
) -> str:
    """组装给 Wan 扩散引擎的完整 Prompt"""
    return f"""# 狗眼眉指令集 — Wan 扩散引擎 Prompt

## 自然语言指令
{nl}

## 情绪预设
{preset}

## 指令集摘要（12 通道 × {FRAME_COUNT} 帧 @ {FPS}fps）
{_summarize_channels(channels)}

## 工程底膜说明
工程底膜文件: dog_eye_control_mesh.mp4
RGB 三色分离含义:
  - R (红色) = 眼眶轮廓（闭合路径，狗眼更圆）
  - G (绿色) = 耳廓几何 + 眉脊线（垂耳/立耳 + 眉肌）
  - B (蓝色) = 瞳孔 + 虹膜（实心圆，水汪汪）

## 关键节奏锚点（合同规定的验收帧）
| 帧 | 节奏点 | 画面要求 |
|----|--------|---------|
| 0~14 | 蓄力 | 狗刚被关进笼子，耳朵开始耷拉 |
| 17 | 瞳孔扫视过冲峰 | 眼睛急扫，全脸张力高峰 |
| 23 | 回弹盯住 | 视线稳定，委屈加深 |
| 32 | 眉/耳压到位 | 耳朵全耷拉，眉脊微动 |
| 86 | 独立轻眨释放 | 全身蜷缩，闭眼释放 |
| 110~149 | 缓和收尾 | 慢慢闭眼，委屈到极点 |

## 节奏说明书
{metronome_text}

## 扩散约束
1. 狗的耳朵随 eyebrow 通道值变化（0=全耷拉, 1=全竖立）
2. 狗的眼神随 pupil_x/y 通道变化
3. blink 为独立眨眼事件，不绑扫视
4. 身体姿态随能量曲线 E(t) 变化（高能量时紧张，低能量时蜷缩）
5. 背景：笼子、暗调、可怜氛围
"""


def _summarize_channels(channels: dict[str, list[float]]) -> str:
    """生成 12 通道摘要"""
    lines = []
    for key in CANONICAL_KEYS:
        series = channels.get(key, [0.0] * FRAME_COUNT)
        peak = max(series)
        valley = min(series)
        mean_val = sum(series) / len(series)
        zh = CHANNEL_LABELS_ZH.get(key, key)
        hint = DIFFUSION_HINTS.get(key, "")
        short_hint = hint.split("；")[0] if "；" in hint else hint[:50]
        lines.append(
            f"  {key} ({zh}): 范围[{valley:.3f}~{peak:.3f}], "
            f"均值{mean_val:.3f} — {short_hint}"
        )
    return "\n".join(lines)


def _draw_keyframe_viz(
    channels: dict[str, list[float]],
    output_path: str,
) -> None:
    """绘制关键帧可视化示意图（12 通道曲线叠在关键帧上）"""
    if cv2 is None:
        return

    W, H = 1200, 800
    canvas = np.ones((H, W, 3), dtype=np.uint8) * 30

    # 标题
    cv2.putText(canvas, "🐶 狗眼眉指令集 · 12 通道脉冲曲线",
                (30, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (200, 200, 200), 2, cv2.LINE_AA)

    graph_top = 80
    graph_h = 40
    graph_gap = 8
    colors = [
        (0, 100, 255), (0, 150, 255), (0, 200, 200),
        (0, 255, 100), (100, 200, 255), (150, 100, 255),
        (200, 100, 200), (50, 255, 50), (200, 200, 0),
        (100, 200, 200), (150, 150, 200), (255, 100, 100),
    ]

    for i, key in enumerate(CANONICAL_KEYS):
        series = channels.get(key, [0.0] * FRAME_COUNT)
        y0 = graph_top + i * (graph_h + graph_gap)
        zh = CHANNEL_LABELS_ZH.get(key, key)

        # 标签
        cv2.putText(canvas, f"{key} ({zh})",
                    (10, y0 + graph_h // 2 + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                    colors[i], 1, cv2.LINE_AA)

        # 曲线
        max_val = max(series) or 0.01
        pts = []
        for t, v in enumerate(series):
            x = 220 + int(t / len(series) * 900)
            y = y0 + graph_h - int((v / max_val) * graph_h * 0.9)
            pts.append([x, y])

        if pts:
            cv2.polylines(canvas, [np.array(pts, np.int32)],
                          False, colors[i], 1, cv2.LINE_AA)

    # 关键帧竖线
    key_frames = [0, 17, 23, 32, 86, 110, 149]
    for tf in key_frames:
        x = 220 + int(tf / FRAME_COUNT * 900)
        cv2.line(canvas, (x, graph_top),
                 (x, graph_top + 12 * (graph_h + graph_gap)),
                 (100, 100, 100), 1, cv2.LINE_AA)
        cv2.putText(canvas, str(tf),
                    (x - 10, graph_top + 12 * (graph_h + graph_gap) + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (150, 150, 150), 1, cv2.LINE_AA)

    cv2.imwrite(output_path, canvas)


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════
def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="狗管线测试 · Wan 资产打包")
    ap.add_argument("--preset", default="dog_sad_puppy", help="狗预设名")
    ap.add_argument("-o", "--out", default="/tmp/dog_test", help="输出目录")
    ap.add_argument("--nl", default="狗子被关进笼子里面的委屈样子",
                    help="自然语言描述")
    ap.add_argument("--skip-render", action="store_true",
                    help="跳过工程底膜渲染")
    args = ap.parse_args()

    build_dog_test_assets(
        preset_name=args.preset,
        out_dir=args.out,
        natural_language=args.nl,
        skip_render=args.skip_render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())