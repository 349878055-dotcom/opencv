"""
通道校验工具 — 纯函数，无全局数据。

所有函数通过 channel_keys 参数接收通道名列表，不硬编码任何物种假设。
"""
from __future__ import annotations


def validate_micro_jitter(sparse: dict) -> list[str]:
    issues: list[str] = []
    block = sparse.get("micro_jitter")
    if not block:
        issues.append("缺少 micro_jitter 初始化块（出关键帧时应写入 by_phase）")
        return issues
    if block.get("enabled") is False:
        return issues
    by_phase = block.get("by_phase")
    if not isinstance(by_phase, dict):
        issues.append("micro_jitter 缺少 by_phase（蓄力/启动/保持/缓和）")
        return issues
    for ph in ("蓄力", "启动", "保持", "缓和"):
        if ph not in by_phase:
            issues.append(f"micro_jitter.by_phase 缺少: {ph}")
    return issues


def validate_channel_tracks(
    sparse: dict,
    channel_keys: list[str],
    channel_labels: dict[str, str] | None = None,
) -> list[str]:
    """校验每个通道是否都包含关键帧。

    Args:
        sparse: 烘焙数据
        channel_keys: 该物种的通道名列表
        channel_labels: 可选的中文标签（用于报错信息）
    """
    issues: list[str] = []
    issues.extend(validate_micro_jitter(sparse))
    tracks = sparse.get("channel_tracks") or {}
    if not tracks:
        return ["缺少 channel_tracks"]
    for key in channel_keys:
        tr = tracks.get(key)
        if not tr:
            label = (channel_labels or {}).get(key, key)
            issues.append(f"缺少通道: {key} ({label})")
            continue
        kfs = tr.get("keyframes") or []
        if len(kfs) < 2:
            issues.append(f"通道 {key} 关键点少于 2 个")
        elif not any(k.get("easing") or k.get("segment_easing") for k in kfs[1:]):
            issues.append(f"通道 {key} 建议从第 2 个点起带 easing")
    return issues


def series_from_baked(
    sparse: dict,
    channel_keys: list[str],
    frame_count: int = 150,
) -> dict[str, list[float]]:
    """烘焙 02 逐帧关键帧 → 每通道序列。"""
    tracks = sparse.get("channel_tracks") or {}
    out: dict[str, list[float]] = {}
    for key in channel_keys:
        kfs = sorted(
            (tracks.get(key) or {}).get("keyframes") or [],
            key=lambda x: int(x["t"]),
        )
        if len(kfs) < frame_count:
            continue
        out[key] = [float(k.get("v", k.get("value", 0))) for k in kfs[:frame_count]]
    return out


def validate_baked_delivery(
    sparse: dict,
    channel_keys: list[str],
    frame_count: int = 150,
) -> list[str]:
    """烘焙定稿 02 出厂校验（全量帧）。"""
    issues: list[str] = []
    if not sparse.get("_baked_dense") and "baked" not in str(
        sparse.get("schema_version") or ""
    ):
        issues.append("缺少 _baked_dense / baked schema")
    tracks = sparse.get("channel_tracks") or {}
    if not tracks:
        return issues + ["缺少 channel_tracks"]
    for key in channel_keys:
        tr = tracks.get(key)
        if not tr:
            issues.append(f"缺少通道: {key}")
            continue
        kfs = tr.get("keyframes") or []
        if len(kfs) < frame_count:
            issues.append(f"通道 {key} 帧数不足: {len(kfs)}/{frame_count}")
    return issues
