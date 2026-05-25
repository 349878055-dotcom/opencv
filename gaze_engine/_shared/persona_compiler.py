"""
persona_compiler.py — 人格枢纽编译器

数据流向：
  上游：16 种情绪的 ADSR 能量波形（150 帧，0.0 ~ 1.0）
  本地：从 persona_matrix.json 加载【九大人格矩阵】
  下游：严格按 CANONICAL_KEYS 输出 12 通道 × 150 帧最终数值

核心公式：
  final_value[t] = clamp(base_offset[ch] + pulse[t] × scale_factor[ch])

工程约束：
  - 所有人格偏置与系数均定义在 persona_matrix.json 中，严禁硬编码
  - 最终输出强制钳位 [0.0, 1.0]，不得越界
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

from gaze_engine._shared.channel_contract import CANONICAL_KEYS

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
    """从 JSON 文件加载人格矩阵 + 物种品种矩阵。

    Args:
        path: JSON 文件路径，默认指向同目录下的 persona_matrix.json

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

    # 加载品种矩阵（猫/狗等），合并到同一命名空间
    raw_breeds: dict = raw.get("breed_personas") or {}
    for pid, data in raw_breeds.items():
        matrix[pid] = Persona(
            persona_id=pid,
            label=data.get("label", pid),
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
) -> Dict[str, List[float]]:
    """将一维情绪脉冲编译为 12 通道全量帧序列。

    Args:
        emotion_pulse:  150 帧浮点数数组，值域 0.0 ~ 1.0
        persona_id:     人格标识（如 "天选者_大祭司"）
        frame_count:    期望帧数（默认 150）

    Returns:
        严格包含 CANONICAL_KEYS 全部 12 个键的 dict，
        每个键对应一个长度为 frame_count 的浮点数列表。
        所有数值均经过 clamp_to_safe_range() 强制钳位，绝不越界。
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
            clamp_to_safe_range(base + (pulse * scale))
            for pulse in emotion_pulse
        ]
        result[key] = channel_series

    # 防御性校验：确保 12 个键齐全
    assert set(result.keys()) == set(CANONICAL_KEYS), (
        f"输出缺少通道: {set(CANONICAL_KEYS) - set(result.keys())}"
    )
    return result


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
        for key in CANONICAL_KEYS:
            series = out[key]
            prefix = "  ".join(f"{series[t]:.4f}" for t in range(5))
            print(f"  {key:15s} │ 前 5 帧: {prefix}")
        print()


if __name__ == "__main__":
    _main()
