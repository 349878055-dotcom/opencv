"""12 通道合同：渲染 + 扩散节拍共用，缺一不可。"""
from __future__ import annotations

CANONICAL_KEYS: list[str] = [
    "pupil_x",
    "pupil_y",
    "blink",
    "eyebrow",
    "pupil_scale",
    "iris_scale",
    "cornea_bulge",
    "squint",
    "brow_raise",
    "lid_upper",
    "lid_lower",
    "eye_gloss",
]

CHANNEL_LABELS_ZH: dict[str, str] = {
    "pupil_x": "视线左右",
    "pupil_y": "视线上下",
    "blink": "眼睑开合",
    "eyebrow": "眉压",
    "pupil_scale": "瞳孔缩放",
    "iris_scale": "虹膜圈",
    "cornea_bulge": "角膜鼓起",
    "squint": "眯眼眶压",
    "brow_raise": "挑眉",
    "lid_upper": "上眼睑",
    "lid_lower": "下眼睑",
    "eye_gloss": "眼湿润高光",
}

DIFFUSION_HINTS: dict[str, str] = {
    "pupil_x": "节拍：扫视方向；牵动注视与头部微转暗示",
    "pupil_y": "节拍：视线沉降；下颌与颈后线条随之处置",
    "blink": "节拍：眼睑脉冲；唇颊放松/微收节奏",
    "eyebrow": "节拍：眉压；颧骨额肌紧张度、口型克制",
    "pupil_scale": "节拍：瞳孔收缩；情绪浓度与面部收紧",
    "iris_scale": "节拍：虹膜显露；眼神锐度",
    "cornea_bulge": "节拍：目光「有神」；额部提亮节奏",
    "squint": "节拍：眶挤压；鼻翼法令与面颊走向",
    "brow_raise": "节拍：挑眉（本戏常压低）",
    "lid_upper": "节拍：上睑压；额头纹与上脸紧张",
    "lid_lower": "节拍：下睑；口周与颊部微绷",
    "eye_gloss": "节拍：湿润高光；皮肤质感与喉颈光泽联动",
}

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

def validate_channel_tracks(sparse: dict) -> list[str]:
    issues: list[str] = []
    issues.extend(validate_micro_jitter(sparse))
    tracks = sparse.get("channel_tracks") or {}
    if not tracks:
        return ["缺少 channel_tracks"]
    for key in CANONICAL_KEYS:
        tr = tracks.get(key)
        if not tr:
            issues.append(f"缺少通道: {key} ({CHANNEL_LABELS_ZH.get(key, key)})")
            continue
        kfs = tr.get("keyframes") or []
        if len(kfs) < 2:
            issues.append(f"通道 {key} 关键点少于 2 个")
        elif not any(k.get("easing") or k.get("segment_easing") for k in kfs[1:]):
            issues.append(f"通道 {key} 建议从第 2 个点起带 easing")
    return issues

def series_from_baked(sparse: dict, frame_count: int = 150) -> dict[str, list[float]]:
    """烘焙 02 逐帧关键帧 → 每通道序列。"""
    tracks = sparse.get("channel_tracks") or {}
    out: dict[str, list[float]] = {}
    for key in CANONICAL_KEYS:
        kfs = sorted(
            (tracks.get(key) or {}).get("keyframes") or [],
            key=lambda x: int(x["t"]),
        )
        if len(kfs) < frame_count:
            continue
        out[key] = [float(k.get("v", k.get("value", 0))) for k in kfs[:frame_count]]
    return out

def validate_baked_delivery(sparse: dict, frame_count: int = 150) -> list[str]:
    """烘焙定稿 02 出厂校验（全量帧）。"""
    issues: list[str] = []
    if not sparse.get("_baked_dense") and "baked" not in str(
        sparse.get("schema_version") or ""
    ):
        issues.append("缺少 _baked_dense / baked schema")
    tracks = sparse.get("channel_tracks") or {}
    if not tracks:
        return issues + ["缺少 channel_tracks"]
    for key in CANONICAL_KEYS:
        tr = tracks.get(key)
        if not tr:
            issues.append(f"缺少通道: {key}")
            continue
        kfs = tr.get("keyframes") or []
        if len(kfs) < frame_count:
            issues.append(f"通道 {key} 帧数不足: {len(kfs)}/{frame_count}")
    return issues
