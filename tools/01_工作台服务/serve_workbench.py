#!/usr/bin/env python3
"""能量工作台 HTTP 服务：静态页 + 全管线 API（NL→滑杆→包络→真人→平庸→烘焙→扩散节拍）。
替代 ComfyUI 节点链。"""
from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # tools/
PKG = ROOT.parent  # 项目根目录
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

PORT = 8765
API_VERSION = 11  # + NL-to-packet + metronome 导出

CONTROL_VIDEO_DIR = ROOT / "04_缓存数据" / "preview_cache"
CONTROL_VIDEO_NAME = "control_video.mp4"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        p = self.path.split("?", 1)[0]
        if p.endswith((".html", ".js", ".json", ".png", ".jpg", ".mp4")):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    # ═══════════════════════════════════════════════════════
    # GET
    # ═══════════════════════════════════════════════════════
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0].rstrip("/")
        if path in ("/health", "/api/health"):
            self._json_response({
                "ok": True,
                "version": API_VERSION,
                "note": "ecursor 能量工作台 · 全管线 API（NL→滑杆→烘焙→扩散节拍）",
                "endpoints": [
                    "GET  /health",
                    "GET  /control_surface.json",
                    "GET  /workbench_context.json",
                    "GET  /persona_matrix.json",
                    "GET  /api/asset-browser",
                    "POST /api/nl-to-packet",
                    "POST /api/run-pipeline",
                    "POST /api/asset-load-baked",
                    "POST /api/export-metronome",
                    "POST /save_packet",
                    "POST /save_context",
                    "POST /render_control_video",
                ],
            })
            return
        if path == "/control_surface.json":
            from gaze_engine.control_surface import export_workbench_json
            self._json_response(export_workbench_json())
            return
        if path == "/workbench_context.json":
            self._json_response(self._load_context())
            return
        if path == "/dense04.json":
            self._json_response(self._load_dense04())
            return
        if path == "/control_video.mp4":
            self._serve_control_video()
            return
        if path == "/persona_matrix.json":
            matrix_path = PKG / "gaze_engine" / "persona_matrix.json"
            if matrix_path.exists():
                self._json_response(json.loads(matrix_path.read_text("utf-8")))
            else:
                self.send_error(404, "persona_matrix.json not found")
            return
        if path == "/api/asset-browser":
            self._asset_browser()
            return
        super().do_GET()

    # ═══════════════════════════════════════════════════════
    # POST
    # ═══════════════════════════════════════════════════════
    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0].rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            if path == "/save_packet":
                self._save_packet(body)
            elif path == "/save_context":
                self._save_context(body)
            elif path in ("/compile_dense04", "/compile_pipeline"):
                self._compile_pipeline(body)
            elif path == "/render_control_video":
                self._render_control_video(body)
            elif path == "/persona_matrix.json":
                self._save_persona_matrix(body)
            elif path == "/api/nl-to-packet":
                self._nl_to_packet(body)
            elif path == "/api/run-pipeline":
                self._run_full_pipeline(body)
            elif path == "/api/export-metronome":
                self._export_metronome(body)
            elif path == "/api/asset-load-baked":
                self._asset_load_baked(body)
            else:
                print(f"[workbench] 未知 POST 路径: {path!r}", flush=True)
                self.send_error(404)
        except Exception as e:
            self.send_error(400, str(e))

    # ═══════════════════════════════════════════════════════
    # 控制视频（待仿射重建）
    # ═══════════════════════════════════════════════════════
    # 旧版 line_drawer 已删除。
    # 新版 affine_renderer 重建后此端点复活。
    def _render_control_video(self, body: bytes) -> None:
        self._json_response({
            "ok": False,
            "note": "渲染引擎重建中（affine_renderer 替代 line_drawer），暂不可用",
        })

    def _serve_control_video(self) -> None:
        """GET /control_video.mp4 — 直接服务视频文件。"""
        p = CONTROL_VIDEO_DIR / CONTROL_VIDEO_NAME
        if not p.is_file():
            self.send_error(404, "尚未生成控制视频，请先点「渲染 2D 控制流」")
            return
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    # ═══════════════════════════════════════════════════════
    # 管线编译
    # ═══════════════════════════════════════════════════════
    def _load_context(self) -> dict:
        from gaze_engine.workbench_context import read_workbench_context
        return read_workbench_context()

    def _compile_pipeline_all(self, pkt_dict: dict) -> dict:
        from gaze_engine.envelope_compile import (
            channels_from_packet,
            export_envelope_series,
            make_delivery_stub,
        )
        from gaze_engine.human_prior import apply_human_prior
        from gaze_engine.packet_finalize import finalize_packet
        from gaze_engine.pulse_quality import fix_pulse_quality
        from gaze_engine.slider_schema import SliderPacket

        pkt, fin_rep = finalize_packet(SliderPacket.from_dict(pkt_dict))
        env_doc = export_envelope_series(pkt)
        fc = int(env_doc.get("frame_count") or 150)
        fps = int(env_doc.get("fps") or 30)
        ch_env = channels_from_packet(pkt, fc)
        stub = make_delivery_stub(pkt, ch_env, frame_count=fc, label=pkt.emotion or "")
        if fin_rep.fixes:
            stub["_finalize_fixes"] = fin_rep.fixes

        ch_human, prior_rep = apply_human_prior(ch_env, pkt, stub, frame_count=fc, fps=fps)
        ch_quality, pq_rep = fix_pulse_quality(ch_human, pkt, stub, frame_count=fc)

        def _stage(channels: dict, *, extra: dict | None = None) -> dict:
            base = {"frame_count": fc, "fps": fps, "channels": channels}
            if extra:
                base.update(extra)
            return base

        return {
            "source": "compile",
            "emotion": pkt.emotion or "",
            "frame_count": fc,
            "fps": fps,
            "envelope": env_doc.get("envelope") or [],
            "stages": {
                "envelope": _stage(ch_env),
                "human": _stage(ch_human, extra={"prior_report": prior_rep.to_dict()}),
                "quality": _stage(
                    ch_quality,
                    extra={
                        "prior_report": prior_rep.to_dict(),
                        "pulse_quality_report": pq_rep.to_dict(),
                    },
                ),
            },
        }

    def _compile_payload(self, pkt_dict: dict) -> dict:
        full = self._compile_pipeline_all(pkt_dict)
        env = full["stages"]["envelope"]
        return {
            "source": full["source"],
            "emotion": full["emotion"],
            "frame_count": full["frame_count"],
            "fps": full["fps"],
            "envelope": full["envelope"],
            "channels": env["channels"],
        }

    def _load_dense04(self) -> dict:
        from gaze_engine.pipeline_io import F_DENSE_ENV, read_dense
        from asset_lib import cmd_dir
        p = cmd_dir() / F_DENSE_ENV
        if not p.is_file():
            return {"error": "missing", "path": str(p)}
        channels, pkt, _ = read_dense(str(p))
        env = {}
        env_p = cmd_dir() / "03_能量包络.json"
        if env_p.is_file():
            env = json.loads(env_p.read_text(encoding="utf-8"))
        return {
            "source": "file",
            "emotion": pkt.emotion or "",
            "frame_count": int(env.get("frame_count") or 150),
            "fps": int(env.get("fps") or 30),
            "envelope": env.get("envelope") or [],
            "channels": channels,
            "path": str(p),
        }

    def _json_response(self, data: dict, *, status: int = 200) -> None:
        out = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def _save_packet(self, body: bytes) -> None:
        from gaze_engine.envelope_compile import channels_from_packet, make_delivery_stub
        from gaze_engine.human_prior import apply_human_prior
        from gaze_engine.pipeline_io import F_DENSE_PRIOR, F_DENSE_QUALITY, cmd_dir, write_dense
        from gaze_engine.pulse_quality import fix_pulse_quality
        from gaze_engine.slider_schema import SliderPacket
        from gaze_engine.workbench_io import finalize_and_write_l1, read_slider_packet, write_slider_packet

        pkt = SliderPacket.from_dict(json.loads(body.decode("utf-8")))
        p01 = write_slider_packet(pkt)
        p_l1 = finalize_and_write_l1(pkt)
        pkt_l1, _ = read_slider_packet(str(p_l1))
        ch_env = channels_from_packet(pkt_l1)
        stub = make_delivery_stub(pkt_l1, ch_env)
        root = cmd_dir()
        p04 = write_dense(ch_env, packet=pkt_l1, stub=stub)
        ch_human, _ = apply_human_prior(ch_env, pkt_l1, stub)
        p05 = write_dense(ch_human, packet=pkt_l1, stub=stub, path=root / F_DENSE_PRIOR)
        ch_quality, _ = fix_pulse_quality(ch_human, pkt_l1, stub)
        p06 = write_dense(ch_quality, packet=pkt_l1, stub=stub, path=root / F_DENSE_QUALITY)
        self._json_response({
            "ok": True,
            "path": str(p01),
            "l1_path": str(p_l1),
            "dense04_path": str(p04),
            "dense05_path": str(p05),
            "dense06_path": str(p06),
            "note": "已写 01 + 02_L1 + 04/05/06 全量",
        })

    def _compile_pipeline(self, body: bytes) -> None:
        pkt_dict = json.loads(body.decode("utf-8"))
        self._json_response(self._compile_pipeline_all(pkt_dict))

    def _save_context(self, body: bytes) -> None:
        from gaze_engine.workbench_context import write_workbench_context
        data = json.loads(body.decode("utf-8"))
        p = write_workbench_context(
            natural_language=data.get("natural_language"),
            energy_map_note=data.get("energy_map_note") or data.get("prompt"),
            knowledge_base=data.get("knowledge_base"),
        )
        nl = (data.get("natural_language") or "").strip()
        if nl:
            from gaze_engine.pipeline_io import F_NL, cmd_dir
            (cmd_dir() / F_NL).write_text(nl + "\n", encoding="utf-8")
        self._json_response({"ok": True, "path": str(p)})

    def _save_persona_matrix(self, body: bytes) -> None:
        """POST /persona_matrix.json — 保存人格矩阵的修改。"""
        try:
            data = json.loads(body.decode("utf-8"))
            action = data.get("action")
            if action == "save":
                persona_id = data.get("persona_id")
                persona_data = data.get("data")
                if not persona_id or not persona_data:
                    self._json_response({"ok": False, "error": "缺少 persona_id 或 data"})
                    return
                matrix_path = PKG / "gaze_engine" / "persona_matrix.json"
                if not matrix_path.exists():
                    self._json_response({"ok": False, "error": "persona_matrix.json 不存在"})
                    return
                matrix = json.loads(matrix_path.read_text("utf-8"))
                if persona_id not in matrix.get("personas", {}):
                    self._json_response({"ok": False, "error": f"未知人格: {persona_id}"})
                    return
                matrix["personas"][persona_id] = persona_data
                matrix_path.write_text(
                    json.dumps(matrix, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                self._json_response({"ok": True})
            else:
                self._json_response({"ok": False, "error": f"未知 action: {action}"})
        except Exception as e:
            self._json_response({"ok": False, "error": str(e)})

    # ═══════════════════════════════════════════════════════
    # API: NL → SliderPacket（AI Agent 主入口）
    # ═══════════════════════════════════════════════════════
    def _nl_to_packet(self, body: bytes) -> None:
        """POST /api/nl-to-packet — 自然语言 → 滑杆包 + 回复。
        
        请求体: {"nl": "施压凝视，更冷更钉", "knowledge_base": "...", "model": "..."}
        返回: {"ok": true, "packet": {...}, "reply": "...", "meta": {...}}
        """
        data = json.loads(body.decode("utf-8"))
        nl = (data.get("nl") or "").strip()
        if not nl:
            self._json_response({"ok": False, "error": "缺少 nl"}, status=400)
            return
        from gaze_engine.llm_openai import chatgpt_customer_nl, openai_configured
        from gaze_engine.nl_to_packet import packet_from_natural_language
        from gaze_engine.nl_intent import INTENT_APPLY

        kb = data.get("knowledge_base") or ""
        model = data.get("model") or ""
        use_llm = data.get("use_llm", True)

        if use_llm and openai_configured():
            result = chatgpt_customer_nl(
                nl,
                knowledge_base=kb,
                model=model or None,
            )
        else:
            pkt = packet_from_natural_language(nl, use_llm=False)
            from gaze_engine.nl_intent import CustomerNLResult, INTENT_APPLY
            result = CustomerNLResult(
                intent=INTENT_APPLY,
                reply=f"【已生成】预设「{pkt.emotion}」（关键词回退）",
                packet=pkt,
                meta={"intent_source": "keyword"},
            )

        if result.intent != INTENT_APPLY or result.packet is None:
            self._json_response({
                "ok": True,
                "intent": "consult",
                "reply": result.reply,
                "packet": None,
            })
            return

        self._json_response({
            "ok": True,
            "intent": "apply",
            "reply": result.reply,
            "packet": result.packet.to_dict(),
            "meta": result.meta if isinstance(result.meta, dict) else {},
        })

    # ═══════════════════════════════════════════════════════
    # API: 全管线交付（AI Agent 主入口）
    # ═══════════════════════════════════════════════════════
    def _run_full_pipeline(self, body: bytes) -> None:
        """POST /api/run-pipeline — 滑杆包 → 全管线 → 烘焙 02 + 各阶段产物。
        
        请求体: {"packet": {...}}  或  {"nl": "..."}  # 自动先 NL→packet
        返回: {"ok": true, "baked": {...}, "stages": {...}, "metronome": "..."}
        """
        data = json.loads(body.decode("utf-8"))

        # 如果传了 nl 没传 packet，先转
        pkt_dict = data.get("packet")
        if not pkt_dict:
            nl = (data.get("nl") or "").strip()
            if nl:
                from gaze_engine.llm_openai import chatgpt_customer_nl, openai_configured
                from gaze_engine.nl_intent import INTENT_APPLY
                from gaze_engine.nl_to_packet import packet_from_natural_language

                kb = data.get("knowledge_base") or ""
                use_llm = data.get("use_llm", True)
                if use_llm and openai_configured():
                    result = chatgpt_customer_nl(nl, knowledge_base=kb)
                else:
                    pkt = packet_from_natural_language(nl, use_llm=False)
                    from gaze_engine.nl_intent import CustomerNLResult
                    result = CustomerNLResult(
                        intent=INTENT_APPLY, reply="", packet=pkt, meta={}
                    )
                if result.intent != INTENT_APPLY or result.packet is None:
                    self._json_response({
                        "ok": False, "error": "NL 无法转为 apply 意图", "reply": result.reply,
                    })
                    return
                pkt_dict = result.packet.to_dict()
            else:
                self._json_response({"ok": False, "error": "需要 packet 或 nl"}, status=400)
                return

        # 跑全管线
        from gaze_engine.slider_schema import SliderPacket
        from gaze_engine.delivery_pipeline import run_delivery_from_packet
        from gaze_engine.envelope_compile import channels_from_packet, export_envelope_series
        from gaze_engine.packet_finalize import finalize_packet
        from gaze_engine.human_prior import dense_to_baked_sparse

        pkt = SliderPacket.from_dict(pkt_dict)
        pkt, fin_rep = finalize_packet(pkt)

        # 编译包络
        env_series = export_envelope_series(pkt)
        # 跑交付链
        baked, dense_out, prior_rep, pq_rep = run_delivery_from_packet(pkt)
        # 扩散节拍
        from gaze_engine.export_diffusion_metronome import build_metronome_text
        metronome = build_metronome_text(baked)

        self._json_response({
            "ok": True,
            "emotion": pkt.emotion,
            "packet": pkt.to_dict(),
            "finalize_fixes": fin_rep.fixes if fin_rep.fixes else [],
            "stages": {
                "envelope": env_series,
                "prior_report": prior_rep.to_dict(),
                "pulse_quality_report": pq_rep.to_dict(),
            },
            "baked": baked,
            "metronome": metronome,
        })

    # ═══════════════════════════════════════════════════════
    # API: 导出扩散节拍表
    # ═══════════════════════════════════════════════════════
    def _export_metronome(self, body: bytes) -> None:
        """POST /api/export-metronome — 从烘焙02导出扩散节拍表。
        
        请求体: {"baked": {...}}  或  {"sparse_json_path": "..."}
        返回: {"ok": true, "metronome": "..."}
        """
        data = json.loads(body.decode("utf-8"))
        baked = data.get("baked")
        if baked:
            from gaze_engine.export_diffusion_metronome import build_metronome_text
            text = build_metronome_text(baked)
            self._json_response({"ok": True, "metronome": text})
            return

        path_str = data.get("sparse_json_path") or data.get("path") or ""
        if path_str:
            path = Path(path_str)
            if not path.is_file():
                self._json_response({"ok": False, "error": f"文件不存在: {path}"}, status=404)
                return
            baked = json.loads(path.read_text("utf-8"))
            from gaze_engine.export_diffusion_metronome import build_metronome_text
            text = build_metronome_text(baked, source_path=str(path))
            self._json_response({"ok": True, "metronome": text})
            return

        self._json_response({"ok": False, "error": "需要 baked 或 sparse_json_path"}, status=400)

    # ═══════════════════════════════════════════════════════
    # 资产库浏览器
    # ═══════════════════════════════════════════════════════
    def _asset_browser(self) -> None:
        """GET /api/asset-browser — 列出资产库目录树（人格包 → 情绪 → 文件）。"""
        from asset_lib import ASSET_LIB, PERSONAS

        def _scan_dir(path: Path, max_depth: int = 3) -> list:
            if max_depth <= 0 or not path.is_dir():
                return []
            items = []
            for entry in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name)):
                if entry.name.startswith(".") or entry.name == "_archive":
                    continue
                item = {"name": entry.name, "type": "dir" if entry.is_dir() else "file"}
                if entry.is_dir():
                    item["children"] = _scan_dir(entry, max_depth - 1)
                else:
                    item["size"] = entry.stat().st_size
                    item["ext"] = entry.suffix.lower()
                    # 标记关键文件类型
                    if entry.name.startswith("02_烘焙"):
                        item["tag"] = "烘焙"
                    elif entry.name.startswith("05_扩散"):
                        item["tag"] = "节拍表"
                    elif entry.name == "人格包.json":
                        item["tag"] = "人格"
                    elif entry.name == "情绪.json":
                        item["tag"] = "情绪"
                items.append(item)
            return items

        root = []
        for persona_dir in sorted(PERSONAS.iterdir()):
            if persona_dir.is_dir() and not persona_dir.name.startswith("."):
                persona_item = {
                    "name": persona_dir.name,
                    "type": "dir",
                    "children": _scan_dir(persona_dir, max_depth=2),
                }
                root.append(persona_item)

        self._json_response({"ok": True, "root": root, "asset_lib": str(ASSET_LIB)})

    def _asset_load_baked(self, body: bytes) -> None:
        """POST /api/asset-load-baked — 加载指定烘焙文件到工作台。

        请求体: {"path": "资产库/人格包/.../02_烘焙_真人律.json"}
        返回: {"ok": true, "baked": {...}, "packet": {...}, "metronome": "..."}
        """
        data = json.loads(body.decode("utf-8"))
        path_str = data.get("path") or ""
        if not path_str:
            self._json_response({"ok": False, "error": "缺少 path"}, status=400)
            return

        baked_path = Path(path_str)
        if not baked_path.is_file():
            baked_path = ROOT / path_str
        if not baked_path.is_file():
            baked_path = PKG / path_str
        if not baked_path.is_file():
            self._json_response({"ok": False, "error": f"文件不存在: {path_str}"}, status=404)
            return

        try:
            baked = json.loads(baked_path.read_text("utf-8"))
        except Exception as e:
            self._json_response({"ok": False, "error": f"JSON 解析失败: {e}"}, status=400)
            return

        # 提取滑杆包（如果有）
        packet = baked.get("slider_packet") or {}

        # 生成扩散节拍表
        metronome = ""
        try:
            from gaze_engine.export_diffusion_metronome import build_metronome_text
            metronome = build_metronome_text(baked, source_path=str(baked_path))
        except Exception:
            pass

        self._json_response({
            "ok": True,
            "baked": baked,
            "packet": packet,
            "metronome": metronome,
            "path": str(baked_path),
            "emotion": baked.get("mood") or baked.get("emotion") or "",
        })

    def log_message(self, fmt: str, *args) -> None:
        print(f"[workbench] {fmt % args}")


