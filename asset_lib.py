"""预设资产 + 客户资产路径工具。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PKG = Path(__file__).resolve().parent
ASSET_LIB = PKG / "预设资产"
# ── 预设资产顶层目录（两大分类）──
EMOTION_PACK_DIR = ASSET_LIB / "情绪包"          # macro + hold_seg（S1 E(t) 真源）
EMOTION_COORD_DIR = ASSET_LIB / "情绪坐标"        # PAD (P,A,D) 真源 · 按 species 分子目录
EMOTION_PRESETS_DIR = EMOTION_PACK_DIR           # 兼容旧常量名
# 跨物种共用情绪大类（目录在 情绪包/ 根下，非 {species}/ 内）
SHARED_EMOTION_CATEGORIES: tuple[str, ...] = ("委屈",)
HUMAN_PRESETS_DIR = EMOTION_PACK_DIR / "human"   # 人类16情绪
CAT_PRESETS_DIR = EMOTION_PACK_DIR / "cat"       # 猫12情绪
DOG_PRESETS_DIR = EMOTION_PACK_DIR / "dog"       # 狗10情绪

STYLE_PACK_DIR = ASSET_LIB / "风格包"              # 风格偏移根目录
STYLE_HUMAN = STYLE_PACK_DIR / "human"             # 人类人格风格（9 archetype）
STYLE_CAT = STYLE_PACK_DIR / "cat"                 # 猫品种风格
STYLE_DOG = STYLE_PACK_DIR / "dog"                 # 狗品种风格

MEMBRANE_PACK_DIR = ASSET_LIB / "底膜包"           # 几何骨架预设（物种默认）
MEMBRANE_HUMAN = MEMBRANE_PACK_DIR / "human"
MEMBRANE_CAT = MEMBRANE_PACK_DIR / "cat"
MEMBRANE_DOG = MEMBRANE_PACK_DIR / "dog"

# ── 运行时输出目录（管线中间产物）──
RUNTIME_DIR = PKG / "_runtime"

def cmd_dir() -> Path:
    """运行时输出目录（管线中间产物：包络/烘焙/节拍表等）。"""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR


# 02 烘焙落盘：每物种独立文件名（人类=真人律，来自 human_prior；狗/猫=各自管线）
BAKED_OUTPUT_BY_SPECIES: dict[str, str] = {
    "human": "02_烘焙_真人律.json",
    "dog": "02_烘焙_狗律.json",
    "cat": "02_烘焙_猫律.json",
}
# 旧版狗/猫误用「真人律」文件名，读取时回退，新写入不再使用
LEGACY_BAKED_FILENAME = "02_烘焙_真人律.json"


def baked_output_filename(species: str = "human") -> str:
    """物种 → 02 烘焙 JSON 文件名。"""
    sp = (species or "human").strip().lower()
    return BAKED_OUTPUT_BY_SPECIES.get(sp, BAKED_OUTPUT_BY_SPECIES["human"])


def baked_output_path(out_dir: Path | str, species: str = "human") -> Path:
    return Path(out_dir) / baked_output_filename(species)


def species_from_baked(baked: dict[str, Any] | None) -> str:
    """从 02 内容推断物种（写盘/读盘路由）。"""
    if not baked:
        return "human"
    sp = (baked.get("species") or "").strip().lower()
    if sp in BAKED_OUTPUT_BY_SPECIES:
        return sp
    schema = (baked.get("schema_version") or "").lower()
    if "dog" in schema:
        return "dog"
    if "cat" in schema:
        return "cat"
    return "human"


def resolve_baked_json_path(out_dir: Path | str, species: str = "") -> Path | None:
    """查找已存在的 02 烘焙文件：优先物种专名，再回退旧版统一名。"""
    root = Path(out_dir)
    candidates: list[Path] = []
    if species:
        candidates.append(baked_output_path(root, species))
    for sp in BAKED_OUTPUT_BY_SPECIES:
        p = baked_output_path(root, sp)
        if p not in candidates:
            candidates.append(p)
    legacy = root / LEGACY_BAKED_FILENAME
    if legacy not in candidates:
        candidates.append(legacy)
    for p in candidates:
        if p.is_file():
            return p
    return None


def write_baked_json(out_dir: Path | str, baked: dict[str, Any], *, species: str = "") -> Path:
    """按物种写入 02；狗/猫写入后删除误放在「真人律」名下的旧文件。"""
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    sp = (species or species_from_baked(baked)).strip().lower()
    target = baked_output_path(root, sp)
    target.write_text(json.dumps(baked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if sp != "human":
        legacy = root / LEGACY_BAKED_FILENAME
        if legacy.is_file() and legacy.resolve() != target.resolve():
            legacy.unlink()
    return target


def remove_baked_json_files(out_dir: Path | str) -> list[str]:
    """删除输出目录下所有 02 烘焙 JSON（门户不落盘策略）。"""
    root = Path(out_dir)
    if not root.is_dir():
        return []
    removed: list[str] = []
    for name in set(BAKED_OUTPUT_BY_SPECIES.values()) | {LEGACY_BAKED_FILENAME}:
        p = root / name
        if p.is_file():
            p.unlink()
            removed.append(name)
    return removed


def resolve_sparse_json(*, prefer_baked: bool = True, species: str = "") -> Path:
    """
    解析当前用于 05 节拍 / 示意图 的 02 路径。

    优先级：ECURSOR_SPARSE_JSON → 物种专名 02 → 其它物种 02 → 旧版真人律名。
    """
    explicit = os.environ.get("ECURSOR_SPARSE_JSON", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    sp = (species or os.environ.get("ECURSOR_SPECIES", "human")).strip().lower()
    runtime = cmd_dir()
    resolved = resolve_baked_json_path(runtime, sp)
    if resolved is not None:
        return resolved
    return baked_output_path(runtime, sp)


CUSTOMER_DB = PKG / "客户资产库"
CUSTOMER_PREFIX = "客户_"
PROJECT_PREFIX = "项目_"

def ensure_dirs() -> None:
    """确保必要的运行时与客户资产目录存在。"""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOMER_DB.mkdir(parents=True, exist_ok=True)


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


def project_profile_path(customer_id: str, project_id: str) -> Path:
    """项目客户资料归档（门户保存 / Agent 读取）。"""
    return project_dir(customer_id, project_id) / "客户资料.json"


def diffusion_bundle_dir(customer_id: str, project_id: str) -> Path:
    """扩散引擎导出包目录（MP4 + Prompt + Wan ± + manifest）。"""
    return project_output_dir(customer_id, project_id) / "扩散引擎包"


def project_adjustment_dir(customer_id: str, project_id: str) -> Path:
    return project_dir(customer_id, project_id) / "调整过程"


# ── 物种底膜模板参数 ──

def customer_template_params_path(customer_id: str) -> Path:
    """客户物种底膜模板参数路径（标定结果 · 非预设资产）。"""
    return customer_dir(customer_id) / "物种底膜模板.json"


def species_membrane_default_path(species: str) -> Path:
    """预设资产：物种默认底膜 JSON（只读真源）。"""
    sp = (species or "human").strip().lower()
    root = {
        "human": MEMBRANE_HUMAN,
        "cat": MEMBRANE_CAT,
        "dog": MEMBRANE_DOG,
    }.get(sp, MEMBRANE_HUMAN)
    return root / "species_default.json"


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


def _preset_id_from_path(dir_path: Path, file_path: Path) -> str:
    """物种目录内 preset id：子目录用 `委屈/变体3_迟疑试探`。"""
    rel = file_path.relative_to(dir_path)
    if rel.parent == Path("."):
        return file_path.stem
    return str(rel.with_suffix("")).replace("\\", "/")


def _shared_category_dir(category: str) -> Path:
    return EMOTION_PACK_DIR / category


def _shared_variant_path(category: str, variant_id: str) -> Path:
    return _shared_category_dir(category) / f"{variant_id}.json"


def _parse_category_preset_id(preset_id: str) -> tuple[str, str] | None:
    """`委屈/变体3_迟疑试探` → (category, variant_id)。"""
    if "/" not in preset_id:
        return None
    category, variant_id = preset_id.split("/", 1)
    if category not in SHARED_EMOTION_CATEGORIES or not variant_id:
        return None
    return category, variant_id


def _iter_emotion_json_files(dir_path: Path):
    """遍历物种情绪包（含子目录；跳过 _ 开头元数据；不含共用大类目录）。"""
    if not dir_path.is_dir():
        return
    for child in sorted(dir_path.rglob("*.json")):
        if child.name.startswith("_"):
            continue
        rel_parts = child.relative_to(dir_path).parts
        if rel_parts and rel_parts[0] in SHARED_EMOTION_CATEGORIES:
            continue
        yield _preset_id_from_path(dir_path, child), child


def _iter_shared_variant_files():
    """遍历共用大类下的变体 JSON（扁平，不含 species 子目录）。"""
    for category in SHARED_EMOTION_CATEGORIES:
        cat_dir = _shared_category_dir(category)
        if not cat_dir.is_dir():
            continue
        for child in sorted(cat_dir.glob("*.json")):
            if child.name.startswith("_"):
                continue
            preset_id = f"{category}/{child.stem}"
            yield preset_id, child


def _load_category_meta(category: str, species: str = "") -> dict[str, Any] | None:
    """读取共用大类 `_category.json`（位于 情绪包/{category}/）。"""
    shared = _shared_category_dir(category) / "_category.json"
    if not shared.is_file():
        return None
    try:
        return json.loads(shared.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _category_pad_for_species(meta: dict[str, Any], species: str) -> dict[str, Any] | None:
    category = str(meta.get("category") or meta.get("label") or "").strip()
    if category:
        coord = load_emotion_coord_pad(species, category)
        if coord:
            return coord
    by_sp = meta.get("pad_by_species")
    if isinstance(by_sp, dict) and species in by_sp:
        return by_sp[species]
    pad = meta.get("pad")
    if isinstance(pad, dict):
        return pad
    return None


def load_emotion_coord_pad(species: str, key: str) -> dict[str, Any] | None:
    """从 预设资产/情绪坐标/{species}/{key}.json 读取 pad 块。"""
    sp = (species or "human").strip().lower()
    name = (key or "").strip()
    if not name:
        return None
    path = EMOTION_COORD_DIR / sp / f"{name}.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    pad = raw.get("pad")
    return pad if isinstance(pad, dict) else None


def _resolve_coord_key(raw: dict[str, Any], preset_stem: str = "") -> str:
    category = str(raw.get("category") or "").strip()
    if category:
        return category
    for candidate in (raw.get("label"), raw.get("emotion"), preset_stem):
        c = str(candidate or "").strip()
        if c:
            return c
    return preset_stem


def _merge_category_pad(raw: dict[str, Any], species: str, dir_path: Path | None = None) -> dict[str, Any]:
    """变体/预设 JSON 无 pad 时，从 情绪坐标/ 或 _category.json 继承。"""
    if raw.get("pad"):
        return raw
    key = _resolve_coord_key(raw)
    coord_pad = load_emotion_coord_pad(species, key)
    if coord_pad:
        merged = dict(raw)
        merged["pad"] = coord_pad
        return merged
    category = str(raw.get("category") or "").strip()
    if not category:
        return raw
    meta = _load_category_meta(category, species)
    if not meta:
        return raw
    pad = _category_pad_for_species(meta, species)
    if not pad:
        return raw
    merged = dict(raw)
    merged["pad"] = pad
    return merged


def load_emotion_categories(species: str) -> list[dict[str, Any]]:
    """读取物种可用的共用情绪大类（三变体列表 + 该 species 的 PAD）。"""
    out: list[dict[str, Any]] = []
    for category in SHARED_EMOTION_CATEGORIES:
        meta = _load_category_meta(category, species)
        if not meta or meta.get("schema") != "emotion-category-v1":
            continue
        variants: list[dict[str, Any]] = []
        for v in meta.get("variants") or []:
            vid = str(v.get("id") or "")
            if not vid:
                continue
            preset_id = f"{category}/{vid}"
            variants.append({
                "id": preset_id,
                "variant": vid,
                "label": v.get("label") or vid,
                "subtitle": v.get("subtitle") or "",
                "aliases": v.get("aliases") or [],
            })
        if not variants:
            continue
        out.append({
            "id": category,
            "label": meta.get("label") or category,
            "note": meta.get("note") or "",
            "pad": _category_pad_for_species(meta, species),
            "variants": variants,
        })
    return out


def _merge_category_extras(raw: dict[str, Any], species: str) -> dict[str, Any]:
    """从 _category.json 注入 pad / ear（变体 JSON 不含这些块）。"""
    merged = _merge_category_pad(raw, species)
    if merged.get("ear"):
        return merged
    category = str(raw.get("category") or "").strip()
    if not category:
        return merged
    meta = _load_category_meta(category, species)
    if not meta:
        return merged
    ear_by = meta.get("ear_by_species")
    if isinstance(ear_by, dict) and species in ear_by:
        merged = dict(merged)
        merged["ear"] = ear_by[species]
    return merged


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
    for preset_id, child in _iter_emotion_json_files(dir_path):
        try:
            data = json.loads(child.read_text(encoding="utf-8"))
            data = _merge_category_extras(data, species)
            name = data.get("emotion", preset_id)
            entry: dict[str, Any] = {
                "note": data.get("note", ""),
                "macro": data["macro"],
                "hold_seg": data["hold_seg"],
                "preset_id": preset_id,
            }
            if data.get("category"):
                entry["category"] = data["category"]
            if data.get("variant"):
                entry["variant"] = data["variant"]
            if "ear" in data:
                entry["ear"] = data["ear"]
            if "pad" in data:
                entry["pad"] = data["pad"]
            out[name] = entry
        except (json.JSONDecodeError, KeyError):
            continue
    for preset_id, child in _iter_shared_variant_files():
        try:
            data = json.loads(child.read_text(encoding="utf-8"))
            data = _merge_category_extras(data, species)
            if not data.get("species"):
                data["species"] = species
            name = data.get("emotion", preset_id)
            if name in out:
                continue
            entry = {
                "note": data.get("note", ""),
                "macro": data["macro"],
                "hold_seg": data["hold_seg"],
                "preset_id": preset_id,
            }
            if data.get("category"):
                entry["category"] = data["category"]
            if data.get("variant"):
                entry["variant"] = data["variant"]
            if "ear" in data:
                entry["ear"] = data["ear"]
            if "pad" in data:
                entry["pad"] = data["pad"]
            out[name] = entry
        except (json.JSONDecodeError, KeyError):
            continue
    return out if out else None


def emotion_preset_path(species: str, preset_id: str) -> Path | None:
    """定位情绪包 JSON：共用大类 `委屈/变体N` 或物种目录内扁平 preset。"""
    parsed = _parse_category_preset_id(preset_id)
    if parsed:
        category, variant_id = parsed
        shared = _shared_variant_path(category, variant_id)
        if shared.is_file():
            return shared
    for category in SHARED_EMOTION_CATEGORIES:
        meta = _load_category_meta(category, species)
        if not meta:
            continue
        for v in meta.get("variants") or []:
            aliases = v.get("aliases") or []
            vid = str(v.get("id") or "")
            if preset_id in aliases or preset_id == f"{category}/{vid}":
                p = _shared_variant_path(category, vid)
                if p.is_file():
                    return p
    dir_path = SPECIES_PRESET_DIRS.get(species)
    if not dir_path or not dir_path.is_dir():
        return None
    direct = dir_path / f"{preset_id}.json"
    if direct.is_file():
        return direct
    nested = dir_path / preset_id.replace("/", os.sep)
    if nested.suffix != ".json":
        nested = nested.with_suffix(".json")
    if nested.is_file():
        return nested
    for preset_key, child in _iter_emotion_json_files(dir_path):
        try:
            raw = json.loads(child.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        aliases = raw.get("aliases") or []
        if (
            raw.get("emotion") == preset_id
            or raw.get("label") == preset_id
            or preset_key == preset_id
            or child.stem == preset_id
            or preset_id in aliases
        ):
            return child
        cat = str(raw.get("category") or "")
        var = str(raw.get("variant") or "")
        if cat and var and preset_id == f"{cat}/{var}":
            return child
    return None


def load_emotion_preset_raw(species: str, preset_id: str) -> dict[str, Any] | None:
    """从 预设资产/情绪包 读取完整 JSON（含 macro/hold/pad）。"""
    path = emotion_preset_path(species, preset_id)
    if not path:
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    raw = _merge_category_extras(raw, species)
    if not raw.get("species"):
        raw["species"] = species
    return raw


def load_emotion_slider_packet(species: str, preset_id: str):
    """从情绪包加载 SliderPacket（S1 pad 收口）。"""
    raw = load_emotion_preset_raw(species, preset_id)
    if not raw:
        return None
    from gaze_engine._shared.emotion_pad import ensure_pad_on_packet
    from gaze_engine._shared.slider_schema import SliderPacket

    pkt = SliderPacket.from_dict(raw)
    if not pkt.emotion or pkt.emotion == "s01_pressure":
        pkt.emotion = str(raw.get("emotion") or preset_id)
    pid = str(raw.get("preset_id") or preset_id).strip()
    if not pid and raw.get("category") and raw.get("variant"):
        pid = f"{raw['category']}/{raw['variant']}"
    pkt.preset_id = pid
    aliases = raw.get("aliases") or []
    pkt.display_alias = str(raw.get("display_alias") or (aliases[0] if aliases else ""))
    return ensure_pad_on_packet(pkt, species)


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
