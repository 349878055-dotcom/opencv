"""
pomot —— Preset Prompt Template 合成引擎

将「预设资产中的情绪模板」与「客户自然语言」合成可控的眼眉滑杆包，
再与 12 通道数值脉冲 + 客户叙事拼装为扩散引擎的最终 Prompt。

模块：
  nl_splitter      : 一句话 → 动作 + 情绪
  emotion_router   : 情绪词 → 预设名 + 物种/品种
  registry         : 按 (species, breed, preset) 加载预设模板
  templates        : PresetPromptTemplate 数据类
  composer         : 第一轮: 预设模板 + NL → SliderPacket
  delta            : 第二轮: delta 叠加
  assembler        : 最终拼装 → 04_Prompt.txt + 送扩散引擎 payload
"""

from gaze_engine.delivery.pomot.templates import NLSplitResult, EmotionRoute, PresetPromptTemplate
from gaze_engine.delivery.pomot.nl_splitter import NLSplitter
from gaze_engine.delivery.pomot.emotion_router import EmotionRouter
from gaze_engine.delivery.pomot.registry import PomotRegistry
from gaze_engine.delivery.pomot.composer import PomotComposer
from gaze_engine.delivery.pomot.delta import PacketDeltaApplier
from gaze_engine.delivery.pomot.assembler import DiffusionPromptAssembler

__all__ = [
    "NLSplitResult",
    "EmotionRoute",
    "PresetPromptTemplate",
    "NLSplitter",
    "EmotionRouter",
    "PomotRegistry",
    "PomotComposer",
    "PacketDeltaApplier",
    "DiffusionPromptAssembler",
]