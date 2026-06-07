"""OpenAI 语言模型 → SliderPacket（自然语言→能量图/滑杆，非扩散成片）。"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Any

from asset_lib import is_valid_preset, load_species_presets
from gaze_engine.input.control_surface import packet_from_acting_preset
from gaze_engine.nl.nl_to_packet import match_preset_from_text
from gaze_engine.input.slider_schema import HOLD_IDS, MACRO_IDS, HoldSegment, SliderPacket, apply_llm_delta

DEFAULT_MODEL = os.environ.get("ECURSOR_OPENAI_MODEL", "gpt-4o-mini")
CHEAP_MODEL = os.environ.get("ECURSOR_CHEAP_MODEL", "gpt-4o-mini")  # 非关键任务用轻量模型省Token

def openai_configured() -> bool:
    return bool((os.environ.get("OPENAI_API_KEY") or "").strip())

def _preset_list() -> str:
    presets = load_species_presets("human") or {}
    return "、".join(presets.keys())

def _router_system_prompt() -> str:
    """紧凑版系统Prompt（比 prompts/node1_system_prompt.txt 更短, 回退用）。"""
    return f"""你是ecursor眼眉编译器。边界: 只产滑杆JSON, 不碰扩散/摄影机/整脸。

【意图】consult=只reply; apply=编译JSON。拿不准→consult。

【预设】{_preset_list()}

【apply】选预设+macro。修改轮:有"刚才/更/再"→macro_delta,单轮改1-2键。

【macro 0-100】push内收↔外放 power轻↔狠 speed慢↔急 steady飘↔钉 grip泄↔憋 outro快收↔慢收
【hold_seg】shape:flat|decay|swell|pulse|tremble

输出仅JSON:
{{"intent":"consult|apply","reply":"中文","preset":"仅apply","macro":{{"push":0,"power":0,"speed":0,"steady":0,"grip":0,"outro":0}},"macro_delta":{{"power":"+5"}},"hold_seg":{{"shape":"flat","pulse_rate":0,"pulse_depth":0,"swell":0}},"energy_map_note":"仅apply"}}"""

def _extract_json(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    if not t:
        raise ValueError("模型返回为空")
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
    if fence:
        t = fence.group(1).strip()
    return json.loads(t)

def _packet_from_llm_apply_json(
    data: dict[str, Any],
    text: str,
    *,
    preset_hint: str = "",
    base_packet: SliderPacket | None = None,
) -> tuple[SliderPacket, dict[str, Any]]:
    preset = str(data.get("preset") or preset_hint or "").strip()
    if base_packet is not None:
        pkt = SliderPacket.from_dict(base_packet.to_dict())
        if preset and is_valid_preset("human", preset) and preset != pkt.emotion:
            pkt = packet_from_acting_preset(preset)
    else:
        preset = preset or match_preset_from_text(text)
        if not is_valid_preset("human", preset):
            preset = match_preset_from_text(preset + " " + text)
        pkt = packet_from_acting_preset(preset)

    macro = data.get("macro")
    if isinstance(macro, dict) and macro:
        d = {k: int(macro[k]) for k in MACRO_IDS if k in macro}
        if d:
            from gaze_engine.input.slider_schema import MacroSliders

            pkt.macro = MacroSliders(**{**{k: getattr(pkt.macro, k) for k in MACRO_IDS}, **d})  # type: ignore[arg-type]

    delta = data.get("macro_delta")
    if isinstance(delta, dict) and delta:
        pkt = apply_llm_delta(pkt, delta)

    hold = data.get("hold_seg")
    if isinstance(hold, dict) and hold:
        hs = asdict(pkt.hold_seg)
        for k in HOLD_IDS:
            if k in hold:
                hs[k] = hold[k]
        pkt.hold_seg = HoldSegment(**hs)  # type: ignore[arg-type]

    pkt = pkt.clamped()
    if not preset or not is_valid_preset("human", preset):
        preset = pkt.emotion
    note = str(
        data.get("energy_map_note") or data.get("diffusion_prompt") or ""
    ).strip()
    meta = {
        "preset": preset,
        "energy_map_note": note,
    }
    return pkt, meta

def resolve_node1_system_prompt(custom: str) -> str:
    """留空 → prompts/node1_system_prompt.txt → 短内置回退。"""
    from gaze_engine.input.node1_defaults import default_system_prompt_text, resolve_system_prompt_input

    t = resolve_system_prompt_input(custom)
    if t:
        return t
    file_default = default_system_prompt_text()
    if file_default:
        return file_default
    return _router_system_prompt()

def chatgpt_node1(
    customer_nl: str,
    *,
    system_prompt: str = "",
    knowledge_base: str = "",
    model: str | None = None,
    previous_packet: SliderPacket | None = None,
) -> "CustomerNLResult":
    """节点 1：系统 Prompt + 知识库 + 历史滑杆 + 客户话。"""
    return chatgpt_customer_nl(
        customer_nl,
        system_prompt=system_prompt,
        knowledge_base=knowledge_base,
        model=model,
        previous_packet=previous_packet,
    )

def chatgpt_customer_nl(
    text: str,
    *,
    system_prompt: str = "",
    knowledge_base: str = "",
    model: str | None = None,
    force_intent: str = "",
    previous_packet: SliderPacket | None = None,
) -> "CustomerNLResult":
    """意图分离 + 咨询或生成。返回 CustomerNLResult。"""
    from gaze_engine.nl.nl_intent import INTENT_APPLY, INTENT_CONSULT, CustomerNLResult, normalize_intent

    if not openai_configured():
        raise RuntimeError("未设置 OPENAI_API_KEY（见 scripts/s01_设置OpenAI密钥.sh）")

    from openai import OpenAI

    from gaze_engine.input.node1_defaults import format_previous_packet_for_llm, resolve_knowledge_base

    nl = (text or "").strip()
    kb = resolve_knowledge_base(knowledge_base)

    # --- 模型分档：consult 用轻量模型省 Token ---
    model = model or DEFAULT_MODEL
    is_consult_only = force_intent in ("consult",)
    cheap_model = CHEAP_MODEL if is_consult_only and CHEAP_MODEL != model else model

    user_parts = [f"客户自然语言：\n{nl}"]
    kb_limit = 4000 if model == CHEAP_MODEL else 8000  # 轻量模型上下文窄，知识库截短
    if kb:
        user_parts.append(f"知识库：\n{kb[:kb_limit]}")
    if previous_packet is not None:
        user_parts.append(
            "当前滑杆包（上一轮，修改请在此基础上用 macro_delta，勿无故换 preset）：\n"
            + format_previous_packet_for_llm(previous_packet)
        )
    if force_intent and force_intent not in ("自动", "auto", ""):
        user_parts.append(f"强制意图：{force_intent}")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=cheap_model,
        temperature=0.35,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": resolve_node1_system_prompt(system_prompt)},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
    )
    used_model = cheap_model
    raw = (resp.choices[0].message.content or "").strip()
    data = _extract_json(raw)

    intent = normalize_intent(str(data.get("intent") or ""), text=nl)
    if force_intent and force_intent not in ("自动", "auto", ""):
        intent = normalize_intent(force_intent, text=nl)

    reply = str(data.get("reply") or "").strip() or "（模型未返回 reply）"
    meta: dict[str, Any] = {
        "llm": "openai",
        "model": used_model,
        "intent": intent,
        "intent_source": "llm",
        "raw_keys": list(data.keys()),
    }

    if intent == INTENT_CONSULT:
        return CustomerNLResult(intent=INTENT_CONSULT, reply=reply, packet=None, meta=meta)

    pkt, apply_meta = _packet_from_llm_apply_json(
        data, nl, base_packet=previous_packet
    )
    meta.update(apply_meta)
    if not reply.startswith("【"):
        reply = f"【已生成】预设「{pkt.emotion}」。{reply}"
    return CustomerNLResult(intent=INTENT_APPLY, reply=reply, packet=pkt, meta=meta)

def _apply_system_prompt() -> str:
    """apply模式专用系统Prompt（比全量路由版更轻量）。"""
    return f"""你是ecursor眼眉编译器。只产滑杆JSON,不碰扩散/摄影机/整脸。

