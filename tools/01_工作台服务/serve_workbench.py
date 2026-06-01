#!/usr/bin/env python3
"""客户创作门户 · HTTP 后端 — 门户 API（标定→Pomot→烘焙→底膜→扩散导出）。"""
from __future__ import annotations

import base64, json, sys, time
from datetime import datetime, timezone
from urllib.parse import unquote
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent       # tools/
PKG = ROOT.parent                                    # 项目根目录
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

PORT = 8765
VERSION = 13
WORKBENCH_SVC = ROOT / "01_工作台服务"
PORTAL_HTML = WORKBENCH_SVC / "客户门户.html"
PORTAL_JS = WORKBENCH_SVC / "static" / "portal.js"
CONTROL_VIDEO_DIR = ROOT / "04_缓存数据" / "preview_cache"
CONTROL_VIDEO_PATH = CONTROL_VIDEO_DIR / "control_video.mp4"

# 门户能力清单 — /api/portal/version 返回；启动脚本与健康检查据此判定服务是否过旧
PORTAL_FEATURES = (
    "calibrate_preview",
    "membrane_preview_api",
    "render_membrane",
    "login_by_name",
    "project_archive",
)


def _file_mtime_token(*paths: Path) -> str:
    latest = 0.0
    for p in paths:
        if p.is_file():
            latest = max(latest, p.stat().st_mtime)
    return str(int(latest)) if latest else "0"


# 由源文件修改时间自动生成 — 改代码后无需手改版本号
PORTAL_BUILD = _file_mtime_token(Path(__file__).resolve(), PORTAL_HTML, PORTAL_JS)
SERVER_BOOT_AT = datetime.now(timezone.utc).isoformat()


def _inject_portal_html(raw: str) -> str:
    return (
        raw.replace("__PORTAL_BUILD__", PORTAL_BUILD)
        .replace("v20260527e", PORTAL_BUILD)  # 兼容旧 HTML 硬编码
    )


def _serve_portal_html(handler: Handler) -> None:
    """始终由当前进程注入 build 号，避免浏览器/static 缓存旧门户。"""
    if not PORTAL_HTML.is_file():
        handler.send_error(404, "客户门户.html 不存在")
        return
    body = _inject_portal_html(PORTAL_HTML.read_text(encoding="utf-8")).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
    handler.end_headers()
    handler.wfile.write(body)


# ─── 路由注册表 ──────────────────────────────────────────────
class Route:
    """装饰器：将 method(path) 注册到 handler 的路由表。"""
    registry: dict[str, dict[str, callable]] = {}  # {"METHOD": {"/path": handler}}

    @classmethod
    def get(cls, path: str):
        return lambda fn: cls._register("GET", path, fn)

    @classmethod
    def post(cls, path: str):
        return lambda fn: cls._register("POST", path, fn)

    @classmethod
    def _register(cls, method: str, path: str, fn: callable):
        cls.registry.setdefault(method, {})[path.rstrip("/")] = fn
        return fn

    @classmethod
    def match(cls, method: str, path: str) -> tuple[callable | None, dict]:
        """匹配精确或带参数的路由 (如 /api/customer/{cid}/project/create)。"""
        p = path.rstrip("/")
        table = cls.registry.get(method, {})
        if p in table:
            return table[p], {}
        # 带参数的路由匹配
        for pattern, handler in table.items():
            parts_p = p.split("/")
            parts_pt = pattern.split("/")
            if len(parts_p) != len(parts_pt):
                continue
            params = {}
            ok = True
            for a, b in zip(parts_p, parts_pt):
                if b.startswith("{") and b.endswith("}"):
                    params[b[1:-1]] = a
                elif a != b:
                    ok = False
                    break
            if ok:
                return handler, params
        return None, {}


# ─── Handler ─────────────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        p = unquote(self.path.split("?", 1)[0])
        if p.endswith((".html", ".js")) or "/portal" in p or "portal.js" in p:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        elif p.endswith((".json", ".png", ".jpg", ".mp4")):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    # ── GET ──
    path: str  # type: ignore[assignment]
    def do_GET(self):
        raw = self.path.split("?", 1)[0]
        path = unquote(raw).rstrip("/")
        if path in ("", "/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/portal")
            self.end_headers()
            return
        if path in ("/portal", "/customer-portal"):
            _serve_portal_html(self)
            return
        if path.endswith("/%E5%AE%A2%E6%88%B7%E9%97%A8%E6%88%B7.html") or path.endswith("/客户门户.html"):
            _serve_portal_html(self)
            return
        handler, params = Route.match("GET", path)
        if handler:
            handler(self, **params)
        else:
            super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        handler, params = Route.match("POST", path)
        if handler:
            try:
                handler(self, body, **params)
            except Exception as e:
                safe = str(e).encode("ascii", errors="replace").decode("ascii")
                self._json({"error": safe}, status=400)
        else:
            self.send_error(404)

    # ── 工具 ──
    def _json(self, data: dict, *, status: int = 200):
        out = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def _read_body(self, body: bytes) -> dict:
        return json.loads(body.decode("utf-8"))

    def log_message(self, fmt: str, *args):
        print(f"[workbench] {fmt % args}", flush=True)


