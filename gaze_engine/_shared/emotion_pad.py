"""情绪 PAD 真源：预设 JSON `pad` 块 + 物种默认表。"""
from __future__ import annotations

from typing import Any

from gaze_engine._shared.slider_schema import PadParams, SliderPacket

# 值域 [-1, 1]：(P 愉悦度, A 激活度, D 控制度)
# 人类/狗用显示名；猫用 emotion id（cat_*）
EMOTION_PAD: dict[str, tuple[float, float, float]] = {
    # ── 人类 16 ──
    "魅惑·勾人": (0.6, 0.3, -0.4),
    "施压·凝视": (-0.2, 0.7, 0.6),
    "冷压·决心": (-0.3, 0.6, 0.8),
    "威慑·一瞬": (0.0, 0.8, 0.5),
    "怒视·压人": (-0.5, 0.8, 0.7),
    "鄙夷·冷瞥": (-0.4, 0.3, 0.5),
    "可怜·委屈": (-0.2, 0.2, -0.5),
    "要哭未哭": (-0.3, 0.3, -0.6),
    "崩溃·泄劲": (-0.6, 0.5, -0.7),
    "哀求·仰望": (0.1, 0.2, -0.6),
    "惊惧·一怔": (-0.4, 0.7, -0.3),
    "空竭·死心": (-0.7, 0.1, -0.2),
    "纯甜·含情": (0.8, 0.2, 0.1),
    "媚杀·一眼": (0.5, 0.4, 0.0),
    "若即若离": (0.3, 0.1, -0.1),
    "打量·玩味": (0.2, 0.3, 0.2),
    # ── 猫 12（🧠 脑补初稿）──
    "cat_alarm_stare": (-0.05, 0.78, 0.38),
    "cat_hunt_fixate": (-0.15, 0.82, 0.52),
    "cat_angry_hiss": (-0.55, 0.88, 0.68),
    "cat_startle_fluff": (-0.45, 0.88, -0.42),
    "cat_scared_flatten": (-0.48, 0.58, -0.62),
    "cat_sad_whimper": (-0.32, 0.28, -0.58),
    "cat_cuddle_squint": (0.72, 0.18, -0.18),
    "cat_content_bliss": (0.78, 0.12, 0.08),
    "cat_sleepy_droop": (0.18, 0.04, -0.32),
    "cat_curious_tilt": (0.28, 0.42, -0.08),
    "cat_play_pounce": (0.62, 0.72, 0.12),
    "cat_annoyed_swish": (-0.38, 0.48, 0.22),
    # ── 狗 10 ──
    "兴奋·期待": (0.55, 0.65, 0.1),
    "凶狠·威吓": (-0.5, 0.85, 0.6),
    "困倦·犯懒": (0.15, 0.05, -0.3),
    "困惑·歪头": (0.1, 0.35, -0.1),
    "委屈·幼犬眼": (-0.40, -0.15, -0.70),
    "委屈·变体1·缓慢泄气": (-0.40, -0.15, -0.70),
    "委屈·变体2·隐忍微颤": (-0.40, -0.15, -0.70),
    "委屈·变体3·迟疑试探": (-0.40, -0.15, -0.70),
    "守护·凝视": (-0.1, 0.55, 0.45),
    "害怕·退缩": (-0.45, 0.55, -0.65),
    "渴望·仰望": (-0.2, 0.3, -0.5),
    "满足·眯眼": (0.65, 0.15, 0.05),
    "警觉·竖耳": (-0.05, 0.75, 0.35),
}


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
    t = EMOTION_PAD.get(emotion)
    if t is None:
        return None
    P, A, D = t
    return PadParams(P=P, A=A, D=D, position=pad_position_text(P, A, D))


def resolve_pad(packet: SliderPacket) -> tuple[float, float, float]:
    """优先级：packet.pad → EMOTION_PAD[emotion] → (0,0,0)。"""
    if packet.pad is not None:
        return packet.pad.P, packet.pad.A, packet.pad.D
    return EMOTION_PAD.get(packet.emotion, (0.0, 0.0, 0.0))


def ensure_pad_on_packet(packet: SliderPacket, species: str = "human") -> SliderPacket:
    """S1 收口：packet 无 pad 块时，从 EMOTION_PAD 补全（不改 macro/hold）。"""
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


def pad_dict_for_json(emotion: str, species: str) -> dict[str, Any]:
    """写入预设 JSON 的 pad 块。"""
    t = EMOTION_PAD.get(emotion)
    if t is None:
        return {"P": 0.0, "A": 0.0, "D": 0.0, "position": "🧠 待补 PAD 定位"}
    P, A, D = t
    return {
        "P": round(P, 2),
        "A": round(A, 2),
        "D": round(D, 2),
        "position": pad_position_text(P, A, D),
        "channel_hint": pad_channel_hint(species, P, A, D),
    }
