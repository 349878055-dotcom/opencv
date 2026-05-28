"""客户资产库核心模块：客户/项目 CRUD + 当前滑杆包（无版本历史）+ 密码认证。

依赖 asset_lib.py 中的路径工具，使用独立的 客户资产库/ 目录存放客户私有数据，
与 预设资产/ 中的预设人格包完全分离。

用法::
    from gaze_engine._shared.customer_db import (
        create_customer, get_customer,
        create_project, get_project,
        save_adjustment, get_adjustment_history,
        verify_customer_password, update_customer_password,
    )
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asset_lib import (
    customer_dir,
    customer_info_path,
    customer_ref_photos_dir,
    customer_template_params_path,
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

from gaze_engine._shared.species_template import (
    SpeciesTemplate,
    species_default_template,
    adjust_template_for_breed,
    apply_customer_adjustments,
)


# ═══════════════════════════════════════════════════════════
# 客户信息 Schema
# ═══════════════════════════════════════════════════════════

CUSTOMER_SCHEMA = "customer_v2"
PROJECT_SCHEMA = "customer_project_v2"
ADJUSTMENT_SCHEMA = "slider_current_v1"
LEGACY_ADJUSTMENT_SCHEMA = "slider_adjustment_v1"
TEMPLATE_PARAMS_SCHEMA = "species_template_v1"


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
# 密码认证
# ═══════════════════════════════════════════════════════════


def _hash_password(password: str) -> str:
    """用 PBKDF2-SHA256 哈希密码，返回 salt$hash 格式。"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """验证密码是否匹配 stored 的 salt$hash 值。"""
    try:
        salt, stored_hash = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(dk.hex(), stored_hash)
    except (ValueError, AttributeError):
        return False


def verify_customer_password(customer_id: str, password: str) -> bool:
    """验证客户密码是否正确。"""
    info = get_customer(customer_id)
    if info is None:
        return False
    stored = info.get("password_hash", "")
    if not stored:
        return False
    return _verify_password(password, stored)


def update_customer_password(customer_id: str, new_password: str) -> bool:
    """更新客户密码。"""
    info = get_customer(customer_id)
    if info is None:
        return False
    info["password_hash"] = _hash_password(new_password)
    info["updated_at"] = _now_iso()
    _write_json(customer_info_path(customer_id), info)
    return True


def create_auth_token(customer_id: str) -> str:
    """生成登录令牌（token = customer_id + timestamp + HMAC）。"""
    secret = os.environ.get("AUTH_SECRET", "jintao_node_eye_dev_secret")
    ts = str(int(datetime.now(timezone.utc).timestamp()))
    raw = f"{customer_id}:{ts}"
    sig = hmac.new(secret.encode(), raw.encode(), "sha256").hexdigest()[:16]
    return f"{customer_id}:{ts}:{sig}"


def verify_auth_token(token: str) -> str | None:
    """验证登录令牌，返回 customer_id 或 None。"""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        cid, ts, sig = parts
        secret = os.environ.get("AUTH_SECRET", "jintao_node_eye_dev_secret")
        raw = f"{cid}:{ts}"
        expected = hmac.new(secret.encode(), raw.encode(), "sha256").hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        # 令牌有效期 7 天
        if int(datetime.now(timezone.utc).timestamp()) - int(ts) > 7 * 86400:
            return None
        return cid
    except (ValueError, IndexError):
        return None


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
    preferred_species: str = "",
    breed: str = "",
    template_adjustments: dict[str, float] | None = None,
    password: str = "",
) -> str:
    """创建新客户，返回 customer_id。

    Args:
        display_name: 客户显示名称（如"张三"）
        customer_id: 可选，不传则自动生成 C001, C002...
        contact: 联系备注
        default_persona: 默认人格包 ID
        default_emotion: 默认情绪 ID
        preferred_species: 已废弃；物种按项目设定，注册时不填
        breed: 品种 ID（如 "poodle_giant", "ragdoll_cat"）
        template_adjustments: 客户照片检测得到的底膜调整参数
        password: 登录密码（不传则无密码认证）

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
        "breed": breed,
        "password_hash": _hash_password(password) if password else "",
    }
    _ensure_dir(customer_dir(cid))
    _ensure_dir(customer_ref_photos_dir(cid))
    _write_json(customer_info_path(cid), info)

    # 底膜模板在标定时按项目物种写入，注册时不绑定物种
    if preferred_species:
        _save_template_params(cid, preferred_species, breed, template_adjustments)

    return cid