# ═══════════════════════════════════════════════════════════════
# GET 路由
# ═══════════════════════════════════════════════════════════════

@Route.get("/health")
def health(self: Handler):
    self._json({
        "ok": True, "version": VERSION,
        "portal_build": PORTAL_BUILD,
        "portal_features": list(PORTAL_FEATURES),
        "server_boot_at": SERVER_BOOT_AT,
        "note": "客户创作门户 · HTTP API",
        "portal_url": "/portal",
    })


@Route.get("/api/portal/version")
def portal_version(self: Handler):
    """门户版本与能力 — 前端启动时对齐，判定后台是否为最新代码。"""
    self._json({
        "ok": True,
        "portal_build": PORTAL_BUILD,
        "server_version": VERSION,
        "server_boot_at": SERVER_BOOT_AT,
        "features": list(PORTAL_FEATURES),
        "portal_url": "/portal",
    })

@Route.get("/api/dev/reload-token")
def dev_reload_token(self: Handler):
    """返回静态文件的最新修改时间戳，前端轮询判断是否需刷新。"""
    latest = 0.0
    for p in _DEV_WATCH_FILES:
        if p.exists():
            m = p.stat().st_mtime
            if m > latest:
                latest = m
    self._json({"token": latest})


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


# ═══════════════════════════════════════════════════════════════
# 客户门户 API（按照片分类资产）
# ═══════════════════════════════════════════════════════════════

@Route.get("/api/customer-portal/{cid}")
def customer_portal(self: Handler, cid: str):
    """返回客户门户数据：按每张参考照片分类展示关联的项目资产。"""
    from gaze_engine._shared.customer_db import get_customer, list_projects
    from asset_lib import customer_dir, customer_ref_photos_dir, project_dir, project_output_dir

    customer = get_customer(cid)
    if customer is None:
        return self._json({"ok": False, "error": f"客户 {cid} 不存在"}, status=404)

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    # 0. 先获取项目列表（后续步骤都需要）
    all_projects = list_projects(cid)

    # 1. 扫描参考照片（客户根目录 + 各项目目录）
    ref_dir = customer_ref_photos_dir(cid)
    photo_map: dict[str, dict] = {}  # name -> photo dict

    # 1a. 客户根目录参考素材
    if ref_dir.is_dir():
        for p in sorted(ref_dir.iterdir()):
            if p.suffix.lower() in exts:
                photo_map[p.name] = {
                    "name": p.name,
                    "url": f"/api/customer/photo-preview/{cid}/{p.name}",
                    "size": p.stat().st_size,
                    "projects": [],
                }

    # 1b. 各项目内的参考素材
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

    # 2. 扫描项目
    project_assets: list[dict] = []
    for proj in all_projects:
        pid = proj.get("project_id", "")
        if not pid:
            continue
        p_dir = project_dir(cid, pid)
        out_dir = project_output_dir(cid, pid)
        ref_photo = proj.get("reference_photo", "") or ""

        # 自动关联项目级参考素材（取第一张）
        if not ref_photo:
            proj_ref_dir = p_dir / "参考素材"
            if proj_ref_dir.is_dir():
                for f in sorted(proj_ref_dir.iterdir()):
                    if f.suffix.lower() in exts:
                        ref_photo = f.name
                        break

        # 收集项目输出文件
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

        # 收集计划文档
        plans: list[dict] = []
        plans_dir = p_dir / "计划文档"
        if plans_dir.is_dir():
            for f in sorted(plans_dir.iterdir()):
                if f.is_file():
                    plans.append({
                        "name": f.name,
                        "size": f.stat().st_size,
                    })

        # 收集调整历史中的 NL 备注
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

        # 将项目关联到对应的照片
        if ref_photo:
            for photo in photos:
                if photo["name"] == ref_photo:
                    photo["projects"].append(asset_entry)
                    break

    # 3. 提取工作台上下文
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


# ═══════════════════════════════════════════════════════════════
# POST 路由
# ═══════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════
# 认证 API
# ═══════════════════════════════════════════════════════════════

@Route.post("/api/auth/register")
def auth_register(self: Handler, body: bytes):
    """注册新客户账号。"""
    from gaze_engine._shared.customer_db import create_customer, get_customer
    data = self._read_body(body)
    name = (data.get("display_name") or "").strip()
    password = (data.get("password") or "").strip()
    if not name:
        return self._json({"ok": False, "error": "请输入客户名称"}, status=400)
    if not password or len(password) < 4:
        return self._json({"ok": False, "error": "密码至少4位"}, status=400)
    cid = create_customer(
        display_name=name,
        contact=data.get("contact", ""),
        preferred_species=data.get("preferred_species", "human"),
        breed=data.get("breed", ""),
        password=password,
    )
    self._json({"ok": True, "customer_id": cid, "customer": get_customer(cid)})


