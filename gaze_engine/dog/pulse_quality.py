"""
狗平庸质检 · 眨眼下限 + 通道解耦抽检
"""
from __future__ import annotations

from dataclasses import dataclass, field

from gaze_engine._shared.envelope_compile import clamp_to_safe_range


@dataclass
class DogPulseQualityReport:
    enabled: bool = True
    fixes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "fixes": self.fixes}


def fix_dog_pulse_quality(
    channels: dict[str, list[float]],
    *,
    frame_count: int = 150,
) -> DogPulseQualityReport:
    """确保 blink 非全零，并在必要时补注入眨眼脉冲。"""
    rep = DogPulseQualityReport()
    blink = channels.get("blink") or [0.0] * frame_count
    peak = max(blink) if blink else 0.0
    nonzero = sum(1 for v in blink if v > 0.01)

    if peak < 0.05 or nonzero < 2:
        anchors = [49, 91, 132]
        for t0 in anchors:
            if t0 < 2 or t0 >= frame_count - 3:
                continue
            for dt, v in ((1, 0.10), (2, 0.14), (3, 0.07)):
                t = t0 + dt
                if 0 <= t < frame_count:
                    blink[t] = max(blink[t], clamp_to_safe_range(v))
        channels["blink"] = blink
        rep.fixes.append(f"blink补脉冲(peak={peak:.3f}→{max(blink):.3f})")

    # 抽检：squint 与 pupil_scale 不应逐帧完全相同
    squ = channels.get("squint") or []
    ps = channels.get("pupil_scale") or []
    if squ and ps and len(squ) == len(ps):
        same = sum(1 for a, b in zip(squ, ps) if abs(a - b) < 1e-6)
        if same > frame_count * 0.85:
            rep.fixes.append("squint/pupil_scale高度重合(需检查 envelope_compile)")

    return rep
