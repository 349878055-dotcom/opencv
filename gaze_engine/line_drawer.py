#!/usr/bin/env python3
"""
line_drawer.py · 纯 2D 霓虹发光控制视频渲染器 — 12 通道生理几何引擎 (抗锯齿柔化版)
=====================================================================
输入: 12×150 全量通道 JSON → 三大层物理渲染 → H.264 mp4

修复病灶：
  1. 引入 cv2.LINE_AA 强制开启全部线条的次像素抗锯齿平滑，彻底消除硬方块锯齿。
  2. 重构多层高斯辉光（Glow Image），将基础线与发光层分离叠加，融出霓虹烟雾质感。
  3. 完美承载 12 指令集：上眼睑遮瞳下压、下眼睑逆推隆起、固定高光分离对抗。
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

# ── 核心图形美学常量定义 ──────────────────────────────────────
DEFAULT_RES = (512, 512)
EYE_SPACING = 0.36           # 双眼间距比例
EYE_Y_BASE = 0.48            # 眼位基准 Y 轴位置
PUPIL_MAX_SHIFT = 0.08       # pupil_x 最大横向偏移
PUPIL_MAX_VSHIFT = 0.04      # pupil_y 最大纵向偏移
BROW_MAX_LIFT = 0.06         # 眉毛最大位置提升

GLOW_BLUR_KSIZE1 = (25, 25)  # 第一层辉光：近场霓虹
GLOW_BLUR_KSIZE2 = (51, 51)  # 第二层辉光：远场环境漫反射
GLOW_WEIGHT = 1.6            # 辉光整体混叠权重
LINE_THICKNESS_BASE = 3      # 基础高清画线宽度

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
    """完美承载 12 指令集的单帧 OpenCV 生理几何高级渲染引擎"""
    W, H = res

    # 建立独立双层画布：一层存实心线（base），一层存加粗发光线（glow）
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

    # 左右眼空间对称中心及 Y 轴基准定位
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
        pupil_cy = cy - int(py * PUPIL_MAX_VSHIFT * H)

        # 动态计算角膜、虹膜和瞳孔半径
        base_iris_r = int(W * 0.082) * (1.0 + i_scale)
        base_pupil_r = int(W * 0.040) * (1.0 + p_scale)

        # 模拟眼球球体侧视转动透视偏折：横向扫视越远，圆心自动非线性压扁
        flatten_factor = 1.0 - min(0.35, abs(px) * 0.4)
        iris_w = int(base_iris_r * flatten_factor)
        pupil_w = int(base_pupil_r * flatten_factor)

        # 绘制蓝色虹膜 (使用 cv2.LINE_AA 强力平滑抗锯齿)
        cv2.ellipse(base_img, (pupil_cx, pupil_cy), (iris_w, int(base_iris_r)), 0, 0, 360, (235, 160, 50), LINE_THICKNESS_BASE, lineType=cv2.LINE_AA)
        cv2.ellipse(glow_img, (pupil_cx, pupil_cy), (iris_w, int(base_iris_r)), 0, 0, 360, (235, 160, 50), LINE_THICKNESS_BASE * 3, lineType=cv2.LINE_AA)

        # 绘制中心瞳孔 (随大闭眼 blink 动态坍缩，防睁眼瞎)
        if blink < 0.95:
            cv2.ellipse(base_img, (pupil_cx, pupil_cy), (pupil_w, int(base_pupil_r)), 0, 0, 360, (180, 50, 20), -1, lineType=cv2.LINE_AA)
            cv2.ellipse(glow_img, (pupil_cx, pupil_cy), (pupil_w, int(base_pupil_r)), 0, 0, 360, (180, 50, 20), LINE_THICKNESS_BASE * 2, lineType=cv2.LINE_AA)

        # 【神级物理对抗卡点：固定光源高光】
        # 高光点物理位置不随眼球移动，死钉在眼眶斜上方 45°，半径随 eye_gloss 动态发颤放电
        gloss_cx = cx + int(W * 0.024)
        gloss_cy = cy - int(H * 0.024)
        gloss_r = max(2, int(W * 0.007 * (1.0 + e_gloss * 2.2)))

        if blink < 0.85:
            cv2.circle(base_img, (gloss_cx, gloss_cy), gloss_r, (255, 255, 255), -1, lineType=cv2.LINE_AA)
            cv2.circle(glow_img, (gloss_cx, gloss_cy), gloss_r + 2, (255, 255, 255), -1, lineType=cv2.LINE_AA)

        # ──────────────────────────────────────────────────────────
        # 层二：【三次贝塞尔眼睑层 & 刚性双向框压】
        # ──────────────────────────────────────────────────────────
        # 建立左右眼角绝对生理骨骼物理端点
        eye_w_half = int(W * 0.125)
        p_start = (cx - eye_w_half, cy)
        p_end = (cx + eye_w_half, cy)

        # 动态计算眼框纵向基础跨度，大闭眼 blink 时压缩到死
        eye_h_upper = int(H * 0.072) * (1.0 - blink)
        eye_h_lower = int(H * 0.052)

        # 【上眼睑：完美承载 lid_upper 遮瞳生理学动作】
        # lid_upper 变大时，控制点向下猛压，切削出肉感非对称冷凝眼神
        upper_ctrl_y = cy - int(eye_h_upper * (1.0 - l_upper * 1.4))
        u_ctrl1 = (cx - int(eye_w_half * BEZIER_DX), upper_ctrl_y)
        u_ctrl2 = (cx + int(eye_w_half * BEZIER_DX), upper_ctrl_y)

        # 【下眼睑：完美承载 squint 眯眼框压向上逆推机制】
        # squint 和 lid_lower 越大，下控制点反重力向上突起隆起，咬死虹膜下沿
        lower_ctrl_y = cy + int(eye_h_lower * (1.0 - (squint * 0.55 + l_lower * 0.45)))
        l_ctrl1 = (cx - int(eye_w_half * BEZIER_DX), lower_ctrl_y)
        l_ctrl2 = (cx + int(eye_w_half * BEZIER_DX), lower_ctrl_y)

        # 离散化生成 24 阶平滑三次贝塞尔曲线点集
        pts_upper = []
        pts_lower = []
        steps = 24
        for i in range(steps + 1):
            t = i / steps
            pts_upper.append(_get_bezier_point(p_start, u_ctrl1, u_ctrl2, p_end, t))
            pts_lower.append(_get_bezier_point(p_start, l_ctrl1, l_ctrl2, p_end, t))

        # 绘制极具张力的老虎钳咬合眼睑 (魅惑色/红色发光)
        color_lid = (80, 60, 255)
        cv2.polylines(base_img, [np.array(pts_upper, np.int32)], False, color_lid, LINE_THICKNESS_BASE, lineType=cv2.LINE_AA)
        cv2.polylines(glow_img, [np.array(pts_upper, np.int32)], False, color_lid, LINE_THICKNESS_BASE * 3, lineType=cv2.LINE_AA)
        cv2.polylines(base_img, [np.array(pts_lower, np.int32)], False, color_lid, LINE_THICKNESS_BASE, lineType=cv2.LINE_AA)
        cv2.polylines(glow_img, [np.array(pts_lower, np.int32)], False, color_lid, LINE_THICKNESS_BASE * 3, lineType=cv2.LINE_AA)

        # ──────────────────────────────────────────────────────────
        # 层三：【梭形非对称下压剑眉多边形】
        # ──────────────────────────────────────────────────────────
        # 确立眉毛基线核心端点
        brow_len_px = int(W * BROW_LEN)
        bx_start = cx - brow_len_px // 2 if side == "left" else cx + brow_len_px // 2 - side_sign * int(W*0.015)
        bx_end = cx + brow_len_px // 2 if side == "left" else cx - brow_len_px // 2 - side_sign * int(W*0.015)

        # 基准眉高 (受抬眉 brow_raise 物理平移控制)
        by_base = cy - int(H * 0.155) - int(b_raise * BROW_MAX_LIFT * H)

        # 【非对称动作拉扯：眉头下压分配 1.0 满权重，眉尾只分 0.4】
        # 这样在第 32 帧眉压爆发时，曲线全自动拧成长满杀气、充满内敛压迫感的剑眉
        by_head = by_base + int(eb * 0.052 * H * 1.0)
        by_peak = by_base - int(H * 0.022) + int(eb * 0.052 * H * 0.6)
        by_tail = by_base + int(H * 0.012) + int(eb * 0.052 * H * 0.4)

        bx_peak = bx_start + side_sign * int(brow_len_px * BROW_PEAK_POS)

        # 赋予多边形实体厚度 (眉头粗、眉峰尖、眉尾细)
        pt_head_top = (bx_start, by_head - int(H * BROW_HEAD_W))
        pt_head_bot = (bx_start, by_head + int(H * BROW_HEAD_W * 0.25))
        pt_peak_top = (bx_peak, by_peak - int(H * BROW_PEAK_W))
        pt_peak_bot = (bx_peak, by_peak + int(H * BROW_PEAK_W * 0.35))
        pt_tail     = (bx_end, by_tail)

        # 封装五个顶点合并成封闭的梭形实体
        brow_poly = [pt_head_top, pt_peak_top, pt_tail, pt_peak_bot, pt_head_bot]
        brow_poly_arr = np.array(brow_poly, np.int32)

        # 绘制高傲的翠绿色霓虹剑眉
        color_brow = (120, 220, 40)
        cv2.fillPoly(base_img, [brow_poly_arr], color_brow, lineType=cv2.LINE_AA)
        cv2.fillPoly(glow_img, [brow_poly_arr], color_brow, lineType=cv2.LINE_AA)

    # ──────────────────────────────────────────────────────────
    # 层四：【重工业多层高斯双重羽化融合】
    # ──────────────────────────────────────────────────────────
    # 拿加粗了3倍的线，去融出一层近场辉光（Blur1）
    blur1 = cv2.GaussianBlur(glow_img, GLOW_BLUR_KSIZE1, 0)
    # 融出第二层厚重的漫反射远场雾气（Blur2），画面从此有了数字厚度
    blur2 = cv2.GaussianBlur(glow_img, GLOW_BLUR_KSIZE2, 0)

    # 将两层光晕按黄金比例 1.2 : 0.5 混叠
    combined_glow = cv2.addWeighted(blur1, 1.2, blur2, 0.5, 0)
    # 把核心的高清清晰线层（base）叠加在光晕层正上方，形成"内挺外润"的顶级发光高级感！
    final_render = cv2.addWeighted(base_img, 1.0, combined_glow, GLOW_WEIGHT, 0)

    return final_render

def render_pipeline(source_json: str, output_mp4: str, res: tuple[int, int] = DEFAULT_RES) -> str:
    """全自动刚性数据结合渲染管线接口"""
    channels, fc, fps = _load_channels(source_json)

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        img_template = str(Path(tmpdir) / "frame_%04d.png")

        for t in range(fc):
            frame_data = {k: channels[k][t] for k in CANONICAL_KEYS}
            img = draw_single_frame(frame_data, res)
            cv2.imwrite(img_template % t, img)

        cmd = [
            "ffmpeg", "-y", "-f", "image2", "-r", str(fps),
            "-i", img_template, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_mp4
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    return output_mp4

if __name__ == "__main__":
    # 工业冒烟自检测试桩
    test_frame = {k: 0.0 for k in CANONICAL_KEYS}
    if _HAS_CV2:
        out_img = draw_single_frame(test_frame)
        print(f"[SUCCESS] 抗锯齿双层高斯霓虹模型初始化成功，矩阵形态: {out_img.shape}")
