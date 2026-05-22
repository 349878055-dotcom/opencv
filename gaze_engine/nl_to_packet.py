"""自然语言 → SliderPacket（ChatGPT 或关键词回退）。"""
from __future__ import annotations

import re
from typing import Any

from gaze_engine.control_surface import PRESETS as ACTING_PULSE_PRESETS, packet_from_acting_preset
from gaze_engine.slider_schema import SliderPacket

# 关键词 → 预设名（先匹配长的）
_KEYWORDS: list[tuple[str, str]] = [
    ("冷压", "冷压·决心"),
    ("威慑", "威慑·一瞬"),
    ("怒视", "怒视·压人"),
    ("鄙夷", "鄙夷·冷瞥"),
    ("要哭未哭", "要哭未哭"),
    ("崩溃", "崩溃·泄劲"),
    ("哀求", "哀求·仰望"),
    ("惊惧", "惊惧·一怔"),
    ("空竭", "空竭·死心"),
    ("死心", "空竭·死心"),
    ("媚杀", "媚杀·一眼"),
    ("纯甜", "纯甜·含情"),
    ("魅惑", "魅惑·勾人"),
    ("若即若离", "若即若离"),
    ("打量", "打量·玩味"),
    ("玩味", "打量·玩味"),
    ("可怜", "可怜·委屈"),
    ("委屈", "可怜·委屈"),
    ("施压", "施压·凝视"),
    ("凝视", "施压·凝视"),
    ("盯", "施压·凝视"),
    ("瞪", "怒视·压人"),
]

def match_preset_from_text(text: str) -> str:
    t = (text or "").strip()
    for name in ACTING_PULSE_PRESETS:
        if name in t:
            return name
    for kw, name in _KEYWORDS:
        if kw in t:
            return name
    return "施压·凝视"

def _packet_keyword_fallback(text: str, *, preset_hint: str = "") -> SliderPacket:
    hint = (preset_hint or "").strip()
    if hint and hint in ACTING_PULSE_PRESETS:
        pkt = packet_from_acting_preset(hint)
    else:
        pkt = packet_from_acting_preset(match_preset_from_text(text))
    pkt = pkt.clamped()
    if text.strip() and not pkt.emotion:
        pkt.emotion = match_preset_from_text(text)
    return pkt

def packet_from_natural_language(
    text: str,
    *,
    preset_hint: str = "",
    use_llm: bool | None = None,
    knowledge_base: str = "",
    llm_model: str = "",
) -> SliderPacket:
    """自然语言 → 滑杆包。use_llm=None 时：有 OPENAI_API_KEY 则用 ChatGPT。"""
    from gaze_engine.llm_openai import chatgpt_nl_to_packet, openai_configured

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
