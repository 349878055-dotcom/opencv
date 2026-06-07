"""
persona_compiler.py — 人格/风格动态合成（人类专属）

数据流向（**不改 E(t)**）：
  上游：物种 envelope_compile 输出的 pulse（12×150）
  本地：persona_matrix.json 或 预设资产/风格包/{id}/style.json（已扁平化，无 species 子目录）
  下游：styled[ch,t] = clamp(base_offset[ch] + pulse[ch,t] × scale_factor[ch])

⚠️ 勿与 build_energy_envelope() 混淆：E(t) 仅由 macro/hold 决定。
旧函数 compile_to_channels(emotion_pulse, persona_id) 用于单通道 pulse 测试，
emotion_pulse 在完整管线中对应某一轨或测试波形，不是替代 E(t) 主钟。
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple


# ──────────────────────────────────────────────
# 0. 常量
# ──────────────────────────────────────────────

FRAME_COUNT: int = 150
"""每段脉冲的标准帧数。"""

SAFE_LOW: float = 0.0
"""物理有效区下限。"""
SAFE_HIGH: float = 1.0
"""物理有效区上限。"""

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MATRIX_PATH = os.path.join(_THIS_DIR, "persona_matrix.json")
"""人格矩阵配置文件路径。"""


# ──────────────────────────────────────────────
# 1. 钳位函数
# ──────────────────────────────────────────────


def clamp_to_safe_range(value: float) -> float:
    """将单个数值强制钳位到 [SAFE_LOW, SAFE_HIGH]。

    这是最后一层保险：
      - 防止人格叠加后数值越界
      - 防止扩散引擎（第五域）读取到非法浮点数
    """
    if value < SAFE_LOW:
        return SAFE_LOW
    if value > SAFE_HIGH:
        return SAFE_HIGH
    return value


# ──────────────────────────────────────────────
# 2. 人格数据结构
# ──────────────────────────────────────────────


class Persona:
    """单一人格矩阵条目（不可变数据容器）。

    Attributes:
        persona_id:   唯一标识（如 "天选者_大祭司"）
        label:        展示名称
        base_offset:  每个通道的基础偏移  (12 keys)
        scale_factor: 每个通道的放大/阻尼系数 (12 keys)
    """

    __slots__ = ("persona_id", "label", "base_offset", "scale_factor")

    def __init__(
        self,
        persona_id: str,
        label: str,
        base_offset: Dict[str, float],
        scale_factor: Dict[str, float],
    ) -> None:
        self.persona_id = persona_id
        self.label = label
        self.base_offset = base_offset
        self.scale_factor = scale_factor


# ──────────────────────────────────────────────
# 3. 从 JSON 加载人格矩阵
# ──────────────────────────────────────────────


def load_persona_matrix(path: str = _MATRIX_PATH) -> Dict[str, Persona]:
    """从 JSON 文件加载九大人格矩阵。

    Args:
        path: JSON 文件路径，默认指向 persona_matrix.json

    Returns:
        persona_id → Persona 的映射字典
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    matrix: Dict[str, Persona] = {}
    raw_personas: dict = raw["personas"]

    for pid, data in raw_personas.items():
        matrix[pid] = Persona(
            persona_id=pid,
            label=data["label"],
            base_offset=dict(data["base_offset"]),
            scale_factor=dict(data["scale_factor"]),
        )

    return matrix


# 模块级缓存 — 运行时加载一次即可
_PERSONA_MATRIX: Dict[str, Persona] | None = None


def _get_matrix() -> Dict[str, Persona]:
    global _PERSONA_MATRIX
    if _PERSONA_MATRIX is None:
        _PERSONA_MATRIX = load_persona_matrix()
    return _PERSONA_MATRIX


def get_persona(persona_id: str) -> Persona:
    """按 ID 获取人格；不存在时抛出 KeyError。"""
    matrix = _get_matrix()
    if persona_id not in matrix:
        raise KeyError(
            f"未知人格 '{persona_id}'，可用选项: {list(matrix.keys())}"
        )
    return matrix[persona_id]


def list_persona_ids() -> List[str]:
    """返回所有可用的人格 ID 列表。"""
    return list(_get_matrix().keys())


# ──────────────────────────────────────────────
# 4. 核心编译函数
# ──────────────────────────────────────────────


def compile_to_channels(
    emotion_pulse: List[float],
    persona_id: str,
    *,
    frame_count: int = FRAME_COUNT,
    channel_keys: list[str] | None = None,
) -> Dict[str, List[float]]:
    """测试/legacy：一维 pulse × 人格 → 12 轨（完整管线请用 apply_persona_style）。

    emotion_pulse 为 **已算好的 150 帧 pulse 模板**（测试用），不是 SliderPacket macro。
    """
    if channel_keys is None:
        from gaze_engine.envelope.envelope_compile import HUMAN_CHANNELS
        channel_keys = HUMAN_CHANNELS
    if len(emotion_pulse) != frame_count:
        raise ValueError(
            f"emotion_pulse 长度应为 {frame_count}，实际为 {len(emotion_pulse)}"
        )

    persona = get_persona(persona_id)
    result: Dict[str, List[float]] = {}

    for key in channel_keys:
        base = persona.base_offset[key]
        scale = persona.scale_factor[key]
        channel_series: List[float] = [
            clamp_to_safe_range(base + (pulse * scale))
            for pulse in emotion_pulse
        ]
        result[key] = channel_series

    # 防御性校验：确保键齐全
    assert set(result.keys()) == set(channel_keys), (
        f"输出缺少通道: {set(channel_keys) - set(result.keys())}"
    )
    return result


def apply_persona_style(
    channels: Dict[str, List[float]],
    persona_id: str,
) -> Dict[str, List[float]]:
    """人格动态偏置：styled = base + scale × pulse（不改 E(t)）。"""
    if not persona_id or persona_id in ("default", ""):
        return channels
    from gaze_engine.envelope.envelope_compile import HUMAN_CHANNELS
    from gaze_engine.style.style_compose import (
        apply_style_offset,
        load_style_json,
        style_offsets_from_dict,
    )

    raw = load_style_json("human", persona_id)
    if raw is not None:
        bo, sf = style_offsets_from_dict(raw)
    else:
        persona = get_persona(persona_id)
        bo, sf = persona.base_offset, persona.scale_factor
    return apply_style_offset(channels, bo, sf, channel_keys=HUMAN_CHANNELS)


# ──────────────────────────────────────────────
# 5. 本地测试
# ──────────────────────────────────────────────


def _main() -> None:
    """用全 1.0 假脉冲测试所有人格，打印前 5 帧。"""
    dummy_pulse = [1.0] * FRAME_COUNT

    for pid in list_persona_ids():
        persona = get_persona(pid)
        print(f"{'='*60}")
        print(f"人格: {persona.label} ({pid})")
        print(f"{'='*60}")
        out = compile_to_channels(dummy_pulse, pid)
        # 从输出结果读取实际通道名
        ch_keys = list(out.keys())
        for key in ch_keys:
            series = out[key]
            prefix = "  ".join(f"{series[t]:.4f}" for t in range(5))
            print(f"  {key:15s} │ 前 5 帧: {prefix}")
        print()


if __name__ == "__main__":
    _main()