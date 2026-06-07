"""门户创作 API — 预设 / Pomot / 标定 / 底膜 / 导出 / 归档。"""
from __future__ import annotations

import json, base64
from datetime import datetime
from pathlib import Path

from serve_workbench import Route, Handler

# ── 常量 ─────────────────────────────────────────────────────
_DIFFUSION_VIDEO_NAME = "03_工程底模.mp4"
_DIFFUSION_PROMPT_NAME = "04_Prompt.txt"


# ── 内部辅助 ─────────────────────────────────────────────────

def _load_project_slider_packet(customer_id: str, project_id: str) -> dict | None:
    """从客户项目输出读取 01_滑杆包（管线产物，非预设资产库）。"""
    from asset_lib import project_output_dir

    path = project_output_dir(customer_id, project_id) / "01_滑杆包.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _resolve_slider_packet(data: dict) -> dict | None:
    """解析 SliderPacket：优先管线产物，否则从 预设资产/情绪包 加载。"""
    from asset_lib import load_emotion_slider_packet

    packet = data.get("packet")
    if isinstance(packet, dict) and packet.get("macro"):
        return packet
    baked = data.get("baked") or {}
    sp = baked.get("slider_packet")
    if isinstance(sp, dict) and sp.get("macro"):
        return sp
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    if cid and pid:
        proj_pkt = _load_project_slider_packet(cid, pid)
        if isinstance(proj_pkt, dict) and proj_pkt.get("macro"):
            return proj_pkt
    species = (data.get("species") or "human").strip().lower()
    emotion = (data.get("emotion") or data.get("active_emotion") or "").strip()
    if emotion:
        pkt = load_emotion_slider_packet(species, emotion)
        if pkt:
            return pkt.to_dict()
    return None


def _portal_compile_baked(data: dict) -> dict:
    """门户即时编译 02（内存用，默认不写盘）。"""
    from gaze_engine.input.slider_schema import SliderPacket
    from gaze_engine.delivery.delivery_pipeline import run_species_delivery
    from serve_render import _resolve_breed_id

    packet_dict = _resolve_slider_packet(data)
    if not packet_dict:
        raise ValueError("无法编译：请先点选情绪或提供 packet")
    species = (data.get("species") or packet_dict.get("species") or "human").strip().lower()
    breed = (data.get("breed") or data.get("active_style") or "").strip()
    cid = (data.get("customer_id") or "").strip()
    if not breed and cid:
        breed = _resolve_breed_id(cid, species)
    packet = SliderPacket.from_dict({**packet_dict, "species": species})
    action = (data.get("action") or "").strip()
    baked, _, _, _ = run_species_delivery(
        packet,
        species,
        breed_id=breed or "",
        style_id=breed or "",
        narrative_action=action,
    )
    baked["species"] = species
    if breed:
        baked["breed"] = breed
    return baked


def _portal_purge_baked_files(out_dir) -> list[str]:
    from asset_lib import remove_baked_json_files
    return remove_baked_json_files(out_dir)


# ── 预设 / 情绪 ─────────────────────────────────────────────

@Route.get("/api/portal/presets")
def portal_presets(self: Handler):
    """返回预设索引（仅 id/label/路径）；数值从 预设资产/ 按需调取，不下发 macro/pad。"""
    from asset_lib import ASSET_LIB, EMOTION_PACK_DIR, load_emotion_categories

    style_kind = {"human": "人格风格"}
    result = {"human": {"emotions": [], "styles": [], "emotion_groups": [], "emotion_categories": []}}

    emotions_dir = EMOTION_PACK_DIR
    styles_dir = ASSET_LIB / "风格包"
    for species in ("human",):
        result[species]["emotion_categories"] = load_emotion_categories(species)
        groups_f = emotions_dir / "_groups.json"
        if groups_f.is_file():
            try:
                result[species]["emotion_groups"] = json.loads(
                    groups_f.read_text(encoding="utf-8")
                )
            except Exception:
                pass
        from asset_lib import _iter_emotion_json_files, _iter_shared_variant_files

        for preset_id, f in _iter_emotion_json_files(emotions_dir):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                rel = f.relative_to(emotions_dir).as_posix()
                result[species]["emotions"].append({
                    "id": preset_id,
                    "label": d.get("label") or d.get("emotion") or f.stem,
                    "emotion_id": d.get("emotion") or preset_id,
                    "category": d.get("category") or "",
                    "variant": d.get("variant") or "",
                    "aliases": d.get("aliases") or [],
                    "file": f"预设资产/情绪包/{rel}",
                    "note": d.get("note") or "",
                })
            except Exception:
                pass
        for preset_id, f in _iter_shared_variant_files():
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                rel = f.relative_to(EMOTION_PACK_DIR).as_posix()
                result[species]["emotions"].append({
                    "id": preset_id,
                    "label": d.get("label") or d.get("emotion") or f.stem,
                    "emotion_id": d.get("emotion") or preset_id,
                    "category": d.get("category") or "",
                    "variant": d.get("variant") or "",
                    "aliases": d.get("aliases") or [],
                    "file": f"预设资产/情绪包/{rel}",
                    "note": d.get("note") or "",
                    "shared": True,
                })
            except Exception:
                pass

    for species in ("human",):
        if styles_dir.is_dir():
            for entry in sorted(styles_dir.iterdir()):
                if entry.is_dir():
                    sf = entry / "style.json"
                    if sf.exists():
                        try:
                            d = json.loads(sf.read_text(encoding="utf-8"))
                            result[species]["styles"].append({
                                "id": d.get("id", entry.name),
                                "label": d.get("label", entry.name),
                                "notes": d.get("notes", ""),
                                "folder": entry.name,
                                "file": f"预设资产/风格包/{entry.name}/style.json",
                            })
                        except Exception:
                            pass

        result[species]["meta"] = {
            "emotions_dir": "预设资产/情绪包/",
            "styles_dir": "预设资产/风格包/",
            "style_kind": style_kind[species],
            "emotion_count": len(result[species]["emotions"]),
            "style_count": len(result[species]["styles"]),
            "asset_source": "预设资产库",
        }

    self._json({"ok": True, "presets": result})


