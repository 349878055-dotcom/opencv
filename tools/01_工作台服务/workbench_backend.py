#!/usr/bin/env python3
"""能量工作台 FastAPI 后端：静态页 + 全管线 API（NL→滑杆→包络→真人→平庸→烘焙→扩散节拍）。
替代 ComfyUI 节点链。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent  # tools/
PKG = ROOT.parent  # 项目根目录
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

API_VERSION = 12
CONTROL_VIDEO_DIR = ROOT / "04_缓存数据" / "preview_cache"
CONTROL_VIDEO_NAME = "control_video.mp4"

app = FastAPI(title="能量工作台", version=str(API_VERSION))

# ── 静态文件服务 ──────────────────────────────────────────
FRONTEND_DIR = ROOT / "01_工作台服务"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════
def _json(data: dict, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status)


def _load_context() -> dict:
    from gaze_engine._shared.workbench_context import read_workbench_context
    return read_workbench_context()


def _load_dense04() -> dict:
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


# ═══════════════════════════════════════════════════════════
# GET 端点
# ═══════════════════════════════════════════════════════════
@app.get("/health")
@app.get("/api/health")
async def health():
    return _json({
        "ok": True,
        "version": API_VERSION,
        "note": "能量工作台 · 全管线 API（NL→滑杆→烘焙→扩散节拍）",
        "endpoints": [
            "GET  /health",
            "GET  /control_surface.json",
            "GET  /workbench_context.json",
            "GET  /persona_matrix.json",
            "GET  /api/asset-browser",
            "GET  /api/customer-context",
            "GET  /api/customer-list",
            "POST /api/nl-to-packet",
            "POST /api/run-pipeline",
            "POST /api/asset-load-baked",
            "POST /api/export-metronome",
            "POST /save_packet",
            "POST /save_context",
            "POST /render_control_video",
            "POST /persona_matrix.json",
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


@app.get("/control_surface.json")
async def control_surface():
    from gaze_engine.human.control_surface import export_workbench_json
    return _json(export_workbench_json())


@app.get("/workbench_context.json")
async def workbench_context():
    return _json(_load_context())


@app.get("/dense04.json")
async def dense04():
    return _json(_load_dense04())


@app.get("/control_video.mp4")
async def control_video():
    p = CONTROL_VIDEO_DIR / CONTROL_VIDEO_NAME
    if not p.is_file():
        raise HTTPException(404, "尚未生成控制视频，请先点「渲染 2D 控制流」")
    return FileResponse(str(p), media_type="video/mp4", headers={
        "Cache-Control": "no-cache",
    })


@app.get("/persona_matrix.json")
async def get_persona_matrix():
    matrix_path = PKG / "gaze_engine" / "persona_matrix.json"
    if not matrix_path.exists():
        raise HTTPException(404, "persona_matrix.json not found")
    return _json(json.loads(matrix_path.read_text("utf-8")))


@app.get("/api/asset-browser")
async def asset_browser():
    """列出预设资产 + 客户资产库目录树。"""
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

    return _json({
        "ok": True,
        "root": root,
        "asset_lib": str(ASSET_LIB),
        "customer_db": str(CUSTOMER_DB),
    })


# ═══════════════════════════════════════════════════════════
# 客户资产库 API（GET）
# ═══════════════════════════════════════════════════════════

@app.get("/api/customer-list")
async def customer_list():
    from gaze_engine._shared.customer_db import list_customers
    customers = list_customers()
    return _json({"ok": True, "customers": customers})


@app.get("/api/customer-context")
async def customer_context():
    from gaze_engine._shared.customer_db import load_workbench_context
    ctx = load_workbench_context()
    return _json({"ok": True, **ctx})


# ═══════════════════════════════════════════════════════════
# POST 端点
# ═══════════════════════════════════════════════════════════

# ── 管线编译 ─────────────────────────────────────────────
def _compile_pipeline_all(pkt_dict: dict) -> dict:
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


@app.post("/save_packet")
async def save_packet(request: Request):
    from gaze_engine._shared.envelope_compile import channels_from_packet, make_delivery_stub
    from gaze_engine.human.human_prior import apply_human_prior
    from gaze_engine._shared.pipeline_io import F_DENSE_PRIOR, F_DENSE_QUALITY, cmd_dir, write_dense
    from gaze_engine.human.pulse_quality import fix_pulse_quality
    from gaze_engine._shared.slider_schema import SliderPacket
    from gaze_engine._shared.workbench_io import finalize_and_write_l1, read_slider_packet, write_slider_packet

    body = await request.json()
    pkt = SliderPacket.from_dict(body)
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
    return _json({
        "ok": True,
        "path": str(p01),
        "l1_path": str(p_l1),
        "dense04_path": str(p04),
        "dense05_path": str(p05),
        "dense06_path": str(p06),
        "note": "已写 01 + 02_L1 + 04/05/06 全量",
    })


@app.post("/save_context")
async def save_context(request: Request):
    from gaze_engine._shared.workbench_context import write_workbench_context

    data = await request.json()
    p = write_workbench_context(
        natural_language=data.get("natural_language"),
        energy_map_note=data.get("energy_map_note") or data.get("prompt"),
        knowledge_base=data.get("knowledge_base"),
    )
    nl = (data.get("natural_language") or "").strip()
    if nl:
        from gaze_engine._shared.pipeline_io import F_NL, cmd_dir
        (cmd_dir() / F_NL).write_text(nl + "\n", encoding="utf-8")
    return _json({"ok": True, "path": str(p)})


@app.post("/compile_pipeline")
@app.post("/compile_dense04")
async def compile_pipeline(request: Request):
    body = await request.json()
    return _json(_compile_pipeline_all(body))


@app.post("/render_control_video")
async def render_control_video(request: Request):
    """全管线 → 工程底模 → mp4。"""
    import cv2
    from gaze_engine.human.affine_renderer import AffineRenderer, CANONICAL_KEYS
    from gaze_engine._shared.slider_schema import SliderPacket
    from gaze_engine.delivery_pipeline import run_delivery_from_packet

    pkt_dict = await request.json()
    pkt = SliderPacket.from_dict(pkt_dict)
    baked, dense_out, prior_rep, pq_rep = run_delivery_from_packet(pkt)

    channels_data = dense_out
    frame_count = len(next(iter(channels_data.values())))

    CONTROL_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    renderer = AffineRenderer()

    frames_dir = CONTROL_VIDEO_DIR / "_frames"
    frames_dir.mkdir(exist_ok=True)

    for t in range(frame_count):
        frame_data = {k: channels_data[k][t] for k in CANONICAL_KEYS if k in channels_data}
        img = renderer.render_frame(frame_data)
        cv2.imwrite(str(frames_dir / f"f_{t:04d}.png"), img)

    import subprocess
    import shutil

    video_path = CONTROL_VIDEO_DIR / CONTROL_VIDEO_NAME
    subprocess.run([
        "ffmpeg", "-y", "-f", "image2", "-r", "30",
        "-i", str(frames_dir / "f_%04d.png"),
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18",
        str(video_path),
    ], capture_output=True, check=True)

    shutil.rmtree(frames_dir)

    return _json({
        "ok": True,
        "path": "/control_video.mp4",
        "frames": frame_count,
    })


@app.post("/persona_matrix.json")
async def save_persona_matrix(request: Request):
    """保存人格矩阵的修改。"""
    data = await request.json()
    action = data.get("action")
    if action != "save":
        return _json({"ok": False, "error": f"未知 action: {action}"})

    persona_id = data.get("persona_id")
    persona_data = data.get("data")
    if not persona_id or not persona_data:
        return _json({"ok": False, "error": "缺少 persona_id 或 data"})

    matrix_path = PKG / "gaze_engine" / "persona_matrix.json"
    if not matrix_path.exists():
        return _json({"ok": False, "error": "persona_matrix.json 不存在"})

    matrix = json.loads(matrix_path.read_text("utf-8"))
    if persona_id not in matrix.get("personas", {}):
        return _json({"ok": False, "error": f"未知人格: {persona_id}"})

    matrix["personas"][persona_id] = persona_data
    matrix_path.write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return _json({"ok": True})


@app.post("/api/nl-to-packet")
async def nl_to_packet(request: Request):
    """自然语言 → 滑杆包 + 回复。"""
    data = await request.json()
    nl = (data.get("nl") or "").strip()
    if not nl:
        return _json({"ok": False, "error": "缺少 nl"}, status=400)

    from gaze_engine._shared.llm_openai import chatgpt_customer_nl, openai_configured
    from gaze_engine.nl_to_packet import packet_from_natural_language
    from gaze_engine.nl_intent import INTENT_APPLY

    kb = data.get("knowledge_base") or ""
    model = data.get("model") or ""
    use_llm = data.get("use_llm", True)

    if use_llm and openai_configured():
        result = chatgpt_customer_nl(nl, knowledge_base=kb, model=model or None)
    else:
        pkt = packet_from_natural_language(nl, use_llm=False)
        from gaze_engine.nl_intent import CustomerNLResult
        result = CustomerNLResult(
            intent=INTENT_APPLY,
            reply=f"【已生成】预设「{pkt.emotion}」（关键词回退）",
            packet=pkt,
            meta={"intent_source": "keyword"},
        )

    if result.intent != INTENT_APPLY or result.packet is None:
        return _json({
            "ok": True,
            "intent": "consult",
            "reply": result.reply,
            "packet": None,
        })

    return _json({
        "ok": True,
        "intent": "apply",
        "reply": result.reply,
        "packet": result.packet.to_dict(),
        "meta": result.meta if isinstance(result.meta, dict) else {},
    })


@app.post("/api/run-pipeline")
async def run_full_pipeline(request: Request):
    """滑杆包 → 全管线 → 烘焙 02 + 各阶段产物。"""
    data = await request.json()

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
                return _json({
                    "ok": False, "error": "NL 无法转为 apply 意图", "reply": result.reply,
                })
            pkt_dict = result.packet.to_dict()
        else:
            return _json({"ok": False, "error": "需要 packet 或 nl"}, status=400)

    from gaze_engine._shared.slider_schema import SliderPacket
    from gaze_engine.delivery_pipeline import run_delivery_from_packet
    from gaze_engine._shared.envelope_compile import channels_from_packet, export_envelope_series
    from gaze_engine._shared.packet_finalize import finalize_packet
    from gaze_engine.human.human_prior import dense_to_baked_sparse

    pkt = SliderPacket.from_dict(pkt_dict)
    pkt, fin_rep = finalize_packet(pkt)

    env_series = export_envelope_series(pkt)
    baked, dense_out, prior_rep, pq_rep = run_delivery_from_packet(pkt)

    from gaze_engine._shared.export_diffusion_metronome import build_metronome_text
    metronome = build_metronome_text(baked)

    return _json({
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


@app.post("/api/export-metronome")
async def export_metronome(request: Request):
    """从烘焙02导出扩散节拍表。"""
    data = await request.json()
    baked = data.get("baked")
    if baked:
        from gaze_engine._shared.export_diffusion_metronome import build_metronome_text
        text = build_metronome_text(baked)
        return _json({"ok": True, "metronome": text})

    path_str = data.get("sparse_json_path") or data.get("path") or ""
    if path_str:
        path = Path(path_str)
        if not path.is_file():
            raise HTTPException(404, f"文件不存在: {path}")
        baked = json.loads(path.read_text("utf-8"))
        from gaze_engine._shared.export_diffusion_metronome import build_metronome_text
        text = build_metronome_text(baked, source_path=str(path))
        return _json({"ok": True, "metronome": text})

    return _json({"ok": False, "error": "需要 baked 或 sparse_json_path"}, status=400)


@app.post("/api/asset-load-baked")
async def asset_load_baked(request: Request):
    """加载指定烘焙文件到工作台。"""
    data = await request.json()
    path_str = data.get("path") or ""
    if not path_str:
        return _json({"ok": False, "error": "缺少 path"}, status=400)

    baked_path = Path(path_str)
    if not baked_path.is_file():
        baked_path = ROOT / path_str
    if not baked_path.is_file():
        baked_path = PKG / path_str
    if not baked_path.is_file():
        raise HTTPException(404, f"文件不存在: {path_str}")

    try:
        baked = json.loads(baked_path.read_text("utf-8"))
    except Exception as e:
        raise HTTPException(400, f"JSON 解析失败: {e}")

    packet = baked.get("slider_packet") or {}

    metronome = ""
    try:
        from gaze_engine._shared.export_diffusion_metronome import build_metronome_text
        metronome = build_metronome_text(baked, source_path=str(baked_path))
    except Exception:
        pass

    return _json({
        "ok": True,
        "baked": baked,
        "packet": packet,
        "metronome": metronome,
        "path": str(baked_path),
        "emotion": baked.get("mood") or baked.get("emotion") or "",
    })


@app.post("/api/dog-test")
async def dog_test(request: Request):
    """狗全身体验测试。"""
    data = await request.json()
    preset = data.get("preset", "dog_sad_puppy")
    nl = data.get("nl", "狗子被关进笼子里面的委屈样子")
    out_dir = data.get("out_dir", "/tmp/dog_test")
    skip_body = data.get("skip_body", False)
    skip_mesh = data.get("skip_mesh", False)

    try:
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
        return _json({
            "ok": True,
            "assets": result,
            "report": result.get("report"),
        })
    except ImportError as e:
        raise HTTPException(500, {
            "ok": False,
            "error": f"导入失败: {e}",
            "hint": "请确保 tools/05_其他工具/dog_full_body_test.py 存在",
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════
# 客户资产库 API（POST）
# ═══════════════════════════════════════════════════════════

@app.post("/api/customer/create")
async def customer_create(request: Request):
    from gaze_engine._shared.customer_db import create_customer, get_customer
    data = await request.json()
    display_name = (data.get("display_name") or "").strip()
    if not display_name:
        raise HTTPException(400, "缺少 display_name")
    cid = create_customer(
        display_name,
        contact=data.get("contact", ""),
        default_persona=data.get("default_persona", ""),
        default_emotion=data.get("default_emotion", ""),
        preferred_species=data.get("preferred_species", "human"),
    )
    return _json({"ok": True, "customer_id": cid, "customer": get_customer(cid)})


@app.post("/api/customer/update")
async def customer_update(request: Request):
    from gaze_engine._shared.customer_db import update_customer
    data = await request.json()
    cid = data.get("customer_id", "").strip()
    if not cid:
        raise HTTPException(400, "缺少 customer_id")
    ok = update_customer(cid, **{k: data[k] for k in data if k != "customer_id"})
    return _json({"ok": ok})


@app.post("/api/customer/delete")
async def customer_delete(request: Request):
    from gaze_engine._shared.customer_db import delete_customer
    data = await request.json()
    cid = data.get("customer_id", "").strip()
    if not cid:
        raise HTTPException(400, "缺少 customer_id")
    ok = delete_customer(cid)
    return _json({"ok": ok})


@app.post("/api/customer/{cid}/project/create")
async def customer_project_create(cid: str, request: Request):
    from gaze_engine._shared.customer_db import create_project, get_customer
    if get_customer(cid) is None:
        raise HTTPException(404, f"客户 {cid} 不存在")
    data = await request.json()
    project_name = (data.get("project_name") or "").strip()
    if not project_name:
        raise HTTPException(400, "缺少 project_name")
    pid = create_project(
        cid, project_name,
        species=data.get("species", "human"),
        base_persona=data.get("base_persona", ""),
        base_emotion=data.get("base_emotion", ""),
        reference_photo=data.get("reference_photo", ""),
        custom_overrides=data.get("custom_overrides"),
    )
    return _json({"ok": True, "project_id": pid})


@app.post("/api/customer/{cid}/project/update")
async def customer_project_update(cid: str, request: Request):
    from gaze_engine._shared.customer_db import update_project
    data = await request.json()
    pid = data.get("project_id", "").strip()
    if not pid:
        raise HTTPException(400, "缺少 project_id")
    ok = update_project(cid, pid, **{k: data[k] for k in data if k not in ("customer_id", "project_id")})
    return _json({"ok": ok})


@app.post("/api/customer/{cid}/project/delete")
async def customer_project_delete(cid: str, request: Request):
    from gaze_engine._shared.customer_db import delete_project
    data = await request.json()
    pid = data.get("project_id", "").strip()
    if not pid:
        raise HTTPException(400, "缺少 project_id")
    ok = delete_project(cid, pid)
    return _json({"ok": ok})


@app.post("/api/customer/{cid}/project/{pid}/save-adjustment")
async def customer_save_adjustment(cid: str, pid: str, request: Request):
    from gaze_engine._shared.customer_db import save_adjustment
    data = await request.json()
    packet = data.get("packet")
    if not packet:
        raise HTTPException(400, "缺少 packet")
    ver = save_adjustment(cid, pid, packet, note=data.get("note", ""), diff=data.get("diff"))
    if ver is None:
        raise HTTPException(404, "项目不存在")
    return _json({"ok": True, "version": ver})


@app.post("/api/customer-context/save")
async def customer_context_save(request: Request):
    from gaze_engine._shared.customer_db import save_workbench_context
    data = await request.json()
    ctx = save_workbench_context(
        customer_id=data.get("customer_id"),
        project_id=data.get("project_id"),
    )
    return _json({"ok": True, "context": ctx})


# ═══════════════════════════════════════════════════════════
# HTML 主页
# ═══════════════════════════════════════════════════════════
from fastapi.responses import HTMLResponse


@app.get("/")
@app.get("/index.html")
async def index():
    html_path = FRONTEND_DIR / "能量工作台.html"
    if html_path.is_file():
        return HTMLResponse(html_path.read_text("utf-8"))
    raise HTTPException(404, "能量工作台.html not found")


# ═══════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)