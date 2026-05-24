#!/usr/bin/env python3
"""
affine_renderer.py · 工程底模渲染引擎（供扩散引擎消费）

核心原理：
  1. 标准底图 eyelid_raw.png（R=眼眶红, G=眉绿, B=瞳孔蓝）
  2. 三角形控制网格驱动顶点位移（12 通道全部参与）
  3. 逐帧输出：三角形变形 → RGB 三色分离工程底模
  4. 0-noise · 闭合路径 · 匹配参照图 5.png 格式

用法:
  # 渲染单帧
  python -c "from gaze_engine.affine_renderer import AffineRenderer; r=AffineRenderer(); img=r.render_frame(channels_dict)"
  
  # 批量烘焙 150 帧
  python gaze_engine/affine_renderer.py --batch 资产库/.../02_烘焙_真人律.json --out /tmp/render
"""
from __future__ import annotations

import json
import sys
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

# ── 仿射渲染模块 — 已启用 ────────────────────────────
_AFFINE_DISABLED = False

# ── 路径 ─────────────────────────────────────────────
_PKG = Path(__file__).resolve().parent.parent
TEXTURE_PATH = _PKG / "eye_asset" / "derived" / "eyelid_raw.png"
OUTPUT_W, OUTPUT_H = 690, 361  # 匹配参照图 5.png 尺寸

