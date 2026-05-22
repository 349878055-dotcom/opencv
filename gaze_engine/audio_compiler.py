#!/usr/bin/env python3
"""
audio_compiler.py — 全自动视听合流机床

功能链:
  1. compile_music_prompt(packet)  →  Suno 风格提示词
  2. bake_audio_by_envelope(path)   →  逐帧音量×envelope 卡点 MP3
  3. merge_audio_video(paths)       →  ffmpeg 无损合流 → 02_烘焙_真人律_自动配乐.mp4

依赖: pydub (pip), ffmpeg (系统), numpy
"""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

try:
    import pydub
    from pydub import AudioSegment
    _HAS_PYDUB = True
except ImportError:
    _HAS_PYDUB = False


# ── 情绪 → 风格 / BPM 映射表（可扩展） ─────────
EMOTION_MUSIC_MAP: dict[str, dict[str, Any]] = {
    "魅惑·勾人": {
        "genre": "Trip-hop, lo-fi vinyl",
        "vocal": "sensual female vocal, breathy whisper",
        "bpm_range": (78, 88),
        "energy": "languid, oozy",
    },
    "纯甜·含情": {
        "genre": "J-pop, city pop",
        "vocal": "sweet female vocal, warm",
        "bpm_range": (92, 105),
        "energy": "bright, bubbly",
    },
    "施压·凝视": {
        "genre": "Dark ambient, industrial",
        "vocal": "spoken word, tense whisper",
        "bpm_range": (60, 72),
        "energy": "brooding, oppressive",
    },
    "冷压·决心": {
        "genre": "Dark techno, minimal",
        "vocal": "monotone, cold",
        "bpm_range": (120, 132),
        "energy": "relentless, mechanical",
    },
    "威慑·一瞬": {
        "genre": "Cinematic, orchestral hit",
        "vocal": "choir stab",
        "bpm_range": (60, 80),
        "energy": "staccato, abrupt",
    },
    "怒视·压人": {
        "genre": "Heavy bass, trap",
        "vocal": "aggressive rap, shouted",
        "bpm_range": (130, 150),
        "energy": "explosive, angry",
    },
    "可怜·委屈": {
        "genre": "Acoustic, sadcore",
        "vocal": "crying female vocal, fragile",
        "bpm_range": (65, 78),
        "energy": "pleading, vulnerable",
    },
    "崩溃·泄劲": {
        "genre": "Post-rock, ambient",
        "vocal": "sobbing, gasping",
        "bpm_range": (55, 68),
        "energy": "collapsing, exhausted",
    },
    "惊惧·一怔": {
        "genre": "Horror synth, glitch",
        "vocal": "sharp intake, gasp",
        "bpm_range": (70, 90),
        "energy": "jittery, startled",
    },
}

DEFAULT_MUSIC: dict[str, Any] = {
    "genre": "Electronic, synthwave",
    "vocal": "ethereal female vocal",
    "bpm_range": (85, 95),
    "energy": "neutral",
}


# ═══════════════════════════════════════════════
# 1. 自动提示词生成器
# ═══════════════════════════════════════════════

def compile_music_prompt(packet) -> str:
    """从 SliderPacket 自动编译 Suno 风格音乐提示词。

    Args:
        packet: SliderPacket 实例

    Returns:
        如 "Trip-hop, lo-fi vinyl, sensual female voc, 85 BPM"
    """
    emotion = packet.emotion
    speed = packet.macro.speed / 100.0   # 0~1
    outro = packet.macro.outro / 100.0   # 0~1

    meta = EMOTION_MUSIC_MAP.get(emotion, DEFAULT_MUSIC)
    bpm_lo, bpm_hi = meta["bpm_range"]

    # 用 speed 微调 BPM（speed 高→BPM 更快）
    bpm = int(round(bpm_lo + (bpm_hi - bpm_lo) * speed))

    parts = [meta["genre"], meta["vocal"], f"{bpm} BPM"]

    # 根据 outro 决定尾段表情
    if outro < 0.3:
        parts.append("abrupt ending, sharp cut")
    elif outro > 0.7:
        parts.append("long reverb fade-out")

    # 能量描述
    energy_word = meta["energy"]
    if speed < 0.35:
        energy_word = "slow, " + energy_word
    elif speed > 0.75:
        energy_word = "fast, " + energy_word
    parts.append(energy_word)

    prompt = ", ".join(parts)
    return prompt


# ═══════════════════════════════════════════════
# 2. 根据能量包络卡点音量
# ═══════════════════════════════════════════════

