#!/usr/bin/env python3
"""
line_drawer.py · 面部纹理驱动引擎 —— 12 通道 → 参考视频变形动画
=====================================================================
输入: 12×150 全量通道 → 基于参考视频帧的纹理变形 → H.264 mp4

机制:
  1. 从参考视频提取一帧清晰正面脸作为"底座纹理"
  2. 根据 12 通道数据对眼部/眉毛区域做局部变形（瞳孔偏移、眼睑开合、眉压）
  3. 为适应 512x512 渲染分辨率，提取脸部并居中放置

依赖: opencv-python, numpy, ffmpeg（可选）
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

# ── 路径 ──────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _THIS_DIR.parent
_REF_VIDEO = _PROJECT_DIR / "资产库" / "1b5798d5e22c6e2c32df3d4236ae194a_raw.mp4"

# ── 渲染尺寸 ──────────────────────────────────
RENDER_W, RENDER_H = 512, 512


# ═══════════════════════════════════════════════
# 1. 加载参考视频 → 提取底座纹理
# ═══════════════════════════════════════════════

def _load_base_texture(ref_path: str = str(_REF_VIDEO)) -> np.ndarray:
    """从参考视频提取一帧人脸作为底座纹理，裁切脸部并缩放到 512×512。"""
    cap = cv2.VideoCapture(ref_path)
    # 跳过前几帧取稳定帧
    cap.set(cv2.CAP_PROP_POS_FRAMES, 3)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError(f"无法读取参考视频: {ref_path}")

    h, w = frame.shape[:2]
    # 裁切脸部区域（手动测量参考视频：脸在 x≈200~1050, y≈150~600）
    face = frame[120:620, 180:1080]
    # 缩放到 512×512
    return cv2.resize(face, (RENDER_W, RENDER_H), interpolation=cv2.INTER_CUBIC)


# ═══════════════════════════════════════════════
# 2. 通道加载
# ═══════════════════════════════════════════════

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


# ═══════════════════════════════════════════════
# 3. 变形参数计算
# ═══════════════════════════════════════════════

# 从参考视频手动测量的关键点（相对 512×512）：
# 左眼中心 ≈ (195, 270)，右眼中心 ≈ (375, 270)
# 虹膜半径 ≈ 30px，瞳孔半径 ≈ 18px
# 眉毛上边界 ≈ y=210，下边界 ≈ y=240

_LEFT_EYE_CX = 195
_RIGHT_EYE_CX = 375
_EYE_CY = 270
_IRIS_R = 30
_PUPIL_R = 18
_BROW_TOP = 210
_BROW_BOT = 240
_HIGHLIGHT_LX = 210  # 左眼高光固定位（45° 方向）
_HIGHLIGHT_LY = 255
_HIGHLIGHT_RX = 360
_HIGHLIGHT_RY = 255


def _compute_warp_params(raw: dict[str, float]) -> dict:
    """计算当前帧的变形参数。"""
    # 瞳孔偏移
    px_off = int(raw["pupil_x"] * 30)  # max ±30px
    py_off = int(raw["pupil_y"] * 20)  # max ±20px

    # 瞳孔/虹膜缩放
    pupil_scale = 0.5 + raw["pupil_scale"] * 0.5
    iris_scale = 0.5 + raw["iris_scale"] * 0.5

    # 眼睑闭合
    lid_close = min(1.0, raw["blink"] * 0.85 + raw["lid_upper"] * 0.30)
    lid_lift = min(1.0, raw["lid_lower"] * 0.6 + raw["squint"] * 0.5)

    # 眉压
    brow_press = raw["eyebrow"] * 0.5 - raw["brow_raise"] * 0.3

    return {
        "px_off": px_off, "py_off": py_off,
        "pupil_scale": pupil_scale, "iris_scale": iris_scale,
        "lid_close": lid_close, "lid_lift": lid_lift,
        "brow_press": brow_press,
        "eye_gloss": raw["eye_gloss"],
    }


# ═══════════════════════════════════════════════
# 4. 单帧渲染（纹理变形）
# ═══════════════════════════════════════════════

# 全局缓存 — 底座纹理只加载一次
_BASE_TEXTURE: np.ndarray | None = None


def _get_base_texture() -> np.ndarray:
    global _BASE_TEXTURE
    if _BASE_TEXTURE is None:
        _BASE_TEXTURE = _load_base_texture()
    return _BASE_TEXTURE.copy()


def draw_glowing_neon_lines(channels, frame_idx, width=RENDER_W, height=RENDER_H):
    """基于参考视频纹理的变形渲染。"""
    if not _HAS_CV2:
        raise ImportError("opencv-python 未安装: pip install opencv-python")

    base = _get_base_texture()
    raw = {k: channels[k][frame_idx] for k in CANONICAL_KEYS}
    p = _compute_warp_params(raw)

    # ── 瞳孔/虹膜变形（覆盖绘制） ─────────
    for cx, hl_cx, hl_cy in [
        (_LEFT_EYE_CX, _HIGHLIGHT_LX, _HIGHLIGHT_LY),
        (_RIGHT_EYE_CX, _HIGHLIGHT_RX, _HIGHLIGHT_RY),
    ]:
        icx = cx + p["px_off"]
        icy = _EYE_CY + p["py_off"]

        # 虹膜（深棕色覆盖）
        iris_r = int(_IRIS_R * p["iris_scale"])
        cv2.circle(base, (icx, icy), iris_r, (30, 50, 80), -1)  # 深棕色 BGR

        # 瞳孔（黑色覆盖）
        pupil_r = int(_PUPIL_R * p["pupil_scale"])
        cv2.circle(base, (icx, icy), pupil_r, (10, 10, 10), -1)

        # 瞳孔内白芯
        core_r = max(1, pupil_r // 3)
        cv2.circle(base, (icx - 1, icy - 1), core_r, (255, 255, 255), -1)

        # 高光（固定 45° 对抗）
        hl_r = max(1, int(4 * p["eye_gloss"]))
        if hl_r > 0:
            cv2.circle(base, (hl_cx, hl_cy), hl_r, (255, 255, 255), -1)

        # 上眼睑覆盖（lid_close → 用肤色覆盖上方区域模拟闭眼）
        if p["lid_close"] > 0.05:
            overlay_h = int(p["lid_close"] * 40)
            cv2.rectangle(base,
                          (cx - 50, _EYE_CY - 20 - overlay_h),
                          (cx + 50, _EYE_CY - 20),
                          (55, 75, 110), -1)  # 肤色 BGR

        # 下眼睑上挤
        if p["lid_lift"] > 0.05:
            lift_h = int(p["lid_lift"] * 15)
            cv2.rectangle(base,
                          (cx - 40, _EYE_CY + 15),
                          (cx + 40, _EYE_CY + 15 + lift_h),
                          (55, 75, 110), -1)

        # 眉压（用深色块+柔化模拟眉下压）
        if abs(p["brow_press"]) > 0.01:
            brow_y_offset = int(p["brow_press"] * 20)
            cv2.rectangle(base,
                          (cx - 60, _BROW_TOP + brow_y_offset),
                          (cx + 60, _BROW_BOT + brow_y_offset),
                          (35, 30, 25), -1)  # 深棕

    return base


# ═══════════════════════════════════════════════
# 5. 视频生成
# ═══════════════════════════════════════════════

def generate_control_video(source, output_path="control_video.mp4", *,
                           width=RENDER_W, height=RENDER_H, fps=30):
    if not _HAS_CV2:
        raise ImportError("opencv-python 未安装: pip install opencv-python")

    channels, frame_count, src_fps = _load_channels(source)
    fps = fps or src_fps
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    tmp = out.parent / f".tmp_{out.name}"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(tmp), fourcc, float(fps), (width, height))
    if not writer.isOpened():
        tmp = tmp.with_suffix('.avi')
        writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*'MJPG'),
                                 float(fps), (width, height))
    if not writer.isOpened():
        raise RuntimeError("无法创建视频文件 — 请确认 opencv-python 安装正确")

    for t in range(frame_count):
        writer.write(draw_glowing_neon_lines(channels, t, width, height))
    writer.release()

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
        import shutil
        shutil.move(str(tmp), str(out))

    return out


def generate_control_frames_numpy(source, *, width=RENDER_W, height=RENDER_H):
    channels, frame_count, _ = _load_channels(source)
    frames = np.zeros((frame_count, height, width, 3), dtype=np.uint8)
    for t in range(frame_count):
        frames[t] = draw_glowing_neon_lines(channels, t, width, height)
    return frames
