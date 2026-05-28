"""控制面定义 · 唯一真源（预设、分区、工作台 UI 结构）。"""
from __future__ import annotations

from typing import Any

SCHEMA_ID = "slider-packet-v1"

MACRO_IDS = ("push", "power", "speed", "steady", "grip", "outro")
HOLD_IDS = ("shape", "pulse_rate", "pulse_depth", "swell")
VALID_SHAPES = frozenset({"flat", "decay", "swell", "pulse", "tremble"})

PRESET_GROUPS: tuple[dict[str, Any], ...] = (
    {"label": "压 · 慑", "keys": ["施压·凝视", "冷压·决心", "威慑·一瞬", "怒视·压人", "鄙夷·冷瞥"]},
    {"label": "悲 · 怯", "keys": ["可怜·委屈", "要哭未哭", "崩溃·泄劲", "哀求·仰望", "惊惧·一怔", "空竭·死心"]},
    {"label": "媚 · 勾", "keys": ["魅惑·勾人", "纯甜·含情", "媚杀·一眼", "若即若离", "打量·玩味"]},
)

PRESETS: dict[str, dict[str, Any]] = {
    "施压·凝视": {
        "note": "外放、急、猛、平顶钉死、慢收",
        "macro": {"push": 85, "power": 90, "speed": 88, "steady": 94, "grip": 90, "outro": 32},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
    },
    "冷压·决心": {
        "note": "更狠更钉，起略缓",
        "macro": {"push": 88, "power": 95, "speed": 76, "steady": 96, "grip": 94, "outro": 38},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
    },
    "威慑·一瞬": {
        "note": "极急、快收",
        "macro": {"push": 90, "power": 92, "speed": 98, "steady": 90, "grip": 86, "outro": 10},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
    },
    "怒视·压人": {
        "note": "外放、高力度、平顶",
        "macro": {"push": 92, "power": 88, "speed": 82, "steady": 88, "grip": 88, "outro": 22},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
    },
    "鄙夷·冷瞥": {
        "note": "外放、快、钉、快收",
        "macro": {"push": 78, "power": 42, "speed": 72, "steady": 86, "grip": 82, "outro": 12},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
    },
    "可怜·委屈": {
        "note": "内收、轻、颤",
        "macro": {"push": 15, "power": 26, "speed": 22, "steady": 62, "grip": 68, "outro": 22},
        "hold_seg": {"shape": "tremble", "pulse_rate": 18, "pulse_depth": 22, "swell": 8},
    },
    "要哭未哭": {
        "note": "更轻更慢、颤",
        "macro": {"push": 12, "power": 18, "speed": 16, "steady": 55, "grip": 52, "outro": 20},
        "hold_seg": {"shape": "tremble", "pulse_rate": 14, "pulse_depth": 16, "swell": 5},
    },
    "崩溃·泄劲": {
        "note": "内收、平顶下泄、快断",
        "macro": {"push": 10, "power": 22, "speed": 28, "steady": 52, "grip": 22, "outro": 8},
        "hold_seg": {"shape": "decay", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
    },
    "哀求·仰望": {
        "note": "内收、轻、慢收留韵",
        "macro": {"push": 8, "power": 32, "speed": 18, "steady": 70, "grip": 62, "outro": 78},
        "hold_seg": {"shape": "tremble", "pulse_rate": 12, "pulse_depth": 14, "swell": 12},
    },
    "惊惧·一怔": {
        "note": "急、中力、颤、快收",
        "macro": {"push": 38, "power": 58, "speed": 96, "steady": 58, "grip": 42, "outro": 14},
        "hold_seg": {"shape": "tremble", "pulse_rate": 28, "pulse_depth": 32, "swell": 0},
    },
    "魅惑·勾人": {
        "note": "外放、中力、脉冲更明显、粘、慢收",
        "macro": {"push": 72, "power": 62, "speed": 40, "steady": 70, "grip": 82, "outro": 72},
        "hold_seg": {"shape": "pulse", "pulse_rate": 46, "pulse_depth": 58, "swell": 32},
    },
    "纯甜·含情": {
        "note": "轻、慢脉冲、很粘、慢收",
        "macro": {"push": 65, "power": 32, "speed": 28, "steady": 74, "grip": 90, "outro": 82},
        "hold_seg": {"shape": "pulse", "pulse_rate": 32, "pulse_depth": 28, "swell": 18},
    },
    "媚杀·一眼": {
        "note": "较猛、中急、深脉冲",
        "macro": {"push": 76, "power": 80, "speed": 58, "steady": 88, "grip": 86, "outro": 42},
        "hold_seg": {"shape": "pulse", "pulse_rate": 44, "pulse_depth": 62, "swell": 22},
    },
    "若即若离": {
        "note": "飘、慢拱、留韵",
        "macro": {"push": 68, "power": 48, "speed": 35, "steady": 36, "grip": 48, "outro": 85},
        "hold_seg": {"shape": "swell", "pulse_rate": 22, "pulse_depth": 18, "swell": 65},
    },
    "打量·玩味": {
        "note": "中外放、慢拱、中等粘",
        "macro": {"push": 70, "power": 45, "speed": 30, "steady": 42, "grip": 72, "outro": 62},
        "hold_seg": {"shape": "swell", "pulse_rate": 18, "pulse_depth": 15, "swell": 42},
    },
    "空竭·死心": {
        "note": "轻、内收、下泄、慢散",
        "macro": {"push": 18, "power": 14, "speed": 24, "steady": 48, "grip": 18, "outro": 58},
        "hold_seg": {"shape": "decay", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
    },
}

NEUTRAL_PRESET: dict[str, Any] = {
    "macro": {"push": 50, "power": 50, "speed": 50, "steady": 50, "grip": 50, "outro": 50},
    "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
}

ZONES: dict[str, Any] = {
    "rise": {
        "title": "起",
        "sub": "上升沿 · 劲怎么甩出来",
        "knobs": [
            {"k": "macro", "id": "speed", "label": "起坡急缓", "lo": "缓", "hi": "急"},
            {"k": "macro", "id": "power", "label": "峰值力度", "lo": "轻", "hi": "猛"},
            {"k": "macro", "id": "push", "label": "往哪使劲", "lo": "内收", "hi": "外放"},
        ],
    },
    "move": {
        "title": "动",
        "sub": "平顶段 · 劲停住时长什么样",
        "shapes": True,
        "knobs": [
            {"k": "hold_seg", "id": "shape", "label": "花纹类型", "type": "shape"},
            {"k": "macro", "id": "steady", "label": "盯得稳", "lo": "飘", "hi": "钉死"},
            {"k": "macro", "id": "grip", "label": "定得住", "lo": "泄", "hi": "憋住"},
            {"k": "hold_seg", "id": "pulse_rate", "label": "勾得多密", "lo": "稀", "hi": "密", "ifShape": ["pulse"]},
            {"k": "hold_seg", "id": "pulse_depth", "label": "一波多深", "lo": "浅", "hi": "深", "ifShape": ["pulse"]},
            {"k": "hold_seg", "id": "swell", "label": "段内起伏", "lo": "平", "hi": "明显", "ifShape": ["swell", "pulse"]},
        ],
    },
    "fall": {
        "title": "收",
        "sub": "下降沿 · 劲怎么没",
        "knobs": [
            {"k": "macro", "id": "outro", "label": "收场快慢", "lo": "快落", "hi": "慢收"},
        ],
    },
}

SHAPE_OPTS: tuple[dict[str, str], ...] = (
    {"id": "flat", "label": "平顶"},
    {"id": "decay", "label": "下泄"},
    {"id": "swell", "label": "慢拱"},
    {"id": "pulse", "label": "脉冲"},
    {"id": "tremble", "label": "发颤"},
)

PIPE_TABS: tuple[dict[str, str], ...] = (
    {"id": "1_slider_packet", "title": "① 滑杆", "sub": "SliderPacket 真值"},
    {"id": "2_energy_envelope", "title": "② 包络", "sub": "能量曲线 E(t)"},
    {"id": "3_dense_from_envelope", "title": "③ 全量", "sub": "12×150 展开"},
    {"id": "4_dense_after_human_prior", "title": "④ 真人", "sub": "Human Prior 后"},
    {"id": "4b_pulse_quality_report", "title": "④b平庸", "sub": "修正日记"},
    {"id": "5_baked_02_delivery", "title": "⑤ 烘焙", "sub": "定稿直出"},
    {"id": "6_human_prior_report", "title": "报告", "sub": "prior+quality"},
)

WORKBENCH_STAGES: tuple[tuple[str, str], ...] = (
    ("queue", "排队"),
    ("bake", "烘焙 02"),
)

# 兼容旧名
ACTING_PULSE_PRESETS = PRESETS

def validate_preset(name: str, data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    macro = data.get("macro") or {}
    hold = data.get("hold_seg") or {}
    for k in MACRO_IDS:
        if k not in macro:
            issues.append(f"{name}: 缺 macro.{k}")
        elif not 0 <= int(macro[k]) <= 100:
            issues.append(f"{name}: macro.{k} 越界")
    for k in HOLD_IDS:
        if k not in hold:
            issues.append(f"{name}: 缺 hold_seg.{k}")
        elif k != "shape" and not 0 <= int(hold[k]) <= 100:
            issues.append(f"{name}: hold_seg.{k} 越界")
    sh = hold.get("shape")
    if sh not in VALID_SHAPES:
        issues.append(f"{name}: shape 非法 {sh!r}")
    if macro.get("push", 50) < 40 and sh == "flat" and macro.get("power", 0) > 80:
        issues.append(f"{name}: [语义] 内收却高力平顶，请核对")
    if macro.get("push", 50) > 75 and sh == "tremble" and macro.get("power", 0) < 35:
        issues.append(f"{name}: [语义] 外放颤却过轻，请核对")
    return issues

def validate_all() -> list[str]:
    out: list[str] = []
    for name, data in PRESETS.items():
        out.extend(validate_preset(name, data))
    return out

def packet_from_acting_preset(name: str) -> "SliderPacket":
    import json

    from asset_lib import HUMAN_PRESETS_DIR
    from gaze_engine._shared.emotion_pad import ensure_pad_on_packet
    from gaze_engine._shared.slider_schema import HoldSegment, MacroSliders, SliderPacket

    json_path = HUMAN_PRESETS_DIR / f"{name}.json"
    if json_path.is_file():
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        pkt = SliderPacket.from_dict(raw)
        if not pkt.emotion or pkt.emotion == "s01_pressure":
            pkt.emotion = name
        return ensure_pad_on_packet(pkt, "human")

    data = PRESETS.get(name)
    if not data:
        raise KeyError(f"未知预设: {name}，可选: {', '.join(PRESETS)}")
    pkt = SliderPacket(
        emotion=name,
        style="default",
        macro=MacroSliders(**data["macro"]),  # type: ignore[arg-type]
        hold_seg=HoldSegment(**data["hold_seg"]),  # type: ignore[arg-type]
    ).clamped()
    return ensure_pad_on_packet(pkt, "human")

def export_workbench_json() -> dict[str, Any]:
    """导出工作台 UI 数据。

    优先级：
      1. 预设资产/通用情绪预设/ 下的文件（可编辑，资产包优先）
      2. 本文件中的 Python 代码 PRESETS（回退）
    """
    from asset_lib import (
        load_generic_presets_from_files,
        load_generic_preset_groups_from_files,
        load_generic_preset_neutral_from_files,
    )

    file_presets = load_generic_presets_from_files()
    file_groups = load_generic_preset_groups_from_files()
    file_neutral = load_generic_preset_neutral_from_files()

    return {
        "schema": SCHEMA_ID,
        "source": "预设资产/human/" if file_presets else "gaze_engine/human/control_surface.py",
        "preset_groups": file_groups or [dict(g) for g in PRESET_GROUPS],
        "presets": file_presets or PRESETS,
        "neutral": file_neutral or NEUTRAL_PRESET,
        "zones": ZONES,
        "shape_opts": list(SHAPE_OPTS),
        "macro_ids": list(MACRO_IDS),
        "hold_ids": list(HOLD_IDS),
        "valid_shapes": sorted(VALID_SHAPES),
        "pipe_tabs": list(PIPE_TABS),
        "workbench_stages": [{"id": sid, "label": label} for sid, label in WORKBENCH_STAGES],
    }