def _generate_mock_audio(duration_sec: float = 5.0,
                         sample_rate: int = 44100,
                         output_path: str = "mock_audio.mp3") -> str:
    """生成 5 秒 Mock 音源桩（正弦波 + 白噪声底 + 鼓点脉冲）。

    真实场景应替换为 Suno / 人工配乐文件。
    """
    from pydub import AudioSegment
    from pydub.generators import Sine, WhiteNoise

    n_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)

    # 主旋律：220Hz + 330Hz 柔和和弦
    tone = (np.sin(2 * math.pi * 220 * t) * 0.3 +
            np.sin(2 * math.pi * 330 * t) * 0.2)

    # 鼓点脉冲（每 0.5 秒一个 kick）
    kick = np.zeros(n_samples)
    for i in range(int(duration_sec * 2)):
        kick_start = int(i * sample_rate * 0.5)
        kick_env = np.exp(-np.linspace(0, 10, sample_rate // 8))
        kick_end = min(kick_start + len(kick_env), n_samples)
        kick[kick_start:kick_end] += kick_env[:kick_end - kick_start] * 0.5

    # 白噪声底
    noise = np.random.uniform(-0.05, 0.05, n_samples)

    mix = (tone + kick + noise)
    mix = np.clip(mix, -1.0, 1.0)
    mix_int16 = (mix * 32767).astype(np.int16)

    seg = AudioSegment(
        mix_int16.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=1,
    )
    seg.export(output_path, format="mp3", bitrate="128k")
    return output_path


def _fade_curve(length: int, peak: int, hold_start: int, hold_end: int,
                pulse_rate: float = 0, pulse_depth: float = 0) -> np.ndarray:
    """生成与 build_energy_envelope 逻辑对齐的 150 帧包络权重。"""
    env = np.zeros(length)
    # rise
    for t in range(peak + 1):
        u = t / max(1, peak)
        env[t] = u * u * (3 - 2 * u)  # smoothstep
    # hold
    for t in range(peak + 1, hold_end + 1):
        u = (t - peak) / max(1, hold_end - peak)
        val = 1.0 - 0.3 * u
        if pulse_rate > 0 and pulse_depth > 0:
            val += pulse_depth * 0.2 * math.sin(2 * math.pi * pulse_rate * u)
        env[t] = min(1.0, max(0.0, val))
    # fade out
    for t in range(hold_end + 1, length):
        u = (t - hold_end) / max(1, length - 1 - hold_end)
        env[t] = max(0.0, 1.0 - u)
    # 归一化
    mx = env.max()
    if mx > 0:
        env /= mx
    return env


def bake_audio_by_envelope(
    audio_path: str,
    envelope: list[float] | None = None,
    *,
    frame_count: int = 150,
    fps: int = 30,
    output_path: str = "",
) -> str:
    """逐帧音量×envelope 卡点切削。

    Args:
        audio_path:  输入 MP3 路径
        envelope:    150 帧能量包络数组；None 则自动生成标准魅惑包络
        frame_count: 帧数（默认 150）
        fps:         帧率（默认 30）
        output_path: 输出路径；空则自动生成

    Returns:
        卡点后 MP3 文件路径
    """
    if not _HAS_PYDUB:
        raise ImportError("pydub 未安装: pip install pydub")

    audio = AudioSegment.from_file(audio_path, format="mp3")
    duration_ms = len(audio)
    frame_ms = duration_ms / frame_count  # 每帧时长 ms

    # 若未提供包络，生成标准魅惑包络
    if envelope is None:
        envelope = _fade_curve(
            frame_count,
            peak=18,
            hold_start=18,
            hold_end=110,
            pulse_rate=4,
            pulse_depth=0.15,
        ).tolist()
    else:
        envelope = list(envelope)

    assert len(envelope) == frame_count, (
        f"envelope 长度应为 {frame_count}，实际为 {len(envelope)}"
    )

    # 逐帧切分并重调音量
    segments: list[AudioSegment] = []
    for t in range(frame_count):
        start_ms = int(t * frame_ms)
        end_ms = int((t + 1) * frame_ms)
        seg = audio[start_ms:end_ms]

        # 音量 = 原音量 × envelope[t]
        gain_db = 20 * math.log10(max(envelope[t], 1e-6))
        seg = seg.apply_gain(gain_db)
        segments.append(seg)

    # 拼接
    baked = sum(segments) if segments else audio

    # 全局淡入淡出
    baked = baked.fade_in(80).fade_out(350)

    if not output_path:
        out_dir = Path(audio_path).parent
        output_path = str(out_dir / "audio_baked.mp3")

    baked.export(output_path, format="mp3", bitrate="128k")
    return output_path


# ═══════════════════════════════════════════════
# 3. 一键合流封装
# ═══════════════════════════════════════════════

def merge_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str = "",
) -> str:
    """ffmpeg 无损合流 → 最终 MP4。

    Args:
        video_path:  OpenCV 渲染的 MP4（无音轨）
        audio_path:  卡点后的 MP3
        output_path: 输出路径；空则自动生成

    Returns:
        合流后的 MP4 文件路径
    """
    if not output_path:
        out_dir = Path(video_path).parent
        output_path = str(out_dir / "02_烘焙_真人律_自动配乐.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return output_path


# ═══════════════════════════════════════════════
# 4. 全自动一键管线
# ═══════════════════════════════════════════════

def compile_full_audiovisual(
    packet,
    *,
    channels: dict[str, list[float]] | None = None,
    envelope: list[float] | None = None,
    frame_count: int = 150,
    fps: int = 30,
    width: int = 512,
    height: int = 512,
    video_dir: str = "",
    mock_audio: bool = True,
) -> dict[str, str]:
    """全自动视听编译一键封装。

    Args:
        packet:      SliderPacket
        channels:    12通道数据（None 则从 packet 编译）
        envelope:    能量包络（None 则自动生成）
        frame_count: 帧数
        fps:         帧率
        width/height: 视频分辨率
        video_dir:   输出目录
        mock_audio:  True = 自动生成 Mock 音源

    Returns:
        {"prompt": str, "audio": path, "video": path, "final": path}
    """
    from gaze_engine.envelope_compile import (
        build_energy_envelope,
        channels_from_packet,
    )

    if envelope is None:
        envelope = build_energy_envelope(packet, frame_count)
    if channels is None:
        channels = channels_from_packet(packet, frame_count)
    out_dir = Path(video_dir) if video_dir else Path.cwd()

    # Step 1: 生成提示词
    prompt = compile_music_prompt(packet)
    print(f"[audio] 提示词: {prompt}")

    # Step 2: Mock 音源 / 卡点
    if mock_audio:
        audio_raw = str(out_dir / "mock_audio.mp3")
        _generate_mock_audio(duration_sec=frame_count / fps, output_path=audio_raw)
        print(f"[audio] Mock 音源 → {audio_raw}")
    else:
        audio_raw = str(out_dir / "input_audio.mp3")

    audio_baked = bake_audio_by_envelope(
        audio_raw, envelope, frame_count=frame_count, fps=fps,
        output_path=str(out_dir / "audio_baked.mp3"),
    )
    print(f"[audio] 卡点音轨 → {audio_baked}")

    # Step 3: 渲染 OpenCV 视频
    from gaze_engine.line_drawer import generate_control_video
    video_path = generate_control_video(
        {"channels": channels, "frame_count": frame_count, "fps": fps},
        output_path=str(out_dir / "control_video.mp4"),
        width=width, height=height, fps=fps,
    )
    print(f"[video] 霓虹控制视频 → {video_path}")

    # Step 4: 合流
    final_path = merge_audio_video(
        str(video_path), audio_baked,
        output_path=str(out_dir / "02_烘焙_真人律_自动配乐.mp4"),
    )
    print(f"[final] 视听合流 → {final_path}")

    return {
        "prompt": prompt,
        "audio": audio_baked,
        "video": str(video_path),
        "final": final_path,
    }


# ── 命令行入口 ────────────────────────────────

def main():
    import argparse
    from gaze_engine.slider_schema import SliderPacket

    ap = argparse.ArgumentParser(description="全自动视听合流")
    ap.add_argument("--emotion", default="魅惑·勾人", help="情绪名称")
    ap.add_argument("--output-dir", default=".", help="输出目录")
    args = ap.parse_args()

    pkt = SliderPacket.from_dict({
        "emotion": args.emotion,
        "macro": {"push": 55, "power": 50, "speed": 50,
                  "steady": 50, "grip": 50, "outro": 50},
        "hold_seg": {"shape": "flat", "pulse_rate": 0,
                     "pulse_depth": 0, "swell": 0},
    })
    result = compile_full_audiovisual(pkt, video_dir=args.output_dir)
    print(f"\n=== 完成 ===")
    print(f"  提示词: {result['prompt']}")
    print(f"  最终文件: {result['final']}")


if __name__ == "__main__":
    main()