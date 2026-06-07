"""渲染辅助函数 — 底膜/对齐/叠加预览 + OpenCV 视频合成，仅供 portal handler 内部调用。"""
from __future__ import annotations

import base64, json
from pathlib import Path
from typing import Any

# ── 常量（同 serve_workbench.py，为避免循环导入直接复制）──
_SPECIES_LABELS = {"human": "🙂 人"}
_MEMBRANE_LABELS = {"human": "人类工程底膜"}
_RENDERER_NAMES = {"human": "AffineRenderer"}


def _resolve_breed_id(customer_id: str, species: str = "human", fallback: str = "") -> str:
    """解析客户品种 ID（人类始终返回空字符串）。"""
    return ""


def _run_live_calibration(
    customer_id: str,
    project_id: str,
    *,
    anchor_mode: str = "eye_center",
    species: str | None = None,
) -> dict | None:
    """实时 MediaPipe 检测 + 全链路标定（不读写任何文件）。

    从项目已上传的照片 + DB 模板参数重新运行完整标定管线。
    返回 calib_doc 结构（同旧 手动标定.json），失败返回 None。
    """
    from asset_lib import project_dir, customer_ref_photos_dir
    from gaze_engine._shared.customer_db import (
        get_project, get_template_params, get_customer,
    )
    from gaze_engine.render.geometry_adapter import adapt_geometry
    from gaze_engine.render.geometry_adapter import apply_render_baseline
    from gaze_engine.render.species_template import (
        species_default_template,
        apply_customer_adjustments,
        sanitize_human_spatial_adjustments,
        template_for_spatial_render,
        template_to_renderer_constants,
    )
    from gaze_engine.render.spatial_calibration import compute_spatial_calibration

    proj = get_project(customer_id, project_id)
    if proj is None:
        return None

    sp = (species or proj.get("species") or "human").strip().lower()
    photo_name = proj.get("reference_photo")
    if not photo_name:
        return None

    photo_path = customer_ref_photos_dir(customer_id) / photo_name
    if not photo_path.is_file():
        return None

    import cv2
    im = cv2.imread(str(photo_path))
    if im is None:
        return None
    img_h, img_w = im.shape[:2]

    breed = ""
    geo = adapt_geometry(
        species=sp,
        breed_id=breed,
        img_width=img_w,
        img_height=img_h,
        photo_path=photo_path,
    )
    if geo.method == "failed":
        return None

    resolved_anchors = geo.anchors
    customer_adj: dict[str, float] = sanitize_human_spatial_adjustments(geo.adjustments)

    _base_tpl = species_default_template(sp)
    _adj_tpl = apply_customer_adjustments(_base_tpl, customer_adj)
    _spatial_tpl = template_for_spatial_render(_adj_tpl, sp, breed_id=None)
    _constants = apply_render_baseline(
        template_to_renderer_constants(sp, _spatial_tpl, breed_id=None),
        geo.render_baseline,
    )

    try:
        spatial_cal = compute_spatial_calibration(
            resolved_anchors, img_w, img_h, _constants,
            anchor_mode=anchor_mode,
        )
    except Exception:
        return None
    spatial_cal_dict = spatial_cal.to_dict()
    if not spatial_cal_dict.get("affine_matrix"):
        return None
    if not geo.render_baseline:
        return None

    return {
        "schema": "mediapipe_calibration_v1",
        "method": geo.method,
        "confidence": geo.confidence,
        "customer_id": customer_id,
        "project_id": project_id,
        "species": sp,
        "photo_name": photo_name,
        "image_size": [img_w, img_h],
        "anchors": resolved_anchors,
        "breed": breed,
        "breed_label": breed or "",
        "adjustments": customer_adj,
        "geometry_adapter": geo.to_dict(),
        "spatial_calibration": spatial_cal_dict,
        "render_baseline": dict(geo.render_baseline or {}),
    }


