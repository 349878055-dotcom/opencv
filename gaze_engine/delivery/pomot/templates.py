"""Pomot 数据类：NLSplitResult, EmotionRoute, PresetPromptTemplate"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gaze_engine.input.slider_schema import SliderPacket


@dataclass
class NLSplitResult:
    """NL 拆解结果"""
    action: str = ""
    """叙事动作（送扩散引擎），如 '走回笼子再回头'"""

    emotion: str = ""
    """情绪描述，如 '委屈'、'魅惑'"""

    species_hint: str = ""
    """物种提示，如 'dog'、'cat'、'human'"""

    breed_hint: str = ""
    """品种提示，如 '贵宾犬'、'布偶猫'"""

    raw_text: str = ""
    """客户原始文本"""

    is_modify: bool = False
    """是否为第二轮微调（含 '更'、'再'、'调' 等修饰词）"""


@dataclass
class EmotionRoute:
    """情绪路由结果"""
    species: str = "human"
    """物种: human|dog|cat"""

    preset_name: str = ""
    """系统预设名，如 '可怜·委屈'"""

    breed: str = ""
    """品种名（human 时留空）"""

    confidence: float = 1.0
    """置信度"""


@dataclass
class PresetPromptTemplate:
    """单条情绪的预设模板"""
    emotion_id: str = ""
    """情绪 ID，如 '施压瞬间凝视'"""

    persona_id: str = ""
    """人格 ID，如 'S01_林青霞_东方不败'"""

    species: str = "human"
    """物种"""

    breed: str = ""
    """品种"""

    # ── 预设文本模板 ──
    nl_script: str = ""
    """01_自然语言.txt 内容，该情绪的表演语言描述"""

    slider_packet: dict = field(default_factory=dict)
    """02_滑杆包.json 内容，默认 macro 值"""

    diffusion_prompt: str = ""
    """04_Prompt模板.txt 内容（如果预设中有），扩散引擎 prompt 框架"""

    beat_table: str = ""
    """05_节拍表模板.txt 内容（如果预设中有）"""

    # ── 运行时 ——
    mood_tags: list[str] = field(default_factory=list)
    """情绪标签，如 ['施压', '瞬间凝视']"""

    emotion_intensity: int = 100
    """情绪浓度 (0-100)"""

    @classmethod
    def from_emotion_json(cls, emotion_json: dict) -> PresetPromptTemplate:
        """从情绪.json 构造基础模板"""
        return cls(
            emotion_id=emotion_json.get("id", ""),
            persona_id=emotion_json.get("persona_pack", ""),
            mood_tags=emotion_json.get("mood_tags", []),
        )

    @property
    def emotion_label(self) -> str:
        return self.emotion_id.replace("瞬间凝视", "·凝视").replace("魅惑勾人", "魅惑·勾人")