@Route.get("/api/portal/preset/emotion-preview")
def portal_preset_emotion_preview(self: Handler):
    """按需从 情绪包 读取 macro/hold（供门户 E(t) 示意图，不缓存 preset 数值）。"""
    from urllib.parse import parse_qs, urlparse
    from asset_lib import load_emotion_preset_raw

    qs = parse_qs(urlparse(self.path).query)
    species = (qs.get("species") or ["human"])[0].strip().lower()
    preset_id = (qs.get("id") or [""])[0].strip()
    if species != "human" or not preset_id:
        return self._json({"ok": False, "error": "缺少 species 或 id"}, status=400)

    raw = load_emotion_preset_raw(species, preset_id)
    if not raw:
        return self._json({"ok": False, "error": f"未找到情绪: {preset_id}"}, status=404)

    self._json({
        "ok": True,
        "species": species,
        "id": preset_id,
        "label": raw.get("label") or preset_id,
        "emotion_id": raw.get("emotion") or preset_id,
        "file": f"预设资产/情绪包/{species}/{preset_id}.json",
        "macro": raw.get("macro") or {},
        "hold_seg": raw.get("hold_seg") or {},
    })


# ── Pomot ───────────────────────────────────────────────────

@Route.post("/api/portal/pomot/round1")
def portal_pomot_round1(self: Handler, body: bytes):
    """Pomot 第一轮：按钮 emotion → 路由 → 合成 → 管线 → 拼装（NL 可选，门户当前纯按钮）。"""
    from gaze_engine.delivery.pomot.pipeline import PomotPipeline
    data = self._read_body(body)
    nl = (data.get("nl") or "").strip()
    species = (data.get("species") or "").strip()
    emotion = (data.get("emotion") or "").strip()
    breed = (data.get("breed") or "").strip()
    if not nl and not emotion:
        return self._json({"ok": False, "error": "缺少 emotion（请先在第②步点选情绪）"}, status=400)
    pipeline = PomotPipeline()
    result = pipeline.round1(
        nl,
        species_override=species,
        emotion_override=emotion,
        breed_override=breed,
        run_pipeline=True,
    )
    split = result["split"]
    route = result["route"]
    from gaze_engine.delivery.pomot.assembler import DiffusionPromptAssembler

    wan_clip = DiffusionPromptAssembler.split_for_wan(result.get("prompt_04") or "")
    self._json({
        "ok": True,
        "split": {
            "action": split.action,
            "emotion": split.emotion,
            "species_hint": split.species_hint,
            "breed_hint": split.breed_hint,
            "raw_text": split.raw_text,
            "is_modify": split.is_modify,
        },
        "route": {
            "species": route.species,
            "preset_name": route.preset_name,
            "breed": route.breed,
            "confidence": route.confidence,
        },
        "packet_dict": result["packet"].to_dict(),
        "baked_json": result["baked_json"],
        "beat_text": result["beat_text"],
        "prompt_04": result["prompt_04"],
        "wan_positive_clip": wan_clip["positive"],
        "wan_negative_clip": wan_clip["negative"],
        "payload": result["payload"],
    })


@Route.post("/api/portal/pomot/round2")
def portal_pomot_round2(self: Handler, body: bytes):
    """Pomot 第二轮：微调 delta → 重新管线 → 重新拼装。"""
    from gaze_engine.input.slider_schema import SliderPacket
    from gaze_engine.delivery.pomot.pipeline import PomotPipeline
    data = self._read_body(body)
    nl = (data.get("nl") or "").strip()
    packet_dict = data.get("previous_packet")
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    previous_baked = data.get("previous_baked")
    if not packet_dict and isinstance(previous_baked, dict):
        packet_dict = previous_baked.get("slider_packet")
    if not packet_dict and cid and pid:
        packet_dict = _load_project_slider_packet(cid, pid)
    if not packet_dict:
        packet_dict = _resolve_slider_packet(data)
    if not nl:
        return self._json({"ok": False, "error": "缺少 nl"}, status=400)
    if not packet_dict:
        return self._json({"ok": False, "error": "缺少 previous_packet（请先完成第一轮生成）"}, status=400)
    previous_packet = SliderPacket.from_dict(packet_dict)
    pipeline = PomotPipeline()
    result = pipeline.round2(nl, previous_packet, previous_baked, run_pipeline=True)
    from gaze_engine.delivery.pomot.assembler import DiffusionPromptAssembler

    wan_clip = DiffusionPromptAssembler.split_for_wan(result.get("prompt_04") or "")
    self._json({
        "ok": True,
        "packet_dict": result["packet"].to_dict(),
        "baked_json": result["baked_json"],
        "beat_text": result["beat_text"],
        "prompt_04": result["prompt_04"],
        "wan_positive_clip": wan_clip["positive"],
        "wan_negative_clip": wan_clip["negative"],
        "payload": result["payload"],
        "delta_summary": result.get("delta_summary", ""),
    })


# ── 保存 / 上传 ─────────────────────────────────────────────

