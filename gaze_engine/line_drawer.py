#!/usr/bin/env python3
"""
line_drawer.py · 纯 2D 霓虹发光控制视频渲染器 — 12 通道生理几何引擎
=====================================================================
输入: 12×150 全量通道 JSON → 三大层物理渲染 → H.264 mp4

架构:
  [眼球层]  cv2.ellipse 透视切角瞳孔/虹膜 + 45° 固定高光对抗
  [眼睑层]  三次贝塞尔曲线 — 上睑 lid_upper+blink 下压 / 下睑 lid_lower+squint 上挤
  [眉毛层]  cv2.fillPoly 梭形多边形 — 非对称下压剑眉

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

# ── 常量 ──────────────────────────────────────
DEFAULT_RES = (512, 512)
EYE_SPACING = 0.38           # 双眼间距比例
EYE_Y_BASE = 0.48            # 眼位 Y
BROW_Y_OFFSET = -0.18        # 眉基线高于眼
PUPIL_MAX_SHIFT = 0.08       # pupil_x 最大横向偏移比例
PUPIL_MAX_VSHIFT = 0.04      # pupil_y 最大纵向偏移比例
BROW_MAX_LIFT = 0.06         # 眉最大提升
GLOW_BLUR_KSIZE = (25, 25)
GLOW_WEIGHT = 1.5
LINE_THICKNESS_BASE = 4

# 三次贝塞尔控制点横向偏移
BEZIER_DX = 0.22              # 控制点横向偏移比例
BROW_HEAD_W = 0.055           # 眉头宽度
BROW_PEAK_W = 0.040           # 眉峰宽度
BROW_TAIL_W = 0.025           # 眉尾宽度
BROW_LEN = 0.30               # 眉毛总长度
BROW_PEAK_POS = 0.40          # 眉峰位置（0~1 沿眉长）
HIGHLIGHT_ANGLE = 45          # 高光固定角度（度）
HIGHLIGHT_DIST = 0.55         # 高光距虹膜中心距离（半径倍率）


# ═══════════════════════════════════════════════
# 1. 贝塞尔工具
# ═══════════════════════════════════════════════

def _cubic_bezier(p0, p1, p2, p3, num=40):
    """三次贝塞尔曲线 → N 个离散点 (N×2 numpy)。"""
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
# 3. 三大层几何计算
# ═══════════════════════════════════════════════

def _compute_eye_geometry(frame_idx, channels, width, height, side):
    """
    计算一帧一只眼的全部几何参数。

    Args:
        side: "L" 或 "R"

    Returns: dict 包含所有渲染所需坐标 / 半径／控制点
    """
    raw = {k: channels[k][frame_idx] for k in CANONICAL_KEYS}
    cx_sign = -1 if side == "L" else 1
    eye_cx = int(width / 2 + cx_sign * EYE_SPACING * width)
    eye_cy = int(EYE_Y_BASE * height)

    # ── 眼球层 ──────────────────────────────
    px_shift = int(raw["pupil_x"] * PUPIL_MAX_SHIFT * width)
    py_shift = int(raw["pupil_y"] * PUPIL_MAX_VSHIFT * height)
    pupil_cx = eye_cx + px_shift
    pupil_cy = eye_cy + py_shift

    pupil_scale = max(0.12, 0.12 + raw["pupil_scale"] * 0.16)
    pupil_rx = int(pupil_scale * height * 0.5)
    iris_scale = max(0.18, 0.18 + raw["iris_scale"] * 0.24)
    iris_rx = int(iris_scale * height * 0.5)

    # ▶ 透视切角：横向偏移越大 → 椭圆越扁
    # 用 pupil_x 绝对值产生纵向压缩
    px_abs = abs(raw["pupil_x"])
    perspective_squeeze = max(0.55, 1.0 - px_abs * 0.55)
    pupil_ry = max(3, int(pupil_rx * perspective_squeeze))
    iris_ry = max(4, int(iris_rx * perspective_squeeze))

    # ── 高光点（固定 45° 物理对抗） ─────────
    # 高光保持在虹膜物理原位，瞳孔在下方滑动 → 高光分离对抗
    highlight_angle_rad = math.radians(-HIGHLIGHT_ANGLE * cx_sign)
    highlight_dist = iris_rx * HIGHLIGHT_DIST
    highlight_cx = int(eye_cx + math.cos(highlight_angle_rad) * highlight_dist)
    highlight_cy = int(eye_cy + math.sin(highlight_angle_rad) * highlight_dist)
    highlight_r = max(2, int(6 * raw["eye_gloss"]))

    # ── 眼睑层 ──────────────────────────────
    blink = raw["blink"]
    lid_upper_val = raw["lid_upper"]
    lid_lower_val = raw["lid_lower"]
    squint = raw["squint"]

    # 内眼角 A / 外眼角 B
    eye_rx = int((0.14 + raw["cornea_bulge"] * 0.04) * width)
    eye_ry_base = int((0.10 + raw["cornea_bulge"] * 0.03) * height)
    a = np.array([eye_cx - eye_rx, eye_cy], dtype=np.float64)   # 内眼角
    b = np.array([eye_cx + eye_rx, eye_cy], dtype=np.float64)   # 外眼角
    bez_dx = eye_rx * BEZIER_DX

    # 上眼睑控制点 C_up — lid_upper + blink 共同驱动下压遮瞳
    lid_closure = min(1.0, blink * 0.85 + lid_upper_val * 0.30)
    up_press = lid_closure * eye_ry_base * 1.2  # 下压量
    c_up = np.array([eye_cx, eye_cy - eye_ry_base * 1.1 + up_press])

    # 下眼睑控制点 C_low — lid_lower + squint 驱动向上逆推隆起
    low_rise = min(1.0, lid_lower_val * 0.6 + squint * 0.5)
    rise_amount = low_rise * eye_ry_base * 0.9
    c_low = np.array([eye_cx, eye_cy + eye_ry_base * 0.7 - rise_amount])

    # 生成上下眼睑曲线
    upper_lid = _cubic_bezier(a, a + [bez_dx, up_press * 0.2], b - [bez_dx, up_press * 0.3], b, 36)
    lower_lid = _cubic_bezier(a, a + [bez_dx * 0.5, -rise_amount * 0.15], b - [bez_dx * 0.5, -rise_amount * 0.15], b, 36)

    # ── 眉毛层 ──────────────────────────────
    eyebrow = raw["eyebrow"]
    brow_raise_val = raw["brow_raise"]

    # 眉基线 Y（高于眼）
    brow_lift = (brow_raise_val - squint * 0.6 - eyebrow * 0.4) * BROW_MAX_LIFT * height
    brow_base_y = eye_cy + int(BROW_Y_OFFSET * height + brow_lift)

    # ▶ 非对称下压：第 ~32 帧 eyebrow 峰值时眉头压得比眉峰/眉尾更狠
    # 眉头下压权重 = 1.0; 眉峰/眉尾 = 0.5
    brow_press = eyebrow * 0.8 * height * 0.04
    head_press = brow_press * 1.0
    peak_press = brow_press * 0.5
    tail_press = brow_press * 0.3

    brow_len_px = int(BROW_LEN * width)
    brow_peak_x = int(brow_len_px * BROW_PEAK_POS)
    brow_tilt = -8 * cx_sign + squint * 6 * cx_sign
    tilt_rad = math.radians(brow_tilt)

    # 定义 4 个关键顶点（绕原点旋转后再平移）
    head_pt = np.array([-brow_len_px // 2, int(head_press)], dtype=np.int32)
    peak_pt = np.array([-brow_len_px // 2 + brow_peak_x, -int(brow_len_px * 0.12) + int(peak_press)], dtype=np.int32)
    tail_pt = np.array([brow_len_px // 2, int(tail_press * 0.5)], dtype=np.int32)
    bottom_pt = np.array([brow_len_px // 2 - brow_peak_x, BROW_HEAD_W * height + int(head_press * 0.3)], dtype=np.int32)

    # 旋转
    cos_t, sin_t = math.cos(tilt_rad), math.sin(tilt_rad)
    def _rot(p):
        return np.array([int(p[0] * cos_t - p[1] * sin_t), int(p[0] * sin_t + p[1] * cos_t)])
    head_r = _rot(head_pt)
    peak_r = _rot(peak_pt)
    tail_r = _rot(tail_pt)
    bottom_r = _rot(bottom_pt)

    brow_pts = np.array([
        [eye_cx + head_r[0], brow_base_y + head_r[1]],
        [eye_cx + peak_r[0], brow_base_y + peak_r[1]],
        [eye_cx + tail_r[0], brow_base_y + tail_r[1]],
        [eye_cx + bottom_r[0], brow_base_y + bottom_r[1]],
    ], dtype=np.int32)

    lid_glow = 0.5 + raw["eye_gloss"] * 0.5

    return {
        # 眼球
        "iris_center": (pupil_cx, pupil_cy),
        "iris_rx": iris_rx, "iris_ry": iris_ry,
        "pupil_rx": pupil_rx, "pupil_ry": pupil_ry,
        "highlight_center": (highlight_cx, highlight_cy),
        "highlight_r": highlight_r,
        # 眼睑
        "upper_lid": upper_lid.astype(np.int32),
        "lower_lid": lower_lid.astype(np.int32),
        # 眉毛
        "brow_polygon": brow_pts,
        "lid_glow": lid_glow,
    }


# ═══════════════════════════════════════════════
# 4. 单帧渲染
# ═══════════════════════════════════════════════

def draw_glowing_neon_lines(channels, frame_idx, width=512, height=512):
    if not _HAS_CV2:
        raise ImportError("opencv-python 未安装: pip install opencv-python")
    base = np.zeros((height, width, 3), dtype=np.uint8)

    for side in ("L", "R"):
        geo = _compute_eye_geometry(frame_idx, channels, width, height, side)

        # ── 眉毛层：梭形多边形 fillPoly ─────
        cv2.fillPoly(base, [geo["brow_polygon"]], (0, 255, 0))

        # ── 眼球层 ──────────────────────────
        icx, icy = geo["iris_center"]

        # 虹膜（蓝）：带透视切角的椭圆
        cv2.ellipse(base, (icx, icy), (geo["iris_rx"], geo["iris_ry"]),
                    0, 0, 360, (255, 0, 0), LINE_THICKNESS_BASE - 1)

        # 瞳孔（蓝实心）：带透视切角
        cv2.ellipse(base, (icx, icy), (geo["pupil_rx"], geo["pupil_ry"]),
                    0, 0, 360, (255, 0, 0), -1)

        # 瞳孔内白芯
        core_rx = max(2, geo["pupil_rx"] // 3)
        core_ry = max(2, geo["pupil_ry"] // 3)
        cv2.ellipse(base, (icx - 1, icy - 1), (core_rx, core_ry),
                    0, 0, 360, (255, 255, 255), -1)

        # ▶ 非对称高光（eye_gloss）：固定 45° 物理对抗
        if geo["highlight_r"] > 1:
            cv2.circle(base, geo["highlight_center"], geo["highlight_r"],
                       (255, 255, 255), -1)

        # ── 眼睑层：三次贝塞尔 polylines ───
        # 上眼睑（红）
        cv2.polylines(base, [geo["upper_lid"]], False, (0, 0, 255), LINE_THICKNESS_BASE)
        # 下眼睑（红）
        cv2.polylines(base, [geo["lower_lid"]], False, (0, 0, 255), LINE_THICKNESS_BASE)

    # ── 高斯发光 ──────────────────────────
    glow = base.copy()
    for i in range(GLOW_LAYERS := 2):
        k = (GLOW_BLUR_KSIZE[0] + i * 6, GLOW_BLUR_KSIZE[1] + i * 6)
        k = (k[0] if k[0] % 2 == 1 else k[0] + 1, k[1] if k[1] % 2 == 1 else k[1] + 1)
        glow = cv2.addWeighted(glow, 1.0, cv2.GaussianBlur(glow, k, 0), GLOW_WEIGHT * 0.5, 0)

    return np.clip(cv2.addWeighted(base, 1.0, glow, GLOW_WEIGHT, 0), 0, 255).astype(np.uint8)


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

    # ffmpeg → H.264
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
    """返回 numpy 数组 (T, H, W, 3) 供内存使用。"""
    channels, frame_count, _ = _load_channels(source)
    frames = np.zeros((frame_count, height, width, 3), dtype=np.uint8)
    for t in range(frame_count):
        frames[t] = draw_glowing_neon_lines(channels, t, width, height)
    return frames
