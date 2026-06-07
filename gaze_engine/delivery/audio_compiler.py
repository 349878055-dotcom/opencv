#!/usr/bin/env python3
"""
audio_compiler.py — 全自动视听合流机床

功能链:
  1. compile_music_prompt(packet)  →  Suno 风格提示词
  2. bake_audio_by_envelope(path)   →  逐帧音量×envelope 卡点 MP3
  3. merge_audio_video(paths)       →  ffmpeg 无损合流 → 02_烘焙_真人律_自动配乐.mp4

依赖: pydub (pip), ffmpeg (系统), numpy

状态: 当前管线未启用（_AUDIO_DISABLED=True），启用请安装 pydub+ffmpeg 后设为 False。
"""
from __future__ import annotations

_AUDIO_DISABLED = True  # 设为 False 启用

if _AUDIO_DISABLED:
    def compile_music_prompt(*a, **kw):
        raise RuntimeError("audio_compiler 当前禁用，启用需 pydub+ffmpeg 并设 _AUDIO_DISABLED=False")
    def bake_audio_by_envelope(*a, **kw):
        raise RuntimeError("audio_compiler 当前禁用")
    def merge_audio_video(*a, **kw):
        raise RuntimeError("audio_compiler 当前禁用")
    # ── 模块启用前，以下 380+ 行代码不会加载 ──
else:
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
        "魅惑·勾人": {"genre": "Trip-hop, lo-fi vinyl", "vocal": "sensual female vocal, breathy whisper", "bpm_range": (78, 88), "energy": "languid, oozy"},
        "纯甜·含情": {"genre": "J-pop, city pop", "vocal": "sweet female vocal, warm", "bpm_range": (92, 105), "energy": "bright, bubbly"},
        "施压·凝视": {"genre": "Dark ambient, industrial", "vocal": "spoken word, tense whisper", "bpm_range": (60, 72), "energy": "brooding, oppressive"},
        "冷压·决心": {"genre": "Dark techno, minimal", "vocal": "monotone, cold", "bpm_range": (120, 132), "energy": "relentless, mechanical"},
        "威慑·一瞬": {"genre": "Cinematic, orchestral hit", "vocal": "choir stab", "bpm_range": (60, 80), "energy": "staccato, abrupt"},
        "怒视·压人": {"genre": "Heavy bass, trap", "vocal": "aggressive rap, shouted", "bpm_range": (130, 150), "energy": "explosive, angry"},
        "鄙夷·冷瞥": {"genre": "Minimal synth, cold wave", "vocal": "sneering, deadpan", "bpm_range": (100, 115), "energy": "dismissive, icy"},
        "可怜·委屈": {"genre": "Solo piano, ambient", "vocal": "fragile female vocal, tiny", "bpm_range": (55, 68), "energy": "vulnerable, curling"},
        "要哭未哭": {"genre": "Ambient, drone", "vocal": "held breath, almost silent", "bpm_range": (50, 62), "energy": "hovering, about to break"},
        "崩溃·泄劲": {"genre": "Noise, glitch", "vocal": "scream, then silence", "bpm_range": (70, 90), "energy": "explosive then hollow"},
        "哀求·仰望": {"genre": "Acoustic guitar, hymnal", "vocal": "pleading, upward", "bpm_range": (58, 70), "energy": "yearning, reaching"},
        "惊惧·一怔": {"genre": "Pizzicato strings, glitch", "vocal": "sharp intake, frozen", "bpm_range": (80, 100), "energy": "jolted, arrested"},
        "空竭·死心": {"genre": "Drone, sub-bass", "vocal": "hollow, barely there", "bpm_range": (40, 55), "energy": "empty, static"},
        "媚杀·一眼": {"genre": "Dark R&B, trap", "vocal": "low female, sultry", "bpm_range": (65, 78), "energy": "sharp, cutting"},
        "若即若离": {"genre": "Shoegaze, dream pop", "vocal": "ethereal, distant", "bpm_range": (70, 82), "energy": "floating, ambiguous"},
        "打量·玩味": {"genre": "Jazz fusion, broken beat", "vocal": "spoken musing, amused", "bpm_range": (85, 100), "energy": "inquisitive, teasing"},
    }

    def compile_music_prompt(packet: Any) -> str:
        """情绪 → Suno/Mubert 风格提示词 + BPM 建议 + 结构注释。"""
        emotion = getattr(packet, "emotion", None) or ""
        macro = getattr(packet, "macro", None)
        style = EMOTION_MUSIC_MAP.get(emotion, {})
        genre = style.get("genre", "Ambient")
        vocal = style.get("vocal", "neutral")
        bpm_lo, bpm_hi = style.get("bpm_range", (80, 120))
        speed = getattr(macro, "speed", 50) if macro else 50
        bpm = bpm_lo + (bpm_hi - bpm_lo) * (speed / 100)
        return f"[{genre}] [{vocal}] [BPM~{bpm:.0f}] [5sec-loop] [no drums break]"

    def bake_audio_by_envelope(sparse_path_str: str, *, damping: float = 0.4) -> str:
        """02 烘焙 → 监听逐帧音量 → 输出 envelope 卡点 MP3。"""
        if not _HAS_PYDUB:
            raise RuntimeError("pydub 未安装 — pip install pydub")
        path = Path(sparse_path_str)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        frames = json.loads(path.read_text("utf-8")).get("channel_tracks", {})
        dur_ms = 5000.0
        seg = AudioSegment.silent(duration=int(dur_ms))
        ch = frames.get("blink", {}).get("keyframes", [])
        if not ch:
            ch = frames.get("pupil_x", {}).get("keyframes", [])
        for kf in ch:
            t = int(kf.get("t", 0))
            v = float(kf.get("v", 0))
            pos = int(t / 150 * dur_ms)
            vol = -60 + v * 54 * damping
            tone = AudioSegment.tone(80, duration=80).apply_gain(-60 + v * 54)
            seg = seg.overlay(tone, position=max(0, pos - 40))
        out = path.with_name(path.stem + "_audio_envelope.mp3")
        seg.export(str(out), format="mp3", bitrate="64k")
        return str(out)

    def merge_audio_video(audio_path: str, video_path: str, output_path: str | None = None) -> str:
        """ffmpeg 无损合流 → MP4。"""
        a, v = Path(audio_path), Path(video_path)
        if not a.is_file():
            raise FileNotFoundError(f"音频: {a}")
        if not v.is_file():
            raise FileNotFoundError(f"视频: {v}")
        out = Path(output_path or v.with_name(v.stem + "_w_audio.mp4"))
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(v), "-i", str(a),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
             "-shortest", str(out)],
            capture_output=True, check=True, timeout=120,
        )
        return str(out)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="音频编译")
    ap.add_argument("--bake", help="02 烘焙 JSON → envelope MP3")
    ap.add_argument("--merge", nargs=2, metavar=("AUDIO", "VIDEO"), help="合流")
    args = ap.parse_args()
    if args.bake:
        print(bake_audio_by_envelope(args.bake))
    elif args.merge:
        print(merge_audio_video(*args.merge))
    else:
        ap.print_help()