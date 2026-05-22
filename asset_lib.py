"""ecursor 资产库：人格包 → 情绪（如 施压瞬间凝视）→ 指令 / 预览 / 成片。"""
from __future__ import annotations

import json
import os
from pathlib import Path

PKG = Path(__file__).resolve().parent
ASSET_LIB = PKG / "资产库"
PERSONAS = ASSET_LIB / "人格包"

DEFAULT_PERSONA_ID = "S01_林青霞_东方不败"
DEFAULT_GAZE_ID = "施压瞬间凝视"

def active_persona_id() -> str:
    return os.environ.get("ECURSOR_PERSONA_PACK", DEFAULT_PERSONA_ID).strip() or DEFAULT_PERSONA_ID

def active_gaze_id() -> str:
    return os.environ.get("ECURSOR_GAZE_EMOTION", DEFAULT_GAZE_ID).strip() or DEFAULT_GAZE_ID

def persona_dir(persona_id: str | None = None) -> Path:
    return PERSONAS / (persona_id or active_persona_id())

def gaze_root(persona_id: str | None = None, gaze_id: str | None = None) -> Path:
    """人格包直下的一条情绪，如 …/S01_林青霞_东方不败/施压瞬间凝视/"""
    return persona_dir(persona_id) / (gaze_id or active_gaze_id())

def cmd_dir() -> Path:
    return gaze_root() / "指令"

def schematic_dir() -> Path:
    return gaze_root() / "示意图"

PREVIEW = gaze_root() / "预览"
WAN_FILM = gaze_root() / "成片"
LOGS = gaze_root() / "日志"

BAKED_JSON = cmd_dir() / "02_烘焙_真人律.json"
# 兼容旧脚本/环境变量名（现指向烘焙定稿）
SPARSE_JSON = BAKED_JSON
DENSE_INFER_JSON = cmd_dir() / "03_逐帧反推.json"
SPARSE_CANDIDATE_JSON = cmd_dir() / "02_候选_从参考片.json"
SPARSE_CANDIDATE_ENERGY_JSON = cmd_dir() / "02_候选_从滑杆.json"
PROMPT_TXT = cmd_dir() / "04_给视频生成的Prompt.txt"

REF_DIR = gaze_root() / "参考"

# 示意图标准文件名（改 02 后跑 scripts/s01_主验收示意图.sh）
def schematic_primary() -> Path:
    return schematic_dir() / "主验收_指令集示意图.png"

def schematic_ref_12ch() -> Path:
    return schematic_dir() / "参考_十二通道全轨.png"

PACK = cmd_dir()

def persona_manifest_path(persona_id: str | None = None) -> Path:
    return persona_dir(persona_id) / "人格包.json"

def emotion_manifest_path(persona_id: str | None = None, gaze_id: str | None = None) -> Path:
    return gaze_root(persona_id, gaze_id) / "情绪.json"

# 兼容旧名
gaze_manifest_path = emotion_manifest_path

def load_persona_manifest(persona_id: str | None = None) -> dict:
    p = persona_manifest_path(persona_id)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}

def load_emotion_manifest(persona_id: str | None = None, gaze_id: str | None = None) -> dict:
    p = emotion_manifest_path(persona_id, gaze_id)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}

def list_emotion_ids(persona_id: str | None = None) -> list[str]:
    """扫描人格包下含 情绪.json 的子文件夹。"""
    root = persona_dir(persona_id)
    if not root.is_dir():
        return []
    out: list[str] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "情绪.json").is_file():
            out.append(child.name)
    return out

def resolve_sparse_json(*, prefer_baked: bool = True) -> Path:
    """
    解析当前用于 05 节拍 / 示意图 的 02 路径。

    优先级：ECURSOR_SPARSE_JSON（若已设）→ 02_烘焙_真人律.json（存在且 prefer_baked）
    → 02_眼眉稀疏指令.json（手搓稀疏母版）。
    """
    explicit = os.environ.get("ECURSOR_SPARSE_JSON", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    if BAKED_JSON.is_file():
        return BAKED_JSON
    archive = cmd_dir() / "_archive" / "02_眼眉稀疏指令_母版.json"
    if archive.is_file():
        return archive
    return BAKED_JSON

def delivery_template_metadata(
    persona_id: str | None = None, gaze_id: str | None = None
) -> dict:
    """参考片反推 / 候选稿用的元数据壳（非稀疏关键帧真源）。"""
    from gaze_engine.channel_contract import CANONICAL_KEYS

    em = load_emotion_manifest(persona_id, gaze_id)
    gid = gaze_id or active_gaze_id()
    return {
        "schema_version": "0.2-envelope-metadata",
        "gaze_emotion_id": em.get("id") or gid,
        "template_id": em.get("template_id") or f"S01_{gid}",
        "character_ref": em.get("character_ref", ""),
        "mood": em.get("mood") or gid,
        "mood_tags": em.get("mood_tags") or [],
        "profile_hint": em.get("profile_hint", "cool_restrained"),
        "energy_phases": ["蓄力", "启动", "保持", "缓和"],
        "controls_doc": "contracts/全量帧指令集规范.md",
        "keys": list(CANONICAL_KEYS),
        "keys_active": list(CANONICAL_KEYS),
    }

def ensure_dirs() -> None:
    for d in (
        PERSONAS,
        persona_dir(),
        gaze_root(),
        cmd_dir(),
        schematic_dir(),
        PREVIEW,
        WAN_FILM,
        LOGS,
        REF_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)

