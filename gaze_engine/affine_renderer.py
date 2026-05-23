#!/usr/bin/env python3
"""
affine_renderer.py · 仿射变形眼眉渲染引擎

核心原理：
  1. 加载一张静态眼眉底图（1024×1024）
  2. 定义三角形控制网格（每眼~20控点）
  3. 12 通道指令集驱动顶点位移
  4. cv2.getAffineTransform + cv2.warpAffine 逐三角形变形
  5. 双路输出：beauty（全彩） + skeleton（二值骨架供Wan）

用法:
  # 渲染单帧
  python -c "from gaze_engine.affine_renderer import AffineRenderer; r=AffineRenderer(); b,s=r.render_frame(channels_dict)"
  
  # 批量烘焙 150 帧
  python gaze_engine/affine_renderer.py --batch 资产库/人格包/.../02_烘焙_真人律.json --out /tmp/render
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

# ── 仿射渲染模块 — 当前管线未启用（待 2D 控制流重建） ────
_AFFINE_DISABLED = True

# ── 路径 ─────────────────────────────────────────────
_PKG = Path(__file__).resolve().parent.parent
# TEXTURE_PATH 暂缺 — eye_asset/ 已清理，待 2D 渲染恢复时重建
# TEXTURE_PATH = _PKG / "eye_asset" / "derived" / "eyelid_raw.png"
DEFAULT_RES = (1024, 1024)
W, H = DEFAULT_RES

# ── 12 通道规范 ──────────────────────────────────────
CANONICAL_KEYS = [
    "pupil_x", "pupil_y", "blink", "eyebrow",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

# ── 眼位常量（映射到 1024×1024） ─────────────────────
# 左眼中心、右眼中心
LEFT_CX, LEFT_CY = 312, 512
RIGHT_CX, RIGHT_CY = 712, 512

# 单眼尺寸
EYE_W = 200   # 半宽
EYE_H = 90    # 半高

# 瞳孔/虹膜
PUPIL_R_BASE = 16
IRIS_R_BASE = 44

# 眉位置
BROW_Y_OFF = 100   # 眼中心上方偏移
BROW_W = 140
BROW_H = 30

# ── 变形幅度常量 ─────────────────────────────────────
BLINK_DROP = 40       # blink=1 时上眼睑下移 px
SQUINT_LIFT = 25      # squint=1 时下眼睑上移 px
LID_UPPER_DROP = 15   # lid_upper=1 时上眼睑微压 px
LID_LOWER_LIFT = 10   # lid_lower=1 时下眼睑微绷 px
BROW_DOWN = 30        # eyebrow=1 时眉下压 px
BROW_RAISE = 25       # brow_raise=1 时眉上抬 px
PUPIL_X_RANGE = 80    # pupil_x 最大偏移 px
PUPIL_Y_RANGE = 40    # pupil_y 最大偏移 px
IRIS_SCALE_RANGE = 1.3  # iris_scale 最大放大倍率
PUPIL_SCALE_RANGE = 1.5 # pupil_scale 最大放大倍率

# ── 骨架输出参数 ─────────────────────────────────────
SKELETON_THRESHOLD = 80  # 二值化阈值


class EyeMesh:
    """单眼三角形控制网格"""
    
    def __init__(self, cx: int, cy: int, side: int):
        """
        cx, cy: 眼中心坐标
        side: -1(左眼) / 1(右眼)
        """
        self.cx = cx
        self.cy = cy
        self.side = side
        
        # ── 源顶点（归一化坐标 0~1，相对于眼中心） ──
        # 命名规则: {位置}_{序号}
        self.src = self._build_source()
        
        # ── 三角形连接关系（顶点索引列表） ──
        self.triangles = self._build_triangles()
        
    def _build_source(self) -> dict[str, tuple[float, float]]:
        """构建源网格顶点（归一化偏移坐标）"""
        ew = EYE_W
        eh = EYE_H
        s = self.side
        
        return {
            # 眼角
            "corner_inner": (-ew, 0),
            "corner_outer": (ew, 0),
            
            # 上眼睑（5点）
            "upper_0": (-int(ew*0.85), -int(eh*0.7)),
            "upper_1": (-int(ew*0.5), -int(eh*0.9)),
            "upper_2": (0, -int(eh*1.0)),
            "upper_3": (int(ew*0.5), -int(eh*0.9)),
            "upper_4": (int(ew*0.85), -int(eh*0.7)),
            
            # 下眼睑（5点）
            "lower_0": (-int(ew*0.85), int(eh*0.6)),
            "lower_1": (-int(ew*0.5), int(eh*0.8)),
            "lower_2": (0, int(eh*0.9)),
            "lower_3": (int(ew*0.5), int(eh*0.8)),
            "lower_4": (int(ew*0.85), int(eh*0.6)),
            
            # 虹膜边界（4点）
            "iris_top": (0, -int(eh*0.55)),
            "iris_bottom": (0, int(eh*0.55)),
            "iris_left": (-int(ew*0.35), 0),
            "iris_right": (int(ew*0.35), 0),
            
            # 瞳孔中心
            "pupil": (0, 0),
            
            # 眉毛
            "brow_inner": (-int(ew*0.7), -int(eh*1.7)),
            "brow_peak": (0, -int(eh*1.9)),
            "brow_outer": (int(ew*0.7), -int(eh*1.6)),
        }
    
    def _build_triangles(self) -> list[list[str]]:
        """构建三角形连接"""
        return [
            # 上眼睑 → 虹膜上
            ["corner_inner", "upper_0", "iris_left"],
            ["upper_0", "upper_1", "iris_left"],
            ["upper_1", "upper_2", "iris_top"],
            ["upper_2", "upper_3", "iris_top"],
            ["upper_3", "upper_4", "iris_right"],
            ["upper_4", "corner_outer", "iris_right"],
            
            # 下眼睑 → 虹膜下
            ["corner_inner", "lower_0", "iris_left"],
            ["lower_0", "lower_1", "iris_left"],
            ["lower_1", "lower_2", "iris_bottom"],
            ["lower_2", "lower_3", "iris_bottom"],
            ["lower_3", "lower_4", "iris_right"],
            ["lower_4", "corner_outer", "iris_right"],
            
            # 虹膜环 → 瞳孔
            ["iris_left", "iris_top", "pupil"],
            ["iris_top", "iris_right", "pupil"],
            ["iris_right", "iris_bottom", "pupil"],
            ["iris_bottom", "iris_left", "pupil"],
            
            # 眉毛
            ["brow_inner", "brow_peak", "upper_0"],
            ["brow_peak", "brow_outer", "upper_4"],
        ]
    
    def get_src_pts(self) -> dict[str, tuple[int, int]]:
        """获取源顶点在画布上的绝对坐标"""
        return {
            name: (self.cx + dx, self.cy + dy)
            for name, (dx, dy) in self.src.items()
        }
    
    def deform(self, channels: dict[str, float]) -> dict[str, tuple[int, int]]:
        """根据 12 通道数据计算目标顶点坐标"""
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
        p_scale = channels.get("pupil_scale", 0.0)
        i_scale = channels.get("iris_scale", 0.0)
        
        # 固定点：内外眼角不动
        dst["corner_inner"] = src["corner_inner"]
        dst["corner_outer"] = src["corner_outer"]
        
        # 上眼睑：blink + lid_upper 驱动下移
        upper_drop = blink * BLINK_DROP + lid_upper * LID_UPPER_DROP
        for name in ["upper_0", "upper_1", "upper_2", "upper_3", "upper_4"]:
            x, y = src[name]
            # 中间下移多、两边下移少
            dist_from_center = abs(x - self.cx) / EYE_W
            factor = 1.0 - dist_from_center * 0.4
            dst[name] = (x, int(y + upper_drop * factor))
        
        # 下眼睑：squint + lid_lower 驱动上移
        lower_lift = squint * SQUINT_LIFT + lid_lower * LID_LOWER_LIFT
        for name in ["lower_0", "lower_1", "lower_2", "lower_3", "lower_4"]:
            x, y = src[name]
            dist_from_center = abs(x - self.cx) / EYE_W
            factor = 1.0 - dist_from_center * 0.3
            dst[name] = (x, int(y - lower_lift * factor))
        
        # 虹膜边界：跟随眼睑微调
        iris_scale_val = 1.0 + i_scale * (IRIS_SCALE_RANGE - 1.0)
        for name in ["iris_top", "iris_bottom", "iris_left", "iris_right"]:
            x, y = src[name]
            dx = x - self.cx
            dy = y - self.cy
            dst[name] = (
                int(self.cx + dx * iris_scale_val),
                int(self.cy + dy * iris_scale_val),
            )
        
        # 瞳孔：跟随 pupil_x/pupil_y 移动 + pupil_scale 缩放
        pupil_scale_val = 1.0 + p_scale * (PUPIL_SCALE_RANGE - 1.0)
        dst["pupil"] = (
            int(self.cx + px * PUPIL_X_RANGE),
            int(self.cy + py * PUPIL_Y_RANGE),
        )
        # 瞳孔缩放会影响 iris 环到瞳孔的三角区域
        # 但我们在 iris 环顶点上做缩放即可
        
        # 眉毛：eyebrow 下压 + brow_raise 上抬
        brow_offset = eyebrow * BROW_DOWN - b_raise * BROW_RAISE
        for name in ["brow_inner", "brow_peak", "brow_outer"]:
            x, y = src[name]
            dst[name] = (x, int(y + brow_offset))
        
        return dst


if _AFFINE_DISABLED:
    # 占位实现 — 不会实际执行，仅防导入报错
    class AffineRenderer:
        """仿射变形渲染引擎（当前禁用）"""
        def __init__(self, *a, **kw):
            raise RuntimeError("affine_renderer 当前禁用（_AFFINE_DISABLED=True），待 2D 控制流重建后启用")
        def render_frame(self, *a, **kw):
            raise RuntimeError("affine_renderer 当前禁用")
        def render_batch(self, *a, **kw):
            raise RuntimeError("affine_renderer 当前禁用")
else:
    class AffineRenderer:
        """仿射变形渲染引擎"""
    
    def __init__(self, texture_path: str | Path = TEXTURE_PATH, res: tuple[int, int] = DEFAULT_RES):
        if not HAS_CV2:
            raise RuntimeError("OpenCV (cv2) 未安装")
        
        self.res = res
        self.W, self.H = res
        
        # 加载底图
        tex = cv2.imread(str(texture_path))
        if tex is None:
            raise FileNotFoundError(f"无法加载底图: {texture_path}")
        self.texture = cv2.resize(tex, res)
        
        # 构建双眼网格
        self.meshes = [
            EyeMesh(LEFT_CX, LEFT_CY, -1),
            EyeMesh(RIGHT_CX, RIGHT_CY, 1),
        ]
    
    def render_frame(self, channels: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
        """
        渲染一帧
        输入: channels — 12 通道值 {name: float}
        输出: (beauty_img, skeleton_img)
          beauty: 全彩变形结果 (H, W, 3)
          skeleton: 黑底白线骨架 (H, W, 1)
        """
        # ── 1. 从底图开始 ──
        beauty = self.texture.copy()
        
        # 用于骨架的独立画布
        skeleton = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        
        # ── 2. 对每只眼做仿射变形 ──
        for mesh in self.meshes:
            src_pts = mesh.get_src_pts()
            dst_pts = mesh.deform(channels)
            
            # 逐三角形变形
            for tri_names in mesh.triangles:
                src_tri = np.float32([src_pts[n] for n in tri_names])
                dst_tri = np.float32([dst_pts[n] for n in tri_names])
                
                # 计算仿射矩阵
                affine_mat = cv2.getAffineTransform(src_tri, dst_tri)
                
                # 计算目标三角形的 bounding rect
                dst_rect = cv2.boundingRect(dst_tri.astype(np.int32))
                x, y, w, h = dst_rect
                
                if w < 1 or h < 1:
                    continue
                
                # 偏移三角形到局部坐标
                dst_tri_local = dst_tri - np.float32([[x, y]])
                
                # 创建目标区域的掩码
                mask = np.zeros((h, w, 3), dtype=np.uint8)
                cv2.fillConvexPoly(mask, dst_tri_local.astype(np.int32), (255, 255, 255), cv2.LINE_AA)
                
                # 获取源图上的对应区域
                src_rect_x = int(affine_mat[0, 2] - affine_mat[0, 0] * x - affine_mat[0, 1] * y)
                src_rect_y = int(affine_mat[1, 2] - affine_mat[1, 0] * x - affine_mat[1, 1] * y)
                
                # 变形
                warp = cv2.warpAffine(
                    self.texture, affine_mat, (self.W, self.H),
                    dst=beauty,
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REFLECT_101,
                )
                
                # 用掩码混合到 beauty
                roi = beauty[y:y+h, x:x+w]
                if roi.shape[:2] == mask.shape[:2]:
                    mask_f = mask.astype(np.float32) / 255.0
                    warp_roi = warp[y:y+h, x:x+w]
                    beauty[y:y+h, x:x+w] = (
                        roi * (1.0 - mask_f) + warp_roi * mask_f
                    ).astype(np.uint8)
            
            # ── 3. 独立绘制瞳孔（不参与变形） ──
            px = channels.get("pupil_x", 0.0)
            py = channels.get("pupil_y", 0.0)
            p_scale = channels.get("pupil_scale", 0.0)
            i_scale = channels.get("iris_scale", 0.0)
            blink = channels.get("blink", 0.0)
            e_gloss = channels.get("eye_gloss", 0.0)
            
            pupil_r = max(2, int(PUPIL_R_BASE * (1.0 + p_scale * 0.5)))
            iris_r = max(4, int(IRIS_R_BASE * (1.0 + i_scale * 0.3)))
            
            pupil_cx = int(mesh.cx + px * PUPIL_X_RANGE)
            pupil_cy = int(mesh.cy + py * PUPIL_Y_RANGE)
            
            if blink < 0.95:
                # 虹膜圈（beauty 上保留底图质感，骨架画亮圈）
                cv2.circle(beauty, (pupil_cx, pupil_cy), iris_r, (200, 220, 255), 2, cv2.LINE_AA)
                cv2.circle(skeleton, (pupil_cx, pupil_cy), iris_r, (255, 255, 255), 2, cv2.LINE_AA)
                
                # 瞳孔
                cv2.circle(beauty, (pupil_cx, pupil_cy), pupil_r, (10, 10, 10), -1, cv2.LINE_AA)
                cv2.circle(skeleton, (pupil_cx, pupil_cy), pupil_r, (255, 255, 255), -1, cv2.LINE_AA)
                
                # 角膜鼓起（渐变光圈）
                if channels.get("cornea_bulge", 0.0) > 0.05:
                    bulge = channels["cornea_bulge"]
                    for r in range(int(iris_r * 0.6), int(iris_r * 1.2)):
                        alpha = bulge * (1.0 - r / (iris_r * 1.2)) * 0.3
                        color = (int(180 * alpha), int(200 * alpha), int(255 * alpha))
                        cv2.circle(beauty, (pupil_cx, pupil_cy), r, color, 1, cv2.LINE_AA)
                
                # 高光
                if e_gloss > 0.05:
                    gloss_r = max(1, int(6 * e_gloss))
                    gloss_cx = pupil_cx - int(iris_r * 0.3)
                    gloss_cy = pupil_cy - int(iris_r * 0.3)
                    cv2.circle(beauty, (gloss_cx, gloss_cy), gloss_r, (255, 255, 255), -1, cv2.LINE_AA)
        
        # ── 4. 提取骨架 ──
        gray = cv2.cvtColor(beauty, cv2.COLOR_BGR2GRAY)
        # Canny 边缘检测
        edges = cv2.Canny(gray, 30, 100)
        # 与独立绘制的骨架合并
        skeleton_gray = cv2.cvtColor(skeleton, cv2.COLOR_BGR2GRAY)
        skeleton_final = cv2.bitwise_or(edges, skeleton_gray)
        
        # ── 5. Beauty 后期：暗调电影风格 ──
        # 叠加暗角
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        dist = np.sqrt((xx - self.W//2)**2 + (yy - self.H//2)**2)
        max_d = np.sqrt((self.W//2)**2 + (self.H//2)**2)
        vignette = np.clip(1.0 - (dist / max_d) * 0.3, 0, 1)
        for c in range(3):
            beauty[:,:,c] = (beauty[:,:,c].astype(float) * vignette).astype(np.uint8)
        
        # 轻微锐化
        sharpen = np.array([[0, -0.2, 0], [-0.2, 1.8, -0.2], [0, -0.2, 0]], dtype=np.float32)
        beauty = cv2.filter2D(beauty, -1, sharpen)
        beauty = np.clip(beauty, 0, 255).astype(np.uint8)
        
        return beauty, skeleton_final
    
    def render_batch(
        self,
        json_path: str | Path,
        out_dir: str | Path,
        fps: int = 30,
    ) -> tuple[Path, Path]:
        """
        批量渲染 150 帧
        输入: 02_烘焙_真人律.json 路径
        输出: (beauty.mp4, skeleton_frames_dir)
        """
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载数据
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        channels_data = data.get("channels", data)
        frame_count = len(next(iter(channels_data.values())))
        
        # 骨架帧输出目录
        skeleton_dir = out_dir / "skeleton_frames"
        skeleton_dir.mkdir(exist_ok=True)
        
        # 临时帧目录
        frames_dir = out_dir / "_frames"
        frames_dir.mkdir(exist_ok=True)
        
        print(f"渲染 {frame_count} 帧...")
        for t in range(frame_count):
            frame_data = {k: channels_data[k][t] for k in CANONICAL_KEYS if k in channels_data}
            beauty, skeleton = self.render_frame(frame_data)
            
            # 保存 beauty 帧
            cv2.imwrite(str(frames_dir / f"f_{t:04d}.png"), beauty)
            # 保存骨架帧
            cv2.imwrite(str(skeleton_dir / f"skeleton_{t:04d}.png"), skeleton)
            
            if (t + 1) % 30 == 0:
                print(f"  ... {t+1}/{frame_count}")
        
        # 合成 mp4
        beauty_video = out_dir / "beauty.mp4"
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-f", "image2", "-r", str(fps),
            "-i", str(frames_dir / "f_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18",
            str(beauty_video),
        ], capture_output=True, check=True)
        
        # 清理临时帧
        import shutil
        shutil.rmtree(frames_dir)
        
        print(f"完成!")
        print(f"  Beauty: {beauty_video}")
        print(f"  Skeleton: {skeleton_dir}/ (骨架序列帧)")
        
        return beauty_video, skeleton_dir


def main() -> int:
    if _AFFINE_DISABLED:
        print("affine_renderer 当前禁用（_AFFINE_DISABLED=True）")
        return 1
    import argparse

    ap = argparse.ArgumentParser(description="仿射变形眼眉渲染引擎")
    ap.add_argument("--batch", help="02_烘焙_真人律.json 路径")
    ap.add_argument("--out", default="/tmp/affine_render", help="输出目录")
    ap.add_argument("--fps", type=int, default=30, help="帧率")
    ap.add_argument("--test", action="store_true", help="跑单帧测试")
    args = ap.parse_args()
    
    if not HAS_CV2:
        print("[ERROR] OpenCV 未安装", file=sys.stderr)
        return 1
    
    renderer = AffineRenderer()
    
    if args.test:
        # 单帧测试
        test_channels = {k: 0.0 for k in CANONICAL_KEYS}
        test_channels["pupil_x"] = 0.2
        test_channels["blink"] = 0.0
        test_channels["eyebrow"] = 0.15
        
        beauty, skeleton = renderer.render_frame(test_channels)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out / "test_beauty.png"), beauty)
        cv2.imwrite(str(out / "test_skeleton.png"), skeleton)
        print(f"测试帧已保存到 {out}/")
        print(f"  beauty: {beauty.shape}  skeleton: {skeleton.shape}")
    
    if args.batch:
        renderer.render_batch(args.batch, args.out, fps=args.fps)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())