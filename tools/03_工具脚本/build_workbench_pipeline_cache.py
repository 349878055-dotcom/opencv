#!/usr/bin/env python3
"""为能量工作台生成各预设的交付链 JSON 缓存（滑杆 → 能量包络 → 全量）。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gaze_engine.human.control_surface import PRESETS as ACTING_PULSE_PRESETS, packet_from_acting_preset  # noqa: E402
from gaze_engine.delivery_pipeline import run_delivery_from_packet  # noqa: E402
from gaze_engine._shared.envelope_compile import (  # noqa: E402
    channels_from_packet,
    export_envelope_series,
)

def _slug(name: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name).strip("_")
    return s or "preset"

def _dense_export(channels: dict[str, list[float]], frame_count: int = 150) -> dict:
    return {
        "schema": "dense-12x150",
        "frame_count": frame_count,
        "fps": 30,
        "channels": {k: [round(v, 6) for v in ser] for k, ser in channels.items()},
        "_note": "能量包络展开；出厂真值在 human_prior 之后",
    }

def build_one(name: str) -> dict:
    packet = packet_from_acting_preset(name)
    env_pre = export_envelope_series(packet)
    dense_pre = channels_from_packet(packet)
    baked, dense_post, rep, pq = run_delivery_from_packet(packet)
    return {
        "preset": name,
        "note": ACTING_PULSE_PRESETS[name].get("note", ""),
        "stages": {
            "1_slider_packet": packet.to_dict(),
            "2_energy_envelope": env_pre,
            "3_dense_from_envelope": _dense_export(dense_pre),
            "4_dense_after_human_prior": _dense_export(dense_post),
            "4b_pulse_quality_report": pq.to_dict(),
            "5_baked_02_delivery": baked,
            "6_human_prior_report": rep.to_dict(),
        },
    }

def main() -> int:
    out_dir = Path(__file__).parent / "pipeline_cache"
    out_dir.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    for name in ACTING_PULSE_PRESETS:
        slug = _slug(name)
        data = build_one(name)
        path = out_dir / f"{slug}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index.append({"preset": name, "slug": slug, "file": path.name})
        print(f"[OK] {name} → {path.name}")
    (out_dir / "index.json").write_text(
        json.dumps({"presets": index}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n共 {len(index)} 个 → {out_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
