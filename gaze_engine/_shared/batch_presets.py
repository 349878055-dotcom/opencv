#!/usr/bin/env python3
"""批量从影帝预设生成烘焙 02（能量包络出厂）。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_PKG = Path(__file__).resolve().parent.parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from asset_lib import ensure_dirs  # noqa: E402
from gaze_engine.human.control_surface import PRESETS as ACTING_PULSE_PRESETS, packet_from_acting_preset  # noqa: E402
from gaze_engine.delivery_pipeline import run_delivery_from_packet, write_delivery_json  # noqa: E402

FIVE_ACTING_SAMPLES: tuple[str, ...] = (
    "施压·凝视",
    "可怜·委屈",
    "魅惑·勾人",
    "惊惧·一怔",
    "崩溃·泄劲",
)

def _safe_slug(name: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name).strip("_")
    return s[:40] or "preset"

def generate_five_samples(out_dir: Path) -> dict[str, Any]:
    ensure_dirs()
    out_dir = Path(out_dir)

    manifest: dict[str, Any] = {
        "schema": "acting-pulse-batch-v1",
        "pipeline": "envelope → human_prior → pulse_quality → baked_02",
        "samples": [],
    }

    for i, name in enumerate(FIVE_ACTING_SAMPLES, start=1):
        packet = packet_from_acting_preset(name)
        baked, _dense, rep, pq = run_delivery_from_packet(packet)
        slug = _safe_slug(name)
        json_name = f"02_样本{i:02d}_{slug}.json"
        json_path = out_dir / json_name
        write_delivery_json(baked, json_path)
        manifest["samples"].append(
            {
                "index": i,
                "preset": name,
                "json": str(json_path),
                "note": ACTING_PULSE_PRESETS[name].get("note", ""),
                "human_prior": rep.to_dict(),
                "pulse_quality": pq.to_dict(),
            }
        )
        print(f"[{i}/5] {name} → {json_path}")

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n[OK] manifest → {manifest_path}")
    return manifest

def main() -> int:
    from asset_lib import cmd_dir

    ap = argparse.ArgumentParser(description="批量预设 → 烘焙 02")
    ap.add_argument(
        "--batch-five",
        action="store_true",
        help=f"生成五样本（{', '.join(FIVE_ACTING_SAMPLES)}）",
    )
    ap.add_argument("--out-dir", default=str(cmd_dir() / "脉冲样本_五连"))
    args = ap.parse_args()
    if not args.batch_five:
        ap.error("需要 --batch-five")
    generate_five_samples(Path(args.out_dir))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