@Route.post("/api/portal/save")
def portal_save(self: Handler, body: bytes):
    """保存当前创作到客户项目。"""
    from gaze_engine._shared.customer_db import (
        get_customer, get_project, create_project, save_adjustment,
        save_workbench_context, _save_template_params, update_customer,
    )
    from asset_lib import project_output_dir
    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    project_name = (data.get("project_name") or "").strip()
    packet = data.get("packet")
    baked = data.get("baked")
    metronome = data.get("metronome", "")
    note = (data.get("note") or "").strip()
    resolved = _resolve_slider_packet(data)
    if resolved:
        packet = resolved

    if not cid:
        return self._json({"ok": False, "error": "缺少 customer_id"}, status=400)
    customer = get_customer(cid)
    if not customer:
        return self._json({"ok": False, "error": "客户不存在"}, status=404)

    if not pid:
        if not project_name:
            project_name = f"创作_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pid = create_project(cid, project_name, species=data.get("species", "human"))
        if not pid:
            return self._json({"ok": False, "error": "项目创建失败"}, status=500)

    ver = None
    if packet:
        ver = save_adjustment(cid, pid, packet, note=note or "手动保存")

    tp = data.get("template_params") or {}
    tp_adj = tp.get("adjustments") or {}
    if tp_adj and cid:
        _save_template_params(cid, data.get("species", "human"), data.get("breed", "") or "", tp_adj)
        update_customer(cid, preferred_species=data.get("species", "human"), breed=data.get("breed", "") or "")

    out = project_output_dir(cid, pid)
    out.mkdir(parents=True, exist_ok=True)
    _portal_purge_baked_files(out)
    if metronome:
        (out / "05_扩散节拍表.txt").write_text(metronome, encoding="utf-8")
    if packet:
        (out / "01_滑杆包.json").write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    prompt_04 = data.get("prompt_04", "")
    if prompt_04:
        (out / "04_Prompt.txt").write_text(prompt_04, encoding="utf-8")

    save_workbench_context(cid, pid)
    self._json({
        "ok": True,
        "customer_id": cid,
        "project_id": pid,
        "version": ver,
        "output_dir": str(out),
    })


@Route.post("/api/portal/project/upload-photo")
def portal_project_upload_photo(self: Handler, body: bytes):
    """上传照片到项目参考素材，并运行几何适配器预检测。"""
    from asset_lib import customer_ref_photos_dir, project_dir
    from gaze_engine._shared.customer_db import get_project, update_project, get_customer
    from gaze_engine.render.geometry_adapter import adapt_geometry

    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    b64 = data.get("photo_data", "")
    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)
    if not b64:
        return self._json({"ok": False, "error": "缺少 photo_data"}, status=400)
    if get_project(cid, pid) is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)

    photo_name = data.get("photo_name", "reference.jpg")
    ext = Path(photo_name).suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        ext = ".jpg"
    safe_name = f"ref_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    ref = customer_ref_photos_dir(cid)
    ref.mkdir(parents=True, exist_ok=True)
    save_path = ref / safe_name
    c = 1
    while save_path.exists():
        save_path = ref / f"ref_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{c}{ext}"
        c += 1
    try:
        save_path.write_bytes(base64.b64decode(b64))
    except Exception as e:
        return self._json({"ok": False, "error": f"图片解码失败: {e}"}, status=400)

    proj_ref = project_dir(cid, pid) / "参考素材"
    proj_ref.mkdir(parents=True, exist_ok=True)
    proj_copy = proj_ref / save_path.name
    proj_copy.write_bytes(save_path.read_bytes())
    update_project(cid, pid, reference_photo=save_path.name)

    resp: dict = {
        "ok": True,
        "photo_name": save_path.name,
        "original_name": photo_name,
        "photo_url": f"/api/customer/photo-preview/{cid}/{save_path.name}",
        "saved_paths": {
            "customer_ref": str(save_path),
            "project_ref": str(proj_copy),
        },
    }
    try:
        import cv2
        im = cv2.imread(str(save_path))
        if im is not None:
            resp["image_height"], resp["image_width"] = im.shape[:2]
    except Exception:
        pass

    if data.get("skip_detect"):
        self._json(resp)
        return

    species = (data.get("species") or "human").strip().lower()
    breed = (data.get("breed") or "").strip()
    img_w = int(resp.get("image_width") or 0)
    img_h = int(resp.get("image_height") or 0)
    geo = adapt_geometry(
        species=species,
        breed_id=breed,
        img_width=img_w,
        img_height=img_h,
        photo_path=save_path,
    )
    if geo.method == "failed":
        err = geo.notes[-1] if geo.notes else "MediaPipe 检测失败"
        return self._json({"ok": False, "error": err, "geometry_adapter": geo.to_dict()}, status=400)
    resp["geometry_adapter"] = geo.to_dict()
    resp["suggested_anchors"] = geo.anchors
    resp["adjustments"] = geo.adjustments
    resp["detection"] = {
        "method": geo.method,
        "confidence": geo.confidence,
        "auto_filled": geo.auto_filled,
        "notes": geo.notes,
    }
    self._json(resp)


# ── 标定 ────────────────────────────────────────────────────

