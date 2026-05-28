#!/usr/bin/env python3
"""从 persona_style_catalog.json 同步九大人格 style.json、persona_matrix 与合同 §4 表。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "gaze_engine" / "human" / "persona_style_catalog.json"
STYLE_ROOT = ROOT / "预设资产" / "风格包" / "human"
MATRIX = ROOT / "gaze_engine" / "human" / "persona_matrix.json"
CONTRACT_DIR = ROOT / "合同" / "05_风格化" / "人"

CHANNELS = [
    "blink", "brow_raise", "cornea_bulge", "eye_gloss", "eyebrow", "iris_scale",
    "lid_lower", "lid_upper", "pupil_scale", "pupil_x", "pupil_y", "squint",
]


def load_catalog() -> dict:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    return data["personas"]


def write_style_json(pid: str, entry: dict) -> Path:
    out_dir = STYLE_ROOT / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "style.json"
    doc = {
        "schema": "ecursor_style_v1",
        "id": pid,
        "label": entry["label"],
        "species": "human",
        "notes": entry["notes"],
        "base_offset": entry["base_offset"],
        "scale_factor": entry["scale_factor"],
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_matrix(personas: dict) -> None:
    matrix = {
        "_schema_version": "1.0",
        "_description": "九大人格矩阵 — 人类戏剧表演人格偏置 + 缩放系数",
        "_note": "真源 gaze_engine/human/persona_style_catalog.json；由 sync_human_style_pack.py 生成",
        "_frame_count": 150,
        "personas": {
            pid: {
                "label": entry["label"],
                "base_offset": entry["base_offset"],
                "scale_factor": entry["scale_factor"],
            }
            for pid, entry in personas.items()
        },
    }
    MATRIX.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _table_block(title: str, values: dict[str, float]) -> str:
    lines = [f"### {title}", "", "| 通道 | 值 |", "|------|-----|"]
    for ch in CHANNELS:
        v = values[ch]
        lines.append(f"| `{ch}` | **{v:g}** |")
    lines.append("")
    return "\n".join(lines)


def patch_contract_md(pid: str, entry: dict) -> bool:
    md_path = CONTRACT_DIR / f"{pid}.md"
    if not md_path.is_file():
        return False
    text = md_path.read_text(encoding="utf-8")
    base_block = _table_block("4.2 base_offset（静态偏置）", entry["base_offset"])
    scale_block = _table_block("4.3 scale_factor（动态增益）", entry["scale_factor"])

    text = re.sub(
        r"### 4\.2 base_offset（静态偏置）\n\n\| 通道 \| 值 \|\n\|[-|]+\|\n(?:\| `[^`]+` \| \*\*[^*]+\*\* \|\n)+",
        base_block,
        text,
        count=1,
    )
    text = re.sub(
        r"### 4\.3 scale_factor（动态增益）\n\n\| 通道 \| 值 \|\n\|[-|]+\|\n(?:\| `[^`]+` \| \*\*[^*]+\*\* \|\n)+",
        scale_block,
        text,
        count=1,
    )
    # 去掉 label 占位后缀
    text = text.replace(f"| label | {entry['label']}（占位） |", f"| label | {entry['label']} |")
    md_path.write_text(text, encoding="utf-8")
    return True


def validate(personas: dict) -> list[str]:
    errors: list[str] = []
    for pid, entry in personas.items():
        for key in ("base_offset", "scale_factor"):
            missing = set(CHANNELS) - set(entry[key])
            if missing:
                errors.append(f"{pid}.{key} 缺通道: {sorted(missing)}")
        for ch in CHANNELS:
            for key in ("base_offset", "scale_factor"):
                v = entry[key][ch]
                if not (0.0 <= v <= 1.0):
                    errors.append(f"{pid}.{key}.{ch}={v} 超出 [0,1]")
    return errors


def main() -> int:
    personas = load_catalog()
    errors = validate(personas)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    for pid, entry in personas.items():
        p = write_style_json(pid, entry)
        print(f"style.json  → {p.relative_to(ROOT)}")
        if patch_contract_md(pid, entry):
            print(f"contract    → 合同/05_风格化/人/{pid}.md §4")

    write_matrix(personas)
    print(f"matrix      → {MATRIX.relative_to(ROOT)}")
    print(f"OK: {len(personas)} personas synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
