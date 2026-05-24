#!/usr/bin/env python3
"""从 能量工作台.html 生成单文件分享版（控制面定义内置，不另维护一份 HTML）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PKG = TOOLS.parent
sys.path.insert(0, str(PKG))

ORIG = TOOLS / "能量工作台.html"
UI_JS = TOOLS / "workbench_pipeline_ui.js"
CACHE_DIR = TOOLS / "pipeline_cache"
OUT = TOOLS / "能量工作台_单文件分享.html"

def _load_embedded_pipeline() -> dict:
    out = {}
    for f in sorted(CACHE_DIR.glob("*.json")):
        if f.name in ("index.json", "control_surface.json"):
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        out[data["preset"]] = data
    return out

def main() -> None:
    from gaze_engine.human.control_surface import export_workbench_json

    html = ORIG.read_text(encoding="utf-8")
    ui_js = UI_JS.read_text(encoding="utf-8")
    control = json.dumps(export_workbench_json(), ensure_ascii=False, separators=(",", ":"))
    pipeline = json.dumps(_load_embedded_pipeline(), ensure_ascii=False, separators=(",", ":"))

    html = html.replace(
        '<script src="workbench_pipeline_ui.js"></script>\n',
        f"<script>\n{ui_js}\n</script>\n<script>\n"
        f"const EMBEDDED_CONTROL_SURFACE = {control};\n"
        f"const EMBEDDED_PIPELINE_CACHE = {pipeline};\n"
        f"const SHARE_STANDALONE = true;\n</script>\n",
    )

    html = html.replace(
        """    async function loadControlSurface() {
      try {
        const r = await fetch("/control_surface.json", { cache: "no-store" });
        if (!r.ok) throw new Error("HTTP " + r.status);
        const s = await r.json();""",
        """    async function loadControlSurface() {
      try {
        let s = null;
        if (typeof EMBEDDED_CONTROL_SURFACE !== "undefined") {
          s = EMBEDDED_CONTROL_SURFACE;
        } else {
          const r = await fetch("/control_surface.json", { cache: "no-store" });
          if (!r.ok) throw new Error("HTTP " + r.status);
          s = await r.json();
        }""",
    )

    html = html.replace(
        "contracts/眼眉真人默认律.md",
        "单文件分享 · 数据已内置",
    )

    html = html.replace(
        "<title>能量脉冲 · 控制面定义台</title>",
        "<title>能量脉冲 · 控制面分享</title>",
    )

    OUT.write_text(html, encoding="utf-8")
    mb = OUT.stat().st_size / 1024 / 1024
    print(f"OK {OUT} ({mb:.2f} MB)")

if __name__ == "__main__":
    main()
