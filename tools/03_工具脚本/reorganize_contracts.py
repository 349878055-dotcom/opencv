#!/usr/bin/env python3
"""按管线流程重组 合同/ 目录（一次性迁移脚本）。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "合同"

# ── 1. 物理搬迁（旧路径 → 新路径）────────────────────────────────────────
MOVES: list[tuple[str, str]] = [
    # 01_总纲 → 拆分
    ("01_输入与收口/滑杆规范.md", "01_输入与收口/滑杆规范.md"),
    ("01_输入与收口/macro与hold_seg专篇.md", "01_输入与收口/macro与hold_seg专篇.md"),
    ("04_通道与先验/全量帧指令集规范.md", "04_通道与先验/全量帧指令集规范.md"),
    ("04_通道与先验/眼眉真人默认律.md", "04_通道与先验/眼眉真人默认律.md"),
    ("04_通道与先验/眼眉指令集_全局情绪节奏主钟.md", "04_通道与先验/眼眉指令集_全局情绪节奏主钟.md"),
    ("04_通道与先验/节奏说明书.md", "04_通道与先验/节奏说明书.md"),
    ("04_通道与先验/节奏说明书编译器.md", "04_通道与先验/节奏说明书编译器.md"),
    # 整目录搬迁
    ("02_情绪与能量", "02_情绪与能量"),
    ("06_工程底膜", "06_工程底膜"),
    ("07_输出与扩散", "07_输出与扩散"),
    ("08_架构与验收", "08_架构与验收"),
    ("03_情绪坐标/人", "03_情绪坐标/人"),
    ("03_情绪坐标/猫", "03_情绪坐标/猫"),
    ("03_情绪坐标/狗", "03_情绪坐标/狗"),
]

# PAD 总纲扁平化 + 短文件名
PAD_THEORY: list[tuple[str, str]] = [
    ("03_情绪坐标/00_情绪坐标导读.md", "03_情绪坐标/00_情绪坐标导读.md"),
    ("03_情绪坐标/01_三层分工与边界.md", "03_情绪坐标/01_三层分工与边界.md"),
    ("03_情绪坐标/02_三轴与情绪坐标.md", "03_情绪坐标/02_三轴与情绪坐标.md"),
    ("03_情绪坐标/03_12通道映射与编译链.md", "03_情绪坐标/03_12通道映射与编译链.md"),
    ("03_情绪坐标/04_四层表演栈与style边界.md", "03_情绪坐标/04_四层表演栈与style边界.md"),
    ("03_情绪坐标/README.md", "03_情绪坐标/README.md"),
]

# 删除：stub / 冗余
DELETE_PATHS = [
    "03_情绪坐标/02_三轴与情绪坐标.md",
    "03_情绪坐标/01_三层分工与边界.md",
    "03_情绪坐标/04_四层表演栈与style边界.md",
    "03_情绪坐标/03_12通道映射与编译链.md",
    "02_情绪与能量/狗情绪与能量曲线.md",
    "02_情绪与能量/魅惑勾人.md",
    "05_风格化/狗品种风格偏向.md",
    "02_情绪与能量/人/情绪坐标定位索引.md",
    "02_情绪与能量/猫/情绪坐标定位索引.md",
    "02_情绪与能量/狗/情绪坐标定位索引.md",
]

# ── 2. 链接替换（顺序：长匹配优先）────────────────────────────────────────
LINK_REPLACEMENTS: list[tuple[str, str]] = [
    # PAD 总纲扁平 + 重命名
    ("03_情绪坐标/00_情绪坐标导读.md", "03_情绪坐标/00_情绪坐标导读.md"),
    ("03_情绪坐标/01_三层分工与边界.md", "03_情绪坐标/01_三层分工与边界.md"),
    ("03_情绪坐标/02_三轴与情绪坐标.md", "03_情绪坐标/02_三轴与情绪坐标.md"),
    ("03_情绪坐标/03_12通道映射与编译链.md", "03_情绪坐标/03_12通道映射与编译链.md"),
    ("03_情绪坐标/04_四层表演栈与style边界.md", "03_情绪坐标/04_四层表演栈与style边界.md"),
    ("03_情绪坐标/", "03_情绪坐标/"),
    ("03_情绪坐标", "03_情绪坐标"),
    # 01_总纲 stub 旧名 → 新 PAD 理论
    ("03_情绪坐标/02_三轴与情绪坐标.md", "03_情绪坐标/02_三轴与情绪坐标.md"),
    ("03_情绪坐标/01_三层分工与边界.md", "03_情绪坐标/01_三层分工与边界.md"),
    ("03_情绪坐标/04_四层表演栈与style边界.md", "03_情绪坐标/04_四层表演栈与style边界.md"),
    ("03_情绪坐标/03_12通道映射与编译链.md", "03_情绪坐标/03_12通道映射与编译链.md"),
    # 目录重命名
    ("01_输入与收口/滑杆规范.md", "01_输入与收口/滑杆规范.md"),
    ("01_输入与收口/macro与hold_seg专篇.md", "01_输入与收口/macro与hold_seg专篇.md"),
    ("04_通道与先验/全量帧指令集规范.md", "04_通道与先验/全量帧指令集规范.md"),
    ("04_通道与先验/眼眉真人默认律.md", "04_通道与先验/眼眉真人默认律.md"),
    ("04_通道与先验/眼眉指令集_全局情绪节奏主钟.md", "04_通道与先验/眼眉指令集_全局情绪节奏主钟.md"),
    ("04_通道与先验/节奏说明书.md", "04_通道与先验/节奏说明书.md"),
    ("04_通道与先验/节奏说明书编译器.md", "04_通道与先验/节奏说明书编译器.md"),
    ("01_输入与收口/", "01_输入与收口/"),  # 兜底：其余 01_总纲 链到输入收口
    ("02_情绪与能量/", "02_情绪与能量/"),
    ("02_情绪与能量", "02_情绪与能量"),
    ("06_工程底膜/", "06_工程底膜/"),
    ("06_工程底膜", "06_工程底膜"),
    ("07_输出与扩散/", "07_输出与扩散/"),
    ("07_输出与扩散", "07_输出与扩散"),
    ("08_架构与验收/", "08_架构与验收/"),
    ("08_架构与验收", "08_架构与验收"),
    ("03_情绪坐标/", "03_情绪坐标/"),
    ("03_情绪坐标", "03_情绪坐标"),
    # 相对路径兄弟引用（PAD 理论文件内）
    ("../../01_输入与收口/", "../../01_输入与收口/"),
    ("../../../01_输入与收口/", "../../../01_输入与收口/"),
    ("../../08_架构与验收/", "../../08_架构与验收/"),
    ("../../../08_架构与验收/", "../../../08_架构与验收/"),
    ("../01_输入与收口/", "../01_输入与收口/"),
    ("../08_架构与验收/", "../08_架构与验收/"),
    ("../02_情绪与能量/", "../02_情绪与能量/"),
    ("../../02_情绪与能量/", "../../02_情绪与能量/"),
    ("../../../02_情绪与能量/", "../../../02_情绪与能量/"),
    ("../06_工程底膜/", "../06_工程底膜/"),
    ("../../06_工程底膜/", "../../06_工程底膜/"),
    ("../07_输出与扩散/", "../07_输出与扩散/"),
    ("../../07_输出与扩散/", "../../07_输出与扩散/"),
    # 旧 PAD 文件名（无总纲前缀）
    ("01_三层分工与边界.md", "01_三层分工与边界.md"),
    ("02_三轴与情绪坐标.md", "02_三轴与情绪坐标.md"),
    ("03_12通道映射与编译链.md", "03_12通道映射与编译链.md"),
    ("00_情绪坐标导读.md", "00_情绪坐标导读.md"),
]


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def move_items() -> None:
    for src_rel, dst_rel in MOVES:
        src = CON / src_rel
        dst = CON / dst_rel
        if not src.exists():
            print(f"  skip (missing): {src_rel}")
            continue
        _ensure_parent(dst)
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        shutil.move(str(src), str(dst))
        print(f"  move: {src_rel} → {dst_rel}")

    for src_rel, dst_rel in PAD_THEORY:
        src = CON / src_rel
        dst = CON / dst_rel
        if not src.exists():
            print(f"  skip pad (missing): {src_rel}")
            continue
        _ensure_parent(dst)
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), str(dst))
        print(f"  pad: {src_rel} → {dst_rel}")


def delete_items() -> None:
    for rel in DELETE_PATHS:
        p = CON / rel
        if p.exists():
            p.unlink()
            print(f"  delete: {rel}")


def cleanup_empty_dirs() -> None:
    for name in ("01_总纲", "03_情绪坐标", "03_情绪坐标", "02_情绪与能量"):
        p = CON / name
        if p.exists() and p.is_dir():
            try:
                p.rmdir()
                print(f"  rmdir: {name}")
            except OSError:
                shutil.rmtree(p)
                print(f"  rmtree: {name}")


def patch_text(text: str) -> str:
    for old, new in LINK_REPLACEMENTS:
        text = text.replace(old, new)
    # 修正「位置」行
    text = re.sub(
        r">\s*\*\*位置\*\*：`合同/03_情绪坐标/`",
        "> **位置**：`合同/03_情绪坐标/`",
        text,
    )
    text = re.sub(
        r">\s*\*\*位置\*\*：\[?`?03_情绪坐标/`?\]?",
        "> **位置**：`合同/03_情绪坐标/`",
        text,
    )
    text = re.sub(
        r"合同/03_情绪坐标/",
        "合同/03_情绪坐标/",
        text,
    )
    text = re.sub(
        r"`03_情绪坐标/` · ",
        "`03_情绪坐标/` · ",
        text,
    )
    return text


def update_all_links() -> int:
    count = 0
    targets = list(CON.rglob("*.md"))
    targets += list((ROOT / "tools").rglob("*.py"))
    targets += [ROOT / "AI_INDEX.md", ROOT / "README.md"]
    targets += list((ROOT / "docs").rglob("*.md"))
    targets += list((ROOT / "scripts").rglob("*.py"))
    seen: set[Path] = set()
    for path in targets:
        if not path.exists() or path in seen:
            continue
        seen.add(path)
        raw = path.read_text(encoding="utf-8")
        new = patch_text(raw)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            count += 1
            print(f"  patch: {path.relative_to(ROOT)}")
    return count


def write_pipeline_overview() -> None:
    out = CON / "00_管线导读" / "00_从门户到扩散_管线总览.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        """# 从门户到扩散 — 管线总览（contracts 阅读地图）