@Route.post("/api/auth/login")
def auth_login(self: Handler, body: bytes):
    """客户登录：验证密码，返回 token。"""
    from gaze_engine._shared.customer_db import (
        get_customer, verify_customer_password, create_auth_token,
        resolve_customer_login,
    )
    data = self._read_body(body)
    login_key = (data.get("customer_id") or "").strip()
    password = (data.get("password") or "").strip()
    if not login_key or not password:
        return self._json({"ok": False, "error": "缺少客户ID或密码"}, status=400)
    cid, resolve_err = resolve_customer_login(login_key)
    if resolve_err:
        return self._json({"ok": False, "error": resolve_err}, status=404)
    customer = get_customer(cid)
    if not customer:
        return self._json({"ok": False, "error": "客户不存在"}, status=404)
    if not verify_customer_password(cid, password):
        return self._json({"ok": False, "error": "密码错误"}, status=403)
    token = create_auth_token(cid)
    self._json({
        "ok": True,
        "token": token,
        "customer_id": cid,
        "customer": customer,
    })


@Route.post("/api/auth/verify")
def auth_verify(self: Handler, body: bytes):
    """验证 token 有效性，返回客户信息。"""
    from gaze_engine._shared.customer_db import verify_auth_token, get_customer
    data = self._read_body(body)
    token = (data.get("token") or "").strip()
    if not token:
        return self._json({"ok": False, "error": "缺少 token"}, status=400)
    cid = verify_auth_token(token)
    if not cid:
        return self._json({"ok": False, "error": "token 无效或已过期"}, status=403)
    customer = get_customer(cid)
    self._json({"ok": True, "customer_id": cid, "customer": customer})


# ═══════════════════════════════════════════════════════════════
# 门户创作 API（客户登录后使用）
# ═══════════════════════════════════════════════════════════════

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
    from gaze_engine._shared.slider_schema import SliderPacket
    from gaze_engine.delivery_pipeline import run_species_delivery

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


