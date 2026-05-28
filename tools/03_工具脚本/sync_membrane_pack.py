#!/usr/bin/env python3
"""从 预设资产/底膜包/{species}/breeds/*.json 同步品种几何偏移到 breed_style_catalog + breed_matrix。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEMBRANE_ROOT = ROOT / "预设资产" / "底膜包"
SPECIES_CFG = {
    "dog": {
        "catalog": ROOT / "gaze_engine" / "dog" / "breed_style_catalog.json",
        "breeds_dir": MEMBRANE_ROOT / "dog" / "breeds",
    },
    "cat": {
        "catalog": ROOT / "gaze_engine" / "cat" / "breed_style_catalog.json",
        "breeds_dir": MEMBRANE_ROOT / "cat" / "breeds",
    },
}


def load_breed_membrane_files(species: str) -> dict[str, dict]:
    breeds_dir = SPECIES_CFG[species]["breeds_dir"]
    out: dict[str, dict] = {}
    if not breeds_dir.is_dir():
        return out
    for path in sorted(breeds_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        bid = doc.get("breed_id") or path.stem
        out[bid] = doc
    return out


def merge_into_catalog(species: str) -> tuple[int, list[str]]:
    catalog_path = SPECIES_CFG[species]["catalog"]
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    breeds = catalog.get("breeds") or {}
    membrane = load_breed_membrane_files(species)
    warnings: list[str] = []

    for bid, mem in membrane.items():
        if bid not in breeds:
            warnings.append(f"{species}/{bid}: 底膜包有记录但 breed_style_catalog 无此 id，已跳过")
            continue
        entry = breeds[bid]
        ref = mem.get("_reference")
        if ref:
            entry["_reference"] = ref
        if mem.get("template_scales"):
            entry["template_scales"] = mem["template_scales"]
        if mem.get("template_structure"):
            entry["template_structure"] = mem["template_structure"]
        note = mem.get("membrane_notes")
        if note:
            prev = (entry.get("notes") or "").strip()
            tag = f"[底膜] {note}"
            entry["notes"] = f"{prev} · {tag}" if prev and tag not in prev else (prev or tag)

    missing = set(breeds) - set(membrane)
    for bid in sorted(missing):
        warnings.append(f"{species}/{bid}: 风格包有品种但 底膜包/breeds/ 缺文件")

    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(membrane), warnings


def main() -> int:
    import importlib.util

    spec_path = ROOT / "tools" / "03_工具脚本" / "sync_species_style_pack.py"
    spec = importlib.util.spec_from_file_location("sync_species_style_pack", spec_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    rc = 0
    for sp in ("dog", "cat"):
        n, warns = merge_into_catalog(sp)
        print(f"[membrane] {sp}: merged {n} breed offset files → catalog")
        for w in warns:
            print(f"  WARN: {w}")
        if mod.sync_species(sp) != 0:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