def _workbench_url(host: str = "127.0.0.1", port: int = PORT) -> str:
    return f"http://{host}:{port}/01_工作台服务/能量工作台.html"


def _probe_running(host: str, port: int) -> bool:
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2) as r:
            if r.status != 200:
                return False
            data = json.loads(r.read().decode("utf-8"))
            return bool(data.get("ok")) and int(data.get("version") or 0) >= API_VERSION
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError, ValueError):
        return False


def _stop_stale_server(port: int) -> None:
    import subprocess, time
    for cmd in (
        ["fuser", "-k", f"{port}/tcp"],
        ["sh", "-c", f"lsof -ti :{port} | xargs -r kill"],
    ):
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    time.sleep(0.4)


def main() -> int:
    host, port = "127.0.0.1", PORT
    url = _workbench_url(host, port)
    httpd = None
    for attempt in range(3):
        try:
            httpd = ThreadingHTTPServer((host, port), Handler)
            break
        except OSError as e:
            if e.errno != 98 or attempt >= 2:
                raise
            if _probe_running(host, port):
                print(f"能量工作台 v{API_VERSION} 已在运行: {url}")
                return 0
            print(f"端口 {port} 占用（旧版），正在重启…", file=sys.stderr)
            _stop_stale_server(port)

    if httpd is None:
        raise RuntimeError("无法绑定工作台端口")

    print(f"能量工作台 v{API_VERSION}: {url}")
    print("API: POST /compile_pipeline  POST /save_packet  POST /render_control_video")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
