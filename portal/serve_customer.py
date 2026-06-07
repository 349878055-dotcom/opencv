"""客户/项目 CRUD API — 客户信息、参考照片、项目增删改查。"""
from __future__ import annotations

import json, base64
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote

from serve_workbench import Route, Handler


@Route.get("/api/customer/photos/{cid}")
def customer_photos(self: Handler, cid: str):
    from asset_lib import customer_ref_photos_dir
    from gaze_engine._shared.customer_db import get_template_params
    ref = customer_ref_photos_dir(cid)
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    photos = [{"name": p.name, "size": p.stat().st_size,
               "url": f"/api/customer/photo-preview/{cid}/{p.name}"}
              for p in sorted(ref.iterdir()) if p.suffix.lower() in exts] if ref.is_dir() else []
    tpl = get_template_params(cid)
    self._json({
        "ok": True, "photos": photos,
        "has_template_params": tpl is not None,
        "template_params": tpl.to_dict() if tpl else None,
    })


@Route.get("/api/customer/photo-preview/{cid}/{name}")
def customer_photo_preview(self: Handler, cid: str, name: str):
    from asset_lib import customer_ref_photos_dir
    name = unquote(name)
    fp = customer_ref_photos_dir(cid) / name
    if not fp.is_file():
        return self.send_error(404)
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".bmp": "image/bmp", ".webp": "image/webp"}.get(fp.suffix.lower(), "application/octet-stream")
    data = fp.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", mime)
    self.send_header("Content-Length", str(len(data)))
    self.send_header("Cache-Control", "max-age=3600")
    self.end_headers()
    self.wfile.write(data)