> **状态：2026-05-28** · 本文件 = contracts 目录的 **流程入口**  
> **原则**：目录编号 = 编译链阶段；一种情绪/风格 = 一份独立 md

---

## 一、5 秒读懂：数据怎么走

```text
客户门户 / Pomot
    │
    ▼ 01  输入收口     SliderPacket + L1 禁区
    ▼ 02  情绪与能量   macro+hold → E(t)
    ▼ 03  情绪坐标 (PAD)  (P,A,D) → pad_scale[12]
    ▼ 04  通道编译     E(t)×情绪坐标 → pulse[12×150]
    ▼ 05  风格化       pulse → styled
    ▼ 06  先验与质检   prior + QC
    ▼ 07  工程底膜     02 烘焙 + MP4
    ▼ 08  输出与扩散   扩散包 + Wan
```

**定稿口诀**：`macro=演多重` · `情绪坐标=哪类戏 (PAD)` · `style=谁的脸`

---

## 二、目录 ↔ 管线阶段

| 阶段 | 目录 | 管什么 | 入口文件 |
|------|------|--------|----------|
| **导读** | [`00_管线导读/`](.) | 阅读地图 | **本文** |
| **01** | [`01_输入与收口/`](../01_输入与收口/) | SliderPacket、L1 | [`滑杆规范.md`](../01_输入与收口/滑杆规范.md) |
| **02** | [`02_情绪与能量/`](../02_情绪与能量/) | macro/E(t) | 各物种索引 md |
| **03** | [`03_情绪坐标/`](../03_情绪坐标/) | 情绪坐标 (PAD) | [`00_情绪坐标导读.md`](../03_情绪坐标/00_情绪坐标导读.md) |
| **04** | [`04_通道编译/`](../04_通道编译/) | 12 通道、02 烘焙 | [`全量帧指令集规范.md`](../04_通道编译/全量帧指令集规范.md) |
| **05** | [`05_风格化/`](../05_风格化/) | 人格/品种 | [`00_风格化导读.md`](../05_风格化/00_风格化导读.md) |
| **06–08** | `06` `07` `08` | 先验、底膜、扩散 | 见 [`00_从门户到扩散_管线总览.md`](../00_管线导读/00_从门户到扩散_管线总览.md) |
| **09** | [`09_架构与验收/`](../09_架构与验收/) | P0/P1 验收 | 狗150帧等 |

