#!/usr/bin/env python3
"""客户创作门户 · HTTP 后端 — 框架核心 + 子模块路由注册。"""
from __future__ import annotations

import json, sys, time
from datetime import datetime, timezone
from urllib.parse import unquote
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent       # 项目根目录
PKG = ROOT                                           # 项目根目录
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

PORT = 8765
VERSION = 13
WORKBENCH_SVC = Path(__file__).resolve().parent       # portal/
PORTAL_HTML = WORKBENCH_SVC / "客户门户.html"
PORTAL_JS = WORKBENCH_SVC / "static" / "portal.js"
CONTROL_VIDEO_DIR = ROOT / "tools" / "04_缓存数据" / "preview_cache"
CONTROL_VIDEO_PATH = CONTROL_VIDEO_DIR / "control_video.mp4"

# 门户能力清单 — /api/portal/version 返回
PORTAL_FEATURES = (
    "calibrate_preview",
    "membrane_preview_api",
    "render_membrane",
    "login_by_name",
    "project_archive",
    "overlay_preview",
)

# 开发热重载监听文件
_DEV_WATCH_FILES = (
    Path(__file__).resolve(),
    PORTAL_HTML,
    PORTAL_JS,
)


def _file_mtime_token(*paths: Path) -> str:
    latest = 0.0
    for p in paths:
        if p.is_file():
            latest = max(latest, p.stat().st_mtime)
    return str(int(latest)) if latest else "0"


PORTAL_BUILD = _file_mtime_token(Path(__file__).resolve(), PORTAL_HTML, PORTAL_JS)
SERVER_BOOT_AT = datetime.now(timezone.utc).isoformat()


def _inject_portal_html(raw: str) -> str:
    return (
        raw.replace("__PORTAL_BUILD__", PORTAL_BUILD)
        .replace("v20260527e", PORTAL_BUILD)
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
    _table: dict[str, dict[str, callable]] = {}

    @classmethod
    def get(cls, path: str):
        def wrapper(fn):
            cls._table.setdefault("GET", {})[path] = fn
            return fn
        return wrapper

    @classmethod
    def post(cls, path: str):
        def wrapper(fn):
            cls._table.setdefault("POST", {})[path] = fn
            return fn
        return wrapper

    @classmethod
    def match(cls, method: str, path: str) -> tuple[callable | None, dict]:
        handlers = cls._table.get(method, {})
        if path in handlers:
            return handlers[path], {}
        for pattern, fn in handlers.items():
            import re
            m = re.fullmatch(pattern.replace("{cid}", r"([^/]+)").replace("{pid}", r"([^/]+)").replace("{name}", r"(.+)"), path)
            if m:
                keys = [k for k in ("cid", "pid", "name") if f"{{{k}}}" in pattern]
                return fn, dict(zip(keys, m.groups()))
        return None, {}


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
# 核心 GET 路由
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


# ═══════════════════════════════════════════════════════════════
# 导入子模块 → 触发路由注册
# ═══════════════════════════════════════════════════════════════

import serve_auth       # noqa: F401, E402
import serve_customer   # noqa: F401, E402
import serve_portal     # noqa: F401, E402


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

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
