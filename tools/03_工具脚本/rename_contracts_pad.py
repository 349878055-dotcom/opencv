#!/usr/bin/env python3
"""一次性：contracts → 合同，03_情绪坐标 → 03_情绪坐标，并修正全库路径引用。"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 文件重命名（相对 合同/03_情绪坐标/）
FILE_RENAMES = [
    ("00_情绪坐标导读.md", "00_情绪坐标导读.md"),
    ("02_三轴与情绪坐标.md", "02_三轴与情绪坐标.md"),
    ("人/情绪坐标定位索引.md", "人/情绪坐标定位索引.md"),
    ("猫/情绪坐标定位索引.md", "猫/情绪坐标定位索引.md"),
    ("狗/情绪坐标定位索引.md", "狗/情绪坐标定位索引.md"),
]

# 文本替换（长匹配优先）
TEXT_REPLACEMENTS: list[tuple[str, str]] = [
    ("合同/03_情绪坐标/", "合同/03_情绪坐标/"),
    ("合同/", "合同/"),
    ("03_情绪坐标/00_情绪坐标导读.md", "03_情绪坐标/00_情绪坐标导读.md"),
    ("03_情绪坐标/02_三轴与情绪坐标.md", "03_情绪坐标/02_三轴与情绪坐标.md"),
    ("00_情绪坐标导读.md", "00_情绪坐标导读.md"),
    ("02_三轴与情绪坐标.md", "02_三轴与情绪坐标.md"),
    ("情绪坐标定位索引.md", "情绪坐标定位索引.md"),
    ("03_情绪坐标/", "03_情绪坐标/"),
    ("03_情绪坐标", "03_情绪坐标"),
    ("00_情绪坐标导读", "00_情绪坐标导读"),
    ("02_三轴与情绪坐标", "02_三轴与情绪坐标"),
    ("情绪坐标定位索引", "情绪坐标定位索引"),
    # 目录 README 标题
    ("# 03_情绪坐标 — 情绪坐标定位合同", "# 03_情绪坐标 — 情绪坐标定位合同"),
    ("# 情绪坐标导读 — 从这里开始读", "# 情绪坐标导读 — 从这里开始读"),
    ("# 三轴与情绪坐标 — 情绪性格轴专篇", "# 三轴与情绪坐标 — 情绪性格轴专篇"),
    ("合同 索引", "合同 索引"),
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".cursor"}
TEXT_SUFFIXES = {".md", ".py", ".js", ".html", ".sh", ".json", ".txt", ".cursorrules", ".clinerules"}


def should_scan(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return False
    if path.suffix and path.suffix not in TEXT_SUFFIXES:
        return False
    if path.name in {".env", "yolov8n-cls.pt"}:
        return False
    return True


def rename_paths() -> None:
    con = ROOT / "contracts"
    he = ROOT / "合同"
    if con.exists() and not he.exists():
        con.rename(he)
        print("renamed: contracts → 合同")
    elif not he.exists():
        raise SystemExit("合同/ 或 合同/ 不存在")

    pad_old = he / "03_情绪坐标"
    pad_new = he / "03_情绪坐标"
    if pad_old.exists() and not pad_new.exists():
        pad_old.rename(pad_new)
        print("renamed: 03_情绪坐标 → 03_情绪坐标")

    base = he / "03_情绪坐标"
    for old_rel, new_rel in FILE_RENAMES:
        src, dst = base / old_rel, base / new_rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            print(f"renamed file: {old_rel} → {new_rel}")


def patch_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    orig = text
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    rename_paths()
    changed = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if should_scan(p):
                if patch_file(p):
                    changed += 1
    print(f"patched {changed} files")


if __name__ == "__main__":
    main()
