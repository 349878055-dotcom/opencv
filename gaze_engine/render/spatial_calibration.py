"""空间标定：标准底膜锚点 → 客户参考图像素对齐。

标定产出两样东西（不改底膜金标准本身）：
  1. scale — 眼距比（照片眼距 / 模型眼距），供审计与 UI 展示
  2. affine_matrix — 2×3 仿射矩阵，渲染时用 cv2.warpAffine 投影线条

用法::

    from gaze_engine.render.spatial_calibration import (
        compute_spatial_calibration,
        load_project_spatial_calibration,
    )

    cal = compute_spatial_calibration(anchors, img_w, img_h, renderer_constants)
    # cal.affine_matrix → 传给 DogAffineRenderer(spatial_calibration=cal)
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]

from asset_lib import project_dir

SCHEMA = "spatial_calibration_v1"
MODEL_CANVAS = 1024
OUTPUT_W, OUTPUT_H = 690, 361
NOSE_EYE_RATIO = 0.62  # 标准模型：鼻尖在眼中心下方 ≈ 0.62×眼距


@dataclass
class SpatialCalibration:
    """客户参考图 ↔ 标准模型 的空间配准结果。"""

    scale: float
    affine_matrix: list[list[float]]
    model_anchors: dict[str, list[float]]
    photo_anchors: dict[str, list[float]]
    output_anchors: dict[str, list[float]]
    image_size: list[int]
    photo_affine_matrix: list[list[float]] = field(default_factory=list)
    nose_eye_ratio: float = NOSE_EYE_RATIO
    output_size: list[int] = field(default_factory=lambda: [OUTPUT_W, OUTPUT_H])
    model_canvas: int = MODEL_CANVAS
    schema: str = SCHEMA

    def matrix_np(self) -> np.ndarray:
        return np.array(self.affine_matrix, dtype=np.float32)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpatialCalibration | None:
        if not data or not data.get("affine_matrix"):
            return None
        return cls(
            scale=float(data.get("scale", 1.0)),
            affine_matrix=data["affine_matrix"],
            photo_affine_matrix=list(data.get("photo_affine_matrix") or []),
            model_anchors=data.get("model_anchors") or {},
            photo_anchors=data.get("photo_anchors") or {},
            output_anchors=data.get("output_anchors") or {},
            image_size=list(data.get("image_size") or [0, 0]),
            nose_eye_ratio=float(data.get("nose_eye_ratio") or NOSE_EYE_RATIO),
            output_size=list(data.get("output_size") or [OUTPUT_W, OUTPUT_H]),
            model_canvas=int(data.get("model_canvas") or MODEL_CANVAS),
            schema=data.get("schema") or SCHEMA,
        )

    def matrix_photo_np(self) -> np.ndarray:
        if self.photo_affine_matrix and len(self.photo_affine_matrix) == 2:
            return np.array(self.photo_affine_matrix, dtype=np.float32)
        return self.matrix_np()

    def warp(self, canvas: np.ndarray) -> np.ndarray:
        """将 1024 模型画布投影到输出分辨率（默认 690×361）。"""
        if cv2 is None:
            raise RuntimeError("OpenCV (cv2) 未安装")
        ow, oh = self.output_size[0], self.output_size[1]
        return cv2.warpAffine(
            canvas,
            self.matrix_np(),
            (ow, oh),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )

    def warp_photo(self, photo_bgr: np.ndarray) -> np.ndarray:
        """将原图投影到与底膜相同的输出画布。"""
        if cv2 is None:
            raise RuntimeError("OpenCV (cv2) 未安装")
        ow, oh = self.output_size[0], self.output_size[1]
        if self.photo_affine_matrix and len(self.photo_affine_matrix) == 2:
            M = self.matrix_photo_np()
        else:
            # 旧标定文件无 photo_affine_matrix：从锚点现场重建
            le = self.photo_anchors.get("left_eye")
            re = self.photo_anchors.get("right_eye")
            nose = self.photo_anchors.get("nose")
            ol = self.output_anchors.get("left_eye")
            or_ = self.output_anchors.get("right_eye")
            on = self.output_anchors.get("nose")
            if not all([le, re, nose, ol, or_, on]):
                raise ValueError("缺少照片/输出锚点，无法 warp 原图")
            src = np.float32([le, re, nose])
            dst = np.float32([ol, or_, on])
            M = cv2.getAffineTransform(src, dst)
        return cv2.warpAffine(
            photo_bgr,
            M,
            (ow, oh),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )


def _anchor_pt(anchors: dict[str, Any], key: str) -> tuple[float, float]:
    p = anchors.get(key)
    if not p or len(p) < 2:
        raise ValueError(f"缺少锚点: {key}")
    return float(p[0]), float(p[1])


def nose_eye_ratio_from_anchors(anchors: dict[str, Any]) -> float:
    """从照片三点标定推算眼-鼻垂直比（中庭长度）。"""
    try:
        le = _anchor_pt(anchors, "left_eye")
        re = _anchor_pt(anchors, "right_eye")
        nose = _anchor_pt(anchors, "nose")
    except ValueError:
        return NOSE_EYE_RATIO
    eye_dist = math.hypot(re[0] - le[0], re[1] - le[1])
    mid_y = (le[1] + re[1]) * 0.5
    dy = nose[1] - mid_y
    if dy > 0 and eye_dist >= 5:
        return max(0.35, min(0.95, dy / eye_dist))
    return NOSE_EYE_RATIO


def standard_model_anchors(
    renderer_constants: dict[str, Any],
    anchor_mode: str = "eye_center",
    *,
    nose_eye_ratio: float | None = None,
) -> np.ndarray:
    """标准底膜在 1024 画布上的三角锚点（左眼、右眼、鼻尖）。

    Args:
        renderer_constants: 渲染器常量（含 LEFT_CX, RIGHT_CX 等）
        anchor_mode: "eye_center"（眼中心，默认）| "outer_canthus"（外眼角）

    外眼角模式：
        - 左外眼角 = (LEFT_CX - EYE_W, LEFT_CY)   # 左眼外角在左侧（远离鼻子）
        - 右外眼角 = (RIGHT_CX + EYE_W, RIGHT_CY)  # 右眼外角在右侧（远离鼻子）
    """
    ly = float(renderer_constants["LEFT_CY"])
    ry = float(renderer_constants["RIGHT_CY"])

    if anchor_mode == "outer_canthus":
        ew = float(renderer_constants.get("EYE_W", 150))
        lx = float(renderer_constants["LEFT_CX"]) - ew
        rx = float(renderer_constants["RIGHT_CX"]) + ew
    else:
        lx = float(renderer_constants["LEFT_CX"])
        rx = float(renderer_constants["RIGHT_CX"])

    cx = (lx + rx) * 0.5
    eye_dist = rx - lx
    ratio = float(nose_eye_ratio) if nose_eye_ratio is not None else NOSE_EYE_RATIO
    nose_y = (ly + ry) * 0.5 + eye_dist * ratio
    return np.float32([[lx, ly], [rx, ry], [cx, nose_y]])


def _map_photo_to_output(
    x: float, y: float, img_w: int, img_h: int,
    out_w: int = OUTPUT_W, out_h: int = OUTPUT_H,
) -> tuple[float, float]:
    return x * out_w / max(img_w, 1), y * out_h / max(img_h, 1)


def compute_spatial_calibration(
    anchors: dict[str, Any],
    img_width: int,
    img_height: int,
    renderer_constants: dict[str, Any],
    *,
    out_w: int = OUTPUT_W,
    out_h: int = OUTPUT_H,
    anchor_mode: str = "eye_center",
) -> SpatialCalibration:
    """从客户标点（左眼、右眼、鼻尖）求 scale + 仿射矩阵。

    模型侧：品种标准底膜 constants（1024 坐标，金标准不改）
    照片侧：客户锚点映射到输出画布 out_w×out_h

    Args:
        anchor_mode: "eye_center"（默认）| "outer_canthus"
            外眼角模式时 model anchors 使用外眼角而非眼中心。
    """
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) 未安装")

    le = _anchor_pt(anchors, "left_eye")
    re = _anchor_pt(anchors, "right_eye")
    nose = _anchor_pt(anchors, "nose")

    eye_dist_photo = math.hypot(re[0] - le[0], re[1] - le[1])
    if eye_dist_photo < 5:
        raise ValueError("左右眼距离过小，请重新标点")

    nose_ratio = nose_eye_ratio_from_anchors(anchors)
    src = standard_model_anchors(
        renderer_constants, anchor_mode=anchor_mode, nose_eye_ratio=nose_ratio,
    )
    eye_dist_model = float(np.linalg.norm(src[1] - src[0]))
    scale = eye_dist_photo / max(eye_dist_model, 1e-6)

    dst = np.float32([
        _map_photo_to_output(le[0], le[1], img_width, img_height, out_w, out_h),
        _map_photo_to_output(re[0], re[1], img_width, img_height, out_w, out_h),
        _map_photo_to_output(nose[0], nose[1], img_width, img_height, out_w, out_h),
    ])
    photo_src = np.float32([[le[0], le[1]], [re[0], re[1]], [nose[0], nose[1]]])
    M = cv2.getAffineTransform(src, dst)
    M_photo = cv2.getAffineTransform(photo_src, dst)

    def _pt_dict(p: tuple[float, float]) -> list[float]:
        return [round(p[0], 2), round(p[1], 2)]

    def _arr_dict(row: np.ndarray) -> list[float]:
        return [round(float(row[0]), 2), round(float(row[1]), 2)]

    return SpatialCalibration(
        scale=round(scale, 4),
        affine_matrix=M.tolist(),
        photo_affine_matrix=M_photo.tolist(),
        nose_eye_ratio=round(nose_ratio, 4),
        model_anchors={
            "left_eye": _arr_dict(src[0]),
            "right_eye": _arr_dict(src[1]),
            "nose": _arr_dict(src[2]),
        },
        photo_anchors={
            "left_eye": _pt_dict(le),
            "right_eye": _pt_dict(re),
            "nose": _pt_dict(nose),
        },
        output_anchors={
            "left_eye": _arr_dict(dst[0]),
            "right_eye": _arr_dict(dst[1]),
            "nose": _arr_dict(dst[2]),
        },
        image_size=[int(img_width), int(img_height)],
        output_size=[out_w, out_h],
    )


def load_project_spatial_calibration(
    customer_id: str,
    project_id: str,
) -> SpatialCalibration | None:
    """[DEPRECATED] 不再落盘，始终返回 None。保留用于外部兼容。"""
    if not customer_id or not project_id:
        return None
    path = project_dir(customer_id, project_id) / "手动标定.json"
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    block = doc.get("spatial_calibration")
    if isinstance(block, dict):
        return SpatialCalibration.from_dict(block)
    return None
