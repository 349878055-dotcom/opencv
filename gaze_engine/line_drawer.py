#!/usr/bin/env python3
"""
line_drawer.py · 纯 2D 霓虹发光控制视频渲染器
================================================
输入: 12×150 全量通道 JSON → 纯黑底红绿蓝高斯发光线条 → H.264 mp4

不依赖任何 3D 引擎，纯 OpenCV + NumPy。
ffmpeg 用于最终 H.264 转码（浏览器兼容）。
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

try:
    from gaze_engine.channel_contract import CANONICAL_KEYS
except ImportError:
    CANONICAL_KEYS = [
        "pupil_x", "pupil_y", "blink", "eyebrow",
        "pupil_scale", "iris_scale", "cornea_bulge",
        "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
    ]

DEFAULT_RES = (512, 512)
EYE_SPACING = 0.38
EYE_Y_BASE = 0.48
BROW_Y_OFFSET = -0.18
PUPIL_MAX_SHIFT = 0.08
PUPIL_MAX_VSHIFT = 0.04
BROW_MAX_LIFT = 0.06
GLOW_BLUR_KSIZE = (25, 25)
GLOW_WEIGHT = 1.5
LINE_THICKNESS_BASE = 5
GLOW_LAYERS = 2


def _load_channels(source) -> tuple[dict[str, list[float]], int, int]:
    if isinstance(source, dict):
        data = source
    else:
        data = json.loads(Path(source).read_text(encoding="utf-8"))
    ch = data.get("channels") or {}
    channels = {}
    for k in CANONICAL_KEYS:
        raw = ch.get(k, [])
        channels[k] = [float(v) for v in raw] if raw else [0.0] * 150
    fc = int(data.get("frame_count") or 150)
    fps = int(data.get("fps") or 30)
    return channels, fc, fps


def _eye_geometry(frame_idx, channels, width, height, side):
    raw = {k: channels[k][frame_idx] for k in CANONICAL_KEYS}
    cx_sign = -1 if side == "L" else 1
    eye_cx = int(width / 2 + cx_sign * EYE_SPACING * width)
    eye_cy = int(EYE_Y_BASE * height)

    px_shift = int(raw["pupil_x"] * PUPIL_MAX_SHIFT * width)
    py_shift = int(raw["pupil_y"] * PUPIL_MAX_VSHIFT * height)
    pupil_cx = eye_cx + px_shift
    pupil_cy = eye_cy + py_shift

    pupil_scale = max(0.12, 0.12 + raw["pupil_scale"] * 0.16)
    pupil_radius = int(pupil_scale * height * 0.5)
    iris_scale = max(0.18, 0.18 + raw["iris_scale"] * 0.24)
    iris_radius = int(iris_scale * height * 0.5)

    blink = raw["blink"]
    lid_upper = raw["lid_upper"]
    lid_lower = raw["lid_lower"]
    cornea = raw["cornea_bulge"]
    eye_open = 1.0 - (blink * 0.85 + lid_upper * 0.15)
    eye_open = max(0.08, min(1.0, eye_open))
    eye_rx = int((0.14 + cornea * 0.04) * width)
    eye_ry = int(eye_open * (0.10 + cornea * 0.03) * height)
    lower_lift = lid_lower * 0.3
    if lower_lift > 0:
        eye_ry = max(4, int(eye_ry * (1.0 - lower_lift * 0.5)))

    eyebrow = raw["eyebrow"]
    brow_raise = raw["brow_raise"]
    squint = raw["squint"]
    eye_gloss = raw["eye_gloss"]
    brow_lift = (brow_raise - squint * 0.6 - eyebrow * 0.4) * BROW_MAX_LIFT * height
    brow_cy = eye_cy + int(BROW_Y_OFFSET * height + brow_lift)
    brow_rx = int((0.13 + eye_gloss * 0.03) * width)
    brow_ry = int((0.035 + eye_gloss * 0.015) * height)
    brow_angle = -10 * cx_sign + squint * 8 * cx_sign
    lid_glow = 0.5 + eye_gloss * 0.5

    return {
        "eye_center": (eye_cx, eye_cy),
        "pupil_center": (pupil_cx, pupil_cy),
        "pupil_radius": pupil_radius,
        "iris_radius": iris_radius,
        "eye_rx": eye_rx, "eye_ry": eye_ry,
        "brow_center": (eye_cx, brow_cy),
        "brow_rx": brow_rx, "brow_ry": brow_ry,
        "brow_angle": brow_angle, "lid_glow": lid_glow,
    }


def draw_glowing_neon_lines(channels, frame_idx, width=512, height=512):
    if not _HAS_CV2:
        raise ImportError("opencv-python 未安装: pip install opencv-python")
    base = np.zeros((height, width, 3), dtype=np.uint8)

    for geo in (_eye_geometry(frame_idx, channels, width, height, s) for s in ("L", "R")):
        ecx, ecy = geo["eye_center"]
        pcx, pcy = geo["pupil_center"]

        # 绿色眉弧
        cv2.ellipse(base, (geo["brow_center"][0], geo["brow_center"][1]),
                    (geo["brow_rx"], geo["brow_ry"]), geo["brow_angle"],
                    160, 380, (0, 255, 0), LINE_THICKNESS_BASE + 1)

        # 红色眼眶
        cv2.ellipse(base, (ecx, ecy), (geo["eye_rx"], geo["eye_ry"]),
                    0, 0, 360, (0, 0, 255), LINE_THICKNESS_BASE)

        # 蓝色虹膜 + 瞳孔
        if geo["iris_radius"] > 3:
            cv2.circle(base, (pcx, pcy), geo["iris_radius"], (255, 0, 0), LINE_THICKNESS_BASE - 1)
        if geo["pupil_radius"] > 1:
            cv2.circle(base, (pcx, pcy), geo["pupil_radius"], (255, 0, 0), -1)
            if geo["pupil_radius"] > 4:
                cv2.circle(base, (pcx - 1, pcy - 1), max(2, geo["pupil_radius"] // 3), (255, 255, 255), -1)

    # 高斯发光
    glow = base.copy()
    for i in range(GLOW_LAYERS):
        k = (GLOW_BLUR_KSIZE[0] + i * 6, GLOW_BLUR_KSIZE[1] + i * 6)
        k = (k[0] if k[0] % 2 == 1 else k[0] + 1, k[1] if k[1] % 2 == 1 else k[1] + 1)
        glow = cv2.addWeighted(glow, 1.0, cv2.GaussianBlur(glow, k, 0), GLOW_WEIGHT * 0.5, 0)

    return np.clip(cv2.addWeighted(base, 1.0, glow, GLOW_WEIGHT, 0), 0, 255).astype(np.uint8)


def generate_control_video(source, output_path="control_video.mp4", *, width=512, height=512, fps=30):
    """
    生成全量霓虹控制视频 (H.264 mp4, 浏览器可播)。

    流程: cv2 mp4v 写临时文件 → ffmpeg 转 libx264 H.264
    """
    if not _HAS_CV2:
        raise ImportError("opencv-python 未安装: pip install opencv-python")

    channels, frame_count, src_fps = _load_channels(source)
    fps = fps or src_fps
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: cv2 写 mp4v 临时文件
    tmp = out.parent / f".tmp_{out.name}"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(tmp), fourcc, float(fps), (width, height))

    if not writer.isOpened():
        tmp = tmp.with_suffix('.avi')
        writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*'MJPG'), float(fps), (width, height))

    if not writer.isOpened():
        raise RuntimeError("无法创建视频文件 — 请确认 opencv-python 安装正确")

    for t in range(frame_count):
        writer.write(draw_glowing_neon_lines(channels, t, width, height))
    writer.release()

    # Step 2: ffmpeg → H.264 (浏览器兼容)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(tmp),
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
             "-pix_fmt", "yuv420p", "-vf", f"fps={fps}",
             str(out)],
            capture_output=True, text=True, timeout=60, check=True
        )
        tmp.unlink(missing_ok=True)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # ffmpeg 不可用，保留原始文件
        import shutil
        shutil.move(str(tmp), str(out))

    return out


def generate_control_frames_numpy(source, *, width=512, height=512):
    channels, frame_count, _ = _load_channels(source)
    frames = np.zeros((frame_count, height, width, 3), dtype=np.uint8)
    for t in range(frame_count):
        frames[t] = draw_glowing_neon_lines(channels, t, width, height)
    return frames


def generate_control_frames_tensor(source, *, width=512, height=512):
    import torch
    frames = generate_control_frames_numpy(source, width=width, height=height)
    return torch.from_numpy(frames).permute(0, 3, 1, 2).float() / 255.0


def generate_from_dense_json(dense_json_path, output_dir=None, *, width=512, height=512):
    p = Path(dense_json_path)
    out_dir = Path(output_dir) if output_dir else p.parent
    return generate_control_video(str(p), str(out_dir / "control_video.mp4"), width=width, height=height)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python line_drawer.py <dense_json> [output.mp4]")
        sys.exit(1)
    result = generate_control_video(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "control_video.mp4")
    print(f"✅ {result}")
