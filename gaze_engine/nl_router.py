"""客户自然语言入口：意图分离 → 咨询回复 或 生成滑杆包。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from gaze_engine.nl_intent import (
    INTENT_APPLY,
    INTENT_CONSULT,
    CustomerNLResult,
    classify_intent_keyword,
    normalize_intent,
)
from gaze_engine.nl_to_packet import _packet_keyword_fallback, match_preset_from_text
from gaze_engine._shared.slider_schema import SliderPacket

def load_internal_knowledge() -> str:
    """厂内知识库（客户画布不填）；来自已保存上下文或空。"""
    try:
        from gaze_engine._shared.workbench_context import read_workbench_context

        ctx = read_workbench_context()
        return str(ctx.get("knowledge_base") or "").strip()
    except Exception:
        return ""

def _consult_reply_keyword(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "请用一句话描述戏意，例如：「林青霞式施压瞬间凝视，更冷更钉」。"
    if "滑杆" in t or "宏观" in t:
        return (
            "【咨询】六根宏观滑杆：往哪使劲、力度、快慢、盯得稳、定得住、收场；"
            "盯住段还有形状（平顶/脉冲/发颤等）。"
            "若要出能量图，请直接描述表演，例如「更冷更钉的施压凝视」。"
        )
    if "预设" in t or "情绪" in t:
        from gaze_engine.human.control_surface import PRESETS as ACTING_PULSE_PRESETS

        names = "、".join(list(ACTING_PULSE_PRESETS.keys())[:6]) + "…"
        return f"【咨询】可选情绪预设共 16 个，例如：{names}。要生成请直接说戏意。"
    return (
        "【咨询】我是眼眉能量图助手：问概念可以；要生成/改戏请用表演语言描述，"
        "例如「可怜委屈、要哭未哭、更轻一点」。"
    )

def process_customer_nl(
    text: str,
    *,
    use_llm: bool | None = None,
    llm_model: str = "",
    force_intent: str = "",
    internal_knowledge: str = "",
) -> CustomerNLResult:
    """
    客户只给自然语言。
    - consult：只写回复，不改滑杆包（沿用已有 01_滑杆包.json）
    - apply：生成/修改滑杆包
    """
    from gaze_engine._shared.llm_openai import chatgpt_customer_nl, openai_configured

    nl = (text or "").strip()
    kb = (internal_knowledge or "").strip() or load_internal_knowledge()

    if force_intent and force_intent not in ("自动", "auto", ""):
        intent = normalize_intent(force_intent, text=nl)
        if intent == INTENT_CONSULT and not (use_llm and openai_configured()):
            return CustomerNLResult(
                intent=INTENT_CONSULT,
                reply=_consult_reply_keyword(nl),
                packet=None,
                meta={"intent_source": "force"},
            )

    want_llm = openai_configured() if use_llm is None else bool(use_llm)
    if want_llm and nl:
        try:
            return chatgpt_customer_nl(
                nl,
                knowledge_base=kb,
                model=llm_model or None,
                force_intent=force_intent,
            )
        except Exception:
            if use_llm is True:
                raise

    intent = normalize_intent(force_intent, text=nl) if force_intent not in ("", "自动", "auto") else classify_intent_keyword(nl)
    if intent == INTENT_CONSULT:
        return CustomerNLResult(
            intent=INTENT_CONSULT,
            reply=_consult_reply_keyword(nl),
            packet=None,
            meta={"intent_source": "keyword"},
        )
    pkt = _packet_keyword_fallback(nl)
    return CustomerNLResult(
        intent=INTENT_APPLY,
        reply=f"【已生成】预设「{pkt.emotion}」（关键词回退）",
        packet=pkt,
        meta={"intent_source": "keyword", "preset": pkt.emotion},
    )

def resolve_packet_path_after_consult(cmd_dir: Path) -> str:
    """咨询模式：沿用已有滑杆包路径。"""
    p = cmd_dir / "01_滑杆包.json"
    if p.is_file():
        return str(p.resolve())
    return ""
