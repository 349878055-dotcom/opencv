"""OpenAI 语言模型 → SliderPacket（自然语言→能量图/滑杆，非扩散成片）。"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Any

from gaze_engine.control_surface import PRESETS as ACTING_PULSE_PRESETS, packet_from_acting_preset
from gaze_engine.nl_to_packet import match_preset_from_text
from gaze_engine.slider_schema import HOLD_IDS, MACRO_IDS, HoldSegment, SliderPacket, apply_llm_delta

DEFAULT_MODEL = os.environ.get("ECURSOR_OPENAI_MODEL", "gpt-4o-mini")

def openai_configured() -> bool:
    return bool((os.environ.get("OPENAI_API_KEY") or "").strip())

def _preset_list() -> str:
    return "、".join(ACTING_PULSE_PRESETS.keys())

def _router_system_prompt() -> str:
    return f"""你是 ecursor 眼眉「自然语言→能量图」助手（不是视频扩散、不是整脸生成）。

客户只有自然语言。你必须先做 **意图分离**，再行动：

| intent | 何时选 | 做什么 |
|--------|--------|--------|
| consult | 问概念、问怎么调、问预设区别、不确定、纯聊天 | 只回答，不编滑杆 |
| apply | 描述一段戏、要生成/改成/更冷更钉等可执行戏意 | 编译滑杆 JSON |

可选情绪预设（apply 时 preset 必须从中选一）：{_preset_list()}

输出必须是单个 JSON 对象，不要 markdown：
{{
  "intent": "consult 或 apply",
  "reply": "给客户的中文回复（两种意图都必填）",
  "preset": "仅 apply：预设全名",
  "macro": {{ "push":0-100, ... }},
  可选 "macro_delta": {{ "power": "+5" }},
  "hold_seg": {{ "shape":"flat|decay|swell|pulse|tremble", ... }},
  "energy_map_note": "仅 apply：一两句能量图戏感要点"
}}

规则：
- 拿不准时选 consult，并在 reply 里引导客户用表演语言再说一遍。
- apply 时 macro 各键 0-100；只写眼眉能量，不写摄影机/服装/Wan。"""

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
        if preset and preset in ACTING_PULSE_PRESETS and preset != pkt.emotion:
            pkt = packet_from_acting_preset(preset)
    else:
        preset = preset or match_preset_from_text(text)
        if preset not in ACTING_PULSE_PRESETS:
            preset = match_preset_from_text(preset + " " + text)
        pkt = packet_from_acting_preset(preset)

    macro = data.get("macro")
    if isinstance(macro, dict) and macro:
        d = {k: int(macro[k]) for k in MACRO_IDS if k in macro}
        if d:
            from gaze_engine.slider_schema import MacroSliders

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
    if not preset or preset not in ACTING_PULSE_PRESETS:
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
    from gaze_engine.node1_defaults import default_system_prompt_text, resolve_system_prompt_input

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
    from gaze_engine.nl_intent import INTENT_APPLY, INTENT_CONSULT, CustomerNLResult, normalize_intent

    if not openai_configured():
        raise RuntimeError("未设置 OPENAI_API_KEY（见 scripts/s01_设置OpenAI密钥.sh）")

    from openai import OpenAI

    from gaze_engine.node1_defaults import format_previous_packet_for_llm, resolve_knowledge_base

    nl = (text or "").strip()
    kb = resolve_knowledge_base(knowledge_base)
    user_parts = [f"客户自然语言：\n{nl}"]
    if kb:
        user_parts.append(f"知识库：\n{kb[:8000]}")
    if previous_packet is not None:
        user_parts.append(
            "当前滑杆包（上一轮，修改请在此基础上用 macro_delta，勿无故换 preset）：\n"
            + format_previous_packet_for_llm(previous_packet)
        )
    if force_intent and force_intent not in ("自动", "auto", ""):
        user_parts.append(f"强制意图：{force_intent}")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        temperature=0.35,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": resolve_node1_system_prompt(system_prompt)},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = _extract_json(raw)

    intent = normalize_intent(str(data.get("intent") or ""), text=nl)
    if force_intent and force_intent not in ("自动", "auto", ""):
        intent = normalize_intent(force_intent, text=nl)

    reply = str(data.get("reply") or "").strip() or "（模型未返回 reply）"
    meta: dict[str, Any] = {
        "llm": "openai",
        "model": model or DEFAULT_MODEL,
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
    return f"""你是 ecursor 眼眉专用编译器：把客户自然语言编译成 5 秒眼眉滑杆 JSON（不是视频扩散）。

可选情绪预设（preset 必须从中选一）：{_preset_list()}

输出单个 JSON，不要 markdown：
{{
  "preset": "预设全名",
  "macro": {{ "push":0-100, "power":0-100, "speed":0-100, "steady":0-100, "grip":0-100, "outro":0-100 }},
  可选 "macro_delta": {{ "power": "+5" }},
  "hold_seg": {{ "shape":"flat|decay|swell|pulse|tremble", "pulse_rate":0-100, "pulse_depth":0-100, "swell":0-100 }},
  "energy_map_note": "可选，厂内备注"
}}

macro 各键 0-100；先选最接近 preset 再微调。"""

def chatgpt_nl_to_packet(
    text: str,
    *,
    preset_hint: str = "",
    knowledge_base: str = "",
    model: str | None = None,
) -> tuple[SliderPacket, dict[str, Any]]:
    """自然语言 → 滑杆包（节点 1 主路径）。"""
    if not openai_configured():
        raise RuntimeError("未设置 OPENAI_API_KEY（见 scripts/s01_设置OpenAI密钥.sh）")

    from openai import OpenAI

    nl = (text or "").strip()
    user_parts = [f"客户自然语言：\n{nl}"]
    if preset_hint.strip() and preset_hint in ACTING_PULSE_PRESETS:
        user_parts.append(f"预设提示：{preset_hint}")
    if knowledge_base.strip():
        user_parts.append(f"厂内参考：\n{knowledge_base.strip()[:4000]}")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        temperature=0.35,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _apply_system_prompt()},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = _extract_json(raw)
    pkt, apply_meta = _packet_from_llm_apply_json(data, nl, preset_hint=preset_hint)
    meta = {
        "llm": "openai",
        "model": model or DEFAULT_MODEL,
        **apply_meta,
    }
    return pkt, meta