---

## 三、改参决策表（最常问）

| 你想… | 去哪个目录 | 不要动 |
|-------|-----------|--------|
| 戏太弱/起势快慢 | `01_输入与收口` macro | 品种 style |
| 更像「委屈」而非「渴望」 | `03_情绪坐标` 换 preset 或改 P/A/D | E(t) 帧轴 |
| 盯住段该颤/该呼吸 | `01_输入与收口` hold_seg | PAD |
| 贵宾比田园更半阖 | `05_风格化` style.json | E(t)、PAD |
| 5 秒不眨眼 | `04_通道与先验` + S7 QC | — |
| 04/Wan 文案 | `07_输出与扩散` | 02 通道数 |

---

## 四、验收命令

```bash
python3 scripts/verify_diffusion_prompt_contract.py
python3 scripts/verify_dog_150_compile_contract.py
python3 scripts/export_prompt_samples.py
```

门户：`http://127.0.0.1:8765/portal` · `./一键打开创作门户.sh`

---

## 五、相关

- 合同五段格式：[`合同规范.md`](../合同规范.md)
- 完整索引：[`README.md`](../README.md)
- 代码图谱：[`AI_INDEX.md`](../../AI_INDEX.md)
""",
        encoding="utf-8",
    )
    print(f"  write: {out.relative_to(ROOT)}")


def main() -> None:
    print("=== 1. 搬迁文件 ===")
    move_items()
    print("\n=== 2. 删除 stub ===")
    delete_items()
    print("\n=== 3. 清理空目录 ===")
    cleanup_empty_dirs()
    print("\n=== 4. 写管线导读 ===")
    write_pipeline_overview()
    print("\n=== 5. 批量更新链接 ===")
    n = update_all_links()
    print(f"\nOK: reorganized contracts, patched {n} files")


if __name__ == "__main__":
    main()