def _diagnostics_from_calib_doc(calib: dict) -> dict[str, Any] | None:
    """从已存标定文件还原诊断（人类无诊断，始终返回 None）。"""
    return None


def _spatial_cal_from_calib_doc(calib: dict) -> Any:
    """从校准 dict 还原 SpatialCalibration（无则 None）。"""
    from gaze_engine.render.spatial_calibration import SpatialCalibration
    block = calib.get("spatial_calibration")
    if isinstance(block, dict) and block.get("affine_matrix"):
        return SpatialCalibration.from_dict(block)
    return None


def _render_baseline_from_calib_doc(calib: dict) -> dict:
    """从校准 dict 还原人类渲染基线（瞳孔静息、眉位）。"""
    block = calib.get("render_baseline")
    if isinstance(block, dict):
        return dict(block)
    geo = calib.get("geometry_adapter") or {}
    nested = geo.get("render_baseline")
    if isinstance(nested, dict):
        return dict(nested)
    return {}


def _human_renderer_constants(
    *,
    customer_id: str = "",
    template=None,
    spatial_calibration=None,
    render_baseline: dict | None = None,
    calib: dict | None = None,
) -> dict:
    """合成人类渲染常量：模板形状 + 标定基线。"""
    from gaze_engine._shared.customer_db import get_effective_template
    from gaze_engine.render.geometry_adapter import apply_render_baseline
    from gaze_engine.render.species_template import (
        SpeciesTemplate,
        species_default_template,
        template_for_spatial_render,
        template_to_renderer_constants,
    )

    if template is None:
        template = get_effective_template(customer_id) if customer_id else None
    elif isinstance(template, dict):
        template = SpeciesTemplate.from_dict(template)
    if template is None:
        template = species_default_template("human")
    if spatial_calibration is not None:
        template = template_for_spatial_render(template, "human", breed_id=None)
    constants = template_to_renderer_constants("human", template, breed_id=None)
    baseline = render_baseline
    if baseline is None and calib:
        baseline = _render_baseline_from_calib_doc(calib)
    return apply_render_baseline(constants, baseline)


def _membrane_renderer(
    species: str = "human",
    customer_id: str = "",
    template=None,
    breed_id: str = "",
    spatial_calibration=None,
    render_baseline: dict | None = None,
    calib: dict | None = None,
):
    """构造 OpenCV 线条渲染器（仅人类）。"""
    from gaze_engine.render.affine_renderer import AffineRenderer

    constants = _human_renderer_constants(
        customer_id=customer_id,
        template=template,
        spatial_calibration=spatial_calibration,
        render_baseline=render_baseline,
        calib=calib,
    )
    return AffineRenderer(constants, spatial_calibration=spatial_calibration)


def _neutral_channel_frame(species: str) -> dict[str, float]:
    """静态底膜预览用的中性通道值（展示模板几何，无表情动画）。"""
    return {k: 0.0 for k in _species_channel_keys(species)}


def _write_membrane_preview_png(
    species: str,
    path: Path,
    *,
    customer_id: str = "",
    template=None,
    breed_id: str = "",
    spatial_calibration=None,
    photo_path: str | Path | None = None,
) -> None:
    """渲染单帧 OpenCV 线条图。"""
    import cv2

    sp = (species or "human").strip().lower()
    renderer = _membrane_renderer(
        sp, customer_id, template=template, breed_id=breed_id,
        spatial_calibration=spatial_calibration,
    )
    neutral = _neutral_channel_frame(sp)
    frame_fn = getattr(renderer, "render_preview_frame", None)
    if callable(frame_fn):
        frame = frame_fn(neutral)
    else:
        frame = renderer.render_frame(neutral)

    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), frame):
        raise RuntimeError(f"无法写入底膜预览: {path}")


def _project_model_to_output(spatial_cal, x: float, y: float) -> tuple[int, int]:
    """1024 模型坐标 → 690×361 输出坐标。"""
    import numpy as np

    M = spatial_cal.matrix_np()
    pt = M @ np.float32([x, y, 1.0])
    return int(round(float(pt[0]))), int(round(float(pt[1])))


