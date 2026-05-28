#!/usr/bin/env python3
"""导出全物种 04_Prompt 样例到 _runtime/prompt_samples/（供人工审定）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine.delivery_pipeline import run_species_delivery
from gaze_engine.dog.dog_pipeline import run_dog_pipeline
from gaze_engine.pomot.assembler import DiffusionPromptAssembler

DEFAULT_BREED = {"dog": "poodle_giant", "cat": "ragdoll_cat", "human": "魅惑者_温碧霞"}
SAMPLE_ACTION = "委屈地跑回笼子再回头看了一眼"


def export_species(species: str, out_root: Path) -> int:
    preset_dir = ROOT / "预设资产" / "情绪包" / species
    breed = DEFAULT_BREED.get(species, "")
    count = 0
    asm = DiffusionPromptAssembler()

    for f in sorted(preset_dir.glob("*.json")):
        if f.name.startswith("_"):
            continue
        raw = json.loads(f.read_text(encoding="utf-8"))
        pkt = SliderPacket.from_dict(raw)
        display = raw.get("label") or f.stem
        emotion_name = f.stem if species in ("human", "dog") else display

        if species == "dog":
            baked, _, _ = run_dog_pipeline(
                pkt, breed_id=breed, narrative_action=SAMPLE_ACTION
            )
        else:
            baked, _, _, _ = run_species_delivery(
                pkt, species, breed_id=breed, style_id=breed,
                narrative_action=SAMPLE_ACTION,
            )

        result = asm.assemble(
            baked,
            customer_action=SAMPLE_ACTION,
            species=species,
            breed=breed,
            emotion=emotion_name,
        )
        wan = DiffusionPromptAssembler.split_for_wan(result["prompt_04"])

        dest = out_root / species / emotion_name
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "04_给视频生成的Prompt.txt").write_text(
            result["prompt_04"], encoding="utf-8"
        )
        (dest / "wan_positive.txt").write_text(wan["positive"], encoding="utf-8")
        (dest / "wan_negative.txt").write_text(wan["negative"], encoding="utf-8")
        count += 1
    return count


def main() -> int:
    out = ROOT / "_runtime" / "prompt_samples"
    total = 0
    for sp in ("dog", "cat", "human"):
        n = export_species(sp, out)
        print(f"  {sp}: {n} presets → {out / sp}")
        total += n
    print(f"OK: exported {total} prompt samples under {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
