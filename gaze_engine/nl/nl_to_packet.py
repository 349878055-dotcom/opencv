"""自然语言 → SliderPacket（ChatGPT 或关键词回退 + 强度修饰解析）。"""
from __future__ import annotations

import re
from typing import Any

from asset_lib import load_species_presets
from gaze_engine.input.control_surface import packet_from_acting_preset
from gaze_engine.input.slider_schema import HOLD_IDS, MACRO_IDS, HoldSegment, MacroSliders, SliderPacket, apply_macro_delta

# ─── 关键词 → 预设名（先匹配长的） ───────────────────────────
_KEYWORDS: list[tuple[str, str]] = [
    ("冷压", "冷压·决心"),
    ("决心", "冷压·决心"),
    ("威慑", "威慑·一瞬"),
    ("一瞬", "威慑·一瞬"),
    ("怒视", "怒视·压人"),
    ("鄙夷", "鄙夷·冷瞥"),
    ("冷瞥", "鄙夷·冷瞥"),
    ("瞥", "鄙夷·冷瞥"),
    ("要哭未哭", "要哭未哭"),
    ("崩溃", "崩溃·泄劲"),
    ("泄劲", "崩溃·泄劲"),
    ("哀求", "哀求·仰望"),
    ("仰望", "哀求·仰望"),
    ("惊惧", "惊惧·一怔"),
    ("一怔", "惊惧·一怔"),
    ("空竭", "空竭·死心"),
    ("死心", "空竭·死心"),
    ("媚杀", "媚杀·一眼"),
    ("一眼", "媚杀·一眼"),
    ("纯甜", "纯甜·含情"),
    ("含情", "纯甜·含情"),
    ("魅惑", "魅惑·勾人"),
    ("勾人", "魅惑·勾人"),
    ("若即若离", "若即若离"),
    ("打量", "打量·玩味"),
    ("玩味", "打量·玩味"),
    ("可怜", "可怜·委屈"),
    ("委屈", "可怜·委屈"),
    ("施压", "施压·凝视"),
    ("凝视", "施压·凝视"),
    ("盯", "施压·凝视"),
    ("瞪", "怒视·压人"),
    ("外放", "施压·凝视"),
    ("内收", "可怜·委屈"),
]

# ─── 强度修饰语 → macro delta 规则 ──────────────────────
# 来源：prompts/node1_knowledge_base.txt 「说法→编译」
_MODIFIER_RULES: list[tuple[str, dict[str, int]]] = [
    # 冷·钉·狠系列
    ("更冷",      {"power": 8, "steady": 6, "grip": 7}),
    ("更钉",      {"steady": 8, "grip": 8}),
    ("更狠",      {"power": 10, "push": 5}),
    ("再冷",      {"power": 5, "steady": 5, "grip": 5}),
    ("再钉",      {"steady": 6, "grip": 6}),
    ("再狠",      {"power": 8, "push": 4}),
    # 轻·可怜系列
    ("更轻",      {"power": -10, "push": -8}),
    ("再轻",      {"power": -8, "push": -6}),
    ("更可怜",    {"power": -8, "push": -8}),
    ("再可怜",    {"power": -5, "push": -5}),
    # 急·快系列
    ("更急",      {"speed": 10}),
    ("再急",      {"speed": 8}),
    ("一瞬间",    {"speed": 15, "outro": -10}),
    ("更快",      {"speed": 8}),
    ("再快",      {"speed": 6}),
    # 慢系列
    ("更慢",      {"speed": -8, "outro": 5}),
    ("再慢",      {"speed": -6}),
    ("慢勾",      {"speed": -10, "steady": -6}),
    ("慢拱",      {"speed": -8, "steady": -8}),
    # 稳·颤系列
    ("更稳",      {"steady": 8, "grip": 6}),
    ("再稳",      {"steady": 6}),
    ("别颤",      {"steady": 10, "grip": 8}),
    ("不颤",      {"steady": 8, "grip": 6}),
    ("更颤",      {"steady": -8, "grip": -6}),
    ("再颤",      {"steady": -6}),
    # 收场系列
    ("快收",      {"outro": -10}),
    ("再快收",    {"outro": -15}),
    ("慢收",      {"outro": 10}),
    ("再慢收",    {"outro": 8}),
    ("留韵",      {"outro": 15}),
    ("留尾",      {"outro": 12}),
    # 力度系列
    ("更猛",      {"power": 10, "push": 5}),
    ("再猛",      {"power": 8}),
    ("更外放",    {"push": 10, "power": 5}),
    ("再外放",    {"push": 8}),
    ("更内收",    {"push": -10, "power": -5}),
    ("再内收",    {"push": -8}),
    # 脉冲系列
    ("脉冲更密",  {"pulse_rate": 10}),
    ("更密",      {"pulse_rate": 8}),
    ("再密",      {"pulse_rate": 6}),
    ("更深",      {"pulse_depth": 10}),
    ("再深",      {"pulse_depth": 8}),
    ("更浅",      {"pulse_depth": -10}),
    ("再浅",      {"pulse_depth": -8}),
    # 通用「再X一点」「更X一些」回退（最后匹配）
    ("再",        {"power": 5, "speed": 3}),  # 通用增强
    ("更",        {"power": 5, "speed": 3}),  # 通用增强
]

