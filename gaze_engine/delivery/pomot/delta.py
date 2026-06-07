"""第二轮微调：上一轮 SliderPacket + 客户修饰语 → 新版 SliderPacket

禁止换 preset，禁止换 hold_seg.shape，只改 macro 6 键 + hold_seg 数值。
"""
from __future__ import annotations

from gaze_engine.input.slider_schema import (
    HOLD_IDS,
    MACRO_IDS,
    HoldSegment,
    SliderPacket,
    apply_macro_delta,
)
from gaze_engine.nl.nl_to_packet import _parse_modifiers


class PacketDeltaApplier:
    """第二轮微调：delta 叠加器"""

    def apply(
        self,
        previous_packet: SliderPacket,
        customer_nl: str,
    ) -> SliderPacket:
        """
        应用 delta 微调。

        Args:
            previous_packet: 上一轮 SliderPacket
            customer_nl: 客户微调文本，如 '再委屈一点'

        Returns:
            微调后的 SliderPacket

        Raises:
            ValueError: 如果 previous_packet 为 None
        """
        if previous_packet is None:
            raise ValueError("第二轮微调需要上一轮的 SliderPacket")

        # 1. 深拷贝上一轮的 packet
        pkt = SliderPacket.from_dict(previous_packet.to_dict())

        # 2. 解析 delta
        delta = _parse_modifiers(customer_nl)
        if not delta:
            return pkt

        # 3. 分离 macro delta 和 hold_seg delta
        macro_d = {k: v for k, v in delta.items() if k in MACRO_IDS}
        hold_d = {k: v for k, v in delta.items() if k in HOLD_IDS}

        # 4. 应用 macro delta
        if macro_d:
            pkt.macro = apply_macro_delta(pkt.macro, macro_d)

        # 5. 应用 hold_seg delta（只改数值，不改 shape）
        if hold_d:
            hs = pkt.hold_seg
            new_rate = max(0, min(100, hs.pulse_rate + hold_d.get("pulse_rate", 0)))
            new_depth = max(0, min(100, hs.pulse_depth + hold_d.get("pulse_depth", 0)))
            new_swell = max(0, min(100, hs.swell + hold_d.get("swell", 0)))
            pkt.hold_seg = HoldSegment(
                shape=hs.shape,  # ⚠️ 锁定 shape，不换
                pulse_rate=new_rate,
                pulse_depth=new_depth,
                swell=new_swell,
            )

        # ⚠️ 禁止换 preset（锁定上一轮的 emotion）
        pkt.emotion = previous_packet.emotion

        return pkt.clamped()

    def extract_delta_summary(self, customer_nl: str) -> dict[str, int]:
        """仅提取 delta 摘要，不修改 packet（用于预览）"""
        delta = _parse_modifiers(customer_nl)
        macro_d = {k: v for k, v in delta.items() if k in MACRO_IDS}
        return macro_d