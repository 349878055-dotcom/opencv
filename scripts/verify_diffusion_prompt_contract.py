#!/usr/bin/env python3
"""扩散 Prompt 全链路 · P0 结构验收（对应 扩散Prompt全链路方案_导读 §五）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine.dog.dog_pipeline import run_dog_pipeline
from gaze_engine.delivery_pipeline import run_species_delivery
from gaze_engine.pomot.assembler import DiffusionPromptAssembler

DOG_CHANNELS = [
    "pupil_x", "pupil_y", "blink", "eyebrow", "pupil_scale", "iris_scale",
    "cornea_bulge", "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]

SAMPLE_ACTION = "委屈地跑回笼子再回头看了一眼"


def _assert_04_structure(prompt_04: str, *, species: str, action: str) -> None:
    for marker in ("## 正向 Prompt", "## 扩散节拍表", "## 叙事", "## 负向 Prompt"):
        assert marker in prompt_04, f"missing {marker}"
    assert len(prompt_04.split("## 正向 Prompt", 1)[1].split("## 扩散节拍表")[0].strip()) > 20
    for ch in DOG_CHANNELS:
        assert ch in prompt_04, f"beat missing channel {ch}"
    assert action in prompt_04, "narrative must be customer原文"
    wan = DiffusionPromptAssembler.split_for_wan(prompt_04)
    assert "跟随控制序列" in wan["positive"], "positive must contain rhythm constraint"
    assert len(wan["negative"]) > 20
    if species == "dog":
        assert "人类五官" in wan["negative"] or "猫耳" in wan["negative"]
    elif species == "cat":
        assert "狗耳" in wan["negative"]
    elif species == "human":
        assert "兽耳" in wan["negative"] or "动物耳朵" in wan["negative"]


def verify_dog_emotion(name: str, breed_id: str = "poodle_giant") -> None:
    p = ROOT / "预设资产" / "预设情绪包" / "dog" / f"{name}.json"
    pkt = SliderPacket.from_dict(json.loads(p.read_text(encoding="utf-8")))
    baked, _, _ = run_dog_pipeline(pkt, breed_id=breed_id, narrative_action=SAMPLE_ACTION)
    asm = DiffusionPromptAssembler()
    r = asm.assemble(
        baked,
        customer_action=SAMPLE_ACTION,
        species="dog",
        breed=breed_id,
        emotion=name,
    )
    display = DiffusionPromptAssembler.resolve_breed_display("dog", breed_id)
    assert display == "巨型贵宾犬", display
    assert "眼耳与控制线的运动严格跟随控制序列" in r["prompt_04"]
    assert display in r["prompt_04"]
    _assert_04_structure(r["prompt_04"], species="dog", action=SAMPLE_ACTION)


def verify_all_dog_presets() -> None:
    preset_dir = ROOT / "预设资产" / "预设情绪包" / "dog"
    for f in sorted(preset_dir.glob("*.json")):
        if f.name.startswith("_"):
            continue
        verify_dog_emotion(f.stem)


def verify_human_sample() -> None:
    p = ROOT / "预设资产" / "预设情绪包" / "human" / "魅惑·勾人.json"
    pkt = SliderPacket.from_dict(json.loads(p.read_text(encoding="utf-8")))
    baked, _, _, _ = run_species_delivery(
        pkt, "human", style_id="魅惑者_温碧霞", narrative_action="微微侧头"
    )
    asm = DiffusionPromptAssembler()
    r = asm.assemble(
        baked, customer_action="微微侧头", species="human",
        breed="魅惑者_温碧霞", emotion="魅惑·勾人",
    )
    assert "温碧霞" in r["prompt_04"] or "魅惑者" in r["prompt_04"]
    _assert_04_structure(r["prompt_04"], species="human", action="微微侧头")


def verify_cat_sample() -> None:
    p = ROOT / "预设资产" / "预设情绪包" / "cat" / "狩猎锁定.json"
    pkt = SliderPacket.from_dict(json.loads(p.read_text(encoding="utf-8")))
    baked, _, _, _ = run_species_delivery(
        pkt, "cat", breed_id="ragdoll_cat", narrative_action="伏低盯住"
    )
    asm = DiffusionPromptAssembler()
    r = asm.assemble(
        baked, customer_action="伏低盯住", species="cat",
        breed="ragdoll_cat", emotion="狩猎锁定",
    )
    assert "布偶" in r["prompt_04"]
    _assert_04_structure(r["prompt_04"], species="cat", action="伏低盯住")


def main() -> int:
    verify_dog_emotion("委屈·幼犬眼")
    verify_all_dog_presets()
    verify_human_sample()
    verify_cat_sample()
    print("OK: diffusion prompt contract P0 (dog×10 + human + cat)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
