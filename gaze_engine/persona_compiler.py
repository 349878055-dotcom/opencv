"""
persona_compiler.py — 人格枢纽编译器

数据流向：
  上游：16 种情绪的 ADSR 能量波形（150 帧，0.0 ~ 1.0）
  本地：加载【九大人格矩阵】→ 取出当前人格的 base_offset / scale_factor
  下游：严格按 CANONICAL_KEYS 输出 12 通道 × 150 帧最终数值

核心公式：
  final_value[t] = persona.base_offset[channel] + (emotion_pulse[t] * persona.scale_factor[channel])
"""

from __future__ import annotations

import dataclasses
from typing import Dict, List

from gaze_engine.channel_contract import CANONICAL_KEYS

# ──────────────────────────────────────────────
# 1. 人格数据结构
# ──────────────────────────────────────────────

FRAME_COUNT: int = 150


@dataclasses.dataclass(frozen=True)
class Persona:
    """单一人格矩阵条目。

    Attributes:
        persona_id:   唯一标识（如 "天选者_大祭司"）
        label:        展示名称
        base_offset:  每个通道的基础偏移  (12 keys)
        scale_factor: 每个通道的放大/阻尼系数 (12 keys)
    """

    persona_id: str
    label: str
    base_offset: Dict[str, float]
    scale_factor: Dict[str, float]


def _build_persona_dict(
    persona_id: str,
    label: str,
    base_overrides: Dict[str, float] | None = None,
    scale_overrides: Dict[str, float] | None = None,
) -> Persona:
    """用可选的局部覆写构建完整 Persona（未指定的通道使用中性默认值）。"""
    DEFAULT_BASE = 0.5
    DEFAULT_SCALE = 0.3

    base: Dict[str, float] = {}
    scale: Dict[str, float] = {}
    for key in CANONICAL_KEYS:
        base[key] = (base_overrides or {}).get(key, DEFAULT_BASE)
        scale[key] = (scale_overrides or {}).get(key, DEFAULT_SCALE)
    return Persona(
        persona_id=persona_id,
        label=label,
        base_offset=base,
        scale_factor=scale,
    )


# ──────────────────────────────────────────────
# 2. 九大人格矩阵（当前占位数据）
# ──────────────────────────────────────────────

# 预留 9 个槽位，当前填入 2 个占位人格
PERSONA_MATRIX: Dict[str, Persona] = {
    # ── 天选者/大祭司 ──
    # 特征：高阻尼、眼神死锁
    #   pupil_x/y scale 极低 → 视线几乎不动
    #   eyebrow    scale 高   → 眉压随情绪强烈响应
    "天选者_大祭司": _build_persona_dict(
        persona_id="天选者_大祭司",
        label="天选者/大祭司",
        base_overrides={
            "pupil_x": 0.50,
            "pupil_y": 0.50,
            "eyebrow": 0.45,
        },
        scale_overrides={
            "pupil_x": 0.05,  # 眼神死锁 → 几乎不随脉冲偏移
            "pupil_y": 0.05,
            "pupil_scale": 0.15,
            "iris_scale": 0.15,
            "eyebrow": 0.85,  # 眉压高响应
            "blink": 0.30,
            "cornea_bulge": 0.20,
            "squint": 0.25,
            "brow_raise": 0.10,
            "lid_upper": 0.20,
            "lid_lower": 0.20,
            "eye_gloss": 0.10,
        },
    ),
    # ── 魅惑者/部落巫医 ──
    # 特征：高湿润度、眼睑延迟
    #   eye_gloss base_offset 高 → 始终带有湿润高光
    #   blink     scale 带有延迟常数 → 眼睑动作幅度大
    "魅惑者_部落巫医": _build_persona_dict(
        persona_id="魅惑者_部落巫医",
        label="魅惑者/部落巫医",
        base_overrides={
            "eye_gloss": 0.80,  # 高湿润度基线
            "lid_upper": 0.55,  # 上眼睑微垂（慵懒感）
            "lid_lower": 0.45,  # 下眼睑微提
        },
        scale_overrides={
            "eye_gloss": 0.35,  # 湿润度本身已有高 base，scale 适中
            "blink": 0.70,  # 眼睑脉冲幅度大（延迟特性通过外部节拍实现）
            "pupil_x": 0.40,  # 视线灵活游走
            "pupil_y": 0.35,
            "eyebrow": 0.50,
            "pupil_scale": 0.40,
            "iris_scale": 0.40,
            "cornea_bulge": 0.45,
            "squint": 0.30,
            "brow_raise": 0.35,
            "lid_upper": 0.50,
            "lid_lower": 0.40,
        },
    ),
}


def get_persona(persona_id: str) -> Persona:
    """按 ID 获取人格；不存在时抛出 KeyError。"""
    if persona_id not in PERSONA_MATRIX:
        raise KeyError(
            f"未知人格 '{persona_id}'，可用选项: {list(PERSONA_MATRIX.keys())}"
        )
    return PERSONA_MATRIX[persona_id]


# ──────────────────────────────────────────────
# 3. 核心编译函数
# ──────────────────────────────────────────────


def compile_to_channels(
    emotion_pulse: List[float],
    persona_id: str,
    *,
    frame_count: int = FRAME_COUNT,
) -> Dict[str, List[float]]:
    """将一维情绪脉冲编译为 12 通道全量帧序列。

    Args:
        emotion_pulse:  150 帧浮点数数组，值域 0.0 ~ 1.0
        persona_id:     人格标识（如 "天选者_大祭司"）
        frame_count:    期望帧数（默认 150）

    Returns:
        严格包含 CANONICAL_KEYS 全部 12 个键的 dict，
        每个键对应一个长度为 frame_count 的浮点数列表。
    """
    if len(emotion_pulse) != frame_count:
        raise ValueError(
            f"emotion_pulse 长度应为 {frame_count}，实际为 {len(emotion_pulse)}"
        )

    persona = get_persona(persona_id)
    result: Dict[str, List[float]] = {}

    for key in CANONICAL_KEYS:
        base = persona.base_offset[key]
        scale = persona.scale_factor[key]
        channel_series: List[float] = [
            min(max(base + (pulse * scale), 0.0), 1.0)  # 钳位到 [0, 1]
            for pulse in emotion_pulse
        ]
        result[key] = channel_series

    # 防御性校验：确保 12 个键齐全
    assert set(result.keys()) == set(CANONICAL_KEYS), (
        f"输出缺少通道: {set(CANONICAL_KEYS) - set(result.keys())}"
    )
    return result


# ──────────────────────────────────────────────
# 4. 本地测试
# ──────────────────────────────────────────────


def _main() -> None:
    """用全 1.0 假脉冲测试两个占位人格，打印前 5 帧。"""
    dummy_pulse = [1.0] * FRAME_COUNT  # 150 帧全 1.0

    for pid in ("天选者_大祭司", "魅惑者_部落巫医"):
        print(f"{'='*60}")
        print(f"人格: {PERSONA_MATRIX[pid].label} ({pid})")
        print(f"{'='*60}")
        out = compile_to_channels(dummy_pulse, pid)
        for key in CANONICAL_KEYS:
            series = out[key]
            prefix = "  ".join(f"{series[t]:.4f}" for t in range(5))
            print(f"  {key:15s} │ 前 5 帧: {prefix}")
        print()


if __name__ == "__main__":
    _main()
