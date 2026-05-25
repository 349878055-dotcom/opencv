"""情绪路由：客户情绪词 → 系统预设名 + 物种/品种"""
from __future__ import annotations

from gaze_engine.pomot.templates import EmotionRoute

# ── 客户情绪词 → 系统预设名映射（按物种分） ──
_EMOTION_MAP: dict[str, dict[str, str]] = {
    "shared": {  # 跨物种通用
        "委屈": "可怜·委屈",
        "可怜": "可怜·委屈",
        "魅惑": "魅惑·勾人",
        "勾人": "魅惑·勾人",
        "温柔": "纯甜·含情",
        "深情": "纯甜·含情",
        "开心": "魅惑·勾人",
        "高兴": "魅惑·勾人",
        "冷漠": "若即若离",
        "不屑": "鄙夷·冷瞥",
        "得意": "打量·玩味",
    },
    "human": {  # 人类专属
        "施压": "施压·凝视",
        "凝视": "施压·凝视",
        "冷压": "冷压·决心",
        "决心": "冷压·决心",
        "威慑": "威慑·一瞬",
        "怒视": "怒视·压人",
        "压人": "怒视·压人",
        "鄙夷": "鄙夷·冷瞥",
        "冷瞥": "鄙夷·冷瞥",
        "要哭未哭": "要哭未哭",
        "崩溃": "崩溃·泄劲",
        "泄劲": "崩溃·泄劲",
        "哀求": "哀求·仰望",
        "仰望": "哀求·仰望",
        "惊惧": "惊惧·一怔",
        "一怔": "惊惧·一怔",
        "空竭": "空竭·死心",
        "死心": "空竭·死心",
        "纯甜": "纯甜·含情",
        "含情": "纯甜·含情",
        "媚杀": "媚杀·一眼",
        "一眼": "媚杀·一眼",
        "若即若离": "若即若离",
        "打量": "打量·玩味",
        "玩味": "打量·玩味",
        "凶狠": "怒视·压人",
        "生气": "怒视·压人",
        "愤怒": "怒视·压人",
        "害怕": "惊惧·一怔",
        "惊恐": "惊惧·一怔",
        "悲伤": "可怜·委屈",
        "伤心": "可怜·委屈",
        "难过": "可怜·委屈",
    },
    "dog": {  # 狗专属（覆盖 human 的映射）
        "委屈": "可怜·委屈",
        "可怜": "可怜·委屈",
        "魅惑": "魅惑·勾人",
        "勾人": "魅惑·勾人",
        "高兴": "魅惑·勾人",
        "凶狠": "怒视·压人",
        "生气": "怒视·压人",
        "害怕": "惊惧·一怔",
        "惊恐": "惊惧·一怔",
        "悲伤": "可怜·委屈",
        "伤心": "可怜·委屈",
    },
    "cat": {  # 猫专属
        "委屈": "可怜·委屈",
        "可怜": "可怜·委屈",
        "魅惑": "魅惑·勾人",
        "勾人": "魅惑·勾人",
        "害怕": "惊惧·一怔",
        "惊恐": "惊惧·一怔",
        "生气": "怒视·压人",
        "高兴": "魅惑·勾人",
    },
}


class EmotionRouter:
    """情绪路由"""

    # 默认回退预设（按物种）
    _DEFAULT_PRESET: dict[str, str] = {
        "human": "施压·凝视",
        "dog": "可怜·委屈",
        "cat": "魅惑·勾人",
    }

    def route(self, emotion: str, species_hint: str = "", breed_hint: str = "") -> EmotionRoute:
        """
        路由：情绪词 → 预设名

        Args:
            emotion: 客户情绪描述，如 '委屈'
            species_hint: 物种提示，如 'dog'
            breed_hint: 品种提示，如 '贵宾犬'

        Returns:
            EmotionRoute
        """
        species = self._normalize_species(species_hint)
        preset_name = self._lookup_preset(emotion, species)
        return EmotionRoute(
            species=species,
            preset_name=preset_name,
            breed=breed_hint,
            confidence=1.0 if emotion else 0.5,
        )

    def _normalize_species(self, hint: str) -> str:
        """规范化物种名"""
        h = hint.strip().lower()
        if h in ("dog", "狗", "犬"):
            return "dog"
        if h in ("cat", "猫", "猫咪"):
            return "cat"
        return "human"

    def _lookup_preset(self, emotion: str, species: str) -> str:
        """查找预设名"""
        if not emotion:
            return self._DEFAULT_PRESET.get(species, "施压·凝视")

        # 先查物种专属映射
        species_map = _EMOTION_MAP.get(species, {})
        if emotion in species_map:
            return species_map[emotion]

        # 再查共享映射
        shared = _EMOTION_MAP.get("shared", {})
        if emotion in shared:
            return shared[emotion]

        # 回退到默认
        return self._DEFAULT_PRESET.get(species, "施压·凝视")

    def list_presets_for_species(self, species: str) -> list[str]:
        """列出某物种所有可用的预设名"""
        names: set[str] = set()
        # 共享
        for v in _EMOTION_MAP.get("shared", {}).values():
            names.add(v)
        # 物种专属
        for v in _EMOTION_MAP.get(species, {}).values():
            names.add(v)
        return sorted(names)