@Route.post("/api/portal/calibrate-template")
def portal_calibrate_template(self: Handler, body: bytes):
    """标定：锚点 → 几何适配器 → 空间配准 + 形状补丁（不落盘，实时返回）。"""
    from asset_lib import project_dir, project_output_dir, customer_ref_photos_dir
    from gaze_engine._shared.customer_db import (
        get_project, get_customer,
    )
    from gaze_engine.render.geometry_adapter import adapt_geometry

    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    species = (data.get("species") or "human").strip()
    photo_name = (data.get("photo_name") or "").strip()
    anchor_mode = (data.get("anchor_mode") or "eye_center").strip()

    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)
    if get_project(cid, pid) is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)
    if species != "human":
        return self._json({"ok": False, "error": "无效 species"}, status=400)
    if data.get("anchors"):
        return self._json(
            {"ok": False, "error": "人类标定不支持手动 anchors，请仅上传照片由 MediaPipe 检测"},
            status=400,
        )
    if not photo_name:
        return self._json({"ok": False, "error": "缺少 photo_name"}, status=400)

    img_w = int(data.get("image_width") or 0)
    img_h = int(data.get("image_height") or 0)
    photo_path = customer_ref_photos_dir(cid) / photo_name
    if not photo_path.is_file():
        return self._json({"ok": False, "error": f"参考照片不存在: {photo_name}"}, status=400)
    if not img_w or not img_h:
        import cv2
        im = cv2.imread(str(photo_path))
        if im is not None:
            img_h, img_w = im.shape[:2]

    breed = ""

    geo = adapt_geometry(
        species=species,
        breed_id=breed,
        img_width=img_w,
        img_height=img_h,
        photo_path=photo_path,
    )
    if geo.method == "failed":
        return self._json({"ok": False, "error": geo.notes[-1] if geo.notes else "几何适配失败"}, status=400)

    resolved_anchors = geo.anchors
    from gaze_engine.render.species_template import (
        species_default_template,
        apply_customer_adjustments,
        sanitize_human_spatial_adjustments,
        template_for_spatial_render,
        template_to_renderer_constants,
    )
    customer_adj: dict[str, float] = sanitize_human_spatial_adjustments(geo.adjustments)

    from gaze_engine.render.spatial_calibration import compute_spatial_calibration
    from gaze_engine.render.geometry_adapter import apply_render_baseline

    _base_tpl = species_default_template(species)
    _adj_tpl = apply_customer_adjustments(_base_tpl, customer_adj)
    _spatial_tpl = template_for_spatial_render(_adj_tpl, species, breed_id=None)
    _constants = apply_render_baseline(
        template_to_renderer_constants(species, _spatial_tpl, breed_id=None),
        geo.render_baseline,
    )
    try:
        spatial_cal = compute_spatial_calibration(
            resolved_anchors, img_w, img_h, _constants,
            anchor_mode=anchor_mode,
        )
    except Exception as e:
        return self._json({"ok": False, "error": f"空间标定失败: {e}"}, status=400)
    spatial_cal_dict = spatial_cal.to_dict()
    if not spatial_cal_dict.get("affine_matrix"):
        return self._json({"ok": False, "error": "空间标定未产出仿射矩阵"}, status=400)
    if not geo.render_baseline:
        return self._json({"ok": False, "error": "MediaPipe 未产出 render_baseline"}, status=400)

    self._json({
        "ok": True,
        "method": geo.method,
        "confidence": geo.confidence,
        "breed": breed,
        "breed_label": breed or "",
        "adjustments": customer_adj,
        "geometry_adapter": geo.to_dict(),
        "spatial_calibration": spatial_cal_dict,
        "render_baseline": dict(geo.render_baseline or {}),
        "saved_params": {"adjustments": customer_adj, "species": species, "breed": breed},
        "membrane_note": "标定后线条底膜 · 红=眼眶 · 蓝=瞳孔 · 绿=眉脊",
    })


# ── 管线调试 / 底膜预览 ──────────────────────────────────────

@Route.get("/api/portal/pipeline-debug")
def portal_pipeline_debug(self: Handler):
    """返回全流程中间数据，用于诊断底膜标定问题（实时 MediaPipe 检测，不读文件）。"""
    from urllib.parse import parse_qs, urlparse
    from gaze_engine.render.species_template import (
        species_default_template,
        apply_customer_adjustments,
        template_to_renderer_constants,
    )
    from gaze_engine.render.spatial_calibration import (
        standard_model_anchors,
        compute_spatial_calibration,
        OUTPUT_W, OUTPUT_H,
    )
    from serve_render import _run_live_calibration
    import math, numpy as np

    qs = parse_qs(urlparse(self.path).query)
    cid = (qs.get("customer_id") or [""])[0].strip()
    pid = (qs.get("project_id") or [""])[0].strip()
    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"})

    calib = _run_live_calibration(cid, pid)
    if calib is None:
        return self._json({"ok": False, "error": "实时标定失败：请确保照片已上传且 MediaPipe 可检测到人脸"}, status=404)

    species = calib.get("species", "human")
    img_w, img_h = calib.get("image_size", [0, 0])
    anchors = calib.get("anchors", {})
    adjustments = calib.get("adjustments", {})
    geo_block = calib.get("geometry_adapter", {})
    spatial_cal_block = calib.get("spatial_calibration", {})

    detection_data = geo_block.get("detection", {})
    if not detection_data:
        detection_data = geo_block.get("_detection", {})
    detection_raw = {}
    for key in ("method", "confidence", "face_width", "face_height",
                "eye_distance", "avg_eye_size", "avg_eye_height",
                "eye_aspect", "avg_iris_radius",
                "left_iris_radius", "right_iris_radius",
                "pupil_offset_lx", "pupil_offset_ly",
                "pupil_offset_rx", "pupil_offset_ry",
                "pupil_offset_l", "pupil_offset_r",
                "left_brow_y", "right_brow_y",
                "left_brow_y_lower", "right_brow_y_lower",
                "nose_tip",
                "left_eye_bbox", "right_eye_bbox"):
        if key in detection_data:
            detection_raw[key] = detection_data[key]
    if not detection_raw and geo_block.get("notes"):
        import re as _re
        for _note in geo_block["notes"]:
            _m = _re.search(r"face_w[=:](\d+)", _note)
            if _m:
                detection_raw["face_width"] = int(_m.group(1))
            _m = _re.search(r"factor[=:](\d+\.?\d*)", _note)
            if _m:
                detection_raw["normalize_factor"] = float(_m.group(1))

    base_tpl = species_default_template(species)
    base_params = {k: getattr(base_tpl, k) for k in
                   ("eye_distance", "eye_size", "eye_aspect",
                    "eye_vertical", "pupil_size", "iris_size",
                    "pupil_slit_ratio")}

    adj_tpl = apply_customer_adjustments(base_tpl, adjustments)
    adj_params = {k: getattr(adj_tpl, k) for k in base_params}

    base_constants = template_to_renderer_constants(species, base_tpl, breed_id=None)
    adj_constants = template_to_renderer_constants(species, adj_tpl, breed_id=None)

    try:
        model_anchors_standard = standard_model_anchors(base_constants, anchor_mode="eye_center")
        model_anchors_standard_list = [
            [round(float(p[0]), 2), round(float(p[1]), 2)] for p in model_anchors_standard
        ]
    except Exception:
        model_anchors_standard_list = []

    try:
        model_anchors_adjusted = standard_model_anchors(adj_constants, anchor_mode="eye_center")
        model_anchors_adjusted_list = [
            [round(float(p[0]), 2), round(float(p[1]), 2)] for p in model_anchors_adjusted
        ]
    except Exception:
        model_anchors_adjusted_list = []

    photo_anchors = {}
    for key in ("left_eye", "right_eye", "nose"):
        pt = anchors.get(key)
        if pt and len(pt) >= 2:
            photo_anchors[key] = [float(pt[0]), float(pt[1])]

    spatial_detail = {}
    if spatial_cal_block:
        spatial_detail = {
            "matrix": spatial_cal_block.get("affine_matrix"),
            "model_anchors": spatial_cal_block.get("model_anchors"),
            "photo_anchors": spatial_cal_block.get("photo_anchors"),
            "output_anchors": spatial_cal_block.get("output_anchors"),
            "nose_eye_ratio": spatial_cal_block.get("nose_eye_ratio"),
            "image_size": spatial_cal_block.get("image_size"),
            "output_size": spatial_cal_block.get("output_size", [OUTPUT_W, OUTPUT_H]),
        }

    scale_info = {}
    if model_anchors_standard_list and photo_anchors.get("left_eye") and photo_anchors.get("right_eye"):
        le_p = photo_anchors["left_eye"]
        re_p = photo_anchors["right_eye"]
        eye_dist_photo = math.hypot(re_p[0] - le_p[0], re_p[1] - le_p[1])
        md = model_anchors_standard_list
        eye_dist_model = math.hypot(md[1][0] - md[0][0], md[1][1] - md[0][1])
        scale_info = {
            "photo_eye_distance_px": round(eye_dist_photo, 2),
            "model_eye_distance_standard": round(eye_dist_model, 2),
            "scale_standard": round(eye_dist_photo / max(eye_dist_model, 1), 4),
            "output_w": OUTPUT_W,
            "output_h": OUTPUT_H,
        }

    _rc_keys = ("LEFT_CX", "RIGHT_CX", "LEFT_CY", "RIGHT_CY", "EYE_W",
                "UPPER_PEAK", "LOWER_BOT",
                "PUPIL_R_BASE", "IRIS_R_BASE",
                "BLINK_DROP", "SQUINT_LIFT",
                "BROW_DOWN", "BROW_RAISE_AMP")
    _renderer_constants_standard = {}
    for _k in _rc_keys:
        if _k in base_constants:
            _renderer_constants_standard[_k] = base_constants[_k]
    _renderer_constants_adjusted = {}
    for _k in _rc_keys:
        if _k in adj_constants:
            _renderer_constants_adjusted[_k] = adj_constants[_k]

    debug = {
        "ok": True,
        "customer_id": cid,
        "project_id": pid,
        "species": species,
        "image_size": [img_w, img_h],
        "anchors": {
            "photo": photo_anchors,
            "model_standard": model_anchors_standard_list,
            "model_adjusted": model_anchors_adjusted_list,
        },
        "detection": detection_raw,
        "template_pipeline": {
            "standard_params": base_params,
            "customer_adjustments": adjustments,
            "applied_params": adj_params,
        },
        "renderer_constants": {
            "standard": _renderer_constants_standard,
            "adjusted": _renderer_constants_adjusted,
        },
        "render_baseline": calib.get("render_baseline", {}),
        "spatial_calibration": spatial_detail,
        "spatial_scale": scale_info,
        "geometry_adapter_notes": geo_block.get("notes", []),
        "geometry_adapter_method": geo_block.get("method", ""),
        "geometry_adapter_confidence": geo_block.get("confidence", 0),
        "_live_calibration": True,
    }

    self._json(debug)


@Route.get("/api/portal/membrane-preview")
def portal_membrane_preview(self: Handler):
    """狗项目 OpenCV 线条底膜：?variant=breed|calibrated（缺图则按标定文件补生成）。"""
    from urllib.parse import parse_qs, urlparse
    from asset_lib import project_output_dir, project_dir

    qs = parse_qs(urlparse(self.path).query)
    cid = (qs.get("customer_id") or [""])[0].strip()
    pid = (qs.get("project_id") or [""])[0].strip()
    variant = (qs.get("variant") or ["calibrated"])[0].strip().lower()
    if not cid or not pid:
        return self.send_error(400)

    out = project_output_dir(cid, pid)
    preview_path = out / "底膜预览_标定后.png"
    if not preview_path.is_file():
        return self.send_error(404)
    data = preview_path.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", "image/png")
    self.send_header("Content-Length", str(len(data)))
    self.send_header("Cache-Control", "no-store")
    self.end_headers()
    self.wfile.write(data)


@Route.get("/api/portal/alignment-verify/bundle")
def portal_alignment_verify_bundle(self: Handler):
    """MP vs CV 对齐诊断图（与 diagnose_mapping_pipeline Step 4b 同源）。"""
    from serve_render import _build_alignment_verify_bundle
    from urllib.parse import parse_qs, urlparse
    import base64

    qs = parse_qs(urlparse(self.path).query)
    cid = (qs.get("customer_id") or [""])[0].strip()
    pid = (qs.get("project_id") or [""])[0].strip()
    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)

    bundle = _build_alignment_verify_bundle(customer_id=cid, project_id=pid)
    if bundle is None:
        return self._json({"ok": False, "error": "对齐诊断生成失败"}, status=404)

    import cv2

    images_b64: dict[str, str] = {}
    for key, arr in bundle["images"].items():
        ok, buf = cv2.imencode(".png", arr)
        if ok:
            images_b64[key] = base64.b64encode(buf.tobytes()).decode("ascii")

    return self._json({
        "ok": True,
        "errors_px": bundle["errors"],
        "images": images_b64,
        "views": [
            {"id": "grid", "label": "2×2 总览 (MP|CV)"},
            {"id": "layers_left", "label": "左眼分层"},
            {"id": "layers_right", "label": "右眼分层"},
        ],
    })


@Route.get("/api/portal/overlay-preview")
def portal_overlay_preview(self: Handler):
    """底膜线条叠加到参考照片。"""
    from serve_render import _build_overlay_preview
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(self.path).query)
    cid = (qs.get("customer_id") or [""])[0].strip()
    pid = (qs.get("project_id") or [""])[0].strip()
    if not cid or not pid:
        return self.send_error(400)

    show_eyelid = (qs.get("show_eyelid") or ["1"])[0].strip().lower() in ("1", "true", "yes")
    show_eyebrow = (qs.get("show_eyebrow") or ["1"])[0].strip().lower() in ("1", "true", "yes")
    show_pupil = (qs.get("show_pupil") or ["1"])[0].strip().lower() in ("1", "true", "yes")
    show_anchors = (qs.get("show_anchors") or ["1"])[0].strip().lower() in ("1", "true", "yes")
    try:
        opacity = float((qs.get("opacity") or ["0.6"])[0].strip())
    except ValueError:
        opacity = 0.6

    png_bytes = _build_overlay_preview(
        customer_id=cid,
        project_id=pid,
        show_eyelid=show_eyelid,
        show_eyebrow=show_eyebrow,
        show_pupil=show_pupil,
        show_anchors=show_anchors,
        opacity=opacity,
    )
    if png_bytes is None:
        return self.send_error(404)

    self.send_response(200)
    self.send_header("Content-Type", "image/png")
    self.send_header("Content-Length", str(len(png_bytes)))
    self.send_header("Cache-Control", "no-store")
    self.end_headers()
    self.wfile.write(png_bytes)


# ── 项目状态 / 保存步骤 ────────────────────────────────────

@Route.get("/api/portal/project/state")
def portal_project_state(self: Handler):
    """恢复项目进度：标定、管线中间产物、扩散引擎两件套。"""
    from urllib.parse import urlparse, parse_qs
    from asset_lib import project_dir, project_output_dir
    from gaze_engine._shared.customer_db import (
        get_project, get_template_params, get_customer,
    )
    from serve_render import _analyze_membrane_status

    qs = parse_qs(urlparse(self.path).query)
    cid = (qs.get("customer_id") or [""])[0].strip()
    pid = (qs.get("project_id") or [""])[0].strip()
    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)

    proj = get_project(cid, pid)
    if proj is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)

    p_dir = project_dir(cid, pid)
    out_dir = project_output_dir(cid, pid)

    calibration = None

    template_params = None
    tpl = get_template_params(cid)
    if tpl is not None:
        template_params = tpl.to_dict()

    pipeline: dict = {}
    packet_path = out_dir / "01_滑杆包.json"
    _portal_purge_baked_files(out_dir)
    if packet_path.is_file():
        try:
            pipeline["packet"] = json.loads(packet_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    video_name = "03_工程底模.mp4"
    prompt_name = "04_Prompt.txt"
    meta_name = "03_工程底模.meta.json"
    mp4 = out_dir / video_name
    prompt_f = out_dir / prompt_name
    meta_f = out_dir / meta_name
    membrane_meta = None
    if meta_f.is_file():
        try:
            membrane_meta = json.loads(meta_f.read_text(encoding="utf-8"))
        except Exception:
            membrane_meta = None

    base_url = f"/api/customer-portal/{cid}/file/{pid}"
    preview_name = "底膜预览.png"
    preview_f = out_dir / preview_name
    preview_url = ""
    if preview_f.is_file():
        preview_url = f"{base_url}/{preview_name}"
    elif calibration and calibration.get("preview_url"):
        preview_url = calibration["preview_url"]

    deliverables = {
        "video_file": video_name,
        "video_exists": mp4.is_file(),
        "video_url": f"{base_url}/{video_name}" if mp4.is_file() else "",
        "video_size": mp4.stat().st_size if mp4.is_file() else 0,
        "prompt_file": prompt_name,
        "prompt_exists": prompt_f.is_file(),
        "prompt_url": f"{base_url}/{prompt_name}" if prompt_f.is_file() else "",
        "prompt_size": prompt_f.stat().st_size if prompt_f.is_file() else 0,
        "preview_file": preview_name,
        "preview_exists": preview_f.is_file(),
        "preview_url": preview_url,
        "membrane_meta": membrane_meta,
    }

    species = proj.get("species") or (get_customer(cid) or {}).get("preferred_species") or "human"
    baked_species = None
    species_mismatch = False
    membrane_status = _analyze_membrane_status(
        species,
        None,
        membrane_meta,
        video_exists=mp4.is_file(),
    )

    profile = None
    bundle = None
    profile_path = p_dir / "客户资料.json"
    if profile_path.is_file():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            profile = None
    from asset_lib import diffusion_bundle_dir
    bundle_dir = diffusion_bundle_dir(cid, pid)
    manifest_f = bundle_dir / "manifest.json"
    if manifest_f.is_file():
        try:
            bundle = json.loads(manifest_f.read_text(encoding="utf-8"))
        except Exception:
            bundle = None

    self._json({
        "ok": True,
        "project_id": pid,
        "species": species,
        "reference_photo": proj.get("reference_photo") or "",
        "calibration": calibration,
        "template_params": template_params,
        "pipeline": pipeline,
        "pipeline_note": "02_烘焙 不落盘；第③步生成或第④步渲染时即时编译",
        "deliverables": deliverables,
        "species_mismatch": species_mismatch,
        "baked_species": baked_species,
        "membrane_status": membrane_status,
        "profile": profile,
        "bundle": bundle,
        "bundle_dir": str(bundle_dir) if bundle_dir.is_dir() else "",
        "profile_path": str(profile_path) if profile_path.is_file() else "",
    })


@Route.post("/api/portal/save-step")
def portal_save_step(self: Handler, body: bytes):
    """分步状态记录（仅内存返回，不落盘到 客户资产库/）。"""
    from gaze_engine._shared.customer_db import get_project

    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    step = (data.get("step") or "").strip()
    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)
    if get_project(cid, pid) is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)

    self._json({"ok": True, "step": step, "note": "中间步骤不落盘"})


# ── 渲染预览 / 导出 / 归档 ──────────────────────────────────

