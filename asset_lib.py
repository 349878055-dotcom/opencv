"""预设资产 + 客户资产路径工具。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PKG = Path(__file__).resolve().parent
ASSET_LIB = PKG / "预设资产"
# ── 预设资产顶层目录（两大分类）──
EMOTION_PRESETS_DIR = ASSET_LIB / "预设情绪包"     # 基本情绪包根目录
HUMAN_PRESETS_DIR = EMOTION_PRESETS_DIR / "human"  # 人类16情绪基准值
CAT_PRESETS_DIR = EMOTION_PRESETS_DIR / "cat"      # 猫12情绪基准值
DOG_PRESETS_DIR = EMOTION_PRESETS_DIR / "dog"      # 狗10情绪基准值

STYLE_PACK_DIR = ASSET_LIB / "风格包"              # 风格偏移根目录
STYLE_HUMAN = STYLE_PACK_DIR / "human"             # 人类人格风格（9 archetype）
STYLE_CAT = STYLE_PACK_DIR / "cat"                 # 猫品种风格
STYLE_DOG = STYLE_PACK_DIR / "dog"                 # 狗品种风格

# 兼容旧路径（部分模块仍引用）
PERSONAS = ASSET_LIB / "人格包"                    # 旧路径，目录可能不存在
PERSONA_DIR = ASSET_LIB / "persona"                # 旧路径，目录可能不存在

DEFAULT_PERSONA_ID = "S01_林青霞_东方不败"
DEFAULT_GAZE_ID = "施压瞬间凝视"

def active_persona_id() -> str:
    return os.environ.get("ECURSOR_PERSONA_PACK", DEFAULT_PERSONA_ID).strip() or DEFAULT_PERSONA_ID

def active_gaze_id() -> str:
    return os.environ.get("ECURSOR_GAZE_EMOTION", DEFAULT_GAZE_ID).strip() or DEFAULT_GAZE_ID

def persona_dir(persona_id: str | None = None) -> Path:
    """人格包目录，优先 persona/（新），回退 人格包/（旧）。"""
    pid = persona_id or active_persona_id()
    new_path = PERSONA_DIR / pid
    if new_path.is_dir():
        return new_path
    return PERSONAS / pid

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


CUSTOMER_DB = PKG / "客户资产库"
CUSTOMER_PREFIX = "客户_"
PROJECT_PREFIX = "项目_"

def delivery_template_metadata(
    persona_id: str | None = None, gaze_id: str | None = None
) -> dict:
    """参考片反推 / 候选稿用的元数据壳（非稀疏关键帧真源）。"""
    from gaze_engine._shared.channel_contract import CANONICAL_KEYS

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
        PERSONA_DIR,
        PERSONAS,
        persona_dir(),
        gaze_root(),
        cmd_dir(),
        schematic_dir(),
        PREVIEW,
        WAN_FILM,
        LOGS,
        REF_DIR,
        CUSTOMER_DB,
    ):
        d.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 客户资产库路径工具（Step 1: 客户资料与预设资产分离）
# ═══════════════════════════════════════════════════════════

# ── 客户路径 ──

def customer_dir(customer_id: str) -> Path:
    """客户根目录，如 …/客户资产库/客户_C001/"""
    return CUSTOMER_DB / f"{CUSTOMER_PREFIX}{customer_id}"


def customer_info_path(customer_id: str) -> Path:
    return customer_dir(customer_id) / "客户信息.json"


def customer_ref_photos_dir(customer_id: str) -> Path:
    """客户参考素材目录。"""
    return customer_dir(customer_id) / "参考素材"


# ── 项目路径 ──

def project_dir(customer_id: str, project_id: str) -> Path:
    """客户项目目录，如 …/客户资产库/客户_C001/项目_P001_贵宾犬委屈/"""
    return customer_dir(customer_id) / f"{PROJECT_PREFIX}{project_id}"


def project_config_path(customer_id: str, project_id: str) -> Path:
    return project_dir(customer_id, project_id) / "项目配置.json"


def project_adjustments_path(customer_id: str, project_id: str) -> Path:
    return project_dir(customer_id, project_id) / "滑杆调整记录.json"


def project_output_dir(customer_id: str, project_id: str) -> Path:
    return project_dir(customer_id, project_id) / "输出"


def project_adjustment_dir(customer_id: str, project_id: str) -> Path:
    return project_dir(customer_id, project_id) / "调整过程"


# ── 客户枚举 ──

def parse_customer_id(dirname: str) -> str | None:
    """从文件夹名解析 customer_id，如 '客户_C001' → 'C001'"""
    if dirname.startswith(CUSTOMER_PREFIX):
        return dirname[len(CUSTOMER_PREFIX):]
    return None


def parse_project_id(dirname: str) -> str | None:
    """从文件夹名解析 project_id，如 '项目_P001_贵宾犬委屈' → 'P001'"""
    if dirname.startswith(PROJECT_PREFIX):
        parts = dirname.split("_", 2)
        if len(parts) >= 2:
            return parts[1]
    return None


def list_customer_ids() -> list[str]:
    """扫描客户资产库，返回所有 customer_id 列表。"""
    if not CUSTOMER_DB.is_dir():
        return []
    out: list[str] = []
    for child in sorted(CUSTOMER_DB.iterdir()):
        cid = parse_customer_id(child.name)
        if cid and child.is_dir():
            out.append(cid)
    return out


def list_project_ids(customer_id: str) -> list[str]:
    """列出客户下的所有项目 ID。"""
    root = customer_dir(customer_id)
    if not root.is_dir():
        return []
    out: list[str] = []
    for child in sorted(root.iterdir()):
        pid = parse_project_id(child.name)
        if pid and child.is_dir():
            out.append(pid)
    return out


def generate_customer_id() -> str:
    """自动生成下一个 customer_id: C001, C002, ..."""
    existing = list_customer_ids()
    nums = [int(cid[1:]) for cid in existing if cid.startswith("C") and cid[1:].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"C{next_num:03d}"


def generate_project_id(customer_id: str) -> str:
    """自动生成下一个 project_id: P001, P002, ..."""
    existing = list_project_ids(customer_id)
    nums = [int(pid[1:]) for pid in existing if pid.startswith("P") and pid[1:].isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return f"P{next_num:03d}"


# ═══════════════════════════════════════════════════════════
# 物种预设包读取（human / cat / dog）
# ═══════════════════════════════════════════════════════════

SPECIES_PRESET_DIRS: dict[str, Path] = {
    "human": HUMAN_PRESETS_DIR,
    "cat": CAT_PRESETS_DIR,
    "dog": DOG_PRESETS_DIR,
}


def _load_groups_neutral(dir_path: Path) -> tuple[list | None, dict | None]:
    """读取目录下的 _groups.json 和 _neutral.json。"""
    groups_file = dir_path / "_groups.json"
    neutral_file = dir_path / "_neutral.json"
    groups = None
    neutral = None
    if groups_file.is_file():
        try:
            groups = json.loads(groups_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    if neutral_file.is_file():
        try:
            neutral = json.loads(neutral_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return groups, neutral


def load_species_presets(species: str) -> dict[str, dict[str, Any]] | None:
    """加载指定物种的全部情绪预设。

    从 预设资产/{species}/ 读取所有 .json（跳过 _ 开头的元数据文件）。
    返回 {emotion_name: {note, macro, hold_seg, ear?}, ...}，None 表示目录不存在。
    """
    dir_path = SPECIES_PRESET_DIRS.get(species)
    if not dir_path or not dir_path.is_dir():
        return None
    out: dict[str, dict[str, Any]] = {}
    for child in sorted(dir_path.iterdir()):
        if child.suffix != ".json" or child.name.startswith("_"):
            continue
        try:
            data = json.loads(child.read_text(encoding="utf-8"))
            name = data.get("emotion", child.stem)
            entry: dict[str, Any] = {
                "note": data.get("note", ""),
                "macro": data["macro"],
                "hold_seg": data["hold_seg"],
            }
            if "ear" in data:
                entry["ear"] = data["ear"]
            out[name] = entry
        except (json.JSONDecodeError, KeyError):
            continue
    return out if out else None


def load_species_preset_groups(species: str) -> list[dict[str, Any]] | None:
    """加载指定物种的 _groups.json。"""
    dir_path = SPECIES_PRESET_DIRS.get(species)
    if not dir_path:
        return None
    g, _ = _load_groups_neutral(dir_path)
    return g


def load_species_preset_neutral(species: str) -> dict[str, Any] | None:
    """加载指定物种的 _neutral.json。"""
    dir_path = SPECIES_PRESET_DIRS.get(species)
    if not dir_path:
        return None
    _, n = _load_groups_neutral(dir_path)
    return n


# ── 兼容旧名（上一层添加的 load_generic_*，现重定向到 human）──

def load_generic_presets_from_files() -> dict[str, dict[str, Any]] | None:
    """（兼容旧名）→ human 物种预设。"""
    return load_species_presets("human")


def load_generic_preset_groups_from_files() -> list[dict[str, Any]] | None:
    """（兼容旧名）→ human 物种分组。"""
    return load_species_preset_groups("human")


def load_generic_preset_neutral_from_files() -> dict[str, Any] | None:
    """（兼容旧名）→ human 中性预设。"""
    return load_species_preset_neutral("human")