# 「再X一点 / 更X一些」动态模式（只匹配单字，不贪婪）
_RE_MODIFIER_PATTERN = re.compile(r"(再|更)(\w)一?[点些]?")


def match_preset_from_text(text: str) -> str:
    """先精确匹配预设全名，再关键词匹配，最后回退到默认。"""
    t = (text or "").strip()
    presets = load_species_presets("human") or {}
    for name in presets:
        if name in t:
            return name
    for kw, name in _KEYWORDS:
        if kw in t:
            return name
    return "施压·凝视"


def _parse_modifiers(text: str) -> dict[str, int]:
    """解析自然语言中的强度修饰语 → macro delta 字典。"""
    if not text:
        return {}
    t = text.strip()

    # ── 单字→delta 映射（用于动态「再X一点」匹配）──
    _CHAR_DELTA: dict[str, dict[str, int]] = {
        "钉": {"steady": 6, "grip": 6},
        "冷": {"power": 5, "steady": 4, "grip": 4},
        "狠": {"power": 8, "push": 4},
        "轻": {"power": -8, "push": -6},
        "快": {"speed": 6, "outro": -5},
        "慢": {"speed": -6},
        "稳": {"steady": 6, "grip": 4},
        "颤": {"steady": -6, "grip": -4},
        "猛": {"power": 8, "push": 4},
        "深": {"pulse_depth": 8},
        "密": {"pulse_rate": 6},
        "浅": {"pulse_depth": -8},
        "收": {"outro": -6},
        "外": {"push": 6},
        "内": {"push": -6},
    }

    # 1. 匹配具体规则（长模式优先，子串排重）
    deltas: list[dict[str, int]] = []
    occupied: set[str] = set()  # 已被更长模式覆盖的短模式，不再匹配
    sorted_rules = sorted(
        [(p, d) for p, d in _MODIFIER_RULES if p not in ("更", "再")],
        key=lambda x: -len(x[0]),
    )
    for pattern, delta in sorted_rules:
        if pattern in occupied:
            continue
        if pattern in t:
            deltas.append(delta)
            # 将当前 pattern 的所有子串（其他规则）标记为已占用
            for other_p, _ in _MODIFIER_RULES:
                if other_p != pattern and other_p in pattern and other_p not in ("更", "再"):
                    occupied.add(other_p)

    # 收集已匹配的"更X""再X"用于后续判断
    matched_geng_zai: set[str] = {
        p for p, _ in _MODIFIER_RULES
        if len(p) >= 2 and (p.startswith("更") or p.startswith("再")) and p in t and p not in occupied
    }

    # 2. 通用"更"/"再"回退（仅当无特定"更X""再X"匹配时）
    #    注意：已占用的模式（如"更密"被"脉冲更密"占用）也要算作已匹配
    has_geng = any(p.startswith("更") for p in matched_geng_zai) or any(p.startswith("更") for p in occupied)
    has_zai = any(p.startswith("再") for p in matched_geng_zai) or any(p.startswith("再") for p in occupied)
    if "更" in t and not has_geng:
        deltas.append({"power": 3, "speed": 2})
    if "再" in t and not has_zai:
        deltas.append({"power": 3, "speed": 2})

    # 3. 动态「再X一点/更X一些」单字回退
    for match in _RE_MODIFIER_PATTERN.finditer(t):
        prefix = match.group(1)
        char = match.group(2)
        full = f"{prefix}{char}"
        if full in matched_geng_zai:
            continue
        if char in _CHAR_DELTA:
            deltas.append(_CHAR_DELTA[char])

    # 4. 合并所有 delta
    merged: dict[str, int] = {}
    for d in deltas:
        for k, v in d.items():
            merged[k] = merged.get(k, 0) + v
    return merged

    # 3. 合并所有 delta
    merged: dict[str, int] = {}
    for d in deltas:
        for k, v in d.items():
            merged[k] = merged.get(k, 0) + v
    return merged


