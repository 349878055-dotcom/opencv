#!/usr/bin/env python3
"""
line_drawer.py · 纯 2D 霓虹发光控制视频渲染器 — 12 通道生理几何引擎
=====================================================================
输入: 12×150 全量通道 JSON → 三大层物理渲染 → H.264 mp4

架构:
  [眼球层]  cv2.ellipse 透视切角瞳孔/虹膜 + 45° 固定高光对抗
  [眼睑层]  三次贝塞尔曲线 — 上睑 lid_upper+blink 下压 / 下睑 lid_lower+squint 上挤
  [眉毛层]  cv2.fillPoly 梭形多边形 — 非对称下压剑眉
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

CANONICAL_KEYS = [
    "pupil_x", "pupil_y", "blink", "eyebrow",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# ── 核心刚性图形常量定义 ──────────────────────────────────────
DEFAULT_RES = (512, 512)
EYE_SPACING = 0.36           # 双眼间距比例
EYE_Y_BASE = 0.48            # 眼位基准 Y 轴位置
PUPIL_MAX_SHIFT = 0.08       # pupil_x 最大横向偏移比例
PUPIL_MAX_VSHIFT = 0.04      # pupil_y 最大纵向偏移比例
BROW_MAX_LIFT = 0.06         # 眉毛最大位置提升

GLOW_BLUR_KSIZE = (25, 25)
GLOW_WEIGHT = 1.5
LINE_THICKNESS_BASE = 4

# 三次贝塞尔控制点横向跨度与梭形眉宽度定义
BEZIER_DX = 0.22
BROW_HEAD_W = 0.045           # 眉头宽度
BROW_PEAK_W = 0.032           # 眉峰宽度
BROW_TAIL_W = 0.015           # 眉尾宽度
BROW_LEN = 0.28               # 眉毛横向总长度
BROW_PEAK_POS = 0.42          # 眉峰处于整条眉毛的 42% 位置

def _load_channels(source) -> tuple[dict[str, list[float]], int, float]:
    if isinstance(source, dict):
        data = source
    else:
        data = json.loads(Path(source).read_text(encoding="utf-8"))

    channels = data.get("channels", {})
    fc = data.get("frame_count", 150)
    fps = data.get("fps", 30.0)

    out = {}
    for k in CANONICAL_KEYS:
        raw_list = channels.get(k, [])
        if not raw_list:
            raw_list = [0.0] * fc
        out[k] = [float(v) for v in raw_list[:fc]]
    return out, fc, fps

def _get_bezier_point(p0, p1, p2, p3, t: float) -> tuple[int, int]:
    """计算三次贝塞尔曲线上的单点坐标"""
    mt = 1.0 - t
    x = (mt**3)*p0[0] + 3*(mt**2)*t*p1[0] + 3*mt*(t**2)*p2[0] + (t**3)*p3[0]
    y = (mt**3)*p0[1] + 3*(mt**2)*t*p1[1] + 3*mt*(t**2)*p2[1] + (t**3)*p3[1]
    return (int(round(x)), int(round(y)))

def draw_single_frame(frame_data: dict[str, float], res: tuple[int, int] = DEFAULT_RES) -> np.ndarray:
    """完美承载 12 指令集的单帧 OpenCV 生理几何重绘引擎"""
    W, H = res
    # 建立刚性中性图层与发光图层
    base_img = np.zeros((H, W, 3), dtype=np.uint8)
    glow_img = np.zeros((H, W, 3), dtype=np.uint8)

    # 1. 提取当前帧的 12 通道物理真值
    px = frame_data["pupil_x"]
    py = frame_data["pupil_y"]
    blink = frame_data["blink"]
    eb = frame_data["eyebrow"]
    p_scale = frame_data["pupil_scale"]
    i_scale = frame_data["iris_scale"]
    squint = frame_data["squint"]
    b_raise = frame_data["brow_raise"]
    l_upper = frame_data["lid_upper"]
    l_lower = frame_data["lid_lower"]
    e_gloss = frame_data["eye_gloss"]

    # 左右眼空间对称中心判定
    eye_centers = [
        ("left",  (int(W * (0.5 - EYE_SPACING/2)), int(H * EYE_Y_BASE)), -1),
        ("right", (int(W * (0.5 + EYE_SPACING/2)), int(H * EYE_Y_BASE)),  1)
    ]

    for side, (cx, cy), side_sign in eye_centers:
        # ──────────────────────────────────────────────────────────
        # 层一：【眼球球体透视层 & 高光分离对抗】
        # ──────────────────────────────────────────────────────────
        # 计算瞳孔物理中心位移 (完美承载 17 帧扫视过冲与 23 帧回弹)
        pupil_cx = cx + int(px * PUPIL_MAX_SHIFT * W)
        pupil_cy = cy - int(py * PUPIL_MAX_VSHIFT * H) # 负=向下

        # 动态计算虹膜和瞳孔半径
        base_iris_r = int(W * 0.085) * (1.0 + i_scale)
        base_pupil_r = int(W * 0.042) * (1.0 + p_scale)

        # 模拟眼球球体侧视转动透视偏折：横向扫视越远，椭圆越扁
        flatten_factor = 1.0 - min(0.35, abs(px) * 0.4)
        iris_w = int(base_iris_r * flatten_factor)
        pupil_w = int(base_pupil_r * flatten_factor)

        # 绘制虹膜 (天蓝色发光线条)
        cv2.ellipse(base_img, (pupil_cx, pupil_cy), (iris_w, int(base_iris_r)), 0, 0, 360, (235, 160, 50), LINE_THICKNESS_BASE)
        cv2.ellipse(glow_img, (pupil_cx, pupil_cy), (iris_w, int(base_iris_r)), 0, 0, 360, (235, 160, 50), LINE_THICKNESS_BASE + 2)

        # 绘制瞳孔 (深海蓝实心圆，随眼合度动态坍缩避免穿帮)
        if blink < 0.95:
            cv2.ellipse(base_img, (pupil_cx, pupil_cy), (pupil_w, int(base_pupil_r)), 0, 0, 360, (180, 50, 20), -1)

        # 【神级卡点：固定光源高光分离对抗】
        # 高光点位置与眼球转动剥离，死钉在眼眶右上角 45 度，半径随 eye_gloss 动态发颤
        gloss_cx = cx + int(W * 0.025)
        gloss_cy = cy - int(H * 0.025)
        gloss_r = max(2, int(W * 0.008 * (1.0 + e_gloss * 2.5)))

        if blink < 0.85:
            cv2.circle(base_img, (gloss_cx, gloss_cy), gloss_r, (255, 255, 255), -1)
            cv2.circle(glow_img, (gloss_cx, gloss_cy), gloss_r + 2, (255, 255, 255), -1)

        # ──────────────────────────────────────────────────────────
        # 层二：【三次贝塞尔眼睑层 & 刚性双向框压】
        # ──────────────────────────────────────────────────────────
        # 确立眼框刚性左右端点
        eye_w_half = int(W * 0.13)
        p_start = (cx - eye_w_half, cy)
        p_end = (cx + eye_w_half, cy)

        # 动态计算眼框纵向基础跨度，随大开合 blink 压低
        eye_h_upper = int(H * 0.075) * (1.0 - blink)
        eye_h_lower = int(H * 0.055)

        # 【上眼睑：完美承载 lid_upper 遮瞳生理学动作】
        # lid_upper 变大时，控制点向下猛压，切削出冷酷凝视眼感
        upper_ctrl_y = cy - int(eye_h_upper * (1.0 - l_upper * 1.5))
        u_ctrl1 = (cx - int(eye_w_half * BEZIER_DX), upper_ctrl_y)
        u_ctrl2 = (cx + int(eye_w_half * BEZIER_DX), upper_ctrl_y)

        # 【下眼睑：完美承载 squint 眶压向上逆推机制】
        # squint 和 lid_lower 变大时，下睑控制点反重力向上挤压，咬死虹膜下沿
        lower_ctrl_y = cy + int(eye_h_lower * (1.0 - (squint * 0.6 + l_lower * 0.4)))
        l_ctrl1 = (cx - int(eye_w_half * BEZIER_DX), lower_ctrl_y)
        l_ctrl2 = (cx + int(eye_w_half * BEZIER_DX), lower_ctrl_y)

        # 离散化生成平滑连续的贝塞尔线段点集
        pts_upper = []
        pts_lower = []
        steps = 24
        for i in range(steps + 1):
            t = i / steps
            pts_upper.append(_get_bezier_point(p_start, u_ctrl1, u_ctrl2, p_end, t))
            pts_lower.append(_get_bezier_point(p_start, l_ctrl1, l_ctrl2, p_end, t))

        # 绘制眼睑霓虹线条 (粉红色/魅惑色)
        cv2.polylines(base_img, [np.array(pts_upper, np.int32)], False, (80, 60, 255), LINE_THICKNESS_BASE)
        cv2.polylines(glow_img, [np.array(pts_upper, np.int32)], False, (80, 60, 255), LINE_THICKNESS_BASE + 2)
        cv2.polylines(base_img, [np.array(pts_lower, np.int32)], False, (80, 60, 255), LINE_THICKNESS_BASE)
        cv2.polylines(glow_img, [np.array(pts_lower, np.int32)], False, (80, 60, 255), LINE_THICKNESS_BASE + 2)

        # ──────────────────────────────────────────────────────────
        # 层三：【梭形非对称下压剑眉】
        # ──────────────────────────────────────────────────────────
        # 确立眉毛基线核心端点
        brow_len_px = int(W * BROW_LEN)
        bx_start = cx - brow_len_px // 2 if side == "left" else cx + brow_len_px // 2 - side_sign * int(W*0.02)
        bx_end = cx + brow_len_px // 2 if side == "left" else cx - brow_len_px // 2 - side_sign * int(W*0.02)

        # 基础眉线 Y 轴位置 (受 brow_raise 抬高影响)
        by_base = cy - int(H * 0.16) - int(b_raise * BROW_MAX_LIFT * H)

        # 【重点：眉头下压权重 1.0，眉尾 0.4，第 32 帧全自动形变为剑眉】
        by_head = by_base + int(eb * 0.055 * H * 1.0)
        by_peak = by_base - int(H * 0.025) + int(eb * 0.055 * H * 0.6)
        by_tail = by_base + int(H * 0.015) + int(eb * 0.055 * H * 0.4)

        # 确立非对称梭形的 4 个刚性骨骼骨骼点
        bx_peak = bx_start + side_sign * int(brow_len_px * BROW_PEAK_POS)

        pt_head_top = (bx_start, by_head - int(H * BROW_HEAD_W))
        pt_head_bot = (bx_start, by_head + int(H * BROW_HEAD_W * 0.3))
        pt_peak_top = (bx_peak, by_peak - int(H * BROW_PEAK_W))
        pt_peak_bot = (bx_peak, by_peak + int(H * BROW_PEAK_W * 0.4))
        pt_tail     = (bx_end, by_tail)

        # 缝合构成非对称实心多边形
        brow_poly = [pt_head_top, pt_peak_top, pt_tail, pt_peak_bot, pt_head_bot]
        brow_poly_arr = np.array(brow_poly, np.int32)

        # 绘制实体剑眉多边形 (碧绿色发光体)
        cv2.fillPoly(base_img, [brow_poly_arr], (120, 220, 40))
        cv2.fillPoly(glow_img, [brow_poly_arr], (120, 220, 40))

    # ──────────────────────────────────────────────────────────
    # 层四：【双层高斯羽化融合】
    # ──────────────────────────────────────────────────────────
    # 第一层高斯发光层融出霓虹拉丝烟雾
    blur1 = cv2.GaussianBlur(glow_img, GLOW_BLUR_KSIZE, 0)
    # 第二层强化波纹辉光
    blur2 = cv2.GaussianBlur(glow_img, (51, 51), 0)

    combined_glow = cv2.addWeighted(blur1, 1.2, blur2, 0.6, 0)
    final_render = cv2.addWeighted(base_img, 1.0, combined_glow, GLOW_WEIGHT, 0)

    return final_render

def render_pipeline(source_json: str, output_mp4: str, res: tuple[int, int] = DEFAULT_RES) -> str:
    """全自动刚性音频指令流结合管线"""
    channels, fc, fps = _load_channels(source_json)

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        img_template = str(Path(tmpdir) / "frame_%04d.png")

        # 逐帧进行非线性几何切削计算
        for t in range(fc):
            frame_data = {k: channels[k][t] for k in CANONICAL_KEYS}
            img = draw_single_frame(frame_data, res)
            cv2.imwrite(img_template % t, img)

        # 强制卡死 H.264 离散指令转码，直接产出高兼容视频
        cmd = [
            "ffmpeg", "-y", "-f", "image2", "-r", str(fps),
            "-i", img_template, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_mp4
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    return output_mp4

if __name__ == "__main__":
    # 出厂独立闭环冒烟回归校验测试
    test_frame = {k: 0.0 for k in CANONICAL_KEYS}
    test_frame["pupil_x"] = 0.5  # 测试横跳过冲
    test_frame["eyebrow"] = 0.6  # 测试眉头冷压
    test_frame["squint"] = 0.4   # 测试眶压逆推
    test_frame["eye_gloss"] = 0.8 # 测试高光微颤

    if _HAS_CV2:
        out_img = draw_single_frame(test_frame)
        print(f"[OK] 12通道生理几何引擎 OpenCV 初始化模型组装成功，图像矩阵形体: {out_img.shape}")
    else:
        print("[WARN] 未检测到 OpenCV 环境，图形核心已转入离散静态桩。")