# ═══════════════════════════════════════════════════════════
# 物种底膜模板 CRUD
# ═══════════════════════════════════════════════════════════

def _save_template_params(
    customer_id: str,
    species: str,
    breed: str = "",
    adjustments: dict[str, float] | None = None,
) -> dict[str, Any]:
    """保存客户的完整底膜模板参数（物种默认 + 品种偏移 + 客户调整）。"""
    # 1. 物种默认
    t = species_default_template(species)
    # 2. 品种偏移
    t = adjust_template_for_breed(t, species, breed or None)
    # 3. 客户调整
    t = apply_customer_adjustments(t, adjustments)

    data = {
        "schema": TEMPLATE_PARAMS_SCHEMA,
        "customer_id": customer_id,
        "species": species,
        "breed": breed,
        "params": t.to_dict(),
        "updated_at": _now_iso(),
    }
    _write_json(customer_template_params_path(customer_id), data)
    return data


def get_template_params(customer_id: str) -> SpeciesTemplate | None:
    """读取客户保存的底膜模板参数，不存在则返回 None。"""
    data = _read_json(customer_template_params_path(customer_id))
    if not data or not data.get("params"):
        return None
    return SpeciesTemplate.from_dict(data["params"])


def get_template_breed(customer_id: str) -> str:
    """读取标定记录绑定的品种 id（猫/狗），无则返回空串。"""
    data = _read_json(customer_template_params_path(customer_id))
    if not data:
        return ""
    return str(data.get("breed") or "").strip()


def get_customer_species_and_breed(customer_id: str) -> tuple[str, str]:
    """获取客户偏好的物种和品种。"""
    info = get_customer(customer_id)
    species = (info or {}).get("preferred_species", "human")
    breed = (info or {}).get("breed", "")
    return species, breed


def get_effective_template(customer_id: str) -> SpeciesTemplate:
    """获取客户的有效底膜模板。

    优先级：客户已保存模板 > 物种默认 + 品种偏移 > 物种默认
    """
    cached = get_template_params(customer_id)
    if cached is not None:
        return cached

    # 无缓存则从客户信息重建
    species, breed = get_customer_species_and_breed(customer_id)
    t = species_default_template(species)
    t = adjust_template_for_breed(t, species, breed or None)
    return t


def update_template_params(
    customer_id: str,
    adjustments: dict[str, float] | None,
) -> dict[str, Any] | None:
    """更新客户的底膜模板调整参数。

    Args:
        customer_id: 客户 ID
        adjustments: 要更新的参数 dict（只更新传入的字段，不传的保留）

    Returns:
        保存后的完整数据，客户不存在返回 None
    """
    info = get_customer(customer_id)
    if info is None:
        return None

    species = info.get("preferred_species", "human")
    breed = info.get("breed", "")

    # 读取已有参数，叠加上去
    existing = get_template_params(customer_id)
    if existing is not None:
        t = apply_customer_adjustments(existing, adjustments)
    else:
        t = species_default_template(species)
        t = adjust_template_for_breed(t, species, breed or None)
        t = apply_customer_adjustments(t, adjustments)

    data = {
        "schema": TEMPLATE_PARAMS_SCHEMA,
        "customer_id": customer_id,
        "species": species,
        "breed": breed,
        "params": t.to_dict(),
        "updated_at": _now_iso(),
    }
    _write_json(customer_template_params_path(customer_id), data)
    return data


# ═══════════════════════════════════════════════════════════
# 客户更新（扩展允许 breed 和 template_adjustments）
# ═══════════════════════════════════════════════════════════


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


def resolve_customer_login(login: str) -> tuple[str | None, str | None]:
    """按客户 ID（如 C006）或显示名称（如 金涛）解析登录目标。

    Returns:
        (customer_id, error_message) — 成功时 error 为 None
    """
    key = (login or "").strip()
    if not key:
        return None, "缺少客户ID或密码"

    if get_customer(key):
        return key, None

    matches = [
        c for c in list_customers()
        if (c.get("display_name") or "").strip() == key
    ]
    if len(matches) == 1:
        return matches[0]["customer_id"], None
    if len(matches) > 1:
        ids = "、".join(c["customer_id"] for c in matches)
        return None, f"名称「{key}」有 {len(matches)} 个账号（{ids}），请用客户 ID 登录"
    return None, "客户不存在（请填 C00x 编号，不是显示名称）"


