"""第一轮合成：预设模板 + 客户 NL → SliderPacket"""
from __future__ import annotations

from gaze_engine._shared.slider_schema import SliderPacket, apply_macro_delta
from gaze_engine.nl_to_packet import _parse_modifiers
from gaze_engine.pomot.registry import PomotRegistry
from gaze_engine.pomot.templates import NLSplitResult, EmotionRoute, PresetPromptTemplate


class PomotComposer:
    """第一轮合成器"""

    def __init__(self, registry: PomotRegistry | None = None) -> None:
        self.registry = registry or PomotRegistry()

    def compose(
        self,
        split: NLSplitResult,
        route: EmotionRoute,
        *,
        previous_packet: SliderPacket | None = None,
        use_llm: bool = False,
        llm_model: str = "",
    ) -> SliderPacket:
        """
        第一轮合成：预设模板 + 客户 NL → SliderPacket

        Args:
            split: NL 拆解结果
            route: 情绪路由结果
            previous_packet: 上一轮 SliderPacket（第二轮时传入，第一轮为 None）
            use_llm: 是否使用 LLM 辅助
            llm_model: LLM 模型名

        Returns:
            SliderPacket
        """
        # 1. 加载预设模板
        template = self.registry.load(
            species=route.species,
            preset_name=route.preset_name,
            breed=route.breed,
        )

        # 2. 从预设构造基础 SliderPacket
        pkt = self._base_packet_from_template(template, route)

        # 3. 应用 NL 修饰（delta）
        if split.emotion:
            delta = _parse_modifiers(split.emotion)
            if delta:
                from gaze_engine._shared.slider_schema import MACRO_IDS, HOLD_IDS

                macro_d = {k: v for k, v in delta.items() if k in MACRO_IDS}
                if macro_d:
                    pkt.macro = apply_macro_delta(pkt.macro, macro_d)

        # 4. 如使用 LLM 且没有 OPENAI_API_KEY 回退
        if use_llm:
            try:
                from gaze_engine._shared.llm_openai import openai_configured
                if openai_configured():
                    from gaze_engine._shared.llm_openai import chatgpt_nl_to_packet

                    llm_pkt, _ = chatgpt_nl_to_packet(
                        split.raw_text,
                        preset_hint=route.preset_name,
                        model=llm_model or None,
                    )
                    if llm_pkt:
                        return llm_pkt.clamped()
            except Exception:
                pass  # 回退到规则

        return pkt.clamped()

    def _base_packet_from_template(
        self,
        template: PresetPromptTemplate,
        route: EmotionRoute,
    ) -> SliderPacket:
        """从预设模板构造基础 SliderPacket"""
        from gaze_engine._shared.slider_schema import SliderPacket

        # 尝试从预设代码构造
        try:
            if route.species == "human":
                from gaze_engine.human.control_surface import packet_from_acting_preset

                return packet_from_acting_preset(route.preset_name)
            elif route.species == "dog":
                from gaze_engine.dog.presets import dog_packet_from_file

                return dog_packet_from_file(route.preset_name)
            elif route.species == "cat":
                from gaze_engine.cat.presets import CAT_PRESETS

                raw = CAT_PRESETS.get(route.preset_name)
                if isinstance(raw, dict):
                    return SliderPacket.from_dict(raw)
                return raw  # type: ignore[return-value]
        except Exception:
            pass

        # 回退：从 template.slider_packet 构造
        if template.slider_packet:
            return SliderPacket.from_dict(template.slider_packet)

        # 最终回退：默认包
        return SliderPacket()