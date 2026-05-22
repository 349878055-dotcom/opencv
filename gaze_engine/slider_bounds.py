"""
滑杆禁区 L1 · 机器真源（合同：contracts/滑杆规范.md §10）

预设中心值来自 control_surface.py；半径与 G 条在此模块。
改规则后运行：python3 scripts/export_slider_forbidden_js.py
"""
from __future__ import annotations

from typing import Any

from gaze_engine.control_surface import PRESETS as ACTING_PULSE_PRESETS, MACRO_IDS

MACRO_RADIUS_DEFAULT = 22

MOOD_GROUPS: dict[str, dict[str, Any]] = {
    "压·慑": {
        "presets": ["施压·凝视", "冷压·决心", "威慑·一瞬", "怒视·压人", "鄙夷·冷瞥"],
        "radius": 18,
        "macro_min_default": {"push": 58, "power": 70, "speed": 55, "steady": 72, "grip": 62},
        "macro_max_default": {"outro": 58},
        "allowed_shapes": ["flat"],
    },
    "悲·怯": {
        "presets": ["可怜·委屈", "要哭未哭", "崩溃·泄劲", "哀求·仰望", "惊惧·一怔", "空竭·死心"],
        "radius": 22,
        "macro_max_default": {"push": 48, "power": 58, "speed": 55, "steady": 88},
        "macro_min_default": {"outro": 0},
        "allowed_shapes": ["tremble", "decay"],
    },
    "媚·勾": {
        "presets": ["魅惑·勾人", "纯甜·含情", "媚杀·一眼", "若即若离", "打量·玩味"],
        "radius": 20,
        "macro_min_default": {"pulse_rate": 10, "pulse_depth": 8},
        "allowed_shapes": ["pulse", "swell"],
    },
}

PRESET_OVERRIDES: dict[str, dict[str, Any]] = {
    "鄙夷·冷瞥": {"macro_min": {"power": 28, "push": 58}},
    "威慑·一瞬": {"macro_min": {"speed": 78}, "macro_max": {"outro": 28}},
    "冷压·决心": {"macro_min": {"power": 78, "speed": 52}},
    "要哭未哭": {"macro_max": {"power": 42, "push": 32}},
    "崩溃·泄劲": {"allowed_shapes": ["decay", "tremble"], "macro_max": {"grip": 38}},
    "空竭·死心": {"allowed_shapes": ["decay"]},
    "惊惧·一怔": {"macro_min": {"speed": 78}, "macro_max": {"outro": 32}},
    "纯甜·含情": {"macro_max": {"power": 52}},
    "媚杀·一眼": {"macro_min": {"power": 62}, "macro_max": {"power": 100}},
    "若即若离": {"allowed_shapes": ["swell", "pulse"], "macro_max": {"steady": 58}},
    "打量·玩味": {"allowed_shapes": ["swell", "pulse"]},
}

GLOBAL_FIXES: list[dict[str, Any]] = [
    {"id": "G1路人中间带", "dead_zone": True},
    {
        "id": "G2急但无力",
        "when": {"macro.speed_min": 82, "macro.power_max": 28},
        "set_macro_min": {"power": 40},
    },
    {
        "id": "G3狠却飘",
        "when": {"macro.power_min": 75, "macro.steady_max": 28},
        "set_macro_min": {"steady": 45},
    },
    {
        "id": "G4钉却泄",
        "when": {"macro.steady_min": 80, "macro.grip_max": 25},
        "set_macro_min": {"grip": 30},
    },
    {
        "id": "G5平顶开脉冲",
        "when": {"hold_seg.shape": "flat", "hold_seg.pulse_rate_min": 1},
        "set": {"hold_seg.pulse_rate": 0, "hold_seg.pulse_depth": 0},
    },
    {
        "id": "G6非脉冲留脉冲",
        "when": {"hold_seg.shape_not": "pulse", "hold_seg.pulse_depth_min": 1},
        "set": {"hold_seg.pulse_rate": 0, "hold_seg.pulse_depth": 0},
    },
    {
        "id": "G7急收打架",
        "when": {"macro.speed_min": 85, "macro.outro_min": 75},
        "set_macro_max": {"outro": 55},
    },
    {
        "id": "G8内收外猛",
        "when": {"macro.push_max": 25, "macro.power_min": 80},
        "set_macro_max": {"power": 55},
    },
]

DEAD_ZONE: dict[str, Any] = {
    "macro_low": 42,
    "macro_high": 58,
    "all_six_in_zone": True,
    "fix": "reset_macro_to_preset_default",
}

def _clamp_range(lo: int, hi: int) -> tuple[int, int]:
    return max(0, lo), min(100, hi)

def build_preset_box(name: str, data: dict[str, Any], group: dict[str, Any]) -> dict[str, Any]:
    r = int(group["radius"])
    macro = data["macro"]
    hold = data["hold_seg"]
    macro_min: dict[str, int] = {}
    macro_max: dict[str, int] = {}
    for k in MACRO_IDS:
        c = int(macro[k])
        lo, hi = _clamp_range(c - r, c + r)
        macro_min[k] = lo
        macro_max[k] = hi
    for k, v in (group.get("macro_min_default") or {}).items():
        macro_min[k] = max(macro_min.get(k, 0), int(v))
    for k, v in (group.get("macro_max_default") or {}).items():
        macro_max[k] = min(macro_max.get(k, 100), int(v))
    ov = PRESET_OVERRIDES.get(name) or {}
    for k, v in (ov.get("macro_min") or {}).items():
        macro_min[k] = max(macro_min.get(k, 0), int(v))
    for k, v in (ov.get("macro_max") or {}).items():
        macro_max[k] = min(macro_max.get(k, 100), int(v))
    for k in MACRO_IDS:
        if macro_min[k] > macro_max[k]:
            macro_min[k] = macro_max[k]

    shapes = list(ov.get("allowed_shapes") or group.get("allowed_shapes") or [hold["shape"]])
    if hold["shape"] not in shapes:
        shapes = [hold["shape"]] + shapes

    hold_min = {"pulse_rate": 0, "pulse_depth": 0, "swell": 0}
    hold_max = {"pulse_rate": 100, "pulse_depth": 100, "swell": 100}
    if hold["shape"] == "pulse":
        hold_min["pulse_rate"] = 12
        hold_min["pulse_depth"] = 10
    if hold["shape"] == "swell":
        hold_min["swell"] = 20

    return {
        "group": next(g for g, gd in MOOD_GROUPS.items() if name in gd["presets"]),
        "macro_min": macro_min,
        "macro_max": macro_max,
        "hold_seg_min": hold_min,
        "hold_seg_max": hold_max,
        "allowed_shapes": shapes,
    }

def load_rules() -> dict[str, Any]:
    """供 packet_finalize / 工作台 JS 导出使用。"""
    preset_to_group = {n: g for g, gd in MOOD_GROUPS.items() for n in gd["presets"]}
    presets: dict[str, dict[str, Any]] = {}
    for name, data in ACTING_PULSE_PRESETS.items():
        g = preset_to_group.get(name)
        if not g:
            continue
        presets[name] = build_preset_box(name, data, MOOD_GROUPS[g])

    return {
        "schema": "slider-forbidden-v1",
        "_doc": "contracts/滑杆规范.md §10 · gaze_engine/slider_bounds.py",
        "dead_zone": DEAD_ZONE,
        "mood_groups": {
            k: {"presets": v["presets"], "allowed_shapes": v.get("allowed_shapes")}
            for k, v in MOOD_GROUPS.items()
        },
        "presets": presets,
        "global_fixes": GLOBAL_FIXES,
    }
