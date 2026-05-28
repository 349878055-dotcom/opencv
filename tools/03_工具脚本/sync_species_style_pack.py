#!/usr/bin/env python3
"""从 breed_style_catalog.json 同步猫/狗品种 style.json 与 breed_matrix.json。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANNELS = [
    "blink", "brow_raise", "cornea_bulge", "eye_gloss", "eyebrow", "iris_scale",
    "lid_lower", "lid_upper", "pupil_scale", "pupil_x", "pupil_y", "squint",
]

SPECIES = {
    "cat": {
        "catalog": ROOT / "gaze_engine" / "cat" / "breed_style_catalog.json",
        "matrix": ROOT / "gaze_engine" / "cat" / "breed_matrix.json",
        "style_root": ROOT / "预设资产" / "风格包" / "cat",
        "matrix_key": "breed_personas",
    },
    "dog": {
        "catalog": ROOT / "gaze_engine" / "dog" / "breed_style_catalog.json",
        "matrix": ROOT / "gaze_engine" / "dog" / "breed_matrix.json",
        "style_root": ROOT / "预设资产" / "风格包" / "dog",
        "matrix_key": "breed_personas",
    },
}


def load_breeds(species: str) -> dict:
    path = SPECIES[species]["catalog"]
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["breeds"]


def validate_breeds(breeds: dict) -> list[str]:
    errors: list[str] = []
    for bid, entry in breeds.items():
        for key in ("base_offset", "scale_factor"):
            missing = set(CHANNELS) - set(entry[key])
            if missing:
                errors.append(f"{bid}.{key} 缺通道: {sorted(missing)}")
            for ch in CHANNELS:
                v = entry[key][ch]
                if not (0.0 <= v <= 1.0):
                    errors.append(f"{bid}.{key}.{ch}={v} 超出 [0,1]")
    return errors


def write_style_json(species: str, bid: str, entry: dict) -> Path:
    out_dir = SPECIES[species]["style_root"] / bid
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "style.json"
    doc = {
        "schema": "ecursor_style_v1",
        "id": bid,
        "label": entry["label"],
        "species": species,
        "notes": entry["notes"],
        "default_emotion": "",
        "base_offset": entry["base_offset"],
        "scale_factor": entry["scale_factor"],
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_matrix(species: str, breeds: dict) -> None:
    cfg = SPECIES[species]
    personas: dict = {}
    for bid, entry in breeds.items():
        row: dict = {
            "species": species,
            "label": entry["label"],
            "base_offset": entry["base_offset"],
            "scale_factor": entry["scale_factor"],
        }
        if entry.get("_reference"):
            row["_reference"] = entry["_reference"]
        for opt in ("template_scales", "template_structure"):
            if entry.get(opt):
                row[opt] = entry[opt]
        personas[bid] = row

    matrix = {
        "_schema_version": "1.0",
        "_description": f"{'猫' if species == 'cat' else '狗'}品种风格矩阵 — base_offset + scale_factor",
        "_note": f"真源 gaze_engine/{species}/breed_style_catalog.json；由 sync_species_style_pack.py 生成",
        "_frame_count": 150,
        cfg["matrix_key"]: personas,
    }
    cfg["matrix"].write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_species(species: str) -> int:
    breeds = load_breeds(species)
    errors = validate_breeds(breeds)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    for bid, entry in breeds.items():
        p = write_style_json(species, bid, entry)
        print(f"[{species}] style.json → {p.relative_to(ROOT)}")

    write_matrix(species, breeds)
    print(f"[{species}] matrix     → {SPECIES[species]['matrix'].relative_to(ROOT)}")
    print(f"[{species}] OK: {len(breeds)} breeds synced")
    return 0


def main() -> int:
    rc = 0
    for species in ("cat", "dog"):
        if sync_species(species) != 0:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
