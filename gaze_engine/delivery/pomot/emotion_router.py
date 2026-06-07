"""情绪路由：客户情绪词 → 系统预设名（仅人类）"""
from __future__ import annotations

from gaze_engine.delivery.pomot.templates import EmotionRoute

# ── 客户情绪词 → 系统预设名映射（仅人类） ──
_EMOTION_MAP: dict[str, str] = {
    # 通用
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
    # 人类专属
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
}

# 默认回退预设（仅人类）
_DEFAULT_PRESET: str = "施压·凝视"


class EmotionRouter:
    """情绪路由（仅人类）"""

    def route(
        self,
        emotion: str,
        species_hint: str = "",
        breed_hint: str = "",
        *,
        preset_override: str = "",
    ) -> EmotionRoute:
        """
        路由：情绪词 → 预设名

        Args:
            emotion: 从 NL 拆出的情绪词（门户手选情绪时应传空）
            species_hint: 保留参数，不再使用
            breed_hint: 保留参数，不再使用
            preset_override: 门户情绪按钮 id（= 情绪包 JSON 文件名或 emotion 字段）

        Returns:
            EmotionRoute
        """
        button = (preset_override or "").strip()
        if button and self._preset_in_assets(button):
            return EmotionRoute(
                species="human",
                preset_name=button,
                breed="",
                confidence=1.0,
            )
        preset_name = self._lookup_preset(emotion)
        return EmotionRoute(
            species="human",
            preset_name=preset_name,
            breed="",
            confidence=1.0 if emotion else 0.5,
        )

    @staticmethod
    def _preset_in_assets(preset_id: str) -> bool:
        """门户按钮 id 是否对应 预设资产/情绪包 中的 JSON。"""
        from asset_lib import is_valid_preset

        return is_valid_preset("human", preset_id)

    def _lookup_preset(self, emotion: str) -> str:
        """查找预设名"""
        if not emotion:
            return _DEFAULT_PRESET
        if emotion in _EMOTION_MAP:
            return _EMOTION_MAP[emotion]
        return _DEFAULT_PRESET

    def list_presets(self) -> list[str]:
        """列出所有可用的预设名"""
        return sorted(set(_EMOTION_MAP.values()))