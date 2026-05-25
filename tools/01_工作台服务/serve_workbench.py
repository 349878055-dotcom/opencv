#!/usr/bin/env python3
"""能量工作台 HTTP 服务：静态页 + 全管线 API（NL→滑杆→包络→真人→平庸→烘焙→扩散节拍）。"""
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
API_VERSION = 11

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

        # 根路径 → 重定向到能量工作台
        if path in ("", "/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/01_%E5%B7%A5%E4%BD%9C%E5%8F%B0%E6%9C%8D%E5%8A%A1/%E8%83%BD%E9%87%8F%E5%B7%A5%E4%BD%9C%E5%8F%B0.html")
            self.end_headers()
            return

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
                    "GET  /api/customer-context",
                    "GET  /api/customer-list",
                    "POST /api/dog-test            ← 🐶 生成狗测试资产",
                    "POST /api/nl-to-packet",
                    "POST /api/run-pipeline",
                    "POST /api/asset-load-baked",
                    "POST /api/export-metronome",
                    "POST /save_packet",
                    "POST /save_context",
                    "POST /render_control_video",
                    "POST /api/customer/create",
                    "POST /api/customer/update",
                    "POST /api/customer/delete",
                    "POST /api/customer/{cid}/project/create",
                    "POST /api/customer/{cid}/project/update",
                    "POST /api/customer/{cid}/project/delete",
                    "POST /api/customer/{cid}/project/{pid}/save-adjustment",
                    "POST /api/customer-context/save",
                ],
            })
            return
        if path == "/control_surface.json":
            from gaze_engine.human.control_surface import export_workbench_json
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
        if path == "/api/customer-list":
            self._customer_list()
            return
        if path == "/api/customer-context":
            self._customer_context()
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
            elif path == "/api/dog-test":
                self._dog_test(body)
            # ── 客户资产库 API ──
            elif path == "/api/customer/create":
                self._customer_create(body)
            elif path == "/api/customer/update":
                self._customer_update(body)
            elif path == "/api/customer/delete":
                self._customer_delete(body)
            elif path.startswith("/api/customer/") and path.endswith("/project/create"):
                cid = path.split("/")[3]
                self._customer_project_create(body, cid)
            elif path.startswith("/api/customer/") and "/project/" in path:
                parts = path.split("/")
                # /api/customer/{cid}/project/{action}
                # /api/customer/{cid}/project/{pid}/save-adjustment
                if len(parts) == 6 and parts[5] in ("update", "delete"):
                    cid, action = parts[3], parts[5]
                    self._customer_project_update(body, cid, action)
                elif len(parts) == 7 and parts[5] == "save-adjustment":
                    cid, pid = parts[3], parts[5]
                    self._customer_save_adjustment(body, cid, pid)
                else:
                    print(f"[workbench] 未知客户 POST 路径: {path!r}", flush=True)
                    self.send_error(404)
            elif path == "/api/customer-context/save":
                self._customer_context_save(body)
            else:
                print(f"[workbench] 未知 POST 路径: {path!r}", flush=True)
                self.send_error(404)
        except Exception as e:
            # 屏蔽非 ASCII 字符，避免 latin-1 send_error 崩溃
            safe_msg = str(e).encode("ascii", errors="replace").decode("ascii")
            self.send_error(400, safe_msg)

    # ═══════════════════════════════════════════════════════
    # 控制视频（仿射渲染引擎）
    # ═══════════════════════════════════════════════════════
    def _render_control_video(self, body: bytes) -> None:
        """POST /render_control_video — 全管线 → 工程底模 → mp4。"""
        import cv2
        from gaze_engine.human.affine_renderer import AffineRenderer
        from gaze_engine._shared.slider_schema import SliderPacket
        from gaze_engine.delivery_pipeline import run_delivery_from_packet

        pkt_dict = json.loads(body.decode("utf-8"))
        pkt = SliderPacket.from_dict(pkt_dict)
        baked, dense_out, prior_rep, pq_rep = run_delivery_from_packet(pkt)

        # 从烘焙结果提取 12 通道 × 150 帧
        channels_data = dense_out  # dict of 12 keys × 150 values
        frame_count = len(next(iter(channels_data.values())))

        # 确保缓存目录存在
        CONTROL_VIDEO_DIR.mkdir(parents=True, exist_ok=True)

        # 初始化渲染引擎（无需底图纹理）
        renderer = AffineRenderer()

        # 临时帧目录
        frames_dir = CONTROL_VIDEO_DIR / "_frames"
        frames_dir.mkdir(exist_ok=True)

        print(f"[workbench] 渲染 {frame_count} 帧工程底模...", flush=True)
        from gaze_engine.human.affine_renderer import CANONICAL_KEYS
        for t in range(frame_count):
            frame_data = {k: channels_data[k][t] for k in CANONICAL_KEYS if k in channels_data}
            img = renderer.render_frame(frame_data)  # (H,W,3) RGB工程底模
            cv2.imwrite(str(frames_dir / f"f_{t:04d}.png"), img)
            if (t + 1) % 30 == 0:
                print(f"  ... {t+1}/{frame_count}", flush=True)

        # 合成 mp4
        import subprocess
        video_path = CONTROL_VIDEO_DIR / CONTROL_VIDEO_NAME
        subprocess.run([
            "ffmpeg", "-y", "-f", "image2", "-r", "30",
            "-i", str(frames_dir / "f_%04d.png"),
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18",
            str(video_path),
        ], capture_output=True, check=True)

        # 清理临时帧
        import shutil
        shutil.rmtree(frames_dir)

        print(f"[workbench] 工程底模视频已保存: {video_path}", flush=True)
        self._json_response({
            "ok": True,
            "path": "/control_video.mp4",
            "frames": frame_count,
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
        from gaze_engine._shared.workbench_context import read_workbench_context
        return read_workbench_context()

    def _compile_pipeline_all(self, pkt_dict: dict) -> dict:
        from gaze_engine._shared.envelope_compile import (
            channels_from_packet,
            export_envelope_series,
            make_delivery_stub,
        )
        from gaze_engine.human.human_prior import apply_human_prior
        from gaze_engine._shared.packet_finalize import finalize_packet
        from gaze_engine.human.pulse_quality import fix_pulse_quality
        from gaze_engine._shared.slider_schema import SliderPacket

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
        from gaze_engine._shared.pipeline_io import F_DENSE_ENV, read_dense
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
        from gaze_engine._shared.envelope_compile import channels_from_packet, make_delivery_stub
        from gaze_engine.human.human_prior import apply_human_prior
        from gaze_engine._shared.pipeline_io import F_DENSE_PRIOR, F_DENSE_QUALITY, cmd_dir, write_dense
        from gaze_engine.human.pulse_quality import fix_pulse_quality
        from gaze_engine._shared.slider_schema import SliderPacket
        from gaze_engine._shared.workbench_io import finalize_and_write_l1, read_slider_packet, write_slider_packet

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
        from gaze_engine._shared.workbench_context import write_workbench_context
        data = json.loads(body.decode("utf-8"))
        p = write_workbench_context(
            natural_language=data.get("natural_language"),
            energy_map_note=data.get("energy_map_note") or data.get("prompt"),
            knowledge_base=data.get("knowledge_base"),
        )
        nl = (data.get("natural_language") or "").strip()
        if nl:
            from gaze_engine._shared.pipeline_io import F_NL, cmd_dir
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
        from gaze_engine._shared.llm_openai import chatgpt_customer_nl, openai_configured
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

        请求体: {"packet": {...}}  或  {"nl": "..."}
        可选: {"customer_id": "C001", "project_id": "P001"}
        返回: {"ok": true, "baked": {...}, "stages": {...}, "metronome": "...", "archive": {...}}
        """
        data = json.loads(body.decode("utf-8"))

        # 如果传了 nl 没传 packet，先转
        pkt_dict = data.get("packet")
        if not pkt_dict:
            nl = (data.get("nl") or "").strip()
            if nl:
                from gaze_engine._shared.llm_openai import chatgpt_customer_nl, openai_configured
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
        from gaze_engine._shared.slider_schema import SliderPacket
        from gaze_engine.delivery_pipeline import run_delivery_from_packet
        from gaze_engine._shared.envelope_compile import channels_from_packet, export_envelope_series
        from gaze_engine._shared.packet_finalize import finalize_packet
        from gaze_engine.human.human_prior import dense_to_baked_sparse

        pkt = SliderPacket.from_dict(pkt_dict)
        pkt, fin_rep = finalize_packet(pkt)

        # 编译包络
        env_series = export_envelope_series(pkt)
        # 跑交付链
        baked, dense_out, prior_rep, pq_rep = run_delivery_from_packet(pkt)
        # 扩散节拍
        from gaze_engine._shared.export_diffusion_metronome import build_metronome_text
        metronome = build_metronome_text(baked)

        # 归档到客户项目（如果提供了客户上下文）
        archive_info = self._archive_pipeline_to_customer(
            data, baked, metronome, pkt.to_dict(),
        )

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
            "archive": archive_info,
        })

    def _archive_pipeline_to_customer(
        self,
        data: dict,
        baked: dict,
        metronome: str,
        packet_dict: dict,
    ) -> dict:
        """将管线输出归档到客户项目（如果请求中包含客户上下文）。

        请求体重可选字段：customer_id, project_id
        若无客户上下文，返回空 dict。
        """
        cid = (data.get("customer_id") or "").strip()
        pid = (data.get("project_id") or "").strip()
        if not cid or not pid:
            # 尝试从工作台上下文读取
            try:
                from gaze_engine._shared.customer_db import load_workbench_context
                ctx = load_workbench_context()
                cid = ctx.get("customer_id", "")
                pid = ctx.get("project_id", "")
            except Exception:
                pass
        if not cid or not pid:
            return {}

        try:
            from gaze_engine._shared.customer_db import (
                get_project, save_adjustment,
            )
            from asset_lib import project_output_dir

            # 确认项目存在
            project = get_project(cid, pid)
            if not project:
                return {"error": f"项目 {cid}/{pid} 不存在"}

            out_dir = project_output_dir(cid, pid)
            out_dir.mkdir(parents=True, exist_ok=True)

            # 写 02_烘焙_真人律.json
            baked_path = out_dir / "02_烘焙_真人律.json"
            import json as _json_mod
            baked_path.write_text(
                _json_mod.dumps(baked, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            # 写 05_扩散节拍表.txt
            metronome_path = out_dir / "05_扩散节拍表.txt"
            metronome_path.write_text(metronome, encoding="utf-8")

            # 写 01_滑杆包.json
            packet_path = out_dir / "01_滑杆包.json"
            packet_path.write_text(
                _json_mod.dumps(packet_dict, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            # 保存调整记录
            save_adjustment(
                cid, pid, packet_dict,
                note="管线自动归档",
                extra={"emotion": packet_dict.get("emotion", "")},
            )

            return {
                "customer_id": cid,
                "project_id": pid,
                "output_dir": str(out_dir),
                "baked": str(baked_path),
                "metronome": str(metronome_path),
                "packet": str(packet_path),
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

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
            from gaze_engine._shared.export_diffusion_metronome import build_metronome_text
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
            from gaze_engine._shared.export_diffusion_metronome import build_metronome_text
            text = build_metronome_text(baked, source_path=str(path))
            self._json_response({"ok": True, "metronome": text})
            return

        self._json_response({"ok": False, "error": "需要 baked 或 sparse_json_path"}, status=400)

    # ═══════════════════════════════════════════════════════
    # 资产库浏览器
    # ═══════════════════════════════════════════════════════
    def _asset_browser(self) -> None:
        """GET /api/asset-browser — 列出预设资产 + 客户资产库目录树。"""
        from asset_lib import (
            ASSET_LIB, CUSTOMER_DB,
            PERSONA_DIR, PERSONAS,
            HUMAN_PRESETS_DIR, CAT_PRESETS_DIR, DOG_PRESETS_DIR,
        )

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
                    if entry.name.startswith("02_烘焙"):
                        item["tag"] = "烘焙"
                    elif entry.name.startswith("05_扩散"):
                        item["tag"] = "节拍表"
                    elif entry.name == "人格包.json":
                        item["tag"] = "人格"
                    elif entry.name == "情绪.json":
                        item["tag"] = "情绪"
                    elif entry.name == "客户信息.json":
                        item["tag"] = "客户"
                    elif entry.name == "项目配置.json":
                        item["tag"] = "项目"
                    elif entry.name == "滑杆调整记录.json":
                        item["tag"] = "调整"
                items.append(item)
            return items

        root = []

        # ── 预设资产库 ──
        preset_section = {
            "name": "📚 预设资产库",
            "type": "dir",
            "tag": "preset_lib",
            "children": [],
        }

        # 1. 物种预设（human/cat/dog）
        SPECIES_LABELS = {"human": "🧑 人类预设", "cat": "🐱 猫预设", "dog": "🐶 狗预设"}
        for sp_dir, sp_label in [(HUMAN_PRESETS_DIR, "🧑 人类预设"),
                                  (CAT_PRESETS_DIR, "🐱 猫预设"),
                                  (DOG_PRESETS_DIR, "🐶 狗预设")]:
            if sp_dir.is_dir():
                preset_section["children"].append({
                    "name": sp_label,
                    "type": "dir",
                    "children": _scan_dir(sp_dir, max_depth=1),
                })

        # 2. 人格包（persona/ 新路径 or 人格包/ 旧路径回退）
        persona_root = PERSONA_DIR if PERSONA_DIR.is_dir() else PERSONAS
        if persona_root.is_dir():
            for pd in sorted(persona_root.iterdir()):
                if pd.is_dir() and not pd.name.startswith("."):
                    preset_section["children"].append({
                        "name": f"🎭 {pd.name}",
                        "type": "dir",
                        "children": _scan_dir(pd, max_depth=2),
                    })

        root.append(preset_section)

        # ── 客户资产库 ──
        customer_section = {
            "name": "👤 客户资产库",
            "type": "dir",
            "tag": "customer_db",
            "children": _scan_dir(CUSTOMER_DB, max_depth=3) if CUSTOMER_DB.is_dir() else [],
        }
        root.append(customer_section)

        self._json_response({
            "ok": True,
            "root": root,
            "asset_lib": str(ASSET_LIB),
            "customer_db": str(CUSTOMER_DB),
        })

    def _asset_load_baked(self, body: bytes) -> None:
        """POST /api/asset-load-baked — 加载指定烘焙文件到工作台。

        请求体: {"path": "预设资产/人格包/.../02_烘焙_真人律.json"}
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
            from gaze_engine._shared.export_diffusion_metronome import build_metronome_text
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

    # ═══════════════════════════════════════════════════════
    # 狗全身体验测试 API
    # ═══════════════════════════════════════════════════════
    def _dog_test(self, body: bytes) -> None:
        """POST /api/dog-test — 狗全身体验测试。

        请求体::
            {
                "preset": "dog_sad_puppy",      # 狗预设名
                "nl": "狗子被关进笼子里面的委屈样子",  # 自然语言描述
                "out_dir": "/tmp/dog_test",      # 输出目录（仅无客户时有效）
                "skip_body": false,              # 跳过全身体视频
                "skip_mesh": false,              # 跳过工程底膜
                "customer_id": "C001",           # 🆕 可选：客户 ID
                "project_id": "P001",            # 🆕 可选：项目 ID（不传则自动创建）
                "project_name": "贵宾犬委屈"      # 🆕 可选：自动创建项目时的名称
            }

        返回::
            {
                "ok": true,
                "assets": { 所有输出文件路径 },
                "report": { 管线报告 },
                "archive": { 客户归档信息 }      # 🆕 有客户时返回
            }
        """
        data = json.loads(body.decode("utf-8"))
        preset = data.get("preset", "dog_sad_puppy")
        nl = data.get("nl", "狗子被关进笼子里面的委屈样子")
        skip_mesh = data.get("skip_mesh", False)

        # 🆕 解析客户上下文
        cid = (data.get("customer_id") or "").strip()
        pid = (data.get("project_id") or "").strip()
        project_name = (data.get("project_name") or nl or "狗测试").strip()

        # 如果有客户 ID 但没有项目 ID，自动创建项目
        if cid and not pid:
            try:
                from gaze_engine._shared.customer_db import (
                    create_project, get_customer,
                )
                customer = get_customer(cid)
                if customer:
                    pid = create_project(
                        cid, project_name,
                        species="dog",
                        base_persona=data.get("preset", ""),
                    )
            except Exception:
                pass

        # 确定输出目录
        if cid and pid:
            from asset_lib import project_output_dir
            out_dir = str(project_output_dir(cid, pid))
            out_dir_path = project_output_dir(cid, pid)
            out_dir_path.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = data.get("out_dir", "/tmp/dog_test")

        try:
            # 添加 tools/05_其他工具/ 到 sys.path
            import sys as _sys
            _tools_dir = Path(__file__).resolve().parent.parent
            _other_tools = _tools_dir / "05_其他工具"
            if str(_other_tools) not in _sys.path:
                _sys.path.insert(0, str(_other_tools))

            from dog_full_body_test import build_dog_test_assets

            result = build_dog_test_assets(
                preset_name=preset,
                out_dir=out_dir,
                natural_language=nl,
                skip_render=skip_mesh,
            )

            response = {
                "ok": True,
                "assets": result,
                "report": result.get("report"),
            }

            # 🆕 归档到客户项目
            if cid and pid:
                archive_info = self._archive_pipeline_to_customer(
                    data,
                    baked=result.get("baked", {}),
                    metronome=result.get("metronome", ""),
                    packet_dict=result.get("packet", {}),
                )
                if archive_info:
                    response["archive"] = archive_info
                    response["customer_id"] = cid
                    response["project_id"] = pid

            self._json_response(response)
        except ImportError as e:
            self._json_response({
                "ok": False,
                "error": f"导入失败: {e}",
                "hint": "请确保 tools/05_其他工具/dog_full_body_test.py 存在",
            }, status=500)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._json_response({
                "ok": False,
                "error": str(e),
            }, status=500)

    # ═══════════════════════════════════════════════════════
    # 客户资产库 API
    # ═══════════════════════════════════════════════════════

    # ── GET ──

    def _customer_list(self) -> None:
        """GET /api/customer-list — 列出所有客户。"""
        from gaze_engine._shared.customer_db import list_customers
        customers = list_customers()
        self._json_response({"ok": True, "customers": customers})

    def _customer_context(self) -> None:
        """GET /api/customer-context — 加载当前工作台客户上下文。"""
        from gaze_engine._shared.customer_db import load_workbench_context
        ctx = load_workbench_context()
        self._json_response({"ok": True, **ctx})

    # ── POST 客户 CRUD ──

    def _customer_create(self, body: bytes) -> None:
        """POST /api/customer/create — 创建客户。
        请求体: {"display_name": "...", "contact": "", "default_persona": ""}
        """
        from gaze_engine._shared.customer_db import create_customer, get_customer
        data = json.loads(body.decode("utf-8"))
        display_name = (data.get("display_name") or "").strip()
        if not display_name:
            self._json_response({"ok": False, "error": "缺少 display_name"}, status=400)
            return
        cid = create_customer(
            display_name,
            contact=data.get("contact", ""),
            default_persona=data.get("default_persona", ""),
            default_emotion=data.get("default_emotion", ""),
            preferred_species=data.get("preferred_species", "human"),
        )
        info = get_customer(cid)
        self._json_response({"ok": True, "customer_id": cid, "customer": info})

    def _customer_update(self, body: bytes) -> None:
        """POST /api/customer/update — 更新客户信息。
        请求体: {"customer_id": "C001", "display_name": "...", ...}
        """
        from gaze_engine._shared.customer_db import update_customer
        data = json.loads(body.decode("utf-8"))
        cid = data.get("customer_id", "").strip()
        if not cid:
            self._json_response({"ok": False, "error": "缺少 customer_id"}, status=400)
            return
        ok = update_customer(cid, **{k: data[k] for k in data if k != "customer_id"})
        self._json_response({"ok": ok})

    def _customer_delete(self, body: bytes) -> None:
        """POST /api/customer/delete — 删除客户。
        请求体: {"customer_id": "C001"}
        """
        from gaze_engine._shared.customer_db import delete_customer
        data = json.loads(body.decode("utf-8"))
        cid = data.get("customer_id", "").strip()
        if not cid:
            self._json_response({"ok": False, "error": "缺少 customer_id"}, status=400)
            return
        ok = delete_customer(cid)
        self._json_response({"ok": ok})

    # ── POST 项目 CRUD ──

    def _customer_project_create(self, body: bytes, customer_id: str) -> None:
        """POST /api/customer/{cid}/project/create — 创建项目。
        请求体: {"project_name": "...", "species": "dog", ...}
        """
        from gaze_engine._shared.customer_db import create_project, get_customer
        if get_customer(customer_id) is None:
            self._json_response({"ok": False, "error": f"客户 {customer_id} 不存在"}, status=404)
            return
        data = json.loads(body.decode("utf-8"))
        project_name = (data.get("project_name") or "").strip()
        if not project_name:
            self._json_response({"ok": False, "error": "缺少 project_name"}, status=400)
            return
        pid = create_project(
            customer_id,
            project_name,
            species=data.get("species", "human"),
            base_persona=data.get("base_persona", ""),
            base_emotion=data.get("base_emotion", ""),
            reference_photo=data.get("reference_photo", ""),
            custom_overrides=data.get("custom_overrides"),
        )
        self._json_response({"ok": True, "project_id": pid})

    def _customer_project_update(self, body: bytes, action: str) -> None:
        """POST /api/customer/{cid}/project/update 或 delete"""
        from gaze_engine._shared.customer_db import update_project, delete_project
        data = json.loads(body.decode("utf-8"))
        cid = data.get("customer_id", "").strip()
        pid = data.get("project_id", "").strip()
        if not cid or not pid:
            self._json_response({"ok": False, "error": "缺少 customer_id 或 project_id"}, status=400)
            return
        if action == "delete":
            ok = delete_project(cid, pid)
        else:
            ok = update_project(cid, pid, **{k: data[k] for k in data
                                              if k not in ("customer_id", "project_id")})
        self._json_response({"ok": ok})

    # ── POST 调整记录 ──

    def _customer_save_adjustment(self, body: bytes, customer_id: str, project_id: str) -> None:
        """POST /api/customer/{cid}/project/{pid}/save-adjustment — 保存调整快照。
        请求体: {"packet": {...}, "note": "...", "diff": {...}}
        """
        from gaze_engine._shared.customer_db import save_adjustment, get_current_adjustment_version
        data = json.loads(body.decode("utf-8"))
        packet = data.get("packet")
        if not packet:
            self._json_response({"ok": False, "error": "缺少 packet"}, status=400)
            return
        ver = save_adjustment(
            customer_id, project_id,
            packet,
            note=data.get("note", ""),
            diff=data.get("diff"),
        )
        if ver is None:
            self._json_response({"ok": False, "error": "项目不存在"}, status=404)
            return
        self._json_response({"ok": True, "version": ver})

    # ── POST 客户上下文 ──

    def _customer_context_save(self, body: bytes) -> None:
        """POST /api/customer-context/save — 保存工作台上下文（当前客户/项目）。
        请求体: {"customer_id": "C001", "project_id": "P001"}
        """
        from gaze_engine._shared.customer_db import save_workbench_context
        data = json.loads(body.decode("utf-8"))
        ctx = save_workbench_context(
            customer_id=data.get("customer_id"),
            project_id=data.get("project_id"),
        )
        self._json_response({"ok": True, "context": ctx})

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
    host, port = "0.0.0.0", PORT
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