【预设】{_preset_list()}

【说法映射】更冷/更钉/更狠→power↑steady↑grip↑ 更轻→power↓push↓ 更急→speed↑ 别颤→steady↑ 慢勾→魅惑·勾人

输出JSON:
{{"preset":"预设全名","macro":{{"push":0-100,"power":0-100,"speed":0-100,"steady":0-100,"grip":0-100,"outro":0-100}},"macro_delta":{{"power":"+5"}},"hold_seg":{{"shape":"flat|decay|swell|pulse|tremble","pulse_rate":0-100,"pulse_depth":0-100,"swell":0-100}},"energy_map_note":"可选"}}

先选最近预设再微调。macro 0-100整数。"""


def _cheap_apply_system_prompt() -> str:
    """超轻量版（配合 CHEAP_MODEL 用, ~50 tokens）。"""
    p = _preset_list()
    return f"你是眼眉编译器。预设:{p}。说法:更冷=power↑steady↑,更轻=power↓push↓,更急=speed↑,别颤=steady↑。输出JSON:{{preset,macro(0-100各键),hold_seg,energy_map_note}}。不碰扩散/摄影机。"

def chatgpt_nl_to_packet(
    text: str,
    *,
    preset_hint: str = "",
    knowledge_base: str = "",
    model: str | None = None,
    use_cheap: bool = False,
) -> tuple[SliderPacket, dict[str, Any]]:
    """自然语言 → 滑杆包（节点 1 主路径）。
    
    use_cheap=True 时使用 CHEAP_MODEL + 精简 Prompt，适用于关键词回退等简单场景。
    """
    if not openai_configured():
        raise RuntimeError("未设置 OPENAI_API_KEY（见 scripts/s01_设置OpenAI密钥.sh）")

    from openai import OpenAI

    nl = (text or "").strip()
    model = model or (CHEAP_MODEL if use_cheap else DEFAULT_MODEL)
    prompt_fn = _cheap_apply_system_prompt if use_cheap else _apply_system_prompt

    user_parts = [f"客户自然语言：\n{nl}"]
    if preset_hint.strip() and is_valid_preset("human", preset_hint):
        user_parts.append(f"预设提示：{preset_hint}")
    kb_limit = 2000 if use_cheap else 4000
    if knowledge_base.strip():
        user_parts.append(f"厂内参考：\n{knowledge_base.strip()[:kb_limit]}")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=model,
        temperature=0.35,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt_fn()},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = _extract_json(raw)
    pkt, apply_meta = _packet_from_llm_apply_json(data, nl, preset_hint=preset_hint)
    meta = {
        "llm": "openai",
        "model": model,
        **apply_meta,
    }
    return pkt, meta