def _model_radius_to_output(spatial_cal, cx: float, cy: float, radius: float) -> int:
    """模型空间半径 → 输出画布像素半径。"""
    import math
    import numpy as np

    M = spatial_cal.matrix_np()
    scale = math.sqrt(float(M[0, 0]) ** 2 + float(M[0, 1]) ** 2)
    return max(1, int(round(radius * scale)))


def _draw_output_anchors_on_preview(
    canvas_bgr,
    spatial_cal,
    *,
    show: bool = True,
):
    """在 overlay 画布上绘制三点锚点标记（左眼青、右眼品红、鼻尖黄）。"""
    import cv2

    if not show or spatial_cal is None:
        return canvas_bgr
    out = canvas_bgr.copy()
    anchors = spatial_cal.output_anchors or {}
    specs = (
        ("left_eye", (255, 255, 0), "L-eye"),   # 青 — 眼角中点
        ("right_eye", (255, 0, 255), "R-eye"),  # 品红
        ("nose", (0, 255, 255), "nose"),        # 黄
    )
    pts: dict[str, tuple[int, int]] = {}
    for key, color, label in specs:
        p = anchors.get(key)
        if not p or len(p) < 2:
            continue
        x, y = int(round(p[0])), int(round(p[1]))
        pts[key] = (x, y)
        cv2.circle(out, (x, y), 7, color, 2, cv2.LINE_AA)
        cv2.line(out, (x - 10, y), (x + 10, y), color, 1, cv2.LINE_AA)
        cv2.line(out, (x, y - 10), (x, y + 10), color, 1, cv2.LINE_AA)
        cv2.putText(out, label, (x + 9, y - 9),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

    le, re, nose = pts.get("left_eye"), pts.get("right_eye"), pts.get("nose")
    if le and re:
        cv2.line(out, le, re, (80, 80, 255), 1, cv2.LINE_AA)
    if le and re and nose:
        mid = ((le[0] + re[0]) // 2, (le[1] + re[1]) // 2)
        cv2.line(out, mid, nose, (255, 180, 80), 1, cv2.LINE_AA)
    return out


def _alignment_renderer_from_calib(calib: dict, photo_bgr) -> dict | None:
    """从 calib doc 构造对齐诊断所需的 renderer / spatial_cal / constants。"""
    import cv2
    from asset_lib import customer_ref_photos_dir
    from gaze_engine.render.geometry_adapter import apply_render_baseline
    from gaze_engine.render.species_template import (
        species_default_template,
        apply_customer_adjustments,
        sanitize_human_spatial_adjustments,
        template_for_spatial_render,
        template_to_renderer_constants,
    )
    from gaze_engine.render.affine_renderer import AffineRenderer

    photo_name = calib.get("photo_name", "")
    if not photo_name:
        return None
    if photo_bgr is None:
        photo_fp = customer_ref_photos_dir(calib.get("customer_id", "")) / photo_name
        if not photo_fp.is_file():
            return None
        photo_bgr = cv2.imread(str(photo_fp))
        if photo_bgr is None:
            return None

    species = (calib.get("species") or "human").strip().lower()
    spatial_cal_obj = _spatial_cal_from_calib_doc(calib)
    if spatial_cal_obj is None:
        return None

    adjustments = calib.get("adjustments") or {}
    shape_adj = sanitize_human_spatial_adjustments(adjustments)
    base = species_default_template(species)
    adj = apply_customer_adjustments(base, shape_adj)
    spatial_tpl = template_for_spatial_render(adj, species, breed_id=None)
    raw_constants = template_to_renderer_constants(species, spatial_tpl, breed_id=None)
    constants = apply_render_baseline(raw_constants, _render_baseline_from_calib_doc(calib))
    renderer = AffineRenderer(constants, spatial_calibration=spatial_cal_obj)

    img_h, img_w = photo_bgr.shape[:2]
    try:
        photo_aligned = spatial_cal_obj.warp_photo(photo_bgr)
    except Exception:
        return None

    return {
        "photo_bgr": photo_bgr,
        "photo_aligned": photo_aligned,
        "img_w": img_w,
        "img_h": img_h,
        "spatial_cal": spatial_cal_obj,
        "constants": constants,
        "renderer": renderer,
    }


def _build_alignment_verify_bundle(
    *,
    customer_id: str,
    project_id: str,
    calib: dict | None = None,
) -> dict | None:
    """生成与 diagnose_mapping_pipeline Step 4b 一致的对齐诊断图包。"""
    import sys
    from pathlib import Path

    _root = Path(__file__).resolve().parents[2]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    from diagnose_mapping_pipeline import (
        _mp_landmarks_from_photo,
        _extract_mp_eye_features,
        _extract_cv_eye_features,
        _build_compare_outputs,
    )
    from gaze_engine.render.affine_renderer import CANONICAL_KEYS

    if calib is None:
        calib = _run_live_calibration(customer_id, project_id)
    if calib is None:
        return None
    calib = dict(calib)
    calib.setdefault("customer_id", customer_id)

    ctx = _alignment_renderer_from_calib(calib, photo_bgr=None)
    if ctx is None:
        return None

    lm = _mp_landmarks_from_photo(ctx["photo_bgr"])
    neutral = {k: 0.0 for k in CANONICAL_KEYS}
    mp_left = _extract_mp_eye_features(lm, ctx["img_w"], ctx["img_h"], "left")
    mp_right = _extract_mp_eye_features(lm, ctx["img_w"], ctx["img_h"], "right")
    cv_left = _extract_cv_eye_features(ctx["renderer"], ctx["constants"], neutral, "left")
    cv_right = _extract_cv_eye_features(ctx["renderer"], ctx["constants"], neutral, "right")

    compare_images, errors = _build_compare_outputs(
        ctx["photo_aligned"],
        mp_left=mp_left,
        mp_right=mp_right,
        cv_left=cv_left,
        cv_right=cv_right,
        cal=ctx["spatial_cal"],
        img_w=ctx["img_w"],
        img_h=ctx["img_h"],
    )

    return {
        "errors": errors,
        "images": {
            "grid": compare_images["10_compare_grid.png"],
            "layers_left": compare_images["10c_layers_left.png"],
            "layers_right": compare_images["10d_layers_right.png"],
        },
    }


def _draw_iris_pupil_labels(
    canvas_bgr: np.ndarray,
    constants: dict,
    spatial_cal,
) -> None:
    """在 overlay 画布上绘制虹膜/瞳孔区分标注（直接修改 canvas_bgr）。"""
    import cv2

    if spatial_cal is None:
        return

    model_iris_r = float(constants.get("IRIS_R_BASE", 30))
    model_pupil_r = float(constants.get("PUPIL_R_BASE", 12))
    eye_specs = (
        ("L", "LEFT_CX", "LEFT_CY", "PUPIL_REST_LEFT"),
        ("R", "RIGHT_CX", "RIGHT_CY", "PUPIL_REST_RIGHT"),
    )

    for side_tag, cx_k, cy_k, rest_k in eye_specs:
        if cx_k not in constants or cy_k not in constants:
            continue
        mcx = float(constants[cx_k])
        mcy = float(constants[cy_k])
        rest = constants.get(rest_k) or (0, 0)
        px = mcx + float(rest[0])
        py = mcy + float(rest[1])
        cx, cy = _project_model_to_output(spatial_cal, px, py)
        iris_r = _model_radius_to_output(spatial_cal, px, py, model_iris_r)
        pupil_r = _model_radius_to_output(spatial_cal, px, py, model_pupil_r)

        cv2.circle(canvas_bgr, (cx, cy), iris_r, (0, 180, 255), 1, cv2.LINE_AA)
        cv2.circle(canvas_bgr, (cx, cy), pupil_r, (255, 255, 0), 1, cv2.LINE_AA)
        cv2.putText(canvas_bgr, f"{side_tag}-iris",
                    (cx - iris_r, cy - iris_r - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 180, 255), 1, cv2.LINE_AA)
        cv2.putText(canvas_bgr, f"{side_tag}-pupil",
                    (cx + pupil_r + 4, cy + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 0), 1, cv2.LINE_AA)


def _build_overlay_preview(
    *,
    customer_id: str,
    project_id: str,
    show_eyelid: bool = True,
    show_eyebrow: bool = True,
    show_pupil: bool = True,
    show_anchors: bool = True,
    opacity: float = 0.6,
    calib: dict | None = None,
) -> bytes | None:
    """构建底膜线条叠加到参考照片的合成图（实时 MediaPipe，不读文件）。"""
    import cv2
    import numpy as np
    from asset_lib import customer_ref_photos_dir

    if calib is None:
        calib = _run_live_calibration(customer_id, project_id)
    if calib is None:
        return None

    photo_name = calib.get("photo_name", "")
    if not photo_name:
        return None
    photo_fp = customer_ref_photos_dir(customer_id) / photo_name
    if not photo_fp.is_file():
        return None
    photo_bgr = cv2.imread(str(photo_fp))
    if photo_bgr is None:
        return None

    species = (calib.get("species") or "human").strip().lower()
    adjustments = calib.get("adjustments") or {}
    from gaze_engine.render.species_template import (
        species_default_template,
        apply_customer_adjustments,
        sanitize_human_spatial_adjustments,
        template_for_spatial_render,
        template_to_renderer_constants,
    )
    from gaze_engine.render.affine_renderer import AffineRenderer, OUTPUT_W, OUTPUT_H, CANONICAL_KEYS
    from gaze_engine.render.geometry_adapter import apply_render_baseline

    spatial_cal_obj = _spatial_cal_from_calib_doc(calib)
    shape_adj = sanitize_human_spatial_adjustments(adjustments)
    base = species_default_template(species)
    adj = apply_customer_adjustments(base, shape_adj)
    _spatial_tpl = template_for_spatial_render(adj, species, breed_id=None)
    _raw_constants = template_to_renderer_constants(species, _spatial_tpl, breed_id=None)
    constants = apply_render_baseline(_raw_constants, _render_baseline_from_calib_doc(calib))
    renderer = AffineRenderer(constants, spatial_calibration=spatial_cal_obj)

    neutral = {k: 0.0 for k in CANONICAL_KEYS}
    membrane_bgr = renderer.render_frame(neutral)

    ph, pw = photo_bgr.shape[:2]
    canvas = None
    affine_from_calib = (calib.get("spatial_calibration") or {}).get("affine_matrix")
    if (
        spatial_cal_obj is not None
        and affine_from_calib
        and len(affine_from_calib) == 2
        and len(affine_from_calib[0]) == 3
    ):
        try:
            canvas = spatial_cal_obj.warp_photo(photo_bgr)
        except Exception:
            canvas = None
    if canvas is None:
        scale = min(OUTPUT_W / pw, OUTPUT_H / ph)
        nw = int(pw * scale)
        nh = int(ph * scale)
        photo_resized = cv2.resize(photo_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((OUTPUT_H, OUTPUT_W, 3), dtype=np.uint8)
        x_off = (OUTPUT_W - nw) // 2
        y_off = (OUTPUT_H - nh) // 2
        canvas[y_off:y_off+nh, x_off:x_off+nw] = photo_resized

    opacity = max(0.0, min(1.0, opacity))
    result = canvas.copy()

    if show_eyelid:
        eyelid_layer = np.zeros_like(membrane_bgr, dtype=np.uint8)
        eyelid_layer[membrane_bgr[:, :, 2] > 0] = (0, 0, 255)
        result = cv2.addWeighted(result, 1.0, eyelid_layer, opacity * 0.35, 0)

    if show_eyebrow:
        brow_layer = np.zeros_like(membrane_bgr, dtype=np.uint8)
        brow_layer[membrane_bgr[:, :, 1] > 0] = (0, 255, 0)
        result = cv2.addWeighted(result, 1.0, brow_layer, opacity, 0)

    if show_pupil:
        pupil_layer = np.zeros_like(membrane_bgr, dtype=np.uint8)
        pupil_layer[membrane_bgr[:, :, 0] > 0] = (255, 0, 0)
        result = cv2.addWeighted(result, 1.0, pupil_layer, opacity, 0)

    if show_pupil and spatial_cal_obj is not None:
        _draw_iris_pupil_labels(result, constants, spatial_cal_obj)

    result = _draw_output_anchors_on_preview(result, spatial_cal_obj, show=show_anchors)

    _, buf = cv2.imencode(".png", result)
    return buf.tobytes()


def _species_channel_keys(species: str) -> list[str]:
    from gaze_engine.render.affine_renderer import CANONICAL_KEYS
    return list(CANONICAL_KEYS)


def _channels_from_baked(baked: dict, keys: list[str]) -> dict[str, list[float]]:
    """从 02_烘焙.json 的 channel_tracks 提取稠密通道（渲染真源）。"""
    tracks = baked.get("channel_tracks") or {}
    if not tracks:
        raise ValueError("baked 缺少 channel_tracks，请重新生成管线")
    out: dict[str, list[float]] = {}
    fc = 0
    for key in keys:
        kfs = tracks.get(key, {}).get("keyframes") or []
        if kfs:
            out[key] = [float(k["v"]) for k in kfs]
            fc = max(fc, len(out[key]))
    if fc <= 0:
        raise ValueError("channel_tracks 为空，无法渲染底膜视频")
    for key in keys:
        if key not in out:
            out[key] = [0.0] * fc
        elif len(out[key]) < fc:
            pad = out[key][-1] if out[key] else 0.0
            out[key] = out[key] + [pad] * (fc - len(out[key]))
    return out


_RENDERER_NAMES = {"human": "AffineRenderer"}


def render_opencv_video(
    *,
    packet_dict: dict | None = None,
    baked: dict | None = None,
    species: str = "human",
    customer_id: str = "",
    project_id: str = "",
    breed_id: str = "",
    spatial_calibration=None,
    control_video_dir: Path | None = None,
) -> tuple[Path, int, dict]:
    """从 baked 的 channel_tracks 渲染 OpenCV 工程底膜 MP4（仅人类）。

    control_video_dir: 临时缓存目录，来自 serve_workbench 的 CONTROL_VIDEO_DIR。
    """
    import cv2
    import shutil
    import subprocess
    from gaze_engine.input.slider_schema import SliderPacket
    from gaze_engine.delivery.delivery_pipeline import run_species_delivery
    from gaze_engine.render.affine_renderer import AffineRenderer

    sp = (baked or {}).get("species") or species or "human"
    keys = _species_channel_keys(sp)

    if baked and baked.get("channel_tracks"):
        channels = _channels_from_baked(baked, keys)
    elif packet_dict:
        _, channels, _, _ = run_species_delivery(SliderPacket.from_dict(packet_dict), sp)
    elif baked and baked.get("slider_packet"):
        _, channels, _, _ = run_species_delivery(
            SliderPacket.from_dict(baked["slider_packet"]), sp
        )
    else:
        raise ValueError("需要 baked（含 channel_tracks）或 packet")

    fc = len(next(iter(channels.values())))

    calib = None
    spatial_cal_obj = spatial_calibration
    if customer_id and project_id:
        calib = _run_live_calibration(customer_id, project_id)
        if spatial_cal_obj is None and calib:
            spatial_cal_obj = _spatial_cal_from_calib_doc(calib)

    constants = _human_renderer_constants(
        customer_id=customer_id,
        spatial_calibration=spatial_cal_obj,
        calib=calib,
    )
    renderer = AffineRenderer(constants, spatial_calibration=spatial_cal_obj)

    render_info = {
        "species": sp,
        "membrane_type": _MEMBRANE_LABELS.get(sp, sp),
        "renderer": _RENDERER_NAMES.get(sp, "AffineRenderer"),
        "frame_count": fc,
        "channel_source": "baked.channel_tracks" if baked and baked.get("channel_tracks") else "species_delivery",
        "baked_revision": (baked or {}).get("revision", ""),
        "baked_mood": (baked or {}).get("mood", ""),
        "spatial_calibration": bool(spatial_cal_obj is not None),
        "render_baseline": bool(_render_baseline_from_calib_doc(calib or {})),
    }

    vid_dir = control_video_dir or Path("/tmp/_portal_video_cache")
    vid_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = vid_dir / "_portal_frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    first_frame_png: Path | None = None
    for t in range(fc):
        fd = {k: channels[k][t] for k in keys if k in channels}
        img = renderer.render_frame(fd)
        cv2.imwrite(str(frames_dir / f"f_{t:04d}.png"), img)
        if t == 0:
            first_frame_png = frames_dir / "f_0000.png"

    out_path = vid_dir / "control_video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "image2", "-r", "30",
        "-i", str(frames_dir / "f_%04d.png"),
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        str(out_path),
    ], capture_output=True, check=True)
    preview_snap = vid_dir / "_portal_first_frame.png"
    if first_frame_png and first_frame_png.is_file():
        shutil.copy2(first_frame_png, preview_snap)
        render_info["first_frame_preview"] = str(preview_snap)
    shutil.rmtree(frames_dir)
    return out_path, fc, render_info


# ── 管线诊断工具（portal + customer 共用）────────────────────────────────────

def _detect_baked_pipeline(baked: dict | None) -> str:
    """返回 baked 实际走的管线：human / human_legacy / none"""
    if not baked:
        return "none"
    schema = str(baked.get("schema_version") or "")
    sp = (baked.get("species") or "").strip().lower()
    if sp == "human":
        return "human"
    if "human-prior" in schema or baked.get("_compile_mode") == "envelope-v1":
        return "human_legacy"
    return "unknown"


def _analyze_membrane_status(
    project_species: str,
    baked: dict | None,
    membrane_meta: dict | None,
    *,
    video_exists: bool = False,
) -> dict:
    """判断项目底膜是否与物种一致，供门户醒目标识。"""
    sp = (project_species or "human").strip().lower()
    baked_pipe = _detect_baked_pipeline(baked)
    video_sp = (membrane_meta or {}).get("species") or ""
    video_type = (membrane_meta or {}).get("membrane_type") or ""
    video_renderer = (membrane_meta or {}).get("renderer") or ""

    status = "unknown"
    warning = ""
    action = ""
    is_valid = False

    if baked_pipe in ("human", "human_legacy") or baked_pipe == "none":
        status, is_valid = "ok", baked_pipe != "none"
    else:
        status, is_valid = "ok", True

    return {
        "project_species": sp,
        "project_species_label": _SPECIES_LABELS.get(sp, sp),
        "expected_membrane": _MEMBRANE_LABELS.get(sp, sp),
        "baked_pipeline": baked_pipe,
        "baked_pipeline_label": {
            "human": "人类管线",
            "human_legacy": "⚠ 人类旧管线", "none": "未生成", "unknown": "未知",
        }.get(baked_pipe, baked_pipe),
        "video_species": video_sp,
        "video_membrane_type": video_type or (_MEMBRANE_LABELS.get(video_sp, "") if video_sp else ""),
        "video_renderer": video_renderer,
        "status": status,
        "is_valid": is_valid,
        "warning": warning,
        "action": action,
    }
