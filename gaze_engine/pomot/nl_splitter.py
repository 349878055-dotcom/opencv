"""NL 拆解器：客户一句话 → 动作 + 情绪 + 物种提示"""
from __future__ import annotations

import re

from gaze_engine.pomot.templates import NLSplitResult

# ── 动作动词 ──
_ACTION_VERBS = [
    "走回", "走", "跑回", "跑", "回头", "回看", "看",
    "望", "盯", "转", "躲", "退", "爬", "站", "坐",
    "闭", "睁", "眨", "摇", "甩", "跳", "扑", "追",
]

# ── 已知情绪词（按预设名匹配） ──
_EMOTION_WORDS = [
    "委屈", "可怜", "魅惑", "勾人", "施压", "凝视",
    "冷压", "决心", "威慑", "怒视", "压人", "鄙夷",
    "冷瞥", "要哭未哭", "崩溃", "泄劲", "哀求", "仰望",
    "惊惧", "一怔", "空竭", "死心", "纯甜", "含情",
    "媚杀", "一眼", "若即若离", "打量", "玩味",
    "悲伤", "伤心", "难过", "愤怒", "生气", "害怕",
    "惊恐", "开心", "高兴", "得意", "不屑", "冷漠",
    "温柔", "深情", "凶狠",
]

# ── 物种关键词 ──
_SPECIES_KEYWORDS: dict[str, list[str]] = {
    "dog": ["狗子", "狗狗", "狗", "犬", "贵宾", "金毛", "柯基", "哈士奇", "萨摩", "柴犬", "泰迪", "拉布拉多", "边牧"],
    "cat": ["猫咪", "猫", "布偶", "英短", "美短", "暹罗", "橘猫", "波斯", "缅因", "狸花"],
    "human": ["人", "女孩", "男孩", "女人", "男人", "女生", "男生", "姐姐", "妹妹", "林青霞", "东方不败"],
}

# 剥离物种词时按长度降序，避免「狗子」先删「狗」留下「子」
_SPECIES_STRIP_WORDS: list[str] = sorted(
    {w for words in _SPECIES_KEYWORDS.values() for w in words},
    key=len,
    reverse=True,
)

# ── 修饰词（第二轮微调） ──
_MODIFY_PATTERNS = re.compile(r"(更|再|调|改|稍[微]?|太|有点|一些|一点|一下)")


class NLSplitter:
    """自然语言拆解器"""

    def split(self, text: str, *, photo_hint: str = "") -> NLSplitResult:
        """
        拆解客户 NL。

        Args:
            text: 客户自然语言文本
            photo_hint: 参考照片路径（可选，暂不实现视觉分析）

        Returns:
            NLSplitResult
        """
        nl = (text or "").strip()
        if not nl:
            return NLSplitResult(raw_text=nl)

        result = NLSplitResult(raw_text=nl)

        # 1. 检测是否为微调意图（第二轮）
        result.is_modify = bool(_MODIFY_PATTERNS.search(nl))

        # 2. 提取物种
        species, breed = self._detect_species(nl)
        result.species_hint = species
        result.breed_hint = breed

        # 3. 提取情绪
        emotion = self._extract_emotion(nl)
        result.emotion = emotion

        # 4. 提取动作
        action = self._extract_action(nl, emotion)
        result.action = action

        return result

    def _detect_species(self, text: str) -> tuple[str, str]:
        """检测物种和品种"""
        for species, keywords in _SPECIES_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    # 如果是 breed 级别的关键词（不只是 dog/cat/human）
                    if species == "dog" and kw not in ("狗", "犬"):
                        return species, kw + "犬" if not kw.endswith("犬") else kw
                    if species == "cat" and kw not in ("猫", "猫咪"):
                        return species, kw
                    return species, ""
        return "human", ""

    def _extract_emotion(self, text: str) -> str:
        """提取情绪词（命中第一个已知情绪词）"""
        for word in _EMOTION_WORDS:
            if word in text:
                return word
        return ""

    def _extract_action(self, text: str, emotion: str) -> str:
        """提取叙事动作——去掉情绪词和物种词后的剩余动词短语"""
        remaining = text
        if emotion:
            remaining = remaining.replace(emotion, "")

        for w in _SPECIES_STRIP_WORDS:
            if w in remaining:
                remaining = remaining.replace(w, "")

        remaining = re.sub(r"(更|再|调|改|稍[微]?|太|有点|一些|一点|一下|的|了|，|。)", "", remaining)
        remaining = remaining.strip().lstrip("子").strip()

        if not remaining or len(remaining) < 2:
            for verb in _ACTION_VERBS:
                if verb in text:
                    idx = text.find(verb)
                    start = max(0, idx - 2)
                    end = min(len(text), idx + len(verb) + 6)
                    phrase = text[start:end].strip()
                    for w in _SPECIES_STRIP_WORDS:
                        phrase = phrase.replace(w, "")
                    phrase = re.sub(r"(更|再|的|了|，|。)", "", phrase).strip().lstrip("子").strip()
                    if phrase:
                        return phrase

        return remaining

    def is_modify_round(self, text: str) -> bool:
        """检查是否微调意图（第二轮）"""
        return bool(_MODIFY_PATTERNS.search(text or ""))