@Route.post("/api/portal/render-preview")
def portal_render_preview(self: Handler, body: bytes):
    """渲染 OpenCV 工程底膜视频（预览用，保存到运行时缓存，不落盘 客户资产库/）。"""
    from serve_render import render_opencv_video

    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    species = data.get("species", "human")
    baked = data.get("baked")
    req_breed = (data.get("breed") or "").strip()

    if not baked or not baked.get("channel_tracks"):
        try:
            baked = _portal_compile_baked(data)
        except ValueError as e:
            return self._json({"ok": False, "error": str(e)}, status=400)

    project_species = species
    if cid and pid:
        from gaze_engine._shared.customer_db import get_project
        proj = get_project(cid, pid)
        if proj:
            project_species = proj.get("species") or species

    baked_species = (baked or {}).get("species")
    if baked_species and baked_species != project_species:
        return self._json({
            "ok": False,
            "error": f"烘焙数据是「{baked_species}」物种，与项目设定「{project_species}」不一致，请重新生成表情",
        }, status=400)

    try:
        video_path, frames, render_info = render_opencv_video(
            baked=baked,
            species=project_species,
            customer_id=cid,
            project_id=pid,
            breed_id=req_breed,
        )
    except Exception as e:
        return self._json({"ok": False, "error": str(e)}, status=500)

    video_url = "/control_video.mp4"

    self._json({
        "ok": True,
        "video_url": video_url,
        "frames": frames,
        "path": str(video_path),
        **render_info,
    })