@Route.get("/api/portal/presets")
def portal_presets(self: Handler):
    """返回预设索引（仅 id/label/路径）；数值从 预设资产/ 按需调取，不下发 macro/pad。"""
    from asset_lib import ASSET_LIB, EMOTION_PACK_DIR, load_emotion_categories

    style_kind = {"human": "人格风格", "cat": "猫品种", "dog": "狗品种"}
    result = {"human": {"emotions": [], "styles": [], "emotion_groups": [], "emotion_categories": []},
              "cat": {"emotions": [], "styles": [], "emotion_groups": [], "emotion_categories": []},
              "dog": {"emotions": [], "styles": [], "emotion_groups": [], "emotion_categories": []}}

    for species in ("human", "cat", "dog"):
        emotions_dir = EMOTION_PACK_DIR / species
        if emotions_dir.is_dir():
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
                    result[species]["emotions"].append({
                        "id": preset_id,
                        "label": d.get("label") or d.get("emotion") or f.stem,
                        "emotion_id": d.get("emotion") or preset_id,
                        "category": d.get("category") or "",
                        "variant": d.get("variant") or "",
                        "aliases": d.get("aliases") or [],
                        "file": f"预设资产/情绪包/{species}/{f.relative_to(emotions_dir).as_posix()}",
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

    for species in ("human", "cat", "dog"):
        styles_dir = ASSET_LIB / "风格包" / species
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
                                "file": f"预设资产/风格包/{species}/{entry.name}/style.json",
                            })
                        except Exception:
                            pass

        result[species]["meta"] = {
            "emotions_dir": f"预设资产/情绪包/{species}/",
            "styles_dir": f"预设资产/风格包/{species}/",
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
    if species not in ("human", "cat", "dog") or not preset_id:
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


@Route.post("/api/portal/pomot/round1")
def portal_pomot_round1(self: Handler, body: bytes):
    """Pomot 第一轮：按钮 emotion → 路由 → 合成 → 管线 → 拼装（NL 可选，门户当前纯按钮）。"""
    from gaze_engine.pomot.pipeline import PomotPipeline
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
    # 手动序列化 dataclass 对象
    split = result["split"]
    route = result["route"]
    from gaze_engine.pomot.assembler import DiffusionPromptAssembler

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
    from gaze_engine._shared.slider_schema import SliderPacket
    from gaze_engine.pomot.pipeline import PomotPipeline
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
    from gaze_engine.pomot.assembler import DiffusionPromptAssembler

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


@Route.post("/api/portal/save")
def portal_save(self: Handler, body: bytes):
    """保存当前创作到客户项目。"""
    from gaze_engine._shared.customer_db import (
        get_customer, get_project, create_project, save_adjustment,
        save_workbench_context,
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

    # 无项目则创建
    if not pid:
        if not project_name:
            project_name = f"创作_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pid = create_project(cid, project_name, species=data.get("species", "human"))
        if not pid:
            return self._json({"ok": False, "error": "项目创建失败"}, status=500)

    # 保存调整记录
    ver = None
    if packet:
        ver = save_adjustment(cid, pid, packet, note=note or "手动保存")

    # 输出目录：不落盘 02 烘焙（即时编译）；清理历史遗留
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

    # 更新工作台上下文
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
    """上传照片到项目参考素材，并执行底膜检测。"""
    from asset_lib import customer_ref_photos_dir, project_dir
    from gaze_engine._shared.customer_db import get_project, update_project
    from gaze_engine._shared.species_detector import auto_detect_for_customer

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
    # 使用 ASCII 安全文件名，避免中文路径导致预览 404
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

    # 项目内也存一份
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

    det = auto_detect_for_customer(cid, data.get("species"))
    resp["detection"] = det.get("detection")
    resp["adjustments"] = det.get("adjustments")
    resp["saved_params"] = det.get("saved_params")
    self._json(resp)


@Route.post("/api/portal/calibrate-template")
def portal_calibrate_template(self: Handler, body: bytes):
    """手动标定：锚点 → 底膜模板参数 → 写入客户资产库。"""
    from asset_lib import project_dir, project_output_dir, customer_ref_photos_dir
    from gaze_engine._shared.customer_db import (
        get_project, update_customer, get_customer, _save_template_params,
    )
    from gaze_engine._shared.species_detector import anchors_to_template_adjustments
    from gaze_engine._shared.species_template import breed_template_ear_params

    DOG_BREED = "poodle_giant"

    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    species = (data.get("species") or "human").strip()
    anchors = data.get("anchors") or {}
    photo_name = (data.get("photo_name") or "").strip()

    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)
    if get_project(cid, pid) is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)
    if species not in ("human", "cat", "dog"):
        return self._json({"ok": False, "error": "无效 species"}, status=400)

    img_w = int(data.get("image_width") or 0)
    img_h = int(data.get("image_height") or 0)
    if (not img_w or not img_h) and photo_name:
        import cv2
        fp = customer_ref_photos_dir(cid) / photo_name
        if fp.is_file():
            im = cv2.imread(str(fp))
            if im is not None:
                img_h, img_w = im.shape[:2]

    try:
        adjustments = anchors_to_template_adjustments(anchors, img_w, img_h, species)
    except ValueError as e:
        return self._json({"ok": False, "error": str(e)}, status=400)

    ears_marked = bool(anchors.get("left_ear") and anchors.get("right_ear"))
    ear_source = "marked" if ears_marked else "breed_template"
    breed = (data.get("breed") or "").strip()
    if species in ("dog", "cat"):
        if not breed:
            breed = (get_customer(cid) or {}).get("breed", "")
        if species == "dog" and not breed:
            breed = DOG_BREED
        if not breed:
            return self._json({"ok": False, "error": "猫/狗标定须先选择品种"}, status=400)
    else:
        breed = ""

    # 眼/鼻来自标点；耳未标则用品种模板（巨型贵宾垂耳线条）
    customer_adj = {
        k: adjustments[k]
        for k in ("eye_distance", "eye_size", "eye_vertical", "pupil_slit_ratio")
        if k in adjustments
    }
    if ears_marked:
        for k in ("ear_droop", "ear_angle", "ear_size", "ear_position_x", "ear_position_y"):
            if k in adjustments:
                customer_adj[k] = adjustments[k]
    elif species in ("dog", "cat"):
        customer_adj.update(breed_template_ear_params(species, breed or None))

    saved = _save_template_params(cid, species, breed, customer_adj)
    update_customer(cid, preferred_species=species, breed=breed)

    preview_url = ""
    preview_base64 = ""
    preview_breed_base64 = ""
    preview_calibrated_base64 = ""
    preview_error = ""
    adjustment_diff: list = []
    breed_preview_url = ""
    calibrated_preview_url = ""
    if species == "dog":
        try:
            out = project_output_dir(cid, pid)
            out.mkdir(parents=True, exist_ok=True)
            dual = _dog_calibrate_previews(
                breed=breed or DOG_BREED,
                customer_adj=customer_adj,
                out_dir=out,
            )
            base_u = f"/api/customer-portal/{cid}/file/{pid}"
            breed_preview_url = f"{base_u}/{dual['breed_preview_file']}"
            calibrated_preview_url = f"{base_u}/{dual['calibrated_preview_file']}"
            preview_url = calibrated_preview_url
            preview_breed_base64 = dual["preview_breed_base64"]
            preview_calibrated_base64 = dual["preview_calibrated_base64"]
            preview_base64 = preview_calibrated_base64
            adjustment_diff = dual["adjustment_diff"]
            # 兼容旧路径
            (out / "底膜预览.png").write_bytes((out / dual["calibrated_preview_file"]).read_bytes())
        except Exception as e:
            preview_error = str(e)

    calib_doc = {
        "schema": "manual_calibration_v1",
        "method": "manual",
        "confidence": 1.0,
        "customer_id": cid,
        "project_id": pid,
        "species": species,
        "photo_name": photo_name,
        "image_size": [img_w, img_h],
        "anchors": anchors,
        "ears_marked": ears_marked,
        "ear_source": ear_source,
        "breed": breed,
        "breed_label": "巨型贵宾犬" if breed == DOG_BREED else breed,
        "adjustments": customer_adj,
        "saved_params": (saved or {}).get("params", {}),
        "preview_url": preview_url,
        "breed_preview_url": breed_preview_url,
        "calibrated_preview_url": calibrated_preview_url,
        "preview_base64": preview_base64,
        "preview_breed_base64": preview_breed_base64,
        "preview_calibrated_base64": preview_calibrated_base64,
        "preview_error": preview_error,
        "adjustment_diff": adjustment_diff,
        "membrane_note": "左=AKC标准巨型贵宾 · 右=标定后 · 红=眼眶 · 绿上弧=眉 · 绿侧下=垂耳",
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    calib_path = project_dir(cid, pid) / "手动标定.json"
    calib_path.write_text(json.dumps(calib_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    self._json({
        "ok": True,
        "method": "manual",
        "confidence": 1.0,
        "breed": breed,
        "breed_label": calib_doc["breed_label"],
        "adjustments": customer_adj,
        "saved_params": (saved or {}).get("params", {}),
        "preview_url": preview_url,
        "breed_preview_url": breed_preview_url,
        "calibrated_preview_url": calibrated_preview_url,
        "preview_base64": preview_base64,
        "preview_breed_base64": preview_breed_base64,
        "preview_calibrated_base64": preview_calibrated_base64,
        "preview_error": preview_error,
        "adjustment_diff": adjustment_diff,
        "membrane_note": calib_doc["membrane_note"],
        "calibration_file": str(calib_path),
    })


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
    name_map = {
        "breed": "底膜预览_品种默认.png",
        "calibrated": "底膜预览_标定后.png",
    }
    preview_path = out / name_map.get(variant, name_map["calibrated"])

    if not preview_path.is_file():
        calib_path = project_dir(cid, pid) / "手动标定.json"
        if not calib_path.is_file():
            return self.send_error(404)
        try:
            calib = json.loads(calib_path.read_text(encoding="utf-8"))
        except Exception:
            return self.send_error(404)
        if (calib.get("species") or "").strip().lower() != "dog":
            return self.send_error(404)
        try:
            out.mkdir(parents=True, exist_ok=True)
            _dog_calibrate_previews(
                breed=calib.get("breed") or "poodle_giant",
                customer_adj=calib.get("adjustments") or {},
                out_dir=out,
            )
        except Exception:
            return self.send_error(500)
        preview_path = out / name_map.get(variant, name_map["calibrated"])
        if not preview_path.is_file():
            return self.send_error(404)

    data = preview_path.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", "image/png")
    self.send_header("Content-Length", str(len(data)))
    self.send_header("Cache-Control", "no-store")
    self.end_headers()
    self.wfile.write(data)


_SPECIES_LABELS = {"dog": "🐶 狗", "cat": "🐱 猫", "human": "🙂 人"}
_MEMBRANE_LABELS = {"dog": "狗工程底膜", "cat": "猫工程底膜", "human": "人类工程底膜"}


def _detect_baked_pipeline(baked: dict | None) -> str:
    """返回 baked 实际走的管线：dog / cat / human / human_legacy / none"""
    if not baked:
        return "none"
    schema = str(baked.get("schema_version") or "")
    sp = (baked.get("species") or "").strip().lower()
    if sp == "dog" or "baked-dog" in schema:
        return "dog"
    if sp == "cat" or "baked-cat" in schema:
        return "cat"
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

    if sp == "dog":
        if baked_pipe == "dog" and video_sp == "dog":
            status, is_valid = "ok", True
        elif video_sp == "dog" and video_exists:
            status, is_valid = "ok", True
        elif baked_pipe == "dog" and video_exists and not video_sp:
            status, warning = "video_unverified", "生成数据是狗管线，但视频未校验 — 请第④步重新渲染"
            action = "render"
        elif baked_pipe == "none":
            status = "pending"
            warning = ""
            action = ""
        elif baked_pipe in ("human_legacy", "human", "unknown"):
            status = "wrong_baked"
            warning = "⚠ 保存的生成数据是人类管线，不是狗底膜 — 请重新生成"
            action = "regenerate"
        elif video_sp and video_sp != "dog":
            status = "wrong_video"
            warning = f"⚠ 视频底膜是「{_MEMBRANE_LABELS.get(video_sp, video_sp)}」，不是狗底膜"
            action = "regenerate"
        elif video_exists and not video_sp:
            status = "video_unverified"
            warning = "⚠ 已有视频但未标记物种，可能是旧版人类底膜 — 请重新生成并渲染"
            action = "regenerate"
    elif sp == "cat":
        if baked_pipe == "cat" and (video_sp == "cat" or (video_exists and not video_sp and baked_pipe == "cat")):
            status, is_valid = "ok", video_sp == "cat"
        elif baked_pipe in ("human_legacy", "human", "unknown", "none"):
            status, warning, action = "wrong_baked", "⚠ 猫项目使用了人类旧管线", "regenerate"
    else:
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
            "dog": "狗管线 ✓", "cat": "猫管线 ✓", "human": "人类管线",
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


@Route.get("/api/portal/project/state")
def portal_project_state(self: Handler):
    """恢复项目进度：标定、管线中间产物、扩散引擎两件套。"""
    from urllib.parse import urlparse, parse_qs
    from asset_lib import project_dir, project_output_dir
    from gaze_engine._shared.customer_db import (
        get_project, get_template_params, get_customer,
    )

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
    calib_path = p_dir / "手动标定.json"
    if calib_path.is_file():
        try:
            calibration = json.loads(calib_path.read_text(encoding="utf-8"))
        except Exception:
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
    """分步保存项目进度到客户资产库。"""
    from gaze_engine._shared.customer_db import save_adjustment, get_project, update_project
    from asset_lib import project_dir, project_output_dir

    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    step = (data.get("step") or "").strip()
    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)
    if get_project(cid, pid) is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)

    p_dir = project_dir(cid, pid)
    steps_dir = p_dir / "流程步骤"
    steps_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    step_file = steps_dir / f"{step}_{ts}.json"
    snapshot = {k: data[k] for k in data if k not in ("customer_id", "project_id")}
    snapshot["step"] = step
    snapshot["saved_at"] = datetime.now(timezone.utc).isoformat()
    step_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ver = None
    packet = data.get("packet")
    if packet and step in ("pipeline", "final", "export"):
        ver = save_adjustment(cid, pid, packet, note=data.get("note") or f"步骤:{step}")

    out = project_output_dir(cid, pid)
    out.mkdir(parents=True, exist_ok=True)
    if packet:
        (out / "01_滑杆包.json").write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _portal_purge_baked_files(out)
    metronome = data.get("metronome", "")
    if metronome:
        (out / "05_扩散节拍表.txt").write_text(metronome, encoding="utf-8")
    prompt_04 = data.get("prompt_04", "")
    if prompt_04:
        (out / "04_Prompt.txt").write_text(prompt_04, encoding="utf-8")
    if data.get("photo_name"):
        update_project(cid, pid, reference_photo=data["photo_name"])
    if data.get("species"):
        update_project(cid, pid, species=data["species"])
    wan_pos = data.get("wan_positive_clip") or data.get("wan_positive") or ""
    wan_neg = data.get("wan_negative_clip") or data.get("wan_negative") or ""
    if wan_pos:
        (out / "wan_positive.txt").write_text(wan_pos, encoding="utf-8")
    if wan_neg:
        (out / "wan_negative.txt").write_text(wan_neg, encoding="utf-8")

    self._json({"ok": True, "step": step, "step_file": str(step_file), "version": ver})


@Route.post("/api/portal/render-membrane")
def portal_render_membrane(self: Handler, body: bytes):
    """标定后一键渲染狗工程底膜 MP4（默认委屈幼犬 preset + 客户巨型贵宾模板）。"""
    from asset_lib import project_output_dir
    from gaze_engine._shared.customer_db import get_project
    from gaze_engine.delivery_pipeline import run_species_delivery
    from gaze_engine.dog.presets import dog_packet_from_file

    data = self._read_body(body)
    cid = (data.get("customer_id") or "").strip()
    pid = (data.get("project_id") or "").strip()
    if not cid or not pid:
        return self._json({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)

    proj = get_project(cid, pid)
    if proj is None:
        return self._json({"ok": False, "error": "项目不存在"}, status=404)

    species = (proj.get("species") or "dog").strip().lower()
    if species != "dog":
        return self._json({"ok": False, "error": "render-membrane 仅支持狗项目"}, status=400)

    preset_name = (data.get("preset") or "委屈·幼犬眼").strip()
    try:
        from gaze_engine.dog.presets import dog_packet_from_file

        packet = dog_packet_from_file(preset_name)
    except KeyError as e:
        return self._json({"ok": False, "error": str(e)}, status=400)

    pkt_dict = packet.to_dict()
    pkt_dict["species"] = "dog"

    try:
        breed = _resolve_breed_id(cid)
        baked, _, _, _ = run_species_delivery(
            packet, "dog", breed_id=breed, style_id=breed,
        )
    except Exception as e:
        return self._json({"ok": False, "error": f"狗管线失败: {e}"}, status=500)

    out = project_output_dir(cid, pid)
    out.mkdir(parents=True, exist_ok=True)
    _portal_purge_baked_files(out)

    try:
        video_path, frames, render_info = _render_opencv_video(
            baked=baked, species="dog", customer_id=cid,
        )
    except Exception as e:
        return self._json({"ok": False, "error": str(e)}, status=500)

    video_name = "03_工程底模.mp4"
    meta_name = "03_工程底模.meta.json"
    dest = out / video_name
    dest.write_bytes(video_path.read_bytes())
    (out / meta_name).write_text(
        json.dumps(render_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    video_url = f"/api/customer-portal/{cid}/file/{pid}/{video_name}"
    self._json({
        "ok": True,
        "video_url": video_url,
        "frames": frames,
        "path": str(dest),
        "preset": preset_name,
        "baked_json": baked,
        "baked_schema": baked.get("schema_version"),
        "baked_species": baked.get("species"),
        **render_info,
    })


@Route.post("/api/portal/render-preview")
def portal_render_preview(self: Handler, body: bytes):
    """渲染 OpenCV 工程底膜视频，保存到项目输出目录。"""
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
        video_path, frames, render_info = _render_opencv_video(
            baked=baked,
            species=project_species,
            customer_id=cid,
            breed_id=req_breed,
        )
    except Exception as e:
        return self._json({"ok": False, "error": str(e)}, status=500)

    video_name = "03_工程底模.mp4"
    meta_name = "03_工程底模.meta.json"
    if cid and pid:
        from asset_lib import project_output_dir
        from gaze_engine._shared.customer_db import get_project
        if get_project(cid, pid):
            out = project_output_dir(cid, pid)
            out.mkdir(parents=True, exist_ok=True)
            _portal_purge_baked_files(out)
            dest = out / video_name
            dest.write_bytes(video_path.read_bytes())
            video_path = dest
            video_url = f"/api/customer-portal/{cid}/file/{pid}/{video_name}"
            (out / meta_name).write_text(
                json.dumps(render_info, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            snap = render_info.get("first_frame_preview") or ""
            if snap and Path(snap).is_file():
                (out / "底膜预览_动画首帧.png").write_bytes(Path(snap).read_bytes())
        else:
            video_url = "/control_video.mp4"
    else:
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
    from gaze_engine.pomot.assembler import DiffusionPromptAssembler
    from asset_lib import project_output_dir
    from gaze_engine._shared.customer_db import get_project, get_customer

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
        _portal_purge_baked_files(out)
        prompt_file = out / "04_Prompt.txt"
        prompt_file.write_text(prompt_04, encoding="utf-8")
        (out / "wan_positive.txt").write_text(wan_clip["positive"], encoding="utf-8")
        (out / "wan_negative.txt").write_text(wan_clip["negative"], encoding="utf-8")
        prompt_path = str(prompt_file)
        try:
            video_path_obj, _, render_info = _render_opencv_video(
                baked=baked, species=species, customer_id=cid,
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
        from gaze_engine._shared.project_archive import (
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
    from gaze_engine._shared.customer_db import get_project, save_adjustment
    from gaze_engine._shared.project_archive import (
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


# ── 辅助 ─────────────────────────────────────────────────────

_DIFFUSION_VIDEO_NAME = "03_工程底模.mp4"
_DIFFUSION_PROMPT_NAME = "04_Prompt.txt"


def _resolve_breed_id(customer_id: str, species: str = "dog", fallback: str = "") -> str:
    if not customer_id:
        return fallback or ("poodle_giant" if species == "dog" else "")
    from gaze_engine._shared.customer_db import get_customer, get_template_breed

    saved = get_template_breed(customer_id)
    if saved:
        return saved
    cust = (get_customer(customer_id) or {}).get("breed") or ""
    if cust:
        return cust
    if species == "dog":
        return fallback or "poodle_giant"
    return fallback


def _membrane_renderer(
    species: str,
    customer_id: str = "",
    template=None,
    breed_id: str = "",
):
    """按物种与模板构造 OpenCV 线条渲染器。"""
    from gaze_engine._shared.customer_db import get_effective_template
    from gaze_engine._shared.species_template import (
        SpeciesTemplate,
        template_to_renderer_constants,
    )

    sp = (species or "human").strip().lower()
    if template is None:
        template = get_effective_template(customer_id) if customer_id else None
    elif isinstance(template, dict):
        template = SpeciesTemplate.from_dict(template)
    bid = breed_id or (_resolve_breed_id(customer_id, sp) if sp == "dog" else "")
    constants = template_to_renderer_constants(sp, template, breed_id=bid or None)
    if sp == "cat":
        from gaze_engine.cat.affine_renderer import CatAffineRenderer
        return CatAffineRenderer(constants)
    if sp == "dog":
        from gaze_engine.dog.affine_renderer import DogAffineRenderer
        return DogAffineRenderer(constants)
    from gaze_engine.human.affine_renderer import AffineRenderer
    return AffineRenderer(constants)


def _neutral_channel_frame(species: str) -> dict[str, float]:
    """静态底膜预览用的中性通道值（展示模板几何，无表情动画）。"""
    frame = {k: 0.0 for k in _species_channel_keys(species)}
    if (species or "").strip().lower() == "dog":
        # eyebrow=0.5 → 垂耳处于品种模板中性位，而非动画极限
        frame["eyebrow"] = 0.5
    return frame


def _write_membrane_preview_png(
    species: str,
    path: Path,
    *,
    customer_id: str = "",
    template=None,
    breed_id: str = "",
) -> None:
    """渲染单帧 OpenCV 线条图并写入 PNG。"""
    import cv2

    sp = (species or "human").strip().lower()
    renderer = _membrane_renderer(sp, customer_id, template=template, breed_id=breed_id)
    neutral = _neutral_channel_frame(sp)
    # 狗 MP4 走 render_frame(690×361)；标定预览必须同路径，否则眼位与 MP4 不一致
    if sp == "dog":
        frame = renderer.render_frame(neutral)
    else:
        frame_fn = getattr(renderer, "render_preview_frame", None)
        if callable(frame_fn):
            frame = frame_fn(neutral)
        else:
            frame = renderer.render_frame(neutral)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), frame):
        raise RuntimeError(f"无法写入底膜预览: {path}")


def _dog_calibrate_previews(
    *,
    breed: str,
    customer_adj: dict[str, float],
    out_dir: Path,
) -> dict[str, Any]:
    """生成狗标定双预览：品种默认 vs 标定后，并返回微调对比表。"""
    import base64
    from gaze_engine._shared.species_template import (
        SpeciesTemplate,
        breed_baseline_template,
        apply_customer_adjustments,
        diff_template_params,
    )
    from gaze_engine.dog.breeds import get_dog_breed

    breed = breed or "poodle_giant"
    breed_info = get_dog_breed(breed)
    breed_tpl = breed_baseline_template("dog", breed)
    final_tpl = apply_customer_adjustments(breed_tpl, customer_adj)
    diff = diff_template_params(breed_tpl, final_tpl, "dog")

    breed_path = out_dir / "底膜预览_品种默认.png"
    custom_path = out_dir / "底膜预览_标定后.png"
    _write_membrane_preview_png("dog", breed_path, template=breed_tpl, breed_id=breed)
    _write_membrane_preview_png("dog", custom_path, template=final_tpl, breed_id=breed)

    def _b64(p: Path) -> str:
        return base64.b64encode(p.read_bytes()).decode("ascii")

    return {
        "breed_template": breed_tpl.to_dict(),
        "calibrated_template": final_tpl.to_dict(),
        "adjustment_diff": diff,
        "breed_preview_file": breed_path.name,
        "calibrated_preview_file": custom_path.name,
        "preview_breed_base64": _b64(breed_path),
        "preview_calibrated_base64": _b64(custom_path),
        "breed_reference": breed_info.get("reference", ""),
        "breed_label": breed_info.get("label", breed),
    }


def _species_channel_keys(species: str) -> list[str]:
    if species == "cat":
        from gaze_engine.cat.envelope_compile import CAT_CHANNELS
        return list(CAT_CHANNELS)
    if species == "dog":
        from gaze_engine.dog.envelope_compile import DOG_CHANNELS
        return list(DOG_CHANNELS)
    from gaze_engine.human.affine_renderer import CANONICAL_KEYS
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


_RENDERER_NAMES = {"human": "AffineRenderer", "dog": "DogAffineRenderer", "cat": "CatAffineRenderer"}


def _render_opencv_video(
    *,
    packet_dict: dict | None = None,
    baked: dict | None = None,
    species: str = "human",
    customer_id: str = "",
    breed_id: str = "",
) -> tuple[Path, int, dict]:
    """从 baked 的 channel_tracks 渲染 OpenCV 工程底膜 MP4。"""
    import cv2
    import shutil
    import subprocess
    from gaze_engine._shared.slider_schema import SliderPacket
    from gaze_engine.delivery_pipeline import run_species_delivery
    from gaze_engine._shared.customer_db import get_effective_template, get_template_breed
    from gaze_engine._shared.species_template import template_to_renderer_constants

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
    template = get_effective_template(customer_id) if customer_id else None
    bid = (breed_id or "").strip()
    if customer_id and sp in ("dog", "cat"):
        saved_breed = get_template_breed(customer_id)
        if saved_breed and bid and saved_breed != bid:
            raise ValueError(
                f"渲染品种「{bid}」与标定品种「{saved_breed}」不一致，请回第①步重新标定"
            )
        bid = bid or saved_breed or _resolve_breed_id(customer_id, sp)
    elif sp == "dog":
        bid = bid or _resolve_breed_id(customer_id, "dog")
    constants = template_to_renderer_constants(sp, template, breed_id=bid or None)

    if sp == "cat":
        from gaze_engine.cat.affine_renderer import CatAffineRenderer
        renderer = CatAffineRenderer(constants)
    elif sp == "dog":
        from gaze_engine.dog.affine_renderer import DogAffineRenderer
        renderer = DogAffineRenderer(constants)
    else:
        from gaze_engine.human.affine_renderer import AffineRenderer
        renderer = AffineRenderer(constants)

    render_info = {
        "species": sp,
        "membrane_type": _MEMBRANE_LABELS.get(sp, sp),
        "renderer": _RENDERER_NAMES.get(sp, "AffineRenderer"),
        "frame_count": fc,
        "channel_source": "baked.channel_tracks" if baked and baked.get("channel_tracks") else "species_delivery",
        "baked_revision": (baked or {}).get("revision", ""),
        "baked_mood": (baked or {}).get("mood", ""),
    }

    CONTROL_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    frames_dir = CONTROL_VIDEO_DIR / "_portal_frames"
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

    out_path = CONTROL_VIDEO_DIR / "control_video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "image2", "-r", "30",
        "-i", str(frames_dir / "f_%04d.png"),
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        str(out_path),
    ], capture_output=True, check=True)
    preview_snap = CONTROL_VIDEO_DIR / "_portal_first_frame.png"
    if first_frame_png and first_frame_png.is_file():
        shutil.copy2(first_frame_png, preview_snap)
        render_info["first_frame_preview"] = str(preview_snap)
    shutil.rmtree(frames_dir)
    return out_path, fc, render_info


def main() -> int:
    host, port = "0.0.0.0", PORT
    url = f"http://127.0.0.1:{port}/portal"
    for _ in range(3):
        try:
            httpd = ThreadingHTTPServer((host, port), Handler)
            break
        except OSError as e:
            if e.errno != 98:
                raise
            import subprocess as _sp
            _sp.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
            time.sleep(0.5)
    else:
        raise RuntimeError(f"端口 {port} 无法绑定")
    print(f"🎨 客户创作门户 v{VERSION}: {url}")
    print(f"   build={PORTAL_BUILD}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
