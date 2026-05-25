"""客户资产库核心模块：客户/项目 CRUD + 滑杆调整版本管理。

依赖 asset_lib.py 中的路径工具，使用独立的 客户资产库/ 目录存放客户私有数据，
与 预设资产/ 中的预设人格包完全分离。

用法::
    from gaze_engine._shared.customer_db import (
        create_customer, get_customer,
        create_project, get_project,
        save_adjustment, get_adjustment_history,
    )
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
    generate_customer_id,
    generate_project_id,
    list_customer_ids,
    list_project_ids,
    project_adjustment_dir,
    project_adjustments_path,
    project_config_path,
    project_dir,
    project_output_dir,
)


# ═══════════════════════════════════════════════════════════
# 客户信息 Schema
# ═══════════════════════════════════════════════════════════

CUSTOMER_SCHEMA = "customer_v1"
PROJECT_SCHEMA = "customer_project_v1"
ADJUSTMENT_SCHEMA = "slider_adjustment_v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# ═══════════════════════════════════════════════════════════
# 客户 CRUD
# ═══════════════════════════════════════════════════════════

def create_customer(
    display_name: str,
    *,
    customer_id: str | None = None,
    contact: str = "",
    default_persona: str = "",
    default_emotion: str = "",
    preferred_species: str = "human",
) -> str:
    """创建新客户，返回 customer_id。

    Args:
        display_name: 客户显示名称（如"张三"）
        customer_id: 可选，不传则自动生成 C001, C002...
        contact: 联系备注
        default_persona: 默认人格包 ID
        default_emotion: 默认情绪 ID
        preferred_species: 偏好的物种（human/cat/dog）

    Returns:
        customer_id（如 "C001"）
    """
    cid = customer_id or generate_customer_id()
    info = {
        "schema": CUSTOMER_SCHEMA,
        "customer_id": cid,
        "display_name": display_name,
        "contact": contact,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "default_persona": default_persona,
        "default_emotion": default_emotion,
        "preferred_species": preferred_species,
    }
    _ensure_dir(customer_dir(cid))
    _ensure_dir(customer_ref_photos_dir(cid))
    _write_json(customer_info_path(cid), info)
    return cid


def get_customer(customer_id: str) -> dict | None:
    """查询客户信息，不存在返回 None。"""
    info = _read_json(customer_info_path(customer_id))
    if not info or not info.get("customer_id"):
        return None
    return info


def list_customers() -> list[dict]:
    """列出所有客户信息列表。"""
    return [get_customer(cid) or {"customer_id": cid, "display_name": cid}
            for cid in list_customer_ids()]


def update_customer(customer_id: str, **kwargs) -> bool:
    """更新客户信息字段。可更新字段：
    display_name, contact, default_persona, default_emotion, preferred_species
    """
    info = get_customer(customer_id)
    if info is None:
        return False
    allowed = {"display_name", "contact", "default_persona",
               "default_emotion", "preferred_species"}
    changed = False
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            info[k] = v
            changed = True
    if changed:
        info["updated_at"] = _now_iso()
        _write_json(customer_info_path(customer_id), info)
    return True


def delete_customer(customer_id: str) -> bool:
    """删除客户及所有数据。"""
    d = customer_dir(customer_id)
    if not d.is_dir():
        return False
    shutil.rmtree(d)
    return True


# ═══════════════════════════════════════════════════════════
# 项目 CRUD
# ═══════════════════════════════════════════════════════════

def create_project(
    customer_id: str,
    project_name: str,
    species: str = "human",
    *,
    project_id: str | None = None,
    base_persona: str = "",
    base_emotion: str = "",
    reference_photo: str = "",
    custom_overrides: dict | None = None,
    pipeline_version: int = 11,
) -> str | None:
    """为客户创建新项目，返回 project_id。

    Args:
        customer_id: 客户 ID
        project_name: 项目名称（如"贵宾犬委屈表情"）
        species: 物种（human/cat/dog）
        project_id: 可选，不传则自动生成 P001...
        base_persona: 基础人格包 ID
        base_emotion: 基础情绪 ID
        reference_photo: 参考照片路径（相对客户参考素材目录）
        custom_overrides: 客户自定义覆盖参数
        pipeline_version: 管线版本

    Returns:
        project_id（如 "P001"），若客户不存在返回 None
    """
    if get_customer(customer_id) is None:
        return None

    pid = project_id or generate_project_id(customer_id)
    config = {
        "schema": PROJECT_SCHEMA,
        "project_id": pid,
        "project_name": project_name,
        "customer_id": customer_id,
        "species": species,
        "base_persona": base_persona,
        "base_emotion": base_emotion,
        "reference_photo": reference_photo,
        "created_at": _now_iso(),
        "last_modified": _now_iso(),
        "pipeline_version": pipeline_version,
        "custom_overrides": custom_overrides or {},
    }
    _ensure_dir(project_dir(customer_id, pid))
    _ensure_dir(project_output_dir(customer_id, pid))
    _ensure_dir(project_adjustment_dir(customer_id, pid))
    _write_json(project_config_path(customer_id, pid), config)

    # 初始化空的调整记录
    adjustments = {
        "schema": ADJUSTMENT_SCHEMA,
        "project_id": pid,
        "customer_id": customer_id,
        "version": 0,
        "history": [],
        "current_version": 0,
    }
    _write_json(project_adjustments_path(customer_id, pid), adjustments)
    return pid


def get_project(customer_id: str, project_id: str) -> dict | None:
    """查询项目配置，不存在返回 None。"""
    return _read_json(project_config_path(customer_id, project_id)) or None


def list_projects(customer_id: str) -> list[dict]:
    """列出客户下所有项目配置列表。"""
    return [get_project(customer_id, pid) or {"project_id": pid}
            for pid in list_project_ids(customer_id)]


def update_project(customer_id: str, project_id: str, **kwargs) -> bool:
    """更新项目配置字段。"""
    config = get_project(customer_id, project_id)
    if config is None:
        return False
    allowed = {"project_name", "species", "base_persona", "base_emotion",
               "reference_photo", "custom_overrides", "pipeline_version"}
    changed = False
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            config[k] = v
            changed = True
    if changed:
        config["last_modified"] = _now_iso()
        _write_json(project_config_path(customer_id, project_id), config)
    return True


def delete_project(customer_id: str, project_id: str) -> bool:
    """删除项目及所有输出数据。"""
    d = project_dir(customer_id, project_id)
    if not d.is_dir():
        return False
    shutil.rmtree(d)
    return True


# ═══════════════════════════════════════════════════════════
# 滑杆调整版本管理
# ═══════════════════════════════════════════════════════════

def save_adjustment(
    customer_id: str,
    project_id: str,
    packet: dict,
    *,
    note: str = "",
    diff: dict | None = None,
    extra: dict | None = None,
) -> int | None:
    """保存一次滑杆调整快照，返回新版本号。

    Args:
        customer_id: 客户 ID
        project_id: 项目 ID
        packet: 完整 SliderPacket 的 dict 表示
        note: 本次调整说明
        diff: 相对上次的变更描述（如 {"macro.power": "+15"}）
        extra: 额外元数据

    Returns:
        新版本号（1-based），若项目不存在返回 None
    """
    adjustments = _read_json(project_adjustments_path(customer_id, project_id))
    if not adjustments or not adjustments.get("schema"):
        return None

    version = adjustments["current_version"] + 1
    entry: dict[str, Any] = {
        "version": version,
        "timestamp": _now_iso(),
        "note": note or "",
        "packet": packet,
    }
    if diff:
        entry["diff"] = diff
    if extra:
        entry["extra"] = extra

    adjustments["version"] = version
    adjustments["current_version"] = version
    adjustments["history"].append(entry)

    _write_json(project_adjustments_path(customer_id, project_id), adjustments)

    # 同时保存独立版本文件（便于外部直接引用）
    version_file = project_adjustment_dir(customer_id, project_id) / f"调整_{version:02d}.json"
    _write_json(version_file, entry)

    return version


def get_adjustment_history(
    customer_id: str, project_id: str
) -> list[dict]:
    """获取项目的完整调整历史。"""
    adjustments = _read_json(project_adjustments_path(customer_id, project_id))
    if not adjustments or not adjustments.get("schema"):
        return []
    return adjustments.get("history", [])


def load_adjustment(
    customer_id: str, project_id: str, version: int | None = None
) -> dict | None:
    """加载指定版本的滑杆包。

    Args:
        customer_id: 客户 ID
        project_id: 项目 ID
        version: 版本号，None 表示加载最新版

    Returns:
        该版本的 packet dict，若不存在返回 None
    """
    adjustments = _read_json(project_adjustments_path(customer_id, project_id))
    if not adjustments or not adjustments.get("history"):
        return None

    history = adjustments["history"]
    if version is not None:
        for entry in history:
            if entry.get("version") == version:
                return entry.get("packet")
        return None

    # 加载最新版
    if history:
        return history[-1].get("packet")
    return None


def get_current_adjustment_version(
    customer_id: str, project_id: str
) -> int:
    """获取当前调整版本号（0 = 无调整）。"""
    adjustments = _read_json(project_adjustments_path(customer_id, project_id))
    if not adjustments:
        return 0
    return adjustments.get("current_version", 0)


# ═══════════════════════════════════════════════════════════
# 工作台上下文（当前活跃的客户/项目）
# ═══════════════════════════════════════════════════════════

WORKBENCH_CONTEXT_KEY = "ecursor_customer_context"
ACTIVE_CONTEXT_PATH: Path | None = None


def set_active_context_path(path: str | Path) -> None:
    """设置工作台上下文文件路径（由 serve_workbench.py 初始化时调用）。"""
    global ACTIVE_CONTEXT_PATH
    ACTIVE_CONTEXT_PATH = Path(path)


def _context_path() -> Path:
    if ACTIVE_CONTEXT_PATH:
        return ACTIVE_CONTEXT_PATH
    from asset_lib import PKG
    return PKG / "tools" / "04_缓存数据" / "customer_context.json"


def save_workbench_context(
    customer_id: str | None,
    project_id: str | None = None,
) -> dict:
    """保存当前工作台上下文（当前正在为哪个客户/项目工作）。

    Returns:
        保存后的上下文 dict
    """
    ctx = {
        "customer_id": customer_id or "",
        "project_id": project_id or "",
        "updated_at": _now_iso(),
    }
    _write_json(_context_path(), ctx)
    return ctx


def load_workbench_context() -> dict:
    """加载当前工作台上下文。"""
    return _read_json(_context_path())
