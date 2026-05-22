#!/usr/bin/env python3
"""
line_drawer.py · 面部几何引擎 — 拟真人脸 OpenCV 渲染器
=====================================================================
输入: 12×150 全量通道 → 三大层物理渲染 → H.264 mp4

架构:
  [基底]    面部椭圆 + 肤色
  [眼球层]   巩膜白底 + 虹膜椭圆透视 + 瞳孔 + 45° 固定高光对抗
  [眼睑层]   三次贝塞尔 — 上睑 lid_upper+blink 下压 / 下睑 lid_lower+squint 上挤
  [眉毛层]   cv2.fillPoly 梭形多边形 — 非对称下压剑眉

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

# ── 面部常量 ──────────────────────────────────
DEFAULT_RES = (512, 512)
FACE_W = 0.72              # 脸宽占全图
FACE_H = 0.85              # 脸高占全图
EYE_SPACING = 0.26         # 眼间距
EYE_Y_BASE = 0.50          # 眼位 Y
EYE_RX_BASE = 0.10         # 眼水平半径（占宽）
EYE_RY_BASE = 0.075        # 眼垂直半径（占高）
BROW_Y_OFFSET = -0.15      # 眉基线高于眼
BROW_MAX_LIFT = 0.055      # 眉最大提升
PUPIL_MAX_SHIFT = 0.06     # pupil_x 最大横向偏移
PUPIL_MAX_VSHIFT = 0.030   # pupil_y 最大纵向偏移
IRIS_RX_FACTOR = 0.45      # 虹膜占眼比例
PUPIL_RX_FACTOR = 0.65     # 瞳孔占虹膜比例
HIGHLIGHT_ANGLE = 45       # 高光固定角度
HIGHLIGHT_DIST = 0.50      # 高光距虹膜中心（半径倍率）

# 眉毛
BROW_HEAD_W = 0.045        # 眉头宽度
BROW_LEN = 0.20            # 眉总长
BROW_PEAK_POS = 0.40       # 眉峰位置

# 颜色调色板（拟真肤色）
SKIN_COLOR = (55, 75, 110)         # BGR 暖肤色
SCLERA_COLOR = (200, 200, 200)     # 巩膜白
IRIS_COLOR = (80, 50, 30)           # 深棕色虹膜
PUPIL_COLOR = (10, 10, 10)          # 黑色瞳孔
BROW_COLOR = (35, 30, 25)           # 深棕眉毛
HIGHLIGHT_COLOR = (255, 255, 255)   # 白色高光
LID_COLOR = (40, 55, 90)            # 眼睑线（深肤色）


# ═══════════════════════════════════════════════
# 1. 贝塞尔工具
# ═══════════════════════════════════════════════

def _cubic_bezier(p0, p1, p2, p3, num=40):
    t = np.linspace(0, 1, num).reshape(-1, 1)
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


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
# 3. 面部几何计算
# ═══════════════════════════════════════════════

def _compute_face_geometry(frame_idx, channels, width, height):
    """计算一帧全脸的完整几何参数。"""
    raw = {k: channels[k][frame_idx] for k in CANONICAL_KEYS}

    # 脸椭圆
    face_cx = width // 2
    face_cy = height // 2
    face_rx = int(FACE_W * width / 2)
    face_ry = int(FACE_H * height / 2)

    result = {"face_center": (face_cx, face_cy), "face_rx": face_rx, "face_ry": face_ry}
    eye_data = {}

    for side in ("L", "R"):
        cx_sign = -1 if side == "L" else 1
        eye_cx = int(width / 2 + cx_sign * EYE_SPACING * width)
        eye_cy = int(EYE_Y_BASE * height)

        # 巩膜半径
        scl_rx = int(EYE_RX_BASE * width)
        scl_ry = int(EYE_RY_BASE * height)

        # 瞳孔偏移
        px_off = int(raw["pupil_x"] * PUPIL_MAX_SHIFT * width)
        py_off = int(raw["pupil_y"] * PUPIL_MAX_VSHIFT * height)
        iris_cx = eye_cx + px_off
        iris_cy = eye_cy + py_off

        # 虹膜大小（挂钩 iris_scale）
        iris_rx = int(scl_rx * IRIS_RX_FACTOR * (0.7 + raw["iris_scale"] * 0.3))
        iris_ry = int(scl_ry * IRIS_RX_FACTOR * (0.7 + raw["iris_scale"] * 0.3))

        # 透视切角
        px_abs = abs(raw["pupil_x"])
        squeeze = max(0.45, 1.0 - px_abs * 0.65)
        iris_ry = max(3, int(iris_ry * squeeze))

        # 瞳孔（挂钩 pupil_scale）
        pupil_rx = max(2, int(iris_rx * PUPIL_RX_FACTOR * (0.5 + raw["pupil_scale"] * 0.5)))
        pupil_ry = max(2, int(pupil_rx * squeeze))

        # 高光（固定 45° 物理对抗）
        hl_rad = math.radians(-HIGHLIGHT_ANGLE * cx_sign)
        hl_dist = iris_rx * HIGHLIGHT_DIST
        hl_cx = int(eye_cx + math.cos(hl_rad) * hl_dist)
        hl_cy = int(eye_cy + math.sin(hl_rad) * hl_dist)
        hl_r = max(1, int(4 * raw["eye_gloss"]))

        # 眼睑
        blink_val = raw["blink"]
        lid_u = raw["lid_upper"]
        lid_l = raw["lid_lower"]
        squint_val = raw["squint"]

        # 贝塞尔端点
        a = np.array([eye_cx - scl_rx, eye_cy], dtype=np.float64)
        b = np.array([eye_cx + scl_rx, eye_cy], dtype=np.float64)
        bez_dx = scl_rx * 0.22

        # 上眼睑：lid_upper+blink 下压遮瞳
        closure = min(1.0, blink_val * 0.85 + lid_u * 0.30)
        up_press = closure * scl_ry * 1.5
        upper_lid = _cubic_bezier(
            a, a + [bez_dx, up_press * 0.6],
            b - [bez_dx, up_press * 0.2], b, 36)

        # 下眼睑：lid_lower+squint 上挤隆起
        low_rise = min(1.0, lid_l * 0.6 + squint_val * 0.5)
        rise = low_rise * scl_ry * 1.1
        lower_lid = _cubic_bezier(
            a + [0, -rise * 0.1],
            a + [bez_dx * 0.7, -rise * 0.6],
            b - [bez_dx * 0.7, -rise * 0.6],
            b + [0, -rise * 0.1], 36)

        # 眉毛
        eyebrow_val = raw["eyebrow"]
        brow_raise_val = raw["brow_raise"]
        brow_lift = (brow_raise_val - squint_val * 0.6 - eyebrow_val * 0.4) * BROW_MAX_LIFT * height
        brow_base_y = eye_cy + int(BROW_Y_OFFSET * height + brow_lift)

        # 非对称下压
        brow_press = eyebrow_val * 0.8 * height * 0.04
        head_pr = brow_press * 1.0
        peak_pr = brow_press * 0.5
        tail_pr = brow_press * 0.3

        brow_len = int(BROW_LEN * width)
        brow_peak_x = int(brow_len * BROW_PEAK_POS)
        brow_tilt = -8 * cx_sign + squint_val * 6 * cx_sign
        tilt_r = math.radians(brow_tilt)

        pts = []
        for dx, dy in [
            (-brow_len // 2, int(head_pr)),
            (-brow_len // 2 + brow_peak_x, -int(brow_len * 0.12) + int(peak_pr)),
            (brow_len // 2, int(tail_pr * 0.5)),
            (brow_len // 2 - brow_peak_x, BROW_HEAD_W * height + int(head_pr * 0.3)),
        ]:
            ct, st = math.cos(tilt_r), math.sin(tilt_r)
            rx = int(dx * ct - dy * st)
            ry = int(dx * st + dy * ct)
            pts.append([eye_cx + rx, brow_base_y + ry])

        brow_poly = np.array(pts, dtype=np.int32)

        eye_data[side] = {
            "sclera_center": (eye_cx, eye_cy),
            "sclera_rx": scl_rx, "sclera_ry": scl_ry,
            "iris_center": (iris_cx, iris_cy),
            "iris_rx": iris_rx, "iris_ry": iris_ry,
            "pupil_rx": pupil_rx, "pupil_ry": pupil_ry,
            "highlight_center": (hl_cx, hl_cy),
            "highlight_r": hl_r,
            "upper_lid": upper_lid.astype(np.int32),
            "lower_lid": lower_lid.astype(np.int32),
            "brow_polygon": brow_poly,
        }

    result["eyes"] = eye_data
    return result


# ═══════════════════════════════════════════════
# 4. 单帧渲染
# ═══════════════════════════════════════════════

def draw_glowing_neon_lines(channels, frame_idx, width=512, height=512):
    """拟真人脸渲染（肤色基底 + 巩膜 + 虹膜 + 贝塞尔眼睑 + 梭形眉）。"""
    if not _HAS_CV2:
        raise ImportError("opencv-python 未安装: pip install opencv-python")

    base = np.zeros((height, width, 3), dtype=np.uint8)

    geo = _compute_face_geometry(frame_idx, channels, width, height)

    # ── 0. 面部基底 ────────────────────────
    cv2.ellipse(base, geo["face_center"], (geo["face_rx"], geo["face_ry"]),
                0, 0, 360, SKIN_COLOR, -1)

    for side_data in geo["eyes"].values():
        ecx, ecy = side_data["sclera_center"]
        icx, icy = side_data["iris_center"]

        # ── 1. 巩膜（眼白椭圆） ─────────────
        cv2.ellipse(base, (ecx, ecy), (side_data["sclera_rx"], side_data["sclera_ry"]),
                    0, 0, 360, SCLERA_COLOR, -1)

        # ── 2. 虹膜（深棕色椭圆透视） ───────
        cv2.ellipse(base, (icx, icy), (side_data["iris_rx"], side_data["iris_ry"]),
                    0, 0, 360, IRIS_COLOR, -1)

        # ── 3. 瞳孔（黑色椭圆） ─────────────
        cv2.ellipse(base, (icx, icy), (side_data["pupil_rx"], side_data["pupil_ry"]),
                    0, 0, 360, PUPIL_COLOR, -1)

        # 瞳孔内白芯
        core_rx = max(1, side_data["pupil_rx"] // 3)
        core_ry = max(1, side_data["pupil_ry"] // 3)
        cv2.ellipse(base, (icx - 1, icy - 1), (core_rx, core_ry),
                    0, 0, 360, HIGHLIGHT_COLOR, -1)

        # ── 4. 高光对抗（固定 45° 物理原位） ─
        if side_data["highlight_r"] > 0:
            cv2.circle(base, side_data["highlight_center"],
                       side_data["highlight_r"], HIGHLIGHT_COLOR, -1)

        # ── 5. 眼睑贝塞尔曲线 ──────────────
        cv2.polylines(base, [side_data["upper_lid"]], False, LID_COLOR, 2)
        cv2.polylines(base, [side_data["lower_lid"]], False, LID_COLOR, 2)

        # ── 6. 眉梭形多边形 ────────────────
        cv2.fillPoly(base, [side_data["brow_polygon"]], BROW_COLOR)

    # ── 高斯发光（柔化） ─────────────────
    glow = base.copy()
    for i in range(2):
        k = (25 + i * 6, 25 + i * 6)
        k = (k[0] | 1, k[1] | 1)
        glow = cv2.addWeighted(glow, 1.0, cv2.GaussianBlur(glow, k, 0), 0.5, 0)

    return np.clip(cv2.addWeighted(base, 1.0, glow, 0.6, 0), 0, 255).astype(np.uint8)


# ═══════════════════════════════════════════════
# 5. 视频生成
# ═══════════════════════════════════════════════

def generate_control_video(source, output_path="control_video.mp4", *,
                           width=512, height=512, fps=30):
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


def generate_control_frames_numpy(source, *, width=512, height=512):
    channels, frame_count, _ = _load_channels(source)
    frames = np.zeros((frame_count, height, width, 3), dtype=np.uint8)
    for t in range(frame_count):
        frames[t] = draw_glowing_neon_lines(channels, t, width, height)
    return frames
