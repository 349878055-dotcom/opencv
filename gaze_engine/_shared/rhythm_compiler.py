#!/usr/bin/env python3
"""
rhythm_compiler.py · 节奏说明书编译器（公共层·算法骨架）

从 02_烘焙_真人律.json（12 通道 × 150 帧）自动编译为
05_扩散节拍表.txt（扩散引擎 Wan 可消费的自然语言节奏说明书）。

合同规范：contracts/01_总纲/节奏说明书编译器.md
数据来源：各物种的 rhythm_data.py 提供提示词文案
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

_REPO = Path(__file__).resolve().parent.parent.parent  # 项目根
_VALUE_EPS = 0.002


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def _is_baked_sparse(sparse: dict) -> bool:
    """检测是否是烘焙定稿（稠密帧）还是稀疏草稿"""
    if sparse.get("_baked_dense"):
        return True
    ver = str(sparse.get("schema_version") or "")
    return "baked" in ver


def _extract_keyframes(track: dict) -> List[Tuple[int, float]]:
    """从通道轨道提取关键帧 (t, v) 列表"""
    kfs = sorted(track.get("keyframes") or [], key=lambda k: int(k["t"]))
    return [(int(k["t"]), float(k["v"])) for k in kfs]


# 物种数据缓存
_SPECIES_CACHE: dict[str, tuple[dict[str, str], dict[str, str], list[str]]] = {}

def _load_species_data(species: str) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """动态加载物种专有数据：hints, labels, constraints_extra（缓存）"""
    if species in _SPECIES_CACHE:
        return _SPECIES_CACHE[species]

    module_path = f"gaze_engine.{species}.rhythm_data"
    try:
        mod = importlib.import_module(module_path)
        hints = getattr(mod, "DIFFUSION_HINTS", {})
        labels = getattr(mod, "CHANNEL_LABELS", {})
        extras: list[str] = []
        for attr in ("CAT_CONSTRAINT", "DOG_CONSTRAINT", "CONSTRAINTS_HUMAN"):
            v = getattr(mod, attr, None)
            if v:
                extras.append(v)
        result = (hints, labels, extras)
        _SPECIES_CACHE[species] = result
        return result
    except (ImportError, ModuleNotFoundError):
        result: tuple[dict[str, str], dict[str, str], list[str]] = ({}, {}, [])
        _SPECIES_CACHE[species] = result
        return result


def _get_diffusion_hint(key: str, species: str = "human") -> str:
    """获取物种自适应的节拍说明"""
    hints, _, _ = _load_species_data(species)
    return hints.get(key, "")


def _collect_all_frames(tracks: dict, sparse: dict) -> List[int]:
    """收集所有通道的去重变帧时刻"""
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


def _build_constraints(sparse: dict, species: str = "human") -> List[str]:
    """生成末尾的硬约束摘要（物种自适应）"""
    tracks = sparse.get("channel_tracks") or {}
    # 尝试从关键帧估算扫视峰帧和轻眨帧
    saccade_peak = 17   # 默认值
    blink_frame = 86    # 默认值
    try:
        px_track = tracks.get("pupil_x", {})
        kfs = sorted(px_track.get("keyframes") or [], key=lambda k: int(k["t"]))
        if kfs:
            vals = [(int(k["t"]), abs(float(k["v"]))) for k in kfs]
            max_v = max(v[1] for v in vals)
            peaks = [v[0] for v in vals if v[1] == max_v]
            if peaks:
                saccade_peak = peaks[-1]
        bl_track = tracks.get("blink", {})
        kfs = sorted(bl_track.get("keyframes") or [], key=lambda k: int(k["t"]))
        blink_candidates = [int(k["t"]) for k in kfs if float(k["v"]) > 0.05
                            and int(k["t"]) > 50 and int(k["t"]) < 130]
        if blink_candidates:
            blink_frame = blink_candidates[0]
    except Exception:
        pass

    _, _, extras = _load_species_data(species)
    base = [
        f"扫视过冲帧(约{saccade_peak})为全脸张力高峰；轻眨帧(约{blink_frame})为全局微释放。",
    ]
    base.extend(extras)
    base.append("远景镜头也需保持脉冲语义：pupil_x/y 仍控制注视方向，head 跟随。")
    return base


# ═══════════════════════════════════════════════════════════
# 核心编译函数
# ═══════════════════════════════════════════════════════════

def build_metronome_text(
    sparse: dict,
    *,
    source_path: str = "",
    species: str = "human",
) -> str:
    """
    节奏说明书编译器 · 核心函数

    Args:
        sparse:   02_烘焙_真人律.json 的解析结果 (dict)
        source_path: 源文件路径（可选，写入文件头）
        species:  物种标识 "human" | "cat" | "dog"

    Returns:
        严格 6 段模板的节奏说明书文本

    """
    baked = _is_baked_sparse(sparse)
    emotion = sparse.get("mood") or sparse.get("emotion", "")
    lines: List[str] = []

    # ── 段 1：文件头 ──
    lines.extend([
        "# 扩散节拍表（12 通道 · 由 02 导出）",
        f"# 情绪: {emotion}",
        f"# 来源: {source_path or '（未标注路径）'}",
        f"# 形态: {'烘焙定稿' if baked else '稀疏草稿（仅节拍点）'}",
        f"# 用途: Wan/扩散引擎节奏主钟；远景也保留脉冲语义",
        f"# 物种: {species}",
        "",
    ])

    # ── 段 2：全局阶段 ──
    phases = sparse.get("energy_phases") or ["蓄力", "启动", "保持", "缓和"]
    lines.extend([
        "## 全局阶段",
        " → ".join(phases),
        "",
    ])

    # ── 段 3：各通道脉冲 ──
    lines.append("## 各通道脉冲")
    tracks = sparse.get("channel_tracks") or {}
    # 从数据中读取实际通道名（不硬编码人类 CANONICAL_KEYS）
    channel_keys = list(tracks.keys()) or []

    for key in channel_keys:
        tr = tracks.get(key)
        _, labels, _ = _load_species_data(species)
        zh = labels.get(key, key)
        hint = _get_diffusion_hint(key, species)

        if not tr:
            lines.append(f"- **{key}**（{zh}）: （缺失）")
            continue

        kfs = _extract_keyframes(tr)
        if not kfs:
            lines.append(f"- **{key}**（{zh}）: （无关键帧）")
            continue

        # 烘焙定稿且帧数过多时做降采样显示（blink 强制保留非零峰）
        if baked and len(kfs) > 24:
            step = max(1, len(kfs) // 20)
            sampled_set = {kfs[i] for i in range(0, len(kfs), step)}
            if key == "blink":
                for pt in kfs:
                    if pt[1] > 0.01:
                        sampled_set.add(pt)
            sampled = sorted(sampled_set, key=lambda x: x[0])
            pts = ", ".join(f"t{t}={v:.4f}" for t, v in sampled)
            pts += f" …（共 {len(kfs)} 帧，已抽样显示）"
        else:
            pts = ", ".join(f"t{t}={v}" for t, v in kfs)

        lines.append(f"- **{key}**（{zh}）: {pts}")
        if hint:
            lines.append(f"  → {hint}")

    lines.append("")

    # ── 段 4：时间轴汇合 ──
    all_frames = _collect_all_frames(tracks, sparse)
    lines.extend([
        "## 时间轴汇合（变帧时刻）",
        ", ".join(str(t) for t in all_frames),
        "",
    ])

    # ── 段 5：硬约束 ──
    lines.append("## 给扩散的硬约束（摘要）")
    lines.extend(_build_constraints(sparse, species))
    lines.append("")

    # ── 段 6：出厂质检（可选） ──
    if sparse.get("pulse_quality_report"):
        lines.extend([
            "## 出厂质检（pulse_quality）",
            json.dumps(sparse["pulse_quality_report"], ensure_ascii=False, indent=2),
            "",
        ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 文件 IO
# ═══════════════════════════════════════════════════════════

def write_metronome_file(
    json_path: str | Path,
    out_path: str | Path | None = None,
    species: str = "human",
) -> Path:
    """
    从 JSON 文件直接编译并写入 TXT

    Args:
        json_path: 02_烘焙_真人律.json 路径
        out_path:  输出路径，None 时自动推导为同目录下 05_扩散节拍表.txt
        species:   物种标识

    Returns:
        输出文件的 Path
    """
    json_path = Path(json_path)
    if not json_path.is_file():
        raise FileNotFoundError(f"找不到输入文件: {json_path}")

    sparse = json.loads(json_path.read_text(encoding="utf-8"))

    if out_path is None:
        out_path = json_path.parent / "05_扩散节拍表.txt"
    else:
        out_path = Path(out_path)

    text = build_metronome_text(sparse, source_path=str(json_path), species=species)
    out_path.write_text(text, encoding="utf-8")
    return out_path


def write_metronome_batch(
    dir_path: str | Path,
    out_dir: str | Path | None = None,
    species: str = "human",
) -> List[Path]:
    """
    批量编译目录下所有 02_烘焙_真人律.json

    自动查找目录及其子目录下的 02_*.json 文件
    """
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"找不到目录: {dir_path}")

    results: List[Path] = []
    for json_path in sorted(dir_path.rglob("02_*.json")):
        if out_dir:
            rel = json_path.relative_to(dir_path)
            out = Path(out_dir) / rel.parent / "05_扩散节拍表.txt"
        else:
            out = json_path.parent / "05_扩散节拍表.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        written = write_metronome_file(json_path, out, species=species)
        results.append(written)
        print(f"  ✅ {written}")
    return results


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))

    ap = argparse.ArgumentParser(
        description="节奏说明书编译器 · 02_烘焙_真人律.json → 05_扩散节拍表.txt"
    )
    ap.add_argument(
        "-i", "--input", type=str, default=None,
        help="输入 JSON 路径（默认: 从 ECURSOR_SPARSE_JSON 环境变量或预设资产自动推导）"
    )
    ap.add_argument(
        "-o", "--output", type=str, default=None,
        help="输出 TXT 路径（默认: 输入文件同目录/05_扩散节拍表.txt）"
    )
    ap.add_argument(
        "--batch", type=str, default=None,
        help="批量编译目录（自动查找其下所有 02_*.json）"
    )
    ap.add_argument(
        "--outdir", type=str, default=None,
        help="批量输出目录（与 --batch 配合）"
    )
    ap.add_argument(
        "--species", type=str, default="human", choices=["human", "cat", "dog"],
        help="物种标识（默认 human）"
    )
    args = ap.parse_args()

    if args.batch:
        outs = write_metronome_batch(args.batch, args.outdir, species=args.species)
        print(f"批量编译完成，共 {len(outs)} 个文件")
        return 0

    if args.input:
        out = write_metronome_file(args.input, args.output, species=args.species)
        print(f"已写入: {out}")
        return 0

    # 默认：从预设资产自动推导
    from asset_lib import cmd_dir, resolve_sparse_json

    src = resolve_sparse_json(prefer_baked=True)
    if not src.is_file():
        print("❌ 找不到 02_烘焙_真人律.json", file=sys.stderr)
        print("   请指定 --input, 或设置 ECURSOR_SPARSE_JSON 环境变量", file=sys.stderr)
        return 1

    sparse = json.loads(src.read_text(encoding="utf-8"))
    # 从 JSON 中读取 species，若没有则用命令行参数
    sp = sparse.get("species", args.species)
    text = build_metronome_text(sparse, source_path=str(src), species=sp)
    out = args.output or (cmd_dir() / "05_扩散节拍表.txt")
    Path(out).write_text(text, encoding="utf-8")
    print(f"已写入: {out}")
    print(f"  读取: {src} ({'烘焙' if _is_baked_sparse(sparse) else '稀疏'})")
    print(f"  物种: {sp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())