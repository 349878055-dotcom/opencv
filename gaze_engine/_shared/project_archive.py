"""项目客户资料归档 + 扩散引擎导出包。

落盘位置（相对 客户资产库/）：
  客户_{cid}/项目_{pid}_*/客户资料.json
  客户_{cid}/项目_{pid}_*/输出/扩散引擎包/
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asset_lib import (
    customer_dir,
    customer_info_path,
    customer_ref_photos_dir,
    diffusion_bundle_dir,
    project_dir,
    project_output_dir,
    project_profile_path,
)

PROFILE_SCHEMA = "project_profile_v1"
MANIFEST_SCHEMA = "diffusion_bundle_v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pad_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """从 packet / baked.slider_packet 提取 PAD 归档块。"""
    for block in (
        payload.get("packet"),
        (payload.get("baked") or {}).get("slider_packet"),
    ):
        if not isinstance(block, dict):
            continue
        pad = block.get("pad")
        if isinstance(pad, dict) and "P" in pad:
            return pad
    return None


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_project_profile(
    customer_id: str,
    project_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """写入/更新 客户资料.json，返回完整档案 dict。"""
    from gaze_engine._shared.customer_db import get_customer, get_project

    customer = get_customer(customer_id) or {}
    project = get_project(customer_id, project_id) or {}
    out_dir = project_output_dir(customer_id, project_id)
    bundle = diffusion_bundle_dir(customer_id, project_id)

    files: dict[str, Any] = {}
    for name in (
        "01_滑杆包.json",
        "03_工程底模.mp4",
        "03_工程底模.meta.json",
        "04_Prompt.txt",
        "05_扩散节拍表.txt",
        "wan_positive.txt",
        "wan_negative.txt",
    ):
        fp = out_dir / name
        if fp.is_file():
            files[name] = {
                "exists": True,
                "size": fp.stat().st_size,
                "path": str(fp),
            }

    calib_path = project_dir(customer_id, project_id) / "手动标定.json"
    if calib_path.is_file():
        files["手动标定.json"] = {"exists": True, "path": str(calib_path)}

    profile: dict[str, Any] = {
        "schema": PROFILE_SCHEMA,
        "saved_at": _now_iso(),
        "customer_id": customer_id,
        "project_id": project_id,
        "customer": {
            "display_name": customer.get("display_name", ""),
            "preferred_species": customer.get("preferred_species", ""),
            "breed": customer.get("breed", ""),
            "contact": customer.get("contact", ""),
        },
        "project": {
            "project_name": project.get("project_name", ""),
            "species": project.get("species") or payload.get("species") or "",
            "reference_photo": project.get("reference_photo") or payload.get("photo_name") or "",
            "base_emotion": project.get("base_emotion", ""),
            "base_persona": project.get("base_persona", ""),
        },
        "creative": {
            "nl": payload.get("nl") or "",
            "emotion": payload.get("emotion") or payload.get("active_emotion") or "",
            "breed": payload.get("breed") or payload.get("active_style") or "",
            "action": payload.get("action") or "",
            "split": payload.get("split"),
            "route": payload.get("route"),
            "pad": _pad_from_payload(payload),
        },
        "pipeline": {
            "revision": (payload.get("baked") or {}).get("revision")
            or payload.get("revision")
            or "",
            "baked_mood": (payload.get("baked") or {}).get("mood")
            or (payload.get("baked") or {}).get("gaze_emotion_id")
            or "",
            "pad_layer": "S1",
        },
        "wan": {
            "positive_len": len(payload.get("wan_positive_clip") or payload.get("wan_positive") or ""),
            "negative_len": len(payload.get("wan_negative_clip") or payload.get("wan_negative") or ""),
        },
        "paths": {
            "customer_root": str(customer_dir(customer_id)),
            "project_root": str(project_dir(customer_id, project_id)),
            "output_dir": str(out_dir),
            "bundle_dir": str(bundle),
            "customer_info": str(customer_info_path(customer_id)),
            "profile_file": str(project_profile_path(customer_id, project_id)),
        },
        "files": files,
        "note": payload.get("note") or "",
    }

    _write_json(project_profile_path(customer_id, project_id), profile)
    return profile


def _copy_reference_photo(customer_id: str, project_id: str, dest: Path) -> str:
    from gaze_engine._shared.customer_db import get_project

    proj = get_project(customer_id, project_id) or {}
    photo_name = (proj.get("reference_photo") or "").strip()
    candidates: list[Path] = []
    if photo_name:
        candidates.append(customer_ref_photos_dir(customer_id) / photo_name)
        candidates.append(project_dir(customer_id, project_id) / "参考素材" / photo_name)
    ref_dir = project_dir(customer_id, project_id) / "参考素材"
    if ref_dir.is_dir():
        for f in sorted(ref_dir.iterdir()):
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                candidates.append(f)
                break

    for src in candidates:
        if src.is_file():
            shutil.copy2(src, dest)
            return src.name
    return ""


def build_diffusion_bundle(
    customer_id: str,
    project_id: str,
    *,
    prompt_04: str = "",
    wan_positive: str = "",
    wan_negative: str = "",
    include_profile: bool = True,
) -> dict[str, Any]:
    """组装 输出/扩散引擎包/，供 AutoDL / Agent 直接 scp。"""
    from gaze_engine.pomot.assembler import DiffusionPromptAssembler

    out = project_output_dir(customer_id, project_id)
    bundle = diffusion_bundle_dir(customer_id, project_id)
    bundle.mkdir(parents=True, exist_ok=True)

    prompt_src = out / "04_Prompt.txt"
    if prompt_04:
        (out / "04_Prompt.txt").write_text(prompt_04, encoding="utf-8")
        prompt_text = prompt_04
    elif prompt_src.is_file():
        prompt_text = prompt_src.read_text(encoding="utf-8")
    else:
        prompt_text = ""

    if prompt_text and (not wan_positive or not wan_negative):
        clips = DiffusionPromptAssembler.split_for_wan(prompt_text)
        wan_positive = wan_positive or clips["positive"]
        wan_negative = wan_negative or clips["negative"]

    if wan_positive:
        (out / "wan_positive.txt").write_text(wan_positive, encoding="utf-8")
    if wan_negative:
        (out / "wan_negative.txt").write_text(wan_negative, encoding="utf-8")

    copied: dict[str, str] = {}
    for src_name, dst_name in (
        ("03_工程底模.mp4", "03_工程底模.mp4"),
        ("04_Prompt.txt", "04_Prompt.txt"),
        ("wan_positive.txt", "wan_positive.txt"),
        ("wan_negative.txt", "wan_negative.txt"),
    ):
        src = out / src_name
        dst = bundle / dst_name
        if src.is_file():
            shutil.copy2(src, dst)
            copied[dst_name] = str(dst)

    start_dest = bundle / "start_image.jpg"
    ref_name = _copy_reference_photo(customer_id, project_id, start_dest)
    if ref_name:
        copied["start_image.jpg"] = str(start_dest)

    profile = None
    if include_profile and project_profile_path(customer_id, project_id).is_file():
        profile = json.loads(
            project_profile_path(customer_id, project_id).read_text(encoding="utf-8")
        )
        shutil.copy2(
            project_profile_path(customer_id, project_id),
            bundle / "客户资料.json",
        )
        copied["客户资料.json"] = str(bundle / "客户资料.json")

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "built_at": _now_iso(),
        "customer_id": customer_id,
        "project_id": project_id,
        "frame_count": 150,
        "fps": 30,
        "files": copied,
        "ready_for_diffusion": bool(
            copied.get("03_工程底模.mp4") and copied.get("04_Prompt.txt")
        ),
        "usage": "整包 scp 到 AutoDL；start_image + 03 MP4 + wan_positive/negative 进 Wan Fun Control",
        "profile_revision": (profile or {}).get("pipeline", {}).get("revision", ""),
    }
    _write_json(bundle / "manifest.json", manifest)
    copied["manifest.json"] = str(bundle / "manifest.json")

    return {
        "bundle_dir": str(bundle),
        "manifest": manifest,
        "files": copied,
    }
