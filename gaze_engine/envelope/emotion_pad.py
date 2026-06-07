"""情绪 PAD 真源：预设 JSON `pad` 块。

EMOTION_PAD 硬编码 dict 已删除 —— 唯一真源为 `预设资产/情绪包/{emotion}.json` 的 `pad` 块。
所有物种共享同一路径（已扁平化，无 /human /cat /dog 子目录）。
"""
from __future__ import annotations

from typing import Any

from gaze_engine.input.slider_schema import PadParams, SliderPacket


def _axis_word(v: float, pos: str, neg: str, mid: str = "中性") -> str:
    if v >= 0.35:
        return pos
    if v <= -0.35:
        return neg
    return mid


def pad_position_text(P: float, A: float, D: float) -> str:
    """一句话 PAD 空间定位（合同 §4 PAD 用）。"""
    p = _axis_word(P, "偏愉悦", "偏不悦/压抑", "愉悦中性")
    a = _axis_word(A, "高激活", "低激活/软塌", "激活中性")
    d = _axis_word(D, "偏支配/压人", "偏顺从/退缩", "控制中性")
    return f"{p} · {a} · {d}"


def pad_channel_hint(species: str, P: float, A: float, D: float) -> str:
    """按 PAD 符号推断主要通道倾向（🧠 启发式，不 import pad_weights 避免循环依赖）。"""
    parts: list[str] = []
    if P >= 0.25:
        parts.extend(["eye_gloss↑", "squint↑"])
    elif P <= -0.25:
        parts.append("eye_gloss↓")
    if A >= 0.35:
        parts.extend(["pupil_x↑", "pupil_y↑", "lid_upper↑"])
    elif A <= 0.15:
        parts.append("blink/幅低")
    if D >= 0.35:
        parts.append("眉压/耳竖↑" if species != "human" else "eyebrow压↓")
    elif D <= -0.35:
        parts.extend(["squint↑", "lid_upper↓"])
    if species == "cat" and P >= 0.4:
        parts.append("pupil_scale↑")
    return " · ".join(parts[:5]) if parts else "接近物种中性"


def default_pad_for_emotion(emotion: str) -> PadParams | None:
    """从情绪包 JSON 查找 PAD，未找到返回 None。"""
    from asset_lib import load_emotion_pad

    t = load_emotion_pad("human", emotion)
    if t is None:
        return None
    P, A, D = t
    return PadParams(P=P, A=A, D=D, position=pad_position_text(P, A, D))


def resolve_pad(packet: SliderPacket) -> tuple[float, float, float]:
    """优先级：packet.pad → 从情绪包 JSON 加载 → (0,0,0)。"""
    if packet.pad is not None:
        return packet.pad.P, packet.pad.A, packet.pad.D
    # packet 无 pad 时尝试从 JSON 加载
    from asset_lib import load_emotion_pad

    t = load_emotion_pad("human", packet.emotion)
    if t is not None:
        return t
    return (0.0, 0.0, 0.0)


def ensure_pad_on_packet(packet: SliderPacket, species: str = "human") -> SliderPacket:
    """S1 收口：packet 无 pad 块时，从情绪包 JSON 补全（不改 macro/hold）。"""
    if packet.pad is not None:
        return packet
    pad = default_pad_for_emotion(packet.emotion)
    if pad is None:
        return packet
    hint = pad_channel_hint(species, pad.P, pad.A, pad.D)
    if not pad.channel_hint and hint:
        pad = PadParams(
            P=pad.P, A=pad.A, D=pad.D,
            position=pad.position,
            channel_hint=hint,
        )
    return SliderPacket(
        emotion=packet.emotion,
        style=packet.style or "default",
        macro=packet.macro,
        hold_seg=packet.hold_seg,
        ear=packet.ear,
        pad=pad,
        schema=packet.schema,
    ).clamped()


def pad_dict_for_json(raw: dict, species: str = "human") -> dict[str, Any]:
    """从已加载的 JSON raw dict 提取 pad 块（不再从 EMOTION_PAD 硬编码读取）。"""
    pad = raw.get("pad")
    if pad:
        return {
            "P": float(pad.get("P", 0.0)),
            "A": float(pad.get("A", 0.0)),
            "D": float(pad.get("D", 0.0)),
            "position": str(pad.get("position", pad_position_text(
                float(pad.get("P", 0.0)),
                float(pad.get("A", 0.0)),
                float(pad.get("D", 0.0)),
            ))),
            "channel_hint": str(pad.get("channel_hint", pad_channel_hint(
                species,
                float(pad.get("P", 0.0)),
                float(pad.get("A", 0.0)),
                float(pad.get("D", 0.0)),
            ))),
        }
    return {"P": 0.0, "A": 0.0, "D": 0.0, "position": "🧠 待补 PAD 定位"}
