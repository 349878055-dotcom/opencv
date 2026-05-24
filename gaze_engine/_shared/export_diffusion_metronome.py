#!/usr/bin/env python3
"""从 02 导出扩散节拍表（12 通道脉冲，供 04 Prompt / Wan）。

优先读 02_烘焙_真人律.json（或 ECURSOR_SPARSE_JSON）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

_VALUE_EPS = 0.002

def _is_baked_sparse(sparse: dict) -> bool:
    if sparse.get("_baked_dense"):
        return True
    ver = str(sparse.get("schema_version") or "")
    return "baked" in ver

def _pulse_frames(sparse: dict) -> list[int]:
    """变帧时刻：稀疏 02 用关键点；烘焙 02 用各通道值变化帧（降采样）。"""
    tracks = sparse.get("channel_tracks") or {}
    baked = _is_baked_sparse(sparse)
    frames: set[int] = set()
    for tr in tracks.values():
        kfs = sorted(tr.get("keyframes") or [], key=lambda k: int(k["t"]))
        if not kfs:
            continue
        if not baked or len(kfs) <= 40:
            for k in kfs:
                frames.add(int(k["t"]))
            continue
        prev_v: float | None = None
        for k in kfs:
            t = int(k["t"])
            v = float(k["v"])
            if prev_v is None or abs(v - prev_v) > _VALUE_EPS:
                frames.add(t)
            prev_v = v
    return sorted(frames)

def build_metronome_text(sparse: dict, *, source_path: str = "") -> str:
    from gaze_engine._shared.channel_contract import CANONICAL_KEYS, CHANNEL_LABELS_ZH, DIFFUSION_HINTS

    baked = _is_baked_sparse(sparse)
    lines = [
        "# 扩散节拍表（12 通道 · 由 02 导出）",
        f"# 情绪: {sparse.get('mood', '')}",
        f"# 来源: {source_path or '（未标注路径）'}",
        f"# 形态: {'烘焙定稿' if baked else '稀疏草稿（仅节拍点）'}",
        f"# 用途: Wan/扩散引擎节奏主钟；远景也保留脉冲语义",
        "",
        "## 全局阶段",
        " → ".join(sparse.get("energy_phases") or []),
        "",
        "## 各通道脉冲",
    ]
    tracks = sparse.get("channel_tracks") or {}
    for key in CANONICAL_KEYS:
        tr = tracks.get(key)
        if not tr:
            lines.append(f"- {key}: （缺失）")
            continue
        kfs = tr.get("keyframes") or []
        if baked and len(kfs) > 24:
            pts = ", ".join(
                f"t{k['t']}={k['v']:.4f}" if isinstance(k.get("v"), float) else f"t{k['t']}={k['v']}"
                for k in kfs[:: max(1, len(kfs) // 20)]
            )
            pts += f" …（共 {len(kfs)} 帧，已抽样显示）"
        else:
            pts = ", ".join(f"t{k['t']}={k['v']}" for k in kfs)
        zh = CHANNEL_LABELS_ZH.get(key, key)
        lines.append(f"- **{key}**（{zh}）: {pts}")
        if key in DIFFUSION_HINTS:
            lines.append(f"  - {DIFFUSION_HINTS[key]}")
    lines.extend(
        [
            "",
            "## 时间轴汇合（变帧时刻）",
            ", ".join(str(t) for t in _pulse_frames(sparse)),
            "",
            "## 给扩散的硬约束（摘要）",
            "眉眼节奏严格跟随上表；眉压↑时口型克制、颧部微绷、额颈随节拍收紧；",
            "扫视过冲帧(约17–25)为全脸张力高峰；轻眨帧(约86)为全局微释放。",
        ]
    )
    if sparse.get("pulse_quality_report"):
        lines.extend(
            [
                "",
                "## 出厂质检（pulse_quality）",
                json.dumps(sparse["pulse_quality_report"], ensure_ascii=False, indent=2),
            ]
        )
    return "\n".join(lines) + "\n"

def main() -> int:
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    from asset_lib import cmd_dir, resolve_sparse_json

    src = resolve_sparse_json(prefer_baked=True)
    if not src.is_file():
        print("缺少 02", file=sys.stderr)
        return 1
    sparse = json.loads(src.read_text(encoding="utf-8"))
    text = build_metronome_text(sparse, source_path=str(src))
    out = cmd_dir() / "05_扩散节拍表.txt"
    out.write_text(text, encoding="utf-8")
    print(f"已写入: {out}")
    print(f"  读取: {src} ({'烘焙' if _is_baked_sparse(sparse) else '稀疏'})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
