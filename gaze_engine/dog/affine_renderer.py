"""
狗工程底膜渲染引擎 · DogEyeMesh

标准底图 eyelid_raw.png（复用人类底图 RGB 分离方案）
  R = 眼眶轮廓（狗眼更圆）
  G = 耳廓几何 + 眉脊线（垂耳三角形 / 立耳片）
  B = 瞳孔/虹膜（圆形）

输出尺寸 690×361，匹配扩散引擎输入。
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None
    HAS_CV2 = False
else:
    HAS_CV2 = True

from gaze_engine._shared.channel_contract import CANONICAL_KEYS

# ── 路径 ─────────────────────────────────────────────
_PKG = Path(__file__).resolve().parent.parent
TEXTURE_PATH = _PKG / "_shared" / "assets" / "eyelid_raw.png"
OUTPUT_W, OUTPUT_H = 690, 361

# ── 眼位常量（底图 1024x1024 坐标系，与人类底图一致）───
LEFT_CX, LEFT_CY = 337, 325
RIGHT_CX, RIGHT_CY = 687, 325

# ── 狗眼解剖参数（vs 人类：更圆、瞳孔占比更大）────
EYE_W = 150               # 单眼半宽
UPPER_PEAK = 38           # 上眼睑峰值（比人 45 更小 = 更圆）
LOWER_BOT = 32            # 下眼睑谷值

BLINK_DROP = 38           # 眨眼闭眼幅度
SQUINT_LIFT = 22          # 眯眼抬升
LID_UPPER_DROP = 12       # 上睑下垂
LID_LOWER_LIFT = 8        # 下睑提升

# ── 狗瞳孔/虹膜（圆形，比人更大更明显）────
PUPIL_R_BASE = 18         # 瞳孔半径基础
IRIS_R_BASE = 28          # 虹膜半径基础（比人 22 更大，狗眼水汪汪）
PUPIL_X_RANGE = 80
PUPIL_Y_RANGE = 40
IRIS_SCALE_RANGE = 1.4
PUPIL_SCALE_RANGE = 1.6

# ── 狗眉脊（狗有眉毛肌，保留）────
BROW_DOWN = 25
BROW_RAISE_AMP = 20
BROW_INNER_OFF = (-110, -80)
BROW_PEAK_OFF = (0, -100)
BROW_OUTER_OFF = (110, -80)

# ── 狗耳廓几何（G 通道绘制）────
# 垂耳（贵宾犬默认）：在眼外上方绘制弧形耳廓
EAR_LEFT_BASE = [(-50, -140), (20, -155), (90, -130)]   # 左耳控制点
EAR_RIGHT_BASE = [(610, -140), (680, -155), (750, -130)]  # 右耳控制点

# ── 轮廓线宽 ────────────────────────────────────────
EYELID_THICK = 7
IRIS_RING_THICK = 5
BROW_THICK = 10
PUPIL_THICK = 2
EAR_THICK = 10


def _calc_scale() -> tuple[float, float]:
    return OUTPUT_W / 1024.0, OUTPUT_H / 1024.0


class DogEyeMesh:
    """单眼三角形控制网格（狗版）"""

    def __init__(self, cx: int, cy: int, side: int):
        self.cx = cx
        self.cy = cy
        self.side = side  # -1=左, 1=右
        self.src = self._build_source()
        self.triangles = self._build_triangles()

    def _build_source(self) -> dict[str, tuple[float, float]]:
        ew = EYE_W
        return {
            "corner_inner": (-ew, 0),
            "corner_outer": (ew, 0),
            # 上眼睑：抛物线 (狗更圆，peak 更小)
            "upper_0": (-int(ew * 0.85), -10),
            "upper_1": (-int(ew * 0.5), -29),
            "upper_2": (0, -UPPER_PEAK),
            "upper_3": (int(ew * 0.5), -29),
            "upper_4": (int(ew * 0.85), -10),
            # 下眼睑
            "lower_0": (-int(ew * 0.85), 8),
            "lower_1": (-int(ew * 0.5), 24),
            "lower_2": (0, LOWER_BOT),
            "lower_3": (int(ew * 0.5), 24),
            "lower_4": (int(ew * 0.85), 8),
            # 虹膜（圆形）
            "iris_top": (0, -IRIS_R_BASE),
            "iris_bottom": (0, IRIS_R_BASE),
            "iris_left": (-IRIS_R_BASE, 0),
            "iris_right": (IRIS_R_BASE, 0),
            "pupil": (0, 0),
            # 眉脊（狗有眉毛肌）
            "brow_inner": BROW_INNER_OFF,
            "brow_peak": BROW_PEAK_OFF,
            "brow_outer": BROW_OUTER_OFF,
        }

    def _build_triangles(self) -> list[list[str]]:
        return [
            ["corner_inner", "upper_0", "iris_left"],
            ["upper_0", "upper_1", "iris_left"],
            ["upper_1", "upper_2", "iris_top"],
            ["upper_2", "upper_3", "iris_top"],
            ["upper_3", "upper_4", "iris_right"],
            ["upper_4", "corner_outer", "iris_right"],
            ["corner_inner", "lower_0", "iris_left"],
            ["lower_0", "lower_1", "iris_left"],
            ["lower_1", "lower_2", "iris_bottom"],
            ["lower_2", "lower_3", "iris_bottom"],
            ["lower_3", "lower_4", "iris_right"],
            ["lower_4", "corner_outer", "iris_right"],
            ["iris_left", "iris_top", "pupil"],
            ["iris_top", "iris_right", "pupil"],
            ["iris_right", "iris_bottom", "pupil"],
            ["iris_bottom", "iris_left", "pupil"],
            ["brow_inner", "brow_peak", "upper_0"],
            ["brow_peak", "brow_outer", "upper_4"],
        ]

    def deform(self, channels: dict[str, float]) -> dict[str, tuple[int, int]]:
        """
        12 通道驱动变形。
        狗版映射：
          - eyebrow → 耳位（垂耳/立耳）
          - brow_raise → 眉脊微动
          - 其余同人类
        """
        dst = {}
        cx, cy, ew = self.cx, self.cy, EYE_W

        blink = channels.get("blink", 0.0)
        squint = channels.get("squint", 0.0)
        lid_upper = channels.get("lid_upper", 0.0)
        lid_lower = channels.get("lid_lower", 0.0)
        eyebrow = channels.get("eyebrow", 0.0)
        b_raise = channels.get("brow_raise", 0.0)
        px = channels.get("pupil_x", 0.0)
        py = channels.get("pupil_y", 0.0)
        i_scale = channels.get("iris_scale", 0.0)
        cornea_bulge = channels.get("cornea_bulge", 0.0)

        # ── 眼角固定 ──
        x0, x1 = cx - ew, cx + ew
        dst["corner_inner"] = (x0, cy)
        dst["corner_outer"] = (x1, cy)

        # ── 上眼睑抛物线 ──
        upper_peak = max(-2, UPPER_PEAK - blink * BLINK_DROP - lid_upper * LID_UPPER_DROP)
        for name, x in [("upper_0", x0 + 22), ("upper_1", x0 + 75),
                         ("upper_2", cx), ("upper_3", x1 - 75),
                         ("upper_4", x1 - 22)]:
            t = (x - x0) / (2 * ew)
            y_offset = upper_peak * (1 - (2 * t - 1) ** 2)
            dst[name] = (x, int(cy - y_offset))

        # ── 下眼睑抛物线 ──
        lower_bot = max(-2, LOWER_BOT - squint * SQUINT_LIFT - lid_lower * LID_LOWER_LIFT)
        for name, x in [("lower_4", x1 - 22), ("lower_3", x1 - 75),
                         ("lower_2", cx), ("lower_1", x0 + 75),
                         ("lower_0", x0 + 22)]:
            t = (x1 - x) / (2 * ew)
            y_offset = lower_bot * (1 - (2 * t - 1) ** 2)
            dst[name] = (x, int(cy + y_offset))

        # ── 瞳孔中心 ──
        pupil_s = 1.0 + channels.get("pupil_scale", 0.0) * (PUPIL_SCALE_RANGE - 1.0)
        pupil_cx = int(cx + px * PUPIL_X_RANGE * pupil_s)
        pupil_cy = int(cy + py * PUPIL_Y_RANGE * pupil_s)
        dst["pupil"] = (pupil_cx, pupil_cy)

        # ── 虹膜（刚体跟随瞳孔）──
        iris_s = 1.0 + i_scale * (IRIS_SCALE_RANGE - 1.0)
        bulge_s = 1.0 + cornea_bulge * 0.15
        iris_scale_val = iris_s * bulge_s
        for name, dx, dy in [("iris_top", 0, -IRIS_R_BASE),
                              ("iris_bottom", 0, IRIS_R_BASE),
                              ("iris_left", -IRIS_R_BASE, 0),
                              ("iris_right", IRIS_R_BASE, 0)]:
            dst[name] = (int(pupil_cx + dx * iris_scale_val),
                         int(pupil_cy + dy * iris_scale_val))

        # ── 眉脊（狗有眉毛肌，受 brow_raise 影响）──
        # eyebrow 通道影响耳位（不在 deform 中处理）
        brow_offset = b_raise * BROW_RAISE_AMP
        for name, dx, dy in [("brow_inner", *BROW_INNER_OFF),
                              ("brow_peak", *BROW_PEAK_OFF),
                              ("brow_outer", *BROW_OUTER_OFF)]:
            dst[name] = (int(cx + dx), int(cy + dy + brow_offset))

        return dst


class DogAffineRenderer:
    """狗工程底膜渲染引擎"""

    def __init__(self):
        if not HAS_CV2:
            raise RuntimeError("OpenCV (cv2) 未安装")
        self.meshes = [DogEyeMesh(LEFT_CX, LEFT_CY, -1),
                       DogEyeMesh(RIGHT_CX, RIGHT_CY, 1)]
        self.sx, self.sy = _calc_scale()

    def _parametric_eyelid(self, mesh: DogEyeMesh, channels: dict[str, float],
                           steps: int = 40) -> np.ndarray:
        """标准参数法：抛物线公式生成眼睑环"""
        cx, cy, ew = mesh.cx, mesh.cy, EYE_W
        blink = channels.get("blink", 0.0)
        squint = channels.get("squint", 0.0)
        lid_upper = channels.get("lid_upper", 0.0)
        lid_lower = channels.get("lid_lower", 0.0)

        upper_peak = max(-2, UPPER_PEAK - blink * BLINK_DROP - lid_upper * LID_UPPER_DROP)
        lower_bot = max(-2, LOWER_BOT - squint * SQUINT_LIFT - lid_lower * LID_LOWER_LIFT)

        pts = []
        # 上眼睑：从左到右
        for i in range(steps + 1):
            t = i / steps
            x = int(cx - ew + 2 * ew * t)
            y_offset = upper_peak * (1 - (2 * t - 1) ** 2)
            pts.append((x, int(cy - y_offset)))
        # 下眼睑：从右到左
        for i in range(steps + 1):
            t = i / steps
            x = int(cx + ew - 2 * ew * t)
            y_offset = lower_bot * (1 - (2 * t - 1) ** 2)
            pts.append((x, int(cy + y_offset)))
        return np.array(pts, np.int32)

    def _ear_flap(self, mesh: DogEyeMesh, channels: dict[str, float]) -> np.ndarray:
        """绘制狗耳廓几何（垂耳版本，G 通道）。

        控制点基于 eyebrow 通道值变形：
          - eyebrow=0（全耷拉）：耳朵完全下垂（委屈）
          - eyebrow=1（全竖立）：耳朵完全竖起（警觉）

        贵宾犬垂耳：从眼外上方垂下弧形片状。
        """
        cx, cy = mesh.cx, mesh.cy
        eyebrow = channels.get("eyebrow", 0.5)

        # 耳廓控制点变换：eyebrow 控制下垂程度
        droop = 1.0 - eyebrow  # 0=竖立, 1=全垂

        # 左/右耳基点偏移
        if mesh.side == -1:  # 左眼
            base = [
                (cx - 50, cy - 140 + int(droop * 20)),
                (cx + 20, cy - 155 + int(droop * 35)),
                (cx + 90, cy - 130 + int(droop * 25)),
            ]
        else:  # 右眼
            base = [
                (cx - 50, cy - 140 + int(droop * 20)),
                (cx + 20, cy - 155 + int(droop * 35)),
                (cx + 90, cy - 130 + int(droop * 25)),
            ]

        return np.array(base, np.int32)

    def render_frame(self, channels: dict[str, float]) -> np.ndarray:
        """
        输出 RGB 三色分离工程底模：
          R = 眼眶轮廓（狗眼更圆抛物线）
          G = 耳廓几何 + 眉脊线
          B = 虹膜 + 瞳孔（圆形）

        返回: (361, 690, 3) uint8
        """
        canvas = np.zeros((1024, 1024, 3), dtype=np.uint8)

        for mesh in self.meshes:
            dst_pts = mesh.deform(channels)

            # ── R 通道：眼睑环 ──
            ring = self._parametric_eyelid(mesh, channels)
            cv2.polylines(canvas, [ring], True, (0, 0, 255),
                          EYELID_THICK, cv2.LINE_8)

            # ── G 通道：眉脊 ──
            brow = np.array([
                dst_pts["brow_inner"],
                dst_pts["brow_peak"],
                dst_pts["brow_outer"],
            ], dtype=np.int32)
            cv2.polylines(canvas, [brow], False, (0, 255, 0),
                          BROW_THICK, cv2.LINE_8)

            # ── G 通道：耳廓线（垂耳片） ──
            ear_pts = self._ear_flap(mesh, channels)
            cv2.polylines(canvas, [ear_pts], False, (0, 255, 0),
                          EAR_THICK, cv2.LINE_8)

            # ── B 通道：虹膜实心圆 + 瞳孔环 ──
            i_scale = channels.get("iris_scale", 0.0)
            cornea_bulge = channels.get("cornea_bulge", 0.0)
            p_scale = channels.get("pupil_scale", 0.0)
            blink = channels.get("blink", 0.0)

            iris_r = max(2, int(IRIS_R_BASE
                                * (1.0 + i_scale * (IRIS_SCALE_RANGE - 1.0))
                                * (1.0 + cornea_bulge * 0.15)))
            cv2.circle(canvas, dst_pts["pupil"], iris_r,
                       (255, 0, 0), -1, cv2.LINE_8)

            if blink < 0.95:
                pupil_r = max(2, int(PUPIL_R_BASE * (1.0 + p_scale * 0.5)))
                cv2.circle(canvas, dst_pts["pupil"], pupil_r,
                           (255, 0, 0), PUPIL_THICK, cv2.LINE_8)

        final_output = cv2.resize(canvas, (OUTPUT_W, OUTPUT_H),
                                  interpolation=cv2.INTER_AREA)
        return final_output

    def render_batch(self, json_path: str | Path, out_dir: str | Path, fps: int = 30) -> Path:
        """批量渲染 150 帧"""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        ch_data = data.get("channels", data)
        fc = len(next(iter(ch_data.values())))
        fd = out_dir / "_frames"
        fd.mkdir(exist_ok=True)
        print(f"渲染 {fc} 帧狗工程底模...")
        for t in range(fc):
            frame = self.render_frame({k: v[t] for k, v in ch_data.items()})
            cv2.imwrite(str(fd / f"frame_{t:04d}.png"), frame)

        # 合成为 MP4
        import subprocess
        mp4 = out_dir / "dog_base_mesh.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", str(fd / "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(mp4),
        ], capture_output=True)
        print(f"✅ 狗底膜视频: {mp4}")
        return mp4