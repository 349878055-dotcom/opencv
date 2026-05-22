"""
test_persona_integrity.py — 人格独立性压力测试

验收标准：
  【天选者/大祭司】vs 【魅惑者/部落巫医】在 pupil_x 和 eye_gloss 上
  必须表现出显著的特征差异（diff_ratio >= 2.0），否则测试不通过。

测试方法：
  1. 输入同一标准「魅惑」情绪波形（正弦衰减 + 随机微扰）
  2. 遍历所有人格，输出第 1、75、150 帧的 12 通道结果
  3. 定量计算 pupil_x 和 eye_gloss 的差异倍数
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from gaze_engine.persona_compiler import (
    FRAME_COUNT,
    compile_to_channels,
    get_persona,
    list_persona_ids,
)
from gaze_engine.channel_contract import CANONICAL_KEYS

# ──────────────────────────────────────────────
# 1. 标准「魅惑」情绪波形生成器
# ──────────────────────────────────────────────

# 固定种子确保可复现
_RNG = random.Random(42)


def _generate_charm_pulse(length: int = FRAME_COUNT) -> List[float]:
    """生成标准魅惑情绪波形：正弦上升 → 保持 → 正弦衰减 + 微扰。"""
    pulse: List[float] = []
    for t in range(length):
        progress = t / length  # 0.0 → 1.0

        # 三段式包络
        if progress < 0.2:
            # 蓄力上升 (0→0.2): 正弦缓入
            phase = progress / 0.2
            envelope = math.sin(phase * math.pi / 2)
        elif progress < 0.6:
            # 保持 (0.2→0.6): 微幅波动
            envelope = 1.0 - 0.05 * math.sin(progress * 8 * math.pi)
        else:
            # 衰减 (0.6→1.0): 余弦缓出
            phase = (progress - 0.6) / 0.4
            envelope = math.cos(phase * math.pi / 2)

        # 叠加微扰 (±0.03)
        noise = (_RNG.random() - 0.5) * 0.06
        val = min(max(envelope + noise, 0.0), 1.0)
        pulse.append(round(val, 6))

    return pulse


# ──────────────────────────────────────────────
# 2. 差异分析
# ──────────────────────────────────────────────


def _compute_diff_ratio(
    series_a: List[float],
    series_b: List[float],
) -> float:
    """计算两条序列之间的峰值差异比率（越大 = 差异越显著）。

    用 max_a / max_b 或 max_b / max_a 中大的那个作为比率，
    直接反映人格在通道上的「特征幅度差异」。
    """
    max_a = max(series_a)
    max_b = max(series_b)
    ratio = max(max_a, max_b) / min(max_a, max_b)
    return ratio


# ──────────────────────────────────────────────
# 3. 压力测试主函数
# ──────────────────────────────────────────────

# 验收判据：差异倍数 ≥ 2.0 即视为通过
DIFF_RATIO_THRESHOLD = 2.0

# 关键对比通道
WATCH_CHANNELS = ("pupil_x", "eye_gloss")

# 采样帧
SAMPLE_FRAMES = (1, 75, 150)  # 1-based → 转 0-based 索引


def _run_integrity_test() -> int:
    """执行压力测试。返回 0 = 通过，1 = 不通过。"""
    charm_pulse = _generate_charm_pulse()
    persona_ids = list_persona_ids()

    print(f"{'='*70}")
    print(f"🧪 人格独立性压力测试")
    print(f"{'='*70}")
    print(f"  情绪波形: 标准「魅惑」正弦衰减 + 随机微扰")
    print(f"  帧数:     {FRAME_COUNT}")
    print(f"  人格数:   {len(persona_ids)} ({', '.join(persona_ids)})")
    print(f"  采样帧:   第 {', '.join(map(str, SAMPLE_FRAMES))} 帧")
    print(f"  验收判据: {WATCH_CHANNELS} 的差异倍数 ≥ {DIFF_RATIO_THRESHOLD}")
    print()

    # ── 收集所有人格的输出 ──
    all_outputs: Dict[str, Dict[str, List[float]]] = {}
    for pid in persona_ids:
        all_outputs[pid] = compile_to_channels(charm_pulse, pid)

    # ── 逐人格打印采样帧 ──
    for pid in persona_ids:
        persona = get_persona(pid)
        out = all_outputs[pid]
        print(f"── {persona.label} ({pid}) ──")
        header = "  ".join(f"{t:>4}" for t in SAMPLE_FRAMES)
        print(f"  {'通道':12s} │ 帧: {header}")
        print(f"  {'─'*12}─┼─{'─'*20}")
        for key in CANONICAL_KEYS:
            series = out[key]
            vals = "  ".join(f"{series[f-1]:.4f}" for f in SAMPLE_FRAMES)
            print(f"  {key:12s} │ {vals}")
        print()

    # ── 定量差异分析（取第一个 vs 其余） ──
    if len(persona_ids) >= 2:
        baseline_pid = persona_ids[0]
        print(f"{'='*70}")
        print(f"📊 定量差异分析（基准: {baseline_pid}）")
        print(f"{'='*70}")

        all_pass = True
        for ch in WATCH_CHANNELS:
            print(f"\n  通道: {ch}")
            for other_pid in persona_ids[1:]:
                ratio = _compute_diff_ratio(
                    all_outputs[baseline_pid][ch],
                    all_outputs[other_pid][ch],
                )
                status = "✅ PASS" if ratio >= DIFF_RATIO_THRESHOLD else "❌ FAIL"
                if ratio < DIFF_RATIO_THRESHOLD:
                    all_pass = False
                print(
                    f"    {baseline_pid:12s} vs {other_pid:12s}  "
                    f"差异倍数={ratio:.2f}  {status}"
                )

        print()
        if all_pass:
            print(f"{'='*70}")
            print(f"✅ 验收通过 — 所有人格在 {WATCH_CHANNELS} 上特征差异显著")
            print(f"{'='*70}")
            return 0
        else:
            print(f"{'='*70}")
            print(f"❌ 验收未通过 — 部分人格差异倍数 < {DIFF_RATIO_THRESHOLD}")
            print(f"{'='*70}")
            return 1
    else:
        print(f"⚠️  只有 1 个人格，无法进行对比分析（最少需要 2 个）")
        return 0


if __name__ == "__main__":
    exit(_run_integrity_test())