@Route.get("/api/customer-portal/{cid}")
def customer_portal(self: Handler, cid: str):
    """返回客户门户数据：按每张参考照片分类展示关联的项目资产。"""
    from gaze_engine._shared.customer_db import get_customer, list_projects
    from asset_lib import customer_dir, customer_ref_photos_dir, project_dir, project_output_dir

    customer = get_customer(cid)
    if customer is None:
        return self._json({"ok": False, "error": f"客户 {cid} 不存在"}, status=404)

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    all_projects = list_projects(cid)

    ref_dir = customer_ref_photos_dir(cid)
    photo_map: dict[str, dict] = {}

    if ref_dir.is_dir():
        for p in sorted(ref_dir.iterdir()):
            if p.suffix.lower() in exts:
                photo_map[p.name] = {
                    "name": p.name,
                    "url": f"/api/customer/photo-preview/{cid}/{p.name}",
                    "size": p.stat().st_size,
                    "projects": [],
                }

    for proj in all_projects:
        pid = proj.get("project_id", "")
        if not pid:
            continue
        proj_ref = project_dir(cid, pid) / "参考素材"
        if proj_ref.is_dir():
            for p in sorted(proj_ref.iterdir()):
                if p.suffix.lower() in exts and p.name not in photo_map:
                    photo_map[p.name] = {
                        "name": p.name,
                        "url": f"/api/customer-portal/{cid}/file/{pid}/{p.name}",
                        "size": p.stat().st_size,
                        "projects": [],
                    }

    photos = list(photo_map.values())

    project_assets: list[dict] = []
    for proj in all_projects:
        pid = proj.get("project_id", "")
        if not pid:
            continue
        p_dir = project_dir(cid, pid)
        out_dir = project_output_dir(cid, pid)
        ref_photo = proj.get("reference_photo", "") or ""

        if not ref_photo:
            proj_ref_dir = p_dir / "参考素材"
            if proj_ref_dir.is_dir():
                for f in sorted(proj_ref_dir.iterdir()):
                    if f.suffix.lower() in exts:
                        ref_photo = f.name
                        break

        outputs: list[dict] = []
        membrane_meta_quick = None
        mp4_quick = out_dir / "03_工程底模.mp4"
        meta_quick = out_dir / "03_工程底模.meta.json"
        if meta_quick.is_file():
            try:
                membrane_meta_quick = json.loads(meta_quick.read_text(encoding="utf-8"))
            except Exception:
                pass
        baked_quick = None
        baked_quick_path = out_dir / "02_烘焙_真人律.json"
        if baked_quick_path.is_file():
            try:
                baked_quick = json.loads(baked_quick_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        proj_species = proj.get("species") or "human"
        from serve_render import _analyze_membrane_status
        membrane_status_quick = _analyze_membrane_status(
            proj_species, baked_quick, membrane_meta_quick, video_exists=mp4_quick.is_file(),
        )

        if out_dir.is_dir():
            for f in sorted(out_dir.iterdir()):
                if f.is_file() and not f.name.startswith("."):
                    ext = f.suffix.lower()
                    tag = ""
                    fname = f.name
                    if "滑杆" in fname or "01_" in fname:
                        tag = "01_滑杆包"
                    elif "烘焙" in fname or "02_" in fname:
                        tag = "02_烘焙"
                    elif "扩散" in fname or "05_" in fname or "节拍" in fname:
                        tag = "05_扩散节拍"
                    elif "底模" in fname or "03_" in fname:
                        tag = "03_工程底模"
                    elif "prompt" in fname.lower() or "04_" in fname:
                        tag = "04_Prompt"
                    outputs.append({
                        "name": fname,
                        "tag": tag,
                        "size": f.stat().st_size,
                        "ext": ext,
                        "url": f"/api/customer-portal/{cid}/file/{pid}/{f.name}",
                    })

        plans: list[dict] = []
        plans_dir = p_dir / "计划文档"
        if plans_dir.is_dir():
            for f in sorted(plans_dir.iterdir()):
                if f.is_file():
                    plans.append({
                        "name": f.name,
                        "size": f.stat().st_size,
                    })

        nl_history: list[str] = []
        adj_dir = p_dir / "调整过程"
        if adj_dir.is_dir():
            for f in sorted(adj_dir.iterdir()):
                if f.suffix.lower() == ".json":
                    try:
                        data = json.loads(f.read_text("utf-8"))
                        note = data.get("note", "") or data.get("extra", {}).get("emotion", "")
                        if note:
                            nl_history.append(note)
                    except Exception:
                        pass

        asset_entry = {
            "project_id": pid,
            "project_name": proj.get("project_name", pid),
            "species": proj_species,
            "reference_photo": ref_photo,
            "outputs": outputs,
            "plan_docs": plans,
            "nl_history": nl_history,
            "membrane_status": membrane_status_quick,
        }
        project_assets.append(asset_entry)

        if ref_photo:
            for photo in photos:
                if photo["name"] == ref_photo:
                    photo["projects"].append(asset_entry)
                    break

    from gaze_engine._shared.customer_db import load_workbench_context
    workbench_ctx = load_workbench_context()

    self._json({
        "ok": True,
        "customer": customer,
        "photos": photos,
        "unlinked_projects": [p for p in project_assets if not p["reference_photo"]],
        "workbench_context": workbench_ctx,
    })


@Route.get("/api/customer-portal/{cid}/file/{pid}/{name}")
def customer_portal_file(self: Handler, cid: str, pid: str, name: str):
    """提供客户门户中的文件下载/预览（输出/参考素材/项目根）。"""
    from asset_lib import project_dir, project_output_dir
    candidates = [
        project_output_dir(cid, pid) / "扩散引擎包" / name,
        project_output_dir(cid, pid) / name,
        project_dir(cid, pid) / "参考素材" / name,
        project_dir(cid, pid) / name,
    ]
    fp = next((p for p in candidates if p.is_file()), None)
    if fp is None:
        return self.send_error(404)
    mime_map = {
        ".json": "application/json",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
    }
    mime = mime_map.get(fp.suffix.lower(), "application/octet-stream")
    data = fp.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", mime)
    self.send_header("Content-Length", str(len(data)))
    self.send_header("Cache-Control", "max-age=3600")
    self.end_headers()
    self.wfile.write(data)


@Route.post("/api/customer/{cid}/project/create")
def project_create(self: Handler, body: bytes, cid: str):
    from gaze_engine._shared.customer_db import create_project, get_customer
    if get_customer(cid) is None:
        return self._json({"ok": False, "error": f"客户 {cid} 不存在"}, status=404)
    data = self._read_body(body)
    name = (data.get("project_name") or "").strip()
    if not name:
        return self._json({"ok": False, "error": "缺少 project_name"}, status=400)
    pid = create_project(cid, name, species=data.get("species", "human"),
                         base_persona=data.get("base_persona", ""),
                         base_emotion=data.get("base_emotion", ""),
                         reference_photo=data.get("reference_photo", ""),
                         custom_overrides=data.get("custom_overrides"))
    self._json({"ok": True, "project_id": pid})


@Route.post("/api/customer/{cid}/project/update")
def project_update(self: Handler, body: bytes, cid: str):
    from gaze_engine._shared.customer_db import update_project
    data = self._read_body(body)
    pid = data.get("project_id", "").strip()
    if not pid:
        return self._json({"ok": False, "error": "缺少 project_id"}, status=400)
    ok = update_project(cid, pid, **{k: data[k] for k in data if k not in ("customer_id", "project_id")})
    self._json({"ok": ok})


@Route.post("/api/customer/{cid}/project/delete")
def project_delete(self: Handler, body: bytes, cid: str):
    from gaze_engine._shared.customer_db import delete_project
    data = self._read_body(body)
    pid = data.get("project_id", "").strip()
    if not pid:
        return self._json({"ok": False, "error": "缺少 project_id"}, status=400)
    self._json({"ok": delete_project(cid, pid)})


@Route.post("/api/customer/{cid}/project/{pid}/save-adjustment")
def project_save_adjustment(self: Handler, body: bytes, cid: str, pid: str):
    from gaze_engine._shared.customer_db import save_adjustment
    data = self._read_body(body)
    packet = data.get("packet")
    if not packet:
        return self._json({"ok": False, "error": "缺少 packet"}, status=400)
    ver = save_adjustment(cid, pid, packet, note=data.get("note", ""), diff=data.get("diff"))
    if ver is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)
    self._json({"ok": True, "version": ver})
