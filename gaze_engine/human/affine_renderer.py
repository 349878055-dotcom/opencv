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
  python -c "from gaze_engine.human.affine_renderer import AffineRenderer; r=AffineRenderer(); img=r.render_frame(channels_dict)"
  
  # 批量烘焙 150 帧
  python gaze_engine/affine_renderer.py --batch 预设资产/.../02_烘焙_真人律.json --out /tmp/render
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

from gaze_engine._shared.affine_gloss import draw_eye_gloss
from gaze_engine._shared.species_template import (
    SpeciesTemplate,
    species_default_template,
    template_to_renderer_constants,
)

# ── 仿射渲染模块 — 已启用 ────────────────────────────
_AFFINE_DISABLED = False

# ── 路径 ─────────────────────────────────────────────
_PKG = Path(__file__).resolve().parent.parent
TEXTURE_PATH = _PKG / "_shared" / "assets" / "eyelid_raw.png"
OUTPUT_W, OUTPUT_H = 690, 361  # 匹配参照图 5.png 尺寸

# ── 12 通道规范（全部参与） ──────────────────────────
CANONICAL_KEYS = [
    "pupil_x", "pupil_y", "blink", "eyebrow",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# ── 人类默认渲染器常量（无模板参数时的回退值） ────────
_DEFAULT_CONSTANTS = template_to_renderer_constants("human", None)

LEFT_CX = _DEFAULT_CONSTANTS["LEFT_CX"]
LEFT_CY = _DEFAULT_CONSTANTS["LEFT_CY"]
RIGHT_CX = _DEFAULT_CONSTANTS["RIGHT_CX"]
RIGHT_CY = _DEFAULT_CONSTANTS["RIGHT_CY"]
EYE_W = _DEFAULT_CONSTANTS["EYE_W"]
UPPER_PEAK = _DEFAULT_CONSTANTS["UPPER_PEAK"]
LOWER_BOT = _DEFAULT_CONSTANTS["LOWER_BOT"]
PUPIL_R_BASE = _DEFAULT_CONSTANTS["PUPIL_R_BASE"]
IRIS_R_BASE = _DEFAULT_CONSTANTS["IRIS_R_BASE"]
BLINK_DROP = _DEFAULT_CONSTANTS["BLINK_DROP"]
SQUINT_LIFT = _DEFAULT_CONSTANTS["SQUINT_LIFT"]
LID_UPPER_DROP = _DEFAULT_CONSTANTS["LID_UPPER_DROP"]
LID_LOWER_LIFT = _DEFAULT_CONSTANTS["LID_LOWER_LIFT"]
BROW_DOWN = _DEFAULT_CONSTANTS["BROW_DOWN"]
BROW_RAISE = _DEFAULT_CONSTANTS["BROW_RAISE_AMP"]
PUPIL_X_RANGE = _DEFAULT_CONSTANTS["PUPIL_X_RANGE"]
PUPIL_Y_RANGE = _DEFAULT_CONSTANTS["PUPIL_Y_RANGE"]
IRIS_SCALE_RANGE = _DEFAULT_CONSTANTS["IRIS_SCALE_RANGE"]
PUPIL_SCALE_RANGE = _DEFAULT_CONSTANTS["PUPIL_SCALE_RANGE"]
EYELID_THICK = _DEFAULT_CONSTANTS["EYELID_THICK"]
BROW_THICK = _DEFAULT_CONSTANTS["BROW_THICK"]
PUPIL_THICK = _DEFAULT_CONSTANTS["PUPIL_THICK"]
BROW_INNER_OFF = tuple(_DEFAULT_CONSTANTS["BROW_INNER_OFF"])
BROW_PEAK_OFF = tuple(_DEFAULT_CONSTANTS["BROW_PEAK_OFF"])
BROW_OUTER_OFF = tuple(_DEFAULT_CONSTANTS["BROW_OUTER_OFF"])


def _calc_scale() -> tuple[float, float]:
    """计算底图→输出的缩放比"""
    return OUTPUT_W / 1024.0, OUTPUT_H / 1024.0


class EyeMesh:
    """单眼三角形控制网格（接受模板参数）"""
    
    def __init__(
        self,
        cx: int, cy: int, side: int, *,
        eye_w: int = EYE_W,
        upper_peak: int = UPPER_PEAK,
        lower_bot: int = LOWER_BOT,
        iris_r: int = 22,
        brow_inner_off: tuple = (-130, -90),
        brow_peak_off: tuple = (0, -115),
        brow_outer_off: tuple = (130, -90),
    ):
        self.cx = cx
        self.cy = cy
        self.side = side
        self.eye_w = eye_w
        self.upper_peak = upper_peak
        self.lower_bot = lower_bot
        self.iris_r = iris_r
        self.brow_inner_off = brow_inner_off
        self.brow_peak_off = brow_peak_off
        self.brow_outer_off = brow_outer_off
        self.src = self._build_source()
        self.triangles = self._build_triangles()
        
    def _build_source(self) -> dict[str, tuple[float, float]]:
        ew = self.eye_w
        up = self.upper_peak
        lb = self.lower_bot
        ir = self.iris_r
        # 上眼睑抛物线：y = up * (1-(2t-1)^2), 取 5 点
        return {
            "corner_inner": (-ew, 0),
            "corner_outer": (ew, 0),
            "upper_0": (-int(ew*0.85), -int(up*0.27)),
            "upper_1": (-int(ew*0.5), -int(up*0.76)),
            "upper_2": (0, -up),
            "upper_3": (int(ew*0.5), -int(up*0.76)),
            "upper_4": (int(ew*0.85), -int(up*0.27)),
            "lower_0": (-int(ew*0.85), int(lb*0.26)),
            "lower_1": (-int(ew*0.5), int(lb*0.76)),
            "lower_2": (0, lb),
            "lower_3": (int(ew*0.5), int(lb*0.76)),
            "lower_4": (int(ew*0.85), int(lb*0.26)),
            "iris_top": (0, -ir),
            "iris_bottom": (0, ir),
            "iris_left": (-ir, 0),
            "iris_right": (ir, 0),
            "pupil": (0, 0),
            "brow_inner": self.brow_inner_off,
            "brow_peak": self.brow_peak_off,
            "brow_outer": self.brow_outer_off,
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
    
    def deform(
        self,
        channels: dict[str, float],
        *,
        # 可覆盖的常量（从外部模板传入）
        blink_drop: int = BLINK_DROP,
        squint_lift: int = SQUINT_LIFT,
        lid_upper_drop: int = LID_UPPER_DROP,
        lid_lower_lift: int = LID_LOWER_LIFT,
        brow_down: int = BROW_DOWN,
        brow_raise: int = BROW_RAISE,
        pupil_x_range: int = PUPIL_X_RANGE,
        pupil_y_range: int = PUPIL_Y_RANGE,
        iris_scale_range: float = IRIS_SCALE_RANGE,
        pupil_scale_range: float = PUPIL_SCALE_RANGE,
    ) -> dict[str, tuple[int, int]]:
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
        cx, cy, ew = self.cx, self.cy, self.eye_w
        
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
        
        # ── 上眼睑：抛物线公式 y = cy − peak × (1−(2t−1)²) ──
        upper_peak = max(-2, self.upper_peak - blink * blink_drop - lid_upper * lid_upper_drop)
        for name, x in [("upper_0", x0 + 22), ("upper_1", x0 + 75),
                         ("upper_2", cx),    ("upper_3", x1 - 75),
                         ("upper_4", x1 - 22)]:
            t = (x - x0) / (2 * ew)
            y_offset = upper_peak * (1 - (2*t - 1)**2)
            dst[name] = (x, int(cy - y_offset))
        
        # ── 下眼睑：抛物线公式 y = cy + bot × (1−(2t−1)²) ──
        lower_bot = max(-2, self.lower_bot - squint * squint_lift - lid_lower * lid_lower_lift)
        for name, x in [("lower_4", x1 - 22), ("lower_3", x1 - 75),
                         ("lower_2", cx),      ("lower_1", x0 + 75),
                         ("lower_0", x0 + 22)]:
            t = (x1 - x) / (2 * ew)
            y_offset = lower_bot * (1 - (2*t - 1)**2)
            dst[name] = (x, int(cy + y_offset))
        
        # ── 瞳孔中心 ──
        pupil_s = 1.0 + channels.get("pupil_scale", 0.0) * (pupil_scale_range - 1.0)
        pupil_cx = int(cx + px * pupil_x_range * pupil_s)
        pupil_cy = int(cy + py * pupil_y_range * pupil_s)
        dst["pupil"] = (pupil_cx, pupil_cy)
        
        # ── 虹膜 ──
        iris_s = 1.0 + i_scale * (iris_scale_range - 1.0)
        bulge_s = 1.0 + cornea_bulge * 0.15
        iris_scale_val = iris_s * bulge_s
        ir = self.iris_r
        for name, dx, dy in [("iris_top", 0, -ir), ("iris_bottom", 0, ir),
                              ("iris_left", -ir, 0), ("iris_right", ir, 0)]:
            dst[name] = (int(pupil_cx + dx * iris_scale_val),
                         int(pupil_cy + dy * iris_scale_val))
        
        # ── 眉毛 ──
        brow_offset = eyebrow * brow_down - b_raise * brow_raise
        for name, dx, dy in [("brow_inner", *self.brow_inner_off),
                              ("brow_peak", *self.brow_peak_off),
                              ("brow_outer", *self.brow_outer_off)]:
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
        
        支持通过 template_constants 传入客户定制底膜参数。
        """
        def __init__(self, template_constants: dict[str, Any] | None = None):
            if not HAS_CV2:
                raise RuntimeError("OpenCV (cv2) 未安装")
            c = template_constants or _DEFAULT_CONSTANTS
            self.c = c  # 保存供 _parametric_eyelid 和 render_frame 使用
            self.meshes = [
                EyeMesh(c["LEFT_CX"], c["LEFT_CY"], -1,
                        eye_w=c["EYE_W"],
                        upper_peak=c["UPPER_PEAK"],
                        lower_bot=c["LOWER_BOT"],
                        brow_inner_off=tuple(c["BROW_INNER_OFF"]),
                        brow_peak_off=tuple(c["BROW_PEAK_OFF"]),
                        brow_outer_off=tuple(c["BROW_OUTER_OFF"])),
                EyeMesh(c["RIGHT_CX"], c["RIGHT_CY"], 1,
                        eye_w=c["EYE_W"],
                        upper_peak=c["UPPER_PEAK"],
                        lower_bot=c["LOWER_BOT"],
                        brow_inner_off=tuple(c["BROW_INNER_OFF"]),
                        brow_peak_off=tuple(c["BROW_PEAK_OFF"]),
                        brow_outer_off=tuple(c["BROW_OUTER_OFF"])),
            ]
            self.sx, self.sy = _calc_scale()
    
        def _parametric_eyelid(self, mesh: EyeMesh, channels: dict[str, float],
                               steps: int = 40) -> np.ndarray:
            """标准参数法，使用 self.c 中的常量。"""
            c = self.c
            cx, cy, ew = mesh.cx, mesh.cy, c["EYE_W"]
            blink = channels.get("blink", 0.0)
            squint = channels.get("squint", 0.0)
            lid_upper = channels.get("lid_upper", 0.0)
            lid_lower = channels.get("lid_lower", 0.0)
            
            upper_peak = max(-2, c["UPPER_PEAK"] - blink * c["BLINK_DROP"] - lid_upper * c["LID_UPPER_DROP"])
            lower_bot = max(-2, c["LOWER_BOT"] - squint * c["SQUINT_LIFT"] - lid_lower * c["LID_LOWER_LIFT"])
            
            pts = []
            for i in range(steps + 1):
                t = i / steps
                x = int(cx - ew + 2 * ew * t)
                y_offset = upper_peak * (1 - (2*t - 1)**2)
                pts.append((x, int(cy - y_offset)))
            for i in range(steps + 1):
                t = i / steps
                x = int(cx + ew - 2 * ew * t)
                y_offset = lower_bot * (1 - (2*t - 1)**2)
                pts.append((x, int(cy + y_offset)))
            
            return np.array(pts, np.int32)
    
        def render_frame(self, channels: dict[str, float]) -> np.ndarray:
            """
            标准参数渲染引擎。
            输出: (361, 690, 3) uint8 — R=眼眶, G=眉, B=虹膜+瞳孔
            """
            c = self.c
            canvas = np.zeros((1024, 1024, 3), dtype=np.uint8)
            
            for mesh in self.meshes:
                dst_pts = mesh.deform(channels,
                    blink_drop=c["BLINK_DROP"],
                    squint_lift=c["SQUINT_LIFT"],
                    lid_upper_drop=c["LID_UPPER_DROP"],
                    lid_lower_lift=c["LID_LOWER_LIFT"],
                    brow_down=c["BROW_DOWN"],
                    brow_raise=c["BROW_RAISE_AMP"],
                    pupil_x_range=c["PUPIL_X_RANGE"],
                    pupil_y_range=c["PUPIL_Y_RANGE"],
                    iris_scale_range=c["IRIS_SCALE_RANGE"],
                    pupil_scale_range=c["PUPIL_SCALE_RANGE"],
                )
                
                # ── R 通道：眼睑环 ──
                ring = self._parametric_eyelid(mesh, channels)
                cv2.polylines(canvas, [ring], True,
                              (0, 0, 255), c["EYELID_THICK"], cv2.LINE_8)
                
                # ── G 通道：眉毛 ──
                brow = np.array([
                    dst_pts["brow_inner"],
                    dst_pts["brow_peak"],
                    dst_pts["brow_outer"],
                ], dtype=np.int32)
                cv2.polylines(canvas, [brow], False,
                              (0, 255, 0), c["BROW_THICK"], cv2.LINE_8)
            
            # ── B 通道：虹膜 + 瞳孔 ──
            for mesh in self.meshes:
                dst_pts = mesh.deform(channels,
                    blink_drop=c["BLINK_DROP"],
                    squint_lift=c["SQUINT_LIFT"],
                    lid_upper_drop=c["LID_UPPER_DROP"],
                    lid_lower_lift=c["LID_LOWER_LIFT"],
                    brow_down=c["BROW_DOWN"],
                    brow_raise=c["BROW_RAISE_AMP"],
                    pupil_x_range=c["PUPIL_X_RANGE"],
                    pupil_y_range=c["PUPIL_Y_RANGE"],
                    iris_scale_range=c["IRIS_SCALE_RANGE"],
                    pupil_scale_range=c["PUPIL_SCALE_RANGE"],
                )
                i_scale = channels.get("iris_scale", 0.0)
                cornea_bulge = channels.get("cornea_bulge", 0.0)
                p_scale = channels.get("pupil_scale", 0.0)
                blink = channels.get("blink", 0.0)
                
                iris_r = max(2, int(c["IRIS_R_BASE"]
                    * (1.0 + i_scale * (c["IRIS_SCALE_RANGE"] - 1.0))
                    * (1.0 + cornea_bulge * 0.15)))
                cv2.circle(canvas, dst_pts["pupil"], iris_r,
                           (255, 0, 0), -1, cv2.LINE_8)
                
                if blink < 0.95:
                    pupil_r = max(2, int(c["PUPIL_R_BASE"] * (1.0 + p_scale * 0.5)))
                    cv2.circle(canvas, dst_pts["pupil"], pupil_r,
                               (255, 0, 0), c["PUPIL_THICK"], cv2.LINE_8)
                draw_eye_gloss(
                    canvas, dst_pts["pupil"], iris_r,
                    channels.get("eye_gloss", 0.0), blink,
                )
            
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