@Route.post("/api/portal/export")
def portal_export(self: Handler, body: bytes):
    """最终导出：仅拼装送扩散引擎的两件套（MP4 + 04_Prompt.txt）。"""
    from gaze_engine.delivery.pomot.assembler import DiffusionPromptAssembler
    from asset_lib import project_output_dir
    from gaze_engine._shared.customer_db import (
        get_project, get_customer, _save_template_params, update_customer,
    )
    from serve_render import render_opencv_video

    data = self._read_body(body)
    baked = data.get("baked")
    if not baked or not baked.get("channel_tracks"):
        try:
            baked = _portal_compile_baked(data)
        except ValueError as e:
            return self._json({"ok": False, "error": str(e)}, status=400)

    species = data.get("species") or baked.get("species") or "human"
    breed = data.get("breed") or baked.get("breed") or ""
    if not breed:
        cid_lookup = (data.get("customer_id") or "").strip()
        if cid_lookup:
            breed = (get_customer(cid_lookup) or {}).get("breed", "")

    emotion = (
        baked.get("gaze_emotion_id")
        or baked.get("mood")
        or data.get("emotion")
        or ""
    )
    action = (data.get("action") or "").strip()

    assembler = DiffusionPromptAssembler()
    assembly = assembler.assemble(
        baked,
        customer_action=action or "（无客户叙事）",
        species=species,
        breed=breed,
        emotion=emotion,
    )
    prompt_04 = assembly["prompt_04"]
    wan_clip = DiffusionPromptAssembler.split_for_wan(prompt_04)

    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    video_path = ""
    video_url = ""
    prompt_path = ""
    membrane_meta = None

    if cid and pid and get_project(cid, pid):
        out = project_output_dir(cid, pid)
        out.mkdir(parents=True, exist_ok=True)

        tp = data.get("template_params") or {}
        tp_adj = tp.get("adjustments") or {}
        if tp_adj and cid:
            _save_template_params(cid, species, breed or "", tp_adj)
            update_customer(cid, preferred_species=species, breed=breed or "")

        _portal_purge_baked_files(out)
        prompt_file = out / "04_Prompt.txt"
        prompt_file.write_text(prompt_04, encoding="utf-8")
        (out / "wan_positive.txt").write_text(wan_clip["positive"], encoding="utf-8")
        (out / "wan_negative.txt").write_text(wan_clip["negative"], encoding="utf-8")
        prompt_path = str(prompt_file)
        try:
            video_path_obj, _, render_info = render_opencv_video(
                baked=baked, species=species, customer_id=cid, project_id=pid,
            )
            render_info["baked_revision"] = baked.get("revision", "")
            render_info["baked_mood"] = baked.get("mood", "")
            dest = out / "03_工程底模.mp4"
            dest.write_bytes(video_path_obj.read_bytes())
            video_path = str(dest)
            video_url = f"/api/customer-portal/{cid}/file/{pid}/03_工程底模.mp4"
            (out / "03_工程底模.meta.json").write_text(
                json.dumps(render_info, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            snap = render_info.get("first_frame_preview") or ""
            if snap and Path(snap).is_file():
                (out / "底膜预览_动画首帧.png").write_bytes(Path(snap).read_bytes())
            membrane_meta = render_info
        except Exception as e:
            mp4 = out / "03_工程底模.mp4"
            if mp4.is_file():
                video_path = str(mp4)
                video_url = f"/api/customer-portal/{cid}/file/{pid}/03_工程底模.mp4"
            meta_f = out / "03_工程底模.meta.json"
            if meta_f.is_file():
                try:
                    membrane_meta = json.loads(meta_f.read_text(encoding="utf-8"))
                except Exception:
                    membrane_meta = None
            if not video_path:
                return self._json({"ok": False, "error": f"底膜渲染失败: {e}"}, status=500)

    prompt_url = ""
    prompt_size = 0
    video_size = 0
    if cid and pid:
        base_url = f"/api/customer-portal/{cid}/file/{pid}"
        if prompt_path:
            pf = Path(prompt_path)
            prompt_url = f"{base_url}/04_Prompt.txt"
            prompt_size = pf.stat().st_size if pf.is_file() else 0
        if video_path:
            vf = Path(video_path)
            video_size = vf.stat().st_size if vf.is_file() else 0

    archive_profile = None
    bundle_info = None
    if cid and pid and get_project(cid, pid):
        from gaze_engine.delivery.project_archive import (
            build_diffusion_bundle,
            save_project_profile,
        )
        archive_profile = save_project_profile(cid, pid, {
            **data,
            "baked": baked,
            "species": species,
            "breed": breed,
            "emotion": emotion,
            "action": action,
            "wan_positive_clip": wan_clip["positive"],
            "wan_negative_clip": wan_clip["negative"],
            "note": "portal_export",
        })
        bundle_info = build_diffusion_bundle(
            cid, pid,
            prompt_04=prompt_04,
            wan_positive=wan_clip["positive"],
            wan_negative=wan_clip["negative"],
        )

    bundle_url = ""
    bundle_zip_url = ""
    if cid and pid:
        bundle_url = f"/api/customer-portal/{cid}/file/{pid}/manifest.json"
        bundle_zip_url = (
            f"/api/portal/download-bundle?customer_id={cid}&project_id={pid}"
        )

    self._json({
        "ok": True,
        "deliverables": {
            "video_file": "03_工程底模.mp4",
            "video_path": video_path,
            "video_url": video_url,
            "video_exists": bool(video_path),
            "video_size": video_size,
            "prompt_file": "04_Prompt.txt",
            "prompt_path": prompt_path,
            "prompt_exists": bool(prompt_path),
            "prompt_url": prompt_url,
            "prompt_size": prompt_size,
            "prompt_04": prompt_04,
            "wan_positive_clip": wan_clip["positive"],
            "wan_negative_clip": wan_clip["negative"],
            "wan_positive_url": f"/api/customer-portal/{cid}/file/{pid}/wan_positive.txt" if cid and pid else "",
            "wan_negative_url": f"/api/customer-portal/{cid}/file/{pid}/wan_negative.txt" if cid and pid else "",
            "membrane_meta": membrane_meta,
            "baked_revision": baked.get("revision", ""),
            "bundle_dir": bundle_info["bundle_dir"] if bundle_info else "",
            "bundle_manifest_url": bundle_url if bundle_info else "",
            "bundle_zip_url": bundle_zip_url if bundle_info else "",
            "profile_path": archive_profile["paths"]["profile_file"] if archive_profile else "",
        },
        "profile": archive_profile,
        "bundle": bundle_info["manifest"] if bundle_info else None,
        "note": "送扩散引擎：① 03_工程底模.mp4  ② 04_Prompt.txt + wan± ；整包见 输出/扩散引擎包/",
    })


@Route.post("/api/portal/archive")
def portal_archive(self: Handler, body: bytes):
    """保存客户资料.json，并可选组装 扩散引擎包/。"""
    from gaze_engine._shared.customer_db import (
        get_project, save_adjustment, _save_template_params, update_customer,
    )
    from gaze_engine.delivery.project_archive import (
        build_diffusion_bundle,
        save_project_profile,
    )
    from asset_lib import project_output_dir

    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)
    if get_project(cid, pid) is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)

    out = project_output_dir(cid, pid)
    out.mkdir(parents=True, exist_ok=True)
    packet = data.get("packet")
    baked = data.get("baked")
    resolved = _resolve_slider_packet(data)
    if resolved:
        packet = resolved
    if packet:
        (out / "01_滑杆包.json").write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _portal_purge_baked_files(out)
    metronome = data.get("metronome") or data.get("beat_text") or ""
    if metronome:
        (out / "05_扩散节拍表.txt").write_text(metronome, encoding="utf-8")
    prompt_04 = data.get("prompt_04") or ""
    if prompt_04:
        (out / "04_Prompt.txt").write_text(prompt_04, encoding="utf-8")
    wan_pos = data.get("wan_positive_clip") or data.get("wan_positive") or ""
    wan_neg = data.get("wan_negative_clip") or data.get("wan_negative") or ""
    if wan_pos:
        (out / "wan_positive.txt").write_text(wan_pos, encoding="utf-8")
    if wan_neg:
        (out / "wan_negative.txt").write_text(wan_neg, encoding="utf-8")

    ver = None
    if packet:
        ver = save_adjustment(
            cid, pid, packet,
            note=data.get("note") or "客户资料归档",
        )

    tp = data.get("template_params") or {}
    tp_adj = tp.get("adjustments") or {}
    if tp_adj and cid:
        _save_template_params(cid, data.get("species", "human"), data.get("breed", "") or "", tp_adj)
        update_customer(cid, preferred_species=data.get("species", "human"), breed=data.get("breed", "") or "")

    profile = save_project_profile(cid, pid, data)
    bundle_info = None
    if data.get("build_bundle", True):
        bundle_info = build_diffusion_bundle(
            cid, pid,
            prompt_04=prompt_04,
            wan_positive=wan_pos,
            wan_negative=wan_neg,
        )

    self._json({
        "ok": True,
        "version": ver,
        "profile": profile,
        "profile_path": profile["paths"]["profile_file"],
        "bundle": bundle_info["manifest"] if bundle_info else None,
        "bundle_dir": bundle_info["bundle_dir"] if bundle_info else "",
        "bundle_zip_url": f"/api/portal/download-bundle?customer_id={cid}&project_id={pid}",
    })


@Route.get("/api/portal/download-bundle")
def portal_download_bundle(self: Handler):
    """下载 扩散引擎包/ 为 zip。"""
    import io
    import zipfile
    from urllib.parse import parse_qs, urlparse
    from asset_lib import diffusion_bundle_dir
    from gaze_engine._shared.customer_db import get_project

    qs = parse_qs(urlparse(self.path).query)
    cid = (qs.get("customer_id") or [""])[0].strip()
    pid = (qs.get("project_id") or [""])[0].strip()
    if not cid or not pid or get_project(cid, pid) is None:
        return self.send_error(404)

    bundle = diffusion_bundle_dir(cid, pid)
    if not bundle.is_dir():
        return self.send_error(404)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(bundle.iterdir()):
            if f.is_file():
                zf.write(f, arcname=f.name)
    data = buf.getvalue()
    fname = f"diffusion_bundle_{cid}_{pid}.zip"
    self.send_response(200)
    self.send_header("Content-Type", "application/zip")
    self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
    self.send_header("Content-Length", str(len(data)))
    self.end_headers()
    self.wfile.write(data)
