"""自然语言意图：咨询 vs 生成/修改（节点 1 路由）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

Intent = Literal["consult", "apply"]

INTENT_CONSULT = "consult"
INTENT_APPLY = "apply"

# 咨询：问概念、不会改滑杆
_CONSULT_PATTERNS = (
    r"(什么是|啥是|什么叫|是什么意思)",
    r"(怎么|如何)(理解|使用|选|调|操作)",
    r"(有什么区别|差别在哪|哪个好)",
    r"(能不能|可以吗|行不行)\?",
    r"(介绍一下|解释|说说|讲讲)",
    r"(什么意思|啥意思)",
    r"(为什么|为何)",
    r"^(吗|呢)\s*$",
    r"\?$",
)

# 生成/修改：要出能量图、改戏
_APPLY_PATTERNS = (
    r"(生成|来一|做一|给我一|出一段|编译)",
    r"(改成|改为|换成|调成|再.+一点|更.+一点|再.+些)",
    r"(施压|凝视|可怜|魅惑|委屈|怒视|威慑)",
    r"(林青霞|东方不败|眼眉|能量|滑杆|脉冲)",
    r"(更冷|更钉|更狠|更轻|更快|更慢)",
)

def classify_intent_keyword(text: str) -> Intent:
    t = (text or "").strip()
    if not t:
        return INTENT_APPLY
    consult = sum(1 for p in _CONSULT_PATTERNS if re.search(p, t))
    apply = sum(1 for p in _APPLY_PATTERNS if re.search(p, t))
    if consult > apply and consult >= 1:
        return INTENT_CONSULT
    if len(t) < 12 and t.endswith("?"):
        return INTENT_CONSULT
    return INTENT_APPLY

def normalize_intent(raw: str | None, *, text: str = "") -> Intent:
    v = (raw or "").strip().lower()
    if v in ("consult", "咨询", "ask", "question", "qa"):
        return INTENT_CONSULT
    if v in ("apply", "生成", "修改", "compile", "generate", "modify"):
        return INTENT_APPLY
    return classify_intent_keyword(text)

@dataclass
class CustomerNLResult:
    intent: Intent
    reply: str
    packet: Any = None  # SliderPacket | None
    meta: dict[str, Any] = field(default_factory=dict)
