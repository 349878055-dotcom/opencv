"""控制面定义 · UI 结构（预设、分区、工作台）。

PRESETS 硬编码 dict 已删除 —— 唯一真源为 `预设资产/情绪包/{species}/{emotion}.json`。
"""
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
    """从 预设资产 JSON 加载全部预设并校验。"""
    from asset_lib import load_species_presets

    out: list[str] = []
    presets = load_species_presets("human") or {}
    for name, data in presets.items():
        out.extend(validate_preset(name, data))
    return out


def packet_from_acting_preset(name: str) -> "SliderPacket":
    """从 预设资产 JSON 加载预设 SliderPacket。

    唯一真源为 `预设资产/情绪包/{name}.json`，无代码回退。
    """
    from asset_lib import HUMAN_PRESETS_DIR, is_valid_preset
    from gaze_engine.envelope.emotion_pad import ensure_pad_on_packet
    from gaze_engine.input.slider_schema import SliderPacket

    if not is_valid_preset("human", name):
        raise KeyError(f"未知预设: {name}，JSON 文件不存在于 {HUMAN_PRESETS_DIR}")

    from asset_lib import load_emotion_slider_packet

    pkt = load_emotion_slider_packet("human", name)
    if pkt is None:
        raise KeyError(f"预设 {name} JSON 加载失败")
    return ensure_pad_on_packet(pkt, "human")


def export_workbench_json() -> dict[str, Any]:
    """导出工作台 UI 数据，唯一真源为 `预设资产/` 下的 JSON 文件。"""
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
        "source": "预设资产/情绪包/",
        "preset_groups": file_groups or [dict(g) for g in PRESET_GROUPS],
        "presets": file_presets or {},
        "neutral": file_neutral or {},
        "zones": ZONES,
        "shape_opts": list(SHAPE_OPTS),
        "macro_ids": list(MACRO_IDS),
        "hold_ids": list(HOLD_IDS),
        "valid_shapes": sorted(VALID_SHAPES),
        "pipe_tabs": list(PIPE_TABS),
        "workbench_stages": [{"id": sid, "label": label} for sid, label in WORKBENCH_STAGES],
    }