def _packet_keyword_fallback(text: str, *, preset_hint: str = "") -> SliderPacket:
    """关键词回退 + 强度修饰语 delta 叠加。"""
    hint = (preset_hint or "").strip()
    if hint:
        from asset_lib import is_valid_preset
        if is_valid_preset("human", hint):
            pkt = packet_from_acting_preset(hint)
    else:
        pkt = packet_from_acting_preset(match_preset_from_text(text))
    pkt = pkt.clamped()
    if text.strip() and not pkt.emotion:
        pkt.emotion = match_preset_from_text(text)

    # 应用强度修饰 delta
    delta = _parse_modifiers(text)
    if delta:
        # 分离 macro delta 和 hold_seg delta
        macro_d = {k: v for k, v in delta.items() if k in MACRO_IDS}
        hold_d = {k: v for k, v in delta.items() if k in HOLD_IDS}
        if macro_d:
            pkt.macro = apply_macro_delta(pkt.macro, macro_d)
        if hold_d:
            hs = pkt.hold_seg
            hd = {"pulse_rate": hs.pulse_rate, "pulse_depth": hs.pulse_depth, "swell": hs.swell}
            for k, v in hold_d.items():
                if k in hd:
                    hd[k] = max(0, min(100, hd[k] + v))
            pkt.hold_seg = HoldSegment(
                shape=hs.shape,
                pulse_rate=hd["pulse_rate"],
                pulse_depth=hd["pulse_depth"],
                swell=hd["swell"],
            )

    return pkt.clamped()

def packet_from_natural_language(
    text: str,
    *,
    preset_hint: str = "",
    use_llm: bool | None = None,
    knowledge_base: str = "",
    llm_model: str = "",
) -> SliderPacket:
    """自然语言 → 滑杆包。use_llm=None 时：有 OPENAI_API_KEY 则用 ChatGPT。"""
    from gaze_engine._shared.llm_openai import chatgpt_nl_to_packet, openai_configured

    want_llm = openai_configured() if use_llm is None else bool(use_llm)
    if want_llm and text.strip():
        try:
            pkt, meta = chatgpt_nl_to_packet(
                text,
                preset_hint=preset_hint,
                knowledge_base=knowledge_base,
                model=llm_model or None,
            )
            pkt._llm_meta = meta  # type: ignore[attr-defined]
            return pkt
        except Exception:
            if use_llm is True:
                raise
    return _packet_keyword_fallback(text, preset_hint=preset_hint)

def pop_llm_meta(packet: SliderPacket) -> dict[str, Any]:
    meta = getattr(packet, "_llm_meta", None)
    if isinstance(meta, dict):
        return meta
    return {}
