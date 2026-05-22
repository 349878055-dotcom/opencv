#!/usr/bin/env python3
"""能量工作台：静态页 + 保存滑杆包 / 操作台上下文 + 管线编译 + 2D 霓虹控制视频。"""
from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKG = ROOT.parent
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

PORT = 8765
API_VERSION = 10  # + 2D 霓虹控制视频渲染

CONTROL_VIDEO_DIR = ROOT / "preview_cache"
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
                "control_video": True,
                "note": "ecursor 能量工作台 HTTP API · 2D 霓虹控制视频",
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
            else:
                print(f"[workbench] 未知 POST 路径: {path!r}", flush=True)
                self.send_error(404)
        except Exception as e:
            self.send_error(400, str(e))

    # ═══════════════════════════════════════════════════════
    # 2D 霓虹控制视频
    # ═══════════════════════════════════════════════════════
    def _render_control_video(self, body: bytes) -> None:
        """POST /render_control_video — 编译全量管线 + 渲染控制视频 + 自动配乐合流。"""
        from gaze_engine.line_drawer import generate_control_video
        from gaze_engine.audio_compiler import (
            _generate_mock_audio,
            bake_audio_by_envelope,
            merge_audio_video,
        )

        pkt_dict = json.loads(body.decode("utf-8"))
        pipeline = self._compile_pipeline_all(pkt_dict)

        # 取最终阶段通道 + 包络
        channels = pipeline["stages"]["quality"]["channels"]
        fps = pipeline["fps"]
        env = pipeline.get("envelope")  # 顶层 envelope 数组

        CONTROL_VIDEO_DIR.mkdir(parents=True, exist_ok=True)

        # Step 1: 渲染无音轨视频（临时文件）
        video_no_audio = CONTROL_VIDEO_DIR / "control_video_noaud.mp4"
        generate_control_video(
            {"channels": channels, "frame_count": 150, "fps": fps},
            str(video_no_audio),
            width=512, height=512, fps=fps,
        )

        # Step 2: 生成 Mock 音源 → 包络卡点
        audio_raw = CONTROL_VIDEO_DIR / "mock_audio.mp3"
        _generate_mock_audio(duration_sec=150 / fps, output_path=str(audio_raw))
        audio_baked = CONTROL_VIDEO_DIR / "audio_baked.mp3"
        bake_audio_by_envelope(
            str(audio_raw), env,
            frame_count=150, fps=fps,
            output_path=str(audio_baked),
        )

        # Step 3: 合流到最终文件（不同路径避免 ffmpeg 读写冲突）
        final_out = CONTROL_VIDEO_DIR / CONTROL_VIDEO_NAME
        merge_audio_video(str(video_no_audio), str(audio_baked), output_path=str(final_out))

        # 清理临时无音轨文件
        video_no_audio.unlink(missing_ok=True)

        self._json_response({
            "ok": True,
            "path": f"/{CONTROL_VIDEO_NAME}",
            "note": "2D 霓虹控制视频 + 自动配乐合流完成",
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

    def log_message(self, fmt: str, *args) -> None:
        print(f"[workbench] {fmt % args}")


def _workbench_url(host: str = "127.0.0.1", port: int = PORT) -> str:
    return f"http://{host}:{port}/能量工作台.html"


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
