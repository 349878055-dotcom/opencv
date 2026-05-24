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
        ew, eh = EYE_W, EYE_H
        return {
            "corner_inner": (-ew, 0),
            "corner_outer": (ew, 0),
            "upper_0": (-int(ew*0.85), -int(eh*0.7)),
            "upper_1": (-int(ew*0.5), -int(eh*0.9)),
            "upper_2": (0, -int(eh*1.0)),
            "upper_3": (int(ew*0.5), -int(eh*0.9)),
            "upper_4": (int(ew*0.85), -int(eh*0.7)),
            "lower_0": (-int(ew*0.85), int(eh*0.6)),
            "lower_1": (-int(ew*0.5), int(eh*0.8)),
            "lower_2": (0, int(eh*0.9)),
            "lower_3": (int(ew*0.5), int(eh*0.8)),
            "lower_4": (int(ew*0.85), int(eh*0.6)),
            "iris_top": (0, -int(eh*0.55)),
            "iris_bottom": (0, int(eh*0.55)),
            "iris_left": (-int(ew*0.35), 0),
            "iris_right": (int(ew*0.35), 0),
            "pupil": (0, 0),
            "brow_inner": (-int(ew*0.7), -int(eh*1.7)),
            "brow_peak": (0, -int(eh*1.9)),
            "brow_outer": (int(ew*0.7), -int(eh*1.6)),
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
        12 通道全部参与网格变形：
        pupil_x/y, blink, eyebrow, pupil_scale, iris_scale,
        cornea_bulge, squint, brow_raise, lid_upper, lid_lower, eye_gloss
        """
        src = self.get_src_pts()
        dst = {}
        
        px = channels.get("pupil_x", 0.0)
        py = channels.get("pupil_y", 0.0)
        blink = channels.get("blink", 0.0)
        eyebrow = channels.get("eyebrow", 0.0)
        squint = channels.get("squint", 0.0)
        b_raise = channels.get("brow_raise", 0.0)
        lid_upper = channels.get("lid_upper", 0.0)
        lid_lower = channels.get("lid_lower", 0.0)
        i_scale = channels.get("iris_scale", 0.0)
        cornea_bulge = channels.get("cornea_bulge", 0.0)
        
        # 眼角固定
        dst["corner_inner"] = src["corner_inner"]
        dst["corner_outer"] = src["corner_outer"]
        
        # 上眼睑
        upper_drop = blink * BLINK_DROP + lid_upper * LID_UPPER_DROP
        for name in ["upper_0", "upper_1", "upper_2", "upper_3", "upper_4"]:
            x, y = src[name]
            factor = 1.0 - abs(x - self.cx) / EYE_W * 0.4
            dst[name] = (x, int(y + upper_drop * factor))
        
        # 下眼睑
        lower_lift = squint * SQUINT_LIFT + lid_lower * LID_LOWER_LIFT
        for name in ["lower_0", "lower_1", "lower_2", "lower_3", "lower_4"]:
            x, y = src[name]
            factor = 1.0 - abs(x - self.cx) / EYE_W * 0.3
            dst[name] = (x, int(y - lower_lift * factor))
        
        # 虹膜（iris_scale + cornea_bulge 共同影响）
        iris_s = 1.0 + i_scale * (IRIS_SCALE_RANGE - 1.0)
        bulge_s = 1.0 + cornea_bulge * 0.15
        iris_scale_val = iris_s * bulge_s
        for name in ["iris_top", "iris_bottom", "iris_left", "iris_right"]:
            x, y = src[name]
            dx, dy = x - self.cx, y - self.cy
            dst[name] = (int(self.cx + dx * iris_scale_val), int(self.cy + dy * iris_scale_val))
        
        # 瞳孔
        pupil_s = 1.0 + channels.get("pupil_scale", 0.0) * (PUPIL_SCALE_RANGE - 1.0)
        dst["pupil"] = (int(self.cx + px * PUPIL_X_RANGE * pupil_s),
                        int(self.cy + py * PUPIL_Y_RANGE * pupil_s))
        
        # 眉毛
        brow_offset = eyebrow * BROW_DOWN - b_raise * BROW_RAISE
        for name in ["brow_inner", "brow_peak", "brow_outer"]:
            x, y = src[name]
            dst[name] = (x, int(y + brow_offset))
        
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
    
        def _sp(self, pt: tuple[int, int]) -> tuple[int, int]:
            """缩放底图坐标到输出坐标"""
            return (int(pt[0] * self.sx), int(pt[1] * self.sy))
    
        def render_frame(self, channels: dict[str, float]) -> np.ndarray:
            """
            渲染一帧工程底模
            输入: 12 通道 {name: float}
            输出: (361, 690, 3) uint8 — R=眼眶, G=眉, B=瞳孔
            """
            canvas = np.zeros((OUTPUT_H, OUTPUT_W, 3), dtype=np.uint8)
            blink = channels.get("blink", 0.0)
            
            for mesh in self.meshes:
                dst = mesh.deform(channels)
                
                # 缩放全部目标点到输出坐标系
                d = {name: self._sp(pt) for name, pt in dst.items()}
                
                # ── R 通道：眼眶闭合路径 ──
                eyelid = np.int32([d["corner_inner"], d["upper_0"], d["upper_1"],
                                   d["upper_2"], d["upper_3"], d["upper_4"],
                                   d["corner_outer"], d["lower_4"], d["lower_3"],
                                   d["lower_2"], d["lower_1"], d["lower_0"],
                                   d["corner_inner"]])
                cv2.polylines(canvas, [eyelid], isClosed=True,
                              color=(0, 0, 255), thickness=EYELID_THICK, lineType=cv2.LINE_AA)
                
                # 虹膜圈
                iris = np.int32([d["iris_left"], d["iris_top"], d["iris_right"],
                                 d["iris_bottom"], d["iris_left"]])
                cv2.polylines(canvas, [iris], isClosed=True,
                              color=(0, 0, 255), thickness=IRIS_RING_THICK, lineType=cv2.LINE_AA)
                
                # ── G 通道：眉骨架线 ──
                brow = np.int32([d["brow_inner"], d["brow_peak"], d["brow_outer"]])
                cv2.polylines(canvas, [brow], isClosed=False,
                              color=(0, 255, 0), thickness=BROW_THICK, lineType=cv2.LINE_AA)
                
                # ── B 通道：瞳孔 ──
                p_scale = channels.get("pupil_scale", 0.0)
                pupil_r = max(2, int(PUPIL_R_BASE * (1.0 + p_scale * 0.5)))
                if blink < 0.95:
                    cv2.circle(canvas, d["pupil"], pupil_r,
                               color=(255, 0, 0), thickness=PUPIL_THICK, lineType=cv2.LINE_AA)
            
            return canvas
    
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