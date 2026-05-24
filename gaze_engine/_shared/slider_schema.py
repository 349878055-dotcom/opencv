"""滑杆规范 v1：LLM 刻度 ↔ Python 映射（见 contracts/滑杆规范.md）。"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SCHEMA_ID = "slider-packet-v1"
LLM_STEP_FINE = 5
LLM_STEP_MID = 10
LLM_STEP_COARSE = 20

Direction = Literal["in", "out"]
HoldShape = Literal["flat", "decay", "swell", "pulse", "tremble"]
Level3 = Literal["low", "mid", "high"]
TimeEffort = Literal["sudden", "mid", "sustained"]
SpaceEffort = Literal["direct", "mid", "indirect"]
FlowEffort = Literal["bound", "mid", "free"]
Ending = Literal["fast", "slow"]

MACRO_IDS = ("push", "power", "speed", "steady", "grip", "outro")
HOLD_IDS = ("shape", "pulse_rate", "pulse_depth", "swell")

@dataclass
class MacroSliders:
    push: int = 50
    power: int = 50
    speed: int = 50
    steady: int = 50
    grip: int = 50
    outro: int = 50

    def clamped(self) -> MacroSliders:
        return MacroSliders(
            **{k: _clamp_i(getattr(self, k)) for k in MACRO_IDS}  # type: ignore[arg-type]
        )

@dataclass
class HoldSegment:
    shape: HoldShape = "flat"
    pulse_rate: int = 0
    pulse_depth: int = 0
    swell: int = 0

    def clamped(self) -> HoldSegment:
        sh: HoldShape = self.shape
        if self.shape not in ("flat", "decay", "swell", "pulse", "tremble"):
            sh = "flat"
        return HoldSegment(
            shape=sh,
            pulse_rate=_clamp_i(self.pulse_rate),
            pulse_depth=_clamp_i(self.pulse_depth),
            swell=_clamp_i(self.swell),
        )

@dataclass
class SliderPacket:
    emotion: str = "s01_pressure"
    style: str = "default"
    macro: MacroSliders = field(default_factory=MacroSliders)
    hold_seg: HoldSegment = field(default_factory=HoldSegment)
    schema: str = SCHEMA_ID

    def clamped(self) -> SliderPacket:
        return SliderPacket(
            emotion=self.emotion,
            style=self.style or "default",
            macro=self.macro.clamped(),
            hold_seg=self.hold_seg.clamped(),
            schema=SCHEMA_ID,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "emotion": self.emotion,
            "style": self.style,
            "macro": asdict(self.macro),
            "hold_seg": asdict(self.hold_seg),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SliderPacket:
        macro_d = d.get("macro") or {}
        hold_d = d.get("hold_seg") or {}
        return cls(
            emotion=str(d.get("emotion") or "s01_pressure"),
            style=str(d.get("style") or "default"),
            macro=MacroSliders(
                **{k: int(macro_d.get(k, 50)) for k in MACRO_IDS}  # type: ignore[arg-type]
            ),
            hold_seg=HoldSegment(
                shape=str(hold_d.get("shape") or "flat"),  # type: ignore[arg-type]
                pulse_rate=int(hold_d.get("pulse_rate", 0)),
                pulse_depth=int(hold_d.get("pulse_depth", 0)),
                swell=int(hold_d.get("swell", 0)),
            ),
        ).clamped()

# 情绪默认点位（风格用 delta 叠在上面）
EMOTION_DEFAULTS: dict[str, dict[str, Any]] = {
    "s01_pressure": {
        "preset": "s01_pressure",
        "macro": {"push": 82, "power": 88, "speed": 90, "steady": 92, "grip": 88, "outro": 28},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
        "styles": {
            "default": {},
            "cold": {"macro_delta": {"power": 8, "steady": 6, "grip": 7}},
            "flash": {"macro_delta": {"speed": 8, "outro": -16}},
        },
    },
    "absorb_pity": {
        "preset": "absorb_pity",
        "macro": {"push": 18, "power": 28, "speed": 22, "steady": 70, "grip": 72, "outro": 22},
        "hold_seg": {"shape": "tremble", "pulse_rate": 15, "pulse_depth": 20, "swell": 10},
        "styles": {
            "default": {},
            "tear": {"macro_delta": {"power": -10, "speed": -10, "grip": -17}},
            "break": {"macro_delta": {"grip": -42, "outro": -12}, "hold_seg": {"shape": "decay"}},
        },
    },
    "charm_seduce": {
        "preset": "charm_seduce",
        "macro": {"push": 72, "power": 52, "speed": 38, "steady": 68, "grip": 80, "outro": 72},
        "hold_seg": {"shape": "pulse", "pulse_rate": 48, "pulse_depth": 42, "swell": 35},
        "styles": {
            "default": {},
            "sweet": {
                "macro_delta": {"power": -20, "speed": -13, "grip": 8},
                "hold_seg": {"pulse_rate": -15, "pulse_depth": -12},
            },
            "kill": {"macro_delta": {"power": 26, "speed": 34, "steady": 22}},
            "elusive": {
                "macro_delta": {"steady": -26, "grip": -25, "outro": 13},
                "hold_seg": {"shape": "swell", "swell": 25, "pulse_rate": -20},
            },
        },
    },
}

def _clamp_i(v: int | float, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(float(v)))))

def _tri(v: int) -> Level3:
    if v < 34:
        return "low"
    if v < 67:
        return "mid"
    return "high"

def _lerp(lo: float, hi: float, t: int) -> float:
    return lo + (hi - lo) * (_clamp_i(t) / 100.0)

def apply_macro_delta(macro: MacroSliders, delta: dict[str, int]) -> MacroSliders:
    d = asdict(macro)
    for k, v in delta.items():
        if k in d:
            d[k] = _clamp_i(d[k] + v)
    return MacroSliders(**d)  # type: ignore[arg-type]

def apply_llm_delta(packet: SliderPacket, macro_delta: dict[str, str | int] | None = None) -> SliderPacket:
    """合并 LLM 增量，如 {\"power\": \"+10\"} 或 {\"power\": 75}。"""
    p = packet.clamped()
    if not macro_delta:
        return p
    d = asdict(p.macro)
    for k, raw in macro_delta.items():
        if k not in d:
            continue
        if isinstance(raw, str) and raw.startswith(("+", "-")):
            d[k] = _clamp_i(d[k] + int(raw))
        else:
            d[k] = _clamp_i(raw)
    p.macro = MacroSliders(**d)  # type: ignore[arg-type]
    from gaze_engine._shared.packet_finalize import finalize_packet

    return finalize_packet(p.clamped())[0]

def packet_from_emotion(emotion: str, style: str = "default") -> SliderPacket:
    base = EMOTION_DEFAULTS.get(emotion)
    if not base:
        raise ValueError(f"未知情绪: {emotion}，可选: {', '.join(EMOTION_DEFAULTS)}")
    st = (base.get("styles") or {}).get(style) or (base.get("styles") or {}).get("default") or {}
    macro = MacroSliders(**base["macro"])  # type: ignore[arg-type]
    macro = apply_macro_delta(macro, st.get("macro_delta") or {})
    hold = HoldSegment(**base["hold_seg"])  # type: ignore[arg-type]
    hold_d = st.get("hold_seg") or {}
    if hold_d:
        hd = asdict(hold)
        hd.update(hold_d)
        hold = HoldSegment(**hd)  # type: ignore[arg-type]
    return SliderPacket(emotion=emotion, style=style, macro=macro, hold_seg=hold).clamped()

def packet_to_compile_params(packet: SliderPacket) -> dict[str, Any]:
    """SliderPacket → compile 线性系数 + hold_seg。"""
    m = packet.macro
    return {
        "direction": "out" if m.push >= 50 else "in",
        "weight_scale": _lerp(0.72, 1.18, m.power),
        "time_peak_offset": int(round(_lerp(3, -3, m.speed))),
        "space_scale": _lerp(0.82, 1.05, m.steady),
        "flow_scale": _lerp(0.88, 1.02, m.grip),
        "ending_fast": m.outro < 50,
        "hold_seg": asdict(packet.hold_seg),
    }

def _tri_time(v: int) -> TimeEffort:
    if v < 34:
        return "sustained"
    if v < 67:
        return "mid"
    return "sudden"

def _tri_space(v: int) -> SpaceEffort:
    if v < 34:
        return "indirect"
    if v < 67:
        return "mid"
    return "direct"

def _tri_flow(v: int) -> FlowEffort:
    if v < 34:
        return "free"
    if v < 67:
        return "mid"
    return "bound"