def update_customer(customer_id: str, **kwargs) -> bool:
    """更新客户信息字段。可更新字段：
    display_name, contact, default_persona, default_emotion,
    preferred_species, breed, template_adjustments
    """
    info = get_customer(customer_id)
    if info is None:
        return False
    allowed = {"display_name", "contact", "default_persona",
               "default_emotion", "preferred_species", "breed"}
    changed = False
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            info[k] = v
            changed = True
    if changed:
        info["updated_at"] = _now_iso()
        _write_json(customer_info_path(customer_id), info)

    # 如果传了 template_adjustments，独立保存到底膜模板文件
    adjustments = kwargs.get("template_adjustments")
    if adjustments is not None:
        update_template_params(customer_id, adjustments)
        changed = True

    return changed


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

    # 初始化当前滑杆包占位（无版本历史）
    adjustments = {
        "schema": ADJUSTMENT_SCHEMA,
        "project_id": pid,
        "customer_id": customer_id,
        "saved_at": "",
        "note": "",
        "packet": None,
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
# 滑杆包（仅保留当前一份，无中间过程版本）
# ═══════════════════════════════════════════════════════════

def _clear_adjustment_snapshots(customer_id: str, project_id: str) -> None:
    """删除旧版「调整过程/调整_XX.json」快照文件。"""
    adj_dir = project_adjustment_dir(customer_id, project_id)
    if not adj_dir.is_dir():
        return
    for f in adj_dir.glob("调整_*.json"):
        try:
            f.unlink()
        except OSError:
            pass


def save_adjustment(
    customer_id: str,
    project_id: str,
    packet: dict,
    *,
    note: str = "",
    diff: dict | None = None,
    extra: dict | None = None,
) -> int | None:
    """覆盖写入当前滑杆包（客户点「保存」时调用，不追加版本历史）。

    diff/extra 仅写入 note 旁注，兼容旧 API 调用方。

    Returns:
        1 表示已保存当前包；项目不存在时返回 None。
    """
    if get_project(customer_id, project_id) is None:
        return None

    record: dict[str, Any] = {
        "schema": ADJUSTMENT_SCHEMA,
        "project_id": project_id,
        "customer_id": customer_id,
        "saved_at": _now_iso(),
        "note": note or "",
        "packet": packet,
    }
    if diff:
        record["diff"] = diff
    if extra:
        record["extra"] = extra

    _write_json(project_adjustments_path(customer_id, project_id), record)
    _clear_adjustment_snapshots(customer_id, project_id)
    return 1


def get_adjustment_history(
    customer_id: str, project_id: str
) -> list[dict]:
    """兼容旧接口：仅返回当前已保存的一包（无历史列表）。"""
    adjustments = _read_json(project_adjustments_path(customer_id, project_id))
    if not adjustments:
        return []
    schema = adjustments.get("schema", "")
    if schema == LEGACY_ADJUSTMENT_SCHEMA:
        return adjustments.get("history", [])
    pkt = adjustments.get("packet")
    if pkt:
        return [{
            "version": 1,
            "timestamp": adjustments.get("saved_at", ""),
            "note": adjustments.get("note", ""),
            "packet": pkt,
        }]
    return []


def load_adjustment(
    customer_id: str, project_id: str, version: int | None = None
) -> dict | None:
    """加载当前滑杆包（version 参数仅兼容旧调用，忽略非 1 的版本号）。"""
    adjustments = _read_json(project_adjustments_path(customer_id, project_id))
    if not adjustments:
        return None

    schema = adjustments.get("schema", "")
    if schema == LEGACY_ADJUSTMENT_SCHEMA:
        history = adjustments.get("history") or []
        if not history:
            return None
        if version is not None:
            for entry in history:
                if entry.get("version") == version:
                    return entry.get("packet")
            return None
        return history[-1].get("packet")

    if version is not None and version != 1:
        return None
    return adjustments.get("packet")


def get_current_adjustment_version(
    customer_id: str, project_id: str
) -> int:
    """当前是否已有保存的滑杆包：0=无，1=有。"""
    return 1 if load_adjustment(customer_id, project_id) else 0


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