# ── 12 通道规范（全部参与） ──────────────────────────
CANONICAL_KEYS = [
    "pupil_x", "pupil_y", "blink", "eyebrow",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# ── 眼位常量（底图 1024x1024 坐标系） ────────────────
LEFT_CX, LEFT_CY = 337, 325
RIGHT_CX, RIGHT_CY = 687, 325

# 单眼尺寸
EYE_W = 150
EYE_H = 72

# 瞳孔/虹膜
PUPIL_R_BASE = 16
IRIS_R_BASE = 44

# ── 底图抛物线常量（匹配 base_mesh_gen._eye_ring）───
UPPER_PEAK = 45      # 上眼睑抛物线峰值（px）
LOWER_BOT = 38       # 下眼睑抛物线谷值（45 * 0.85）

# ── 变形幅度常量 ─────────────────────────────────────
BLINK_DROP = 40
SQUINT_LIFT = 25
LID_UPPER_DROP = 15
LID_LOWER_LIFT = 10
BROW_DOWN = 30
BROW_RAISE = 25
PUPIL_X_RANGE = 80
PUPIL_Y_RANGE = 40
IRIS_SCALE_RANGE = 1.3
PUPIL_SCALE_RANGE = 1.5

# ── 轮廓线宽（输出像素） ─────────────────────────────
EYELID_THICK = 7       # 眼眶轮廓
IRIS_RING_THICK = 5    # 虹膜圈
BROW_THICK = 12        # 眉线
PUPIL_THICK = 2        # 瞳孔轮廓线宽（参照图为细环）


def _calc_scale() -> tuple[float, float]:
    """计算底图→输出的缩放比"""
    return OUTPUT_W / 1024.0, OUTPUT_H / 1024.0


class EyeMesh:
    """单眼三角形控制网格"""
    
    def __init__(self, cx: int, cy: int, side: int):
        self.cx = cx
        self.cy = cy
        self.side = side
        self.src = self._build_source()
        self.triangles = self._build_triangles()
        
    def _build_source(self) -> dict[str, tuple[float, float]]:
        ew = EYE_W  # 150
        # 精确匹配 base_mesh_gen._eye_ring 抛物线几何
        # 上眼睑 peak=45, 下眼睑 bot=38, 虹膜半径=22
        return {
            "corner_inner": (-ew, 0),
            "corner_outer": (ew, 0),
            # 上眼睑沿 _eye_ring 抛物线取点: y = 45*(1-(2t-1)^2)
            "upper_0": (-int(ew*0.85), -12),
            "upper_1": (-int(ew*0.5), -34),
            "upper_2": (0, -45),
            "upper_3": (int(ew*0.5), -34),
            "upper_4": (int(ew*0.85), -12),
            # 下眼睑沿 _eye_ring 抛物线取点: y = 38*(1-(2t-1)^2)
            "lower_0": (-int(ew*0.85), 10),
            "lower_1": (-int(ew*0.5), 29),
            "lower_2": (0, 38),
            "lower_3": (int(ew*0.5), 29),
            "lower_4": (int(ew*0.85), 10),
            # 虹膜边界（匹配 base_mesh_gen.IRIS_R = 22）
            "iris_top": (0, -22),
            "iris_bottom": (0, 22),
            "iris_left": (-22, 0),
            "iris_right": (22, 0),
            "pupil": (0, 0),
            # 眉毛近似位置（source 网格对称近似）
            "brow_inner": (-130, -90),
            "brow_peak": (0, -115),
            "brow_outer": (130, -90),
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
    
    def get_src_pts(self) -> dict[str, tuple[int, int]]:
        return {
            name: (self.cx + dx, self.cy + dy)
            for name, (dx, dy) in self.src.items()
        }
    
    def deform(self, channels: dict[str, float]) -> dict[str, tuple[int, int]]:
        """
        12 通道驱动变形 — 基于底图抛物线公式直接计算。
        
        核心原理（修复前 vs 修复后）：
        
        修复前（错误）：y_新 = y_原 + 指令值 * 线性衰减因子
                  → 眼角被拽下来，抛物线被压成折线
        
        修复后（正确）：y_新 = cy − 当前峰值 × (1 − (2t−1)²)
                  → 眼角 (t=0, t=1) 天然锁死在 cy，
                    中间 (t=0.5) 受峰值控制，
                    曲线始终保持完美抛物线
        
        pupil_x/y, blink, eyebrow, pupil_scale, iris_scale,
        cornea_bulge, squint, brow_raise, lid_upper, lid_lower, eye_gloss
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
        x0, x1 = cx - ew, cx + ew  # corner_inner.x, corner_outer.x
        dst["corner_inner"] = (x0, cy)
        dst["corner_outer"] = (x1, cy)
        
        # ── 上眼睑：抛物线公式 y = cy − peak × (1−(2t−1)²) ──
        upper_peak = max(-2, UPPER_PEAK - blink * BLINK_DROP - lid_upper * LID_UPPER_DROP)
        for name, x in [("upper_0", x0 + 22), ("upper_1", x0 + 75),
                         ("upper_2", cx),    ("upper_3", x1 - 75),
                         ("upper_4", x1 - 22)]:
            t = (x - x0) / (2 * ew)
            y_offset = upper_peak * (1 - (2*t - 1)**2)
            dst[name] = (x, int(cy - y_offset))
        
        # ── 下眼睑：抛物线公式 y = cy + bot × (1−(2t−1)²) ──
        lower_bot = max(-2, LOWER_BOT - squint * SQUINT_LIFT - lid_lower * LID_LOWER_LIFT)
        # 下眼睑从右到左，t 从 0 到 1
        for name, x in [("lower_4", x1 - 22), ("lower_3", x1 - 75),
                         ("lower_2", cx),      ("lower_1", x0 + 75),
                         ("lower_0", x0 + 22)]:
            t = (x1 - x) / (2 * ew)  # 反向：右→左
            y_offset = lower_bot * (1 - (2*t - 1)**2)
            dst[name] = (x, int(cy + y_offset))
        
        # ── 虹膜（iris_scale + cornea_bulge）──
        iris_s = 1.0 + i_scale * (IRIS_SCALE_RANGE - 1.0)
        bulge_s = 1.0 + cornea_bulge * 0.15
        iris_scale_val = iris_s * bulge_s
        for name, dx, dy in [("iris_top", 0, -22), ("iris_bottom", 0, 22),
                              ("iris_left", -22, 0), ("iris_right", 22, 0)]:
            dst[name] = (int(cx + dx * iris_scale_val),
                         int(cy + dy * iris_scale_val))
        
        # ── 瞳孔（随 pupil_x/y 偏移）──
        pupil_s = 1.0 + channels.get("pupil_scale", 0.0) * (PUPIL_SCALE_RANGE - 1.0)
        dst["pupil"] = (int(cx + px * PUPIL_X_RANGE * pupil_s),
                        int(cy + py * PUPIL_Y_RANGE * pupil_s))
        
        # ── 眉毛 ──
        brow_offset = eyebrow * BROW_DOWN - b_raise * BROW_RAISE
        for name, dx, dy in [("brow_inner", -130, -90),
                              ("brow_peak", 0, -115),
                              ("brow_outer", 130, -90)]:
            dst[name] = (int(cx + dx), int(cy + dy + brow_offset))
        
        return dst


if _AFFINE_DISABLED:
    class AffineRenderer:
        def __init__(self, *a, **kw): raise RuntimeError("禁用")
        def render_frame(self, *a, **kw): raise RuntimeError("禁用")
        def render_batch(self, *a, **kw): raise RuntimeError("禁用")
else:
    class AffineRenderer:
        """
        工程底模渲染引擎
        
        标准底图 eyelid_raw.png 经 12 通道驱动变形 → RGB 三色分离
        R=眼眶轮廓, G=眉轮廓, B=瞳孔轮廓
        输出尺寸 690×361，匹配参照图 5.png
        """
        def __init__(self):
            if not HAS_CV2:
                raise RuntimeError("OpenCV (cv2) 未安装")
            self.meshes = [EyeMesh(LEFT_CX, LEFT_CY, -1), EyeMesh(RIGHT_CX, RIGHT_CY, 1)]
            self.sx, self.sy = _calc_scale()
    
        def _smooth_ring(self, dst: dict, steps: int = 40) -> np.ndarray:
            """
            从变形控制点拟合抛物线，生成平滑眼睑环（82点，精确闭合）
            
            关键：把 corner_inner/corner_outer 也加入抛物线拟合，
            避免外推导致眼角跑偏 → 消除"眼睛边上多出一块"。
            
            上下眼睑共用眼角点，首尾天然闭合 → 消除毛刺。
            """
            # ── 上眼睑：7点拟合（含眼角）──
            up_names = ["corner_inner", "upper_0", "upper_1",
                        "upper_2", "upper_3", "upper_4", "corner_outer"]
            xs = np.array([dst[n][0] for n in up_names], dtype=np.float32)
            ys = np.array([dst[n][1] for n in up_names], dtype=np.float32)
            A = np.vstack([xs**2, xs, np.ones_like(xs)]).T
            a_up, b_up, c_up = np.linalg.lstsq(A, ys, rcond=None)[0]
            
            x0, x1 = dst["corner_inner"][0], dst["corner_outer"][0]
            xs_up = np.linspace(x0, x1, steps + 1)
            ys_up = a_up * xs_up**2 + b_up * xs_up + c_up
            # 强制眼角精确闭合
            ys_up[0] = dst["corner_inner"][1]
            ys_up[-1] = dst["corner_outer"][1]
            
            # ── 下眼睑：7点拟合（含眼角，逆序）──
            low_names = ["corner_outer", "lower_4", "lower_3",
                         "lower_2", "lower_1", "lower_0", "corner_inner"]
            xs = np.array([dst[n][0] for n in low_names], dtype=np.float32)
            ys = np.array([dst[n][1] for n in low_names], dtype=np.float32)
            A = np.vstack([xs**2, xs, np.ones_like(xs)]).T
            a_lo, b_lo, c_lo = np.linalg.lstsq(A, ys, rcond=None)[0]
            
            xs_lo = np.linspace(x1, x0, steps + 1)
            ys_lo = a_lo * xs_lo**2 + b_lo * xs_lo + c_lo
            # 强制眼角精确闭合
            ys_lo[0] = dst["corner_outer"][1]
            ys_lo[-1] = dst["corner_inner"][1]
            
            # ── 合并为闭合环（首尾均为 corner_inner，天然闭合）──
            ring = np.column_stack([
                np.concatenate([xs_up, xs_lo]),
                np.concatenate([ys_up, ys_lo])
            ])
            return np.array(ring, dtype=np.int32)
    
        def render_frame(self, channels: dict[str, float]) -> np.ndarray:
            """
            平滑参数渲染引擎 (Smooth Parametric Render)
            
            原理：
              不用三角网格 warp（会产生三角形边界毛刺），
              改用从 deform() 算出的变形控制点拟合抛物线，
              生成 40+ 点平滑眼睑环 → 直接画线。
            
            输出: (361, 690, 3) uint8 — R=眼眶, G=眉, B=虹膜+瞳孔
            """
            canvas = np.zeros((1024, 1024, 3), dtype=np.uint8)
            
            for mesh in self.meshes:
                dst_pts = mesh.deform(channels)
                
                # ── R 通道：抛物线拟合平滑眼睑环 ──
                ring = self._smooth_ring(dst_pts)
                cv2.polylines(canvas, [ring], True,
                              (0, 0, 255), 8, cv2.LINE_8)
                
                # ── G 通道：眉毛直接 3 点折线 ──
                brow = np.array([
                    dst_pts["brow_inner"],
                    dst_pts["brow_peak"],
                    dst_pts["brow_outer"],
                ], dtype=np.int32)
                cv2.polylines(canvas, [brow], False,
                              (0, 255, 0), 8, cv2.LINE_8)
            
            # ── B 通道：虹膜完美实心圆 + 瞳孔环 ──
            for mesh in self.meshes:
                dst_pts = mesh.deform(channels)
                i_scale = channels.get("iris_scale", 0.0)
                cornea_bulge = channels.get("cornea_bulge", 0.0)
                p_scale = channels.get("pupil_scale", 0.0)
                blink = channels.get("blink", 0.0)
                
                iris_r = max(2, int(22
                    * (1.0 + i_scale * (IRIS_SCALE_RANGE - 1.0))
                    * (1.0 + cornea_bulge * 0.15)))
                cv2.circle(canvas, (mesh.cx, mesh.cy), iris_r,
                           (255, 0, 0), -1, cv2.LINE_8)
                
                if blink < 0.95:
                    pupil_r = max(2, int(PUPIL_R_BASE * (1.0 + p_scale * 0.5)))
                    cv2.circle(canvas, dst_pts["pupil"], pupil_r,
                               (255, 0, 0), 2, cv2.LINE_8)
            
            final_output = cv2.resize(canvas, (OUTPUT_W, OUTPUT_H),
                                      interpolation=cv2.INTER_AREA)
            return final_output
    
        def render_batch(self, json_path: str | Path, out_dir: str | Path, fps: int = 30) -> Path:
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            data = json.loads(Path(json_path).read_text(encoding="utf-8"))
            ch_data = data.get("channels", data)
            fc = len(next(iter(ch_data.values())))
            fd = out_dir / "_frames"
            fd.mkdir(exist_ok=True)
            print(f"渲染 {fc} 帧工程底模...")
            for t in range(fc):
                f = {k: ch_data[k][t] for k in CANONICAL_KEYS if k in ch_data}
                cv2.imwrite(str(fd / f"f_{t:04d}.png"), self.render_frame(f))
                if (t + 1) % 30 == 0: print(f"  ... {t+1}/{fc}")
            vp = out_dir / "engineering_base.mp4"
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-f", "image2", "-r", str(fps),
                "-i", str(fd / "f_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "18", str(vp)], capture_output=True, check=True)
            import shutil; shutil.rmtree(fd)
            print(f"完成! 工程底模: {vp}")
            return vp


def main() -> int:
    if _AFFINE_DISABLED: print("禁用"); return 1
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch"); ap.add_argument("--out", default="/tmp/affine_render")
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    if not HAS_CV2: print("[ERROR] 无 cv2", file=sys.stderr); return 1
    r = AffineRenderer()
    if args.test:
        ch = {k: 0.0 for k in CANONICAL_KEYS}
        ch["pupil_x"] = 0.2; ch["eyebrow"] = 0.15
        img = r.render_frame(ch)
        p = Path(args.out); p.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p / "test_engineering.png"), img)
        print(f"已保存到 {p}/test_engineering.png ({img.shape[1]}x{img.shape[0]})")
    if args.batch: r.render_batch(args.batch, args.out, fps=args.fps)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())