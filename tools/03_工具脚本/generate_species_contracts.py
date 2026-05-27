#!/usr/bin/env python3
"""生成 02_情绪 / 05_人格化 下各物种的 **独立单项合同**（完整五段，互不捆绑）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gaze_engine._shared.envelope_compile import export_envelope_series
from gaze_engine._shared.emotion_pad import (
    EMOTION_PAD,
    pad_channel_hint,
    pad_dict_for_json,
    pad_position_text,
    resolve_pad,
)
from gaze_engine._shared.slider_schema import SliderPacket

SPECIES_DIR = {"human": "人", "cat": "猫", "dog": "狗"}
SPECIES_LABEL = {"human": "人类", "cat": "猫", "dog": "狗"}
PARENT_EMOTION = {
    "human": "人类情绪与能量曲线.md",
    "cat": "猫情绪与能量曲线.md",
    "dog": "狗情绪与能量曲线.md",
}
PARENT_STYLE = {
    "human": "人类人格风格偏向.md",
    "cat": "猫品种风格偏向.md",
    "dog": "狗品种风格偏向.md",
}

MACRO_DOCS = {
    "push": ("往哪使劲", "内收", "外放", "direction；阈值 50"),
    "power": ("力度", "轻", "狠", "weight 线性 + 全轨幅度"),
    "speed": ("快慢", "缓", "急", "peak 帧 ±4"),
    "steady": ("盯得稳", "飘", "钉死", "盯住段 jitter 权重"),
    "grip": ("定得住", "泄", "憋住", "盯住段值衰减"),
    "outro": ("收场", "快落", "慢收", "ending；阈值 50"),
}

HOLD_SHAPE = {
    "flat": "平顶盯住",
    "tremble": "长保持微颤",
    "pulse": "脉冲节奏保持",
    "decay": "段内下泄",
    "swell": "慢拱起伏",
}

CHANNEL_ZH = {
    "pupil_x": ("瞳孔水平", "扫视/回头幅度"),
    "pupil_y": ("瞳孔垂直", "抬眼/低眉视线"),
    "blink": ("眨眼", "眼睑开合动态"),
    "eyebrow": ("眉形整体", "眉弓压抬"),
    "pupil_scale": ("瞳孔缩放", "惊恐/聚焦"),
    "iris_scale": ("虹膜缩放", "眼内圈大小"),
    "cornea_bulge": ("角膜鼓胀", "湿润/受光"),
    "squint": ("眯眼", "笑眼/不适"),
    "brow_raise": ("挑眉", "警觉/疑问"),
    "lid_upper": ("上睑", "睁眼度"),
    "lid_lower": ("下睑", "眼下缘"),
    "eye_gloss": ("高光", "泪膜/湿润感"),
}

STYLE_ARCHETYPE = {
    "魅惑者": "眼波流连、上睑抬高、慢眨动态放大；适合媚戏叠加",
    "狠厉者": "眉压眶缘、眨眼收敛、瞳孔扫视幅度克制；适合压戏",
    "悲悯者": "眼下缘偏软、高光弱、整体低 attack",
    "怯弱者": "瞳孔易缩、眉内收、blink 基线偏高显怯",
    "天选者": "眉弓稳定、扫视极小、盯住感强",
    "天真者": "眼圆、blink 幅度大、高光亮",
    "呆滞者": "blink/扫视 scale 双低，接近木偶",
    "癫狂者": "pupil/iris scale 高，扫视幅度大",
    "british": "英短：圆眼、半阖基线、低扫视",
    "ragdoll": "布偶：大圆眼、高 blink 基线、温顺",
    "siamese": "暹罗：细长眼、高眉、瞳孔动态大",
    "stray": "田园：机敏、扫视 scale 偏高",
    "poodle": "贵宾：杏仁眼、优雅半阖、耳廓控制点偏长",
}


def _l1_band(v: int, delta: int = 8) -> str:
    lo = max(0, v - delta)
    hi = min(100, v + delta)
    return f"{lo}～{hi}"


def _push_word(v: int) -> str:
    if v >= 70:
        return "外放"
    if v <= 30:
        return "内收"
    return "中性"


def _power_word(v: int) -> str:
    if v >= 75:
        return "高强度"
    if v <= 30:
        return "低强度"
    return "中等强度"


def _outro_word(v: int) -> str:
    return "慢收留韵" if v >= 50 else "快收"


def _brain_one_liner(name: str, pkt: SliderPacket, peak: float, group: str) -> str:
    m, h = pkt.macro, pkt.hold_seg
    return (
        f"**{name}** = {_push_word(m.push)}、{_power_word(m.power)}、"
        f"{HOLD_SHAPE.get(h.shape, h.shape)}、{_outro_word(m.outro)}（peak≈{peak:.3f}）；"
        f"分组「{group or '未分组'}」。"
    )


def _brain_reading(pkt: SliderPacket, peak: float, note: str) -> list[str]:
    m, h = pkt.macro, pkt.hold_seg
    lines = []
    if note and note != "（无 note）":
        lines.append(f"资产 note：**{note}**。")
    if m.push >= 70:
        lines.append("视线/情绪 **面向外放**，有压向镜头或对方的倾向。")
    elif m.push <= 25:
        lines.append("视线 **内收**，弱攻击感，偏怯、恳求或退缩。")
    if peak >= 0.35:
        lines.append("整体 **能量偏高**，盯住段硬，不宜像发呆或困倦。")
    elif peak <= 0.12:
        lines.append("整体 **能量偏低**，软、幼、疲惫或空竭感。")
    if h.shape == "tremble":
        lines.append("保持段有 **细颤**，避免 5 秒铁板同一帧。")
    elif h.shape == "pulse":
        lines.append("保持段有 **呼吸式脉冲**，适合勾人/期待类戏。")
    elif h.shape == "flat" and m.grip >= 80:
        lines.append("保持段 **平顶高 grip**，钉住不放。")
    elif h.shape == "decay":
        lines.append("保持段 **段内下泄**，适合崩溃/泄劲。")
    elif h.shape == "swell":
        lines.append("保持段 **慢拱起伏**，适合含情/若即若离。")
    if m.speed >= 75:
        lines.append("起势 **偏急**，戏眼来得快。")
    elif m.speed <= 30:
        lines.append("起势 **偏缓**，蓄力段更长。")
    if not lines:
        lines.append("（🧠 待审：补观众 3 秒内读到的戏）")
    return lines


def _macro_why_rows(pkt: SliderPacket) -> str:
    m = pkt.macro
    rows = []
    for key in ("push", "power", "speed", "steady", "grip", "outro"):
        v = getattr(m, key)
        zh, lo, hi, py = MACRO_DOCS[key]
        alt_lo = f"偏低 → 偏{lo}"
        alt_hi = f"偏高 → 偏{hi}"
        pick = alt_hi if v >= 55 else (alt_lo if v <= 45 else "居中 → 中性戏")
        rows.append(
            f"| `{key}` | {zh} | {alt_lo} / {alt_hi} | **{v}** → {pick} | 🧠 与 JSON 同步 |"
        )
    h = pkt.hold_seg
    rows.append(
        f"| `hold.shape` | 盯住段纹理 | flat/pulse/tremble/… | **{h.shape}** | "
        f"{HOLD_SHAPE.get(h.shape, h.shape)} |"
    )
    return "\n".join(rows)


def _pad_axis_reading(v: float, pos: str, neg: str) -> str:
    if v >= 0.35:
        return f"偏高 → {pos}"
    if v <= -0.35:
        return f"偏低 → {neg}"
    return "居中 → 中性"


def _pad_why_rows(P: float, A: float, D: float) -> str:
    return "\n".join(
        [
            f"| `P` 愉悦度 | 正=愉悦/吸引，负=不悦/压抑 | 高/低 | **{P}** | {_pad_axis_reading(P, '偏甜/含情', '偏苦/压人')} |",
            f"| `A` 激活度 | 正=alert/急，负=软/塌 | 高/低 | **{A}** | {_pad_axis_reading(A, '偏急/警觉', '偏软/困倦')} |",
            f"| `D` 控制度 | 正=支配/压人，负=顺从/退缩 | 高/低 | **{D}** | {_pad_axis_reading(D, '偏压/控场', '偏怯/泄劲')} |",
        ]
    )


def _pad_species_note(species: str) -> str:
    if species == "human":
        return "人类：`eyebrow` 的 D 权重为负 → 高 D 时眉压下（拒/压）；`eye_gloss` 吃 P。"
    if species == "cat":
        return "猫：`pupil_scale`/`squint` 的 P 权重高于人类；`eyebrow` 由 ear 块覆盖为耳位。"
    return "狗：`eyebrow` 映射耳位（竖/耷）；`cornea_bulge` 对 A 敏感（巩膜暴露）。"


def _confusions(species: str, name: str, group: str) -> list[tuple[str, str]]:
    pools = {
        "human": {
            "压 · 慑": ["施压·凝视", "冷压·决心", "威慑·一瞬", "怒视·压人", "鄙夷·冷瞥"],
            "悲 · 怯": ["可怜·委屈", "要哭未哭", "崩溃·泄劲", "哀求·仰望", "惊惧·一怔"],
            "媚 · 勾": ["魅惑·勾人", "纯甜·含情", "媚杀·一眼", "若即若离", "打量·玩味"],
        },
        "cat": {
            "警觉 · 攻击": ["警觉瞪视", "狩猎锁定", "愤怒嘶哈"],
            "恐惧 · 退缩": ["受惊炸毛", "恐惧贴耳", "委屈呜咽"],
            "亲昵 · 放松": ["亲昵眯眼", "满足幸福", "困倦垂眼"],
            "好奇 · 玩耍": ["好奇歪头", "玩耍扑击", "烦闷甩尾"],
        },
        "dog": {
            "警觉 · 攻击": ["警觉·竖耳", "凶狠·威吓", "守护·凝视"],
            "恐惧 · 退缩": ["害怕·退缩", "委屈·幼犬眼", "渴望·仰望"],
            "亲昵 · 放松": ["满足·眯眼", "兴奋·期待", "困倦·犯懒"],
            "困惑 · 好奇": ["困惑·歪头"],
        },
    }
    out = []
    for other in pools.get(species, {}).get(group, []):
        if other != name:
            out.append((other, "🧠 同组邻近戏：peak、hold.shape、push 勿三者全撞"))
            if len(out) >= 3:
                break
    if not out:
        out.append(("（待补）", "🧠 填写易混淆预设及区分点"))
    return out


def _load_groups(species: str) -> dict[str, str]:
    p = ROOT / "预设资产" / "预设情绪包" / species / "_groups.json"
    if not p.is_file():
        return {}
    groups = json.loads(p.read_text(encoding="utf-8"))
    m: dict[str, str] = {}
    for g in groups:
        label = g.get("label", "")
        keys = g.get("keys") or []
        labels = g.get("keys_label") or keys
        for i, k in enumerate(keys):
            disp = labels[i] if i < len(labels) else k
            m[disp] = label
            m[k] = label
    return m


def _species_pipeline(species: str) -> tuple[str, str, str]:
    compile_py = f"gaze_engine/{species}/envelope_compile.py"
    if species == "human":
        extra = "人类 prior / 眉滞后见 `gaze_engine/human/human_prior.py`。"
    elif species in ("cat", "dog"):
        extra = "宠物 `ear` 块映射眉/耳通道，不进 E(t) 公式。"
    else:
        extra = ""
    upstream = f"`预设资产/预设情绪包/{species}/{{本情绪}}.json`（SliderPacket）"
    downstream = f"`{compile_py}` → 02 烘焙 → 工程底膜 →（可选）04 Prompt"
    return upstream, downstream, extra


def _load_matrix_entry(species: str, style_id: str) -> dict | None:
    if species == "human":
        p = ROOT / "gaze_engine" / "human" / "persona_matrix.json"
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")).get("personas", {}).get(style_id)
    else:
        p = ROOT / "gaze_engine" / species / "breed_matrix.json"
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")).get("breed_personas", {}).get(style_id)
    return None


def _style_archetype_text(style_id: str, notes: str) -> str:
    for key, text in STYLE_ARCHETYPE.items():
        if key in style_id.lower() or key in style_id:
            return text
    if notes:
        return f"资产 notes：{notes}"
    return "🧠 待审：写清该风格/品种的气质、适用情绪、禁用场景"


def _channel_style_row(ch: str, base: float, scale: float) -> str:
    zh, role = CHANNEL_ZH.get(ch, (ch, ""))
    intent = []
    if base >= 0.58:
        intent.append("基线偏高")
    elif base <= 0.42:
        intent.append("基线偏低")
    if scale >= 0.2:
        intent.append("动态幅度大")
    elif scale <= 0.06:
        intent.append("动态幅度小")
    intent_txt = "；".join(intent) if intent else "接近物种默认"
    return f"| `{ch}` | {zh} | **{base}** | **{scale}** | {role}；{intent_txt} |"


def render_emotion_md(
    species: str,
    display_name: str,
    filename: str,
    pkt: SliderPacket,
    raw: dict,
    meta: dict,
) -> str:
    tm = meta["timing"]
    env = meta["envelope"]
    peak = meta["peak_level"]
    group = _load_groups(species).get(display_name) or _load_groups(species).get(
        raw.get("emotion", ""), ""
    )
    asset = f"预设资产/预设情绪包/{species}/{filename}"
    note = raw.get("note") or "（无 note）"
    sp_label = SPECIES_LABEL[species]
    upstream, downstream, extra_theory = _species_pipeline(species)

    macro_rows = "\n".join(
        f"| `{k}` | **{getattr(pkt.macro, k)}** | 0～100 | {_l1_band(getattr(pkt.macro, k))} | "
        f"{MACRO_DOCS[k][0]} |"
        for k in ("push", "power", "speed", "steady", "grip", "outro")
    )
    hold = pkt.hold_seg
    P, A, D = resolve_pad(pkt)
    pad_raw = raw.get("pad") or {}
    position = pad_raw.get("position") or pad_position_text(P, A, D)
    channel_hint = pad_raw.get("channel_hint") or pad_channel_hint(species, P, A, D)
    has_ear = pkt.ear is not None
    sec_ear = 3 if has_ear else None
    sec_pad = 4 if has_ear else 3
    sec_env = sec_pad + 1
    sec_read = sec_env + 1
    sec_conf = sec_read + 1
    sec_code = sec_conf + 1

    ear_block = ""
    if pkt.ear:
        ear_block = f"""
### 4.{sec_ear} 耳位（宠物，`ear` 块）

| 侧 | angle | offset | 🧠 读感 |
|----|-------|--------|--------|
| left | {pkt.ear.left_angle} | {pkt.ear.left_offset} | 耷/竖耳眉联动 |
| right | {pkt.ear.right_angle} | {pkt.ear.right_offset} | 同上 |

> `ear` **不参与** E(t)；只进 `{species}/envelope_compile` 的眉/耳通道。
"""
    elif species == "human":
        ear_block = "\n> 人类预设无 `ear` 块。\n"

    pad_block = f"""
### 4.{sec_pad} PAD 定位（通道性格，与滑杆/E(t) 正交）

> **真源**：JSON `pad` 块 · 值域各 **[-1, 1]** · 客户调滑杆 **不改变** PAD。

| 轴 | 定稿值 | 空间定位 | 主要通道倾向 |
|----|--------|----------|--------------|
| **P** 愉悦度 | **{P}** | {_pad_axis_reading(P, "偏愉悦/吸引", "偏不悦/压抑")} | 吃 P 权重：`eye_gloss` · `squint` · `pupil_scale` |
| **A** 激活度 | **{A}** | {_pad_axis_reading(A, "偏急/警觉", "偏软/困倦")} | 吃 A 权重：`pupil_x/y` · `lid_upper` · `cornea_bulge` |
| **D** 控制度 | **{D}** | {_pad_axis_reading(D, "偏支配/压人", "偏顺从/退缩")} | 吃 D 权重：`eyebrow`（人类 D 负权）· `brow_raise` |

**一句话定位**：{position}

**通道投影 hint**（🧠 近似）：`{channel_hint}`

**物种映射**：{_pad_species_note(species)}

公式（全物种共用，权重见 `{species}/pad_weights.py`）：

```text
scale[ch] = base[ch] + P×Wp + A×Wa + D×Wd
pulse[ch,t] = E[t] × scale[ch]   // 品种/style 叠在 pulse 之后
```
"""

    conf_rows = "\n".join(f"| {a} | {b} |" for a, b in _confusions(species, display_name, group))
    read_lines = "\n".join(f"- {x}" for x in _brain_reading(pkt, peak, note))

    t_hold0, t_hold1 = tm["t_hold0"], tm["t_hold1"]
    hold_min = min(env[t_hold0 : t_hold1 + 1])
    hold_max = max(env[t_hold0 : t_hold1 + 1])
    env_tail = env[149]

    compile_py = f"gaze_engine/{species}/envelope_compile.py"
    preset_py = f"gaze_engine/{species}/presets.py"

    return f"""# {display_name} — {sp_label}情绪合同（独立）

> **状态：🧠 脑补初稿（可逐份审定）** — 本文 **只管辖「{display_name}」** 一种情绪；不与其他情绪合并修订。
> **数值真源**：`{asset}`（含 `pad` 块）· E(t) 由 `build_energy_envelope()` 自动计算。
> **兄弟规范**：[`滑杆规范.md`](../../01_总纲/滑杆规范.md) · [`全量帧指令集规范.md`](../../01_总纲/全量帧指令集规范.md)

---

## 一、概述（What）

### 本文件用途

定义 **{display_name}** 这一种{sp_label}情绪的：**滑杆定稿、PAD 定位、E(t) 指标、观众读感、验收标准**。  
改情绪只改 **本文件 + 对应 JSON**，勿改其他情绪 md。

### 一句话定义

{_brain_one_liner(display_name, pkt, peak, group)}

### 管线位置

| 环节 | 内容 |
|------|------|
| 上游 | {upstream} |
| **本合同** | macro / hold_seg / ear / **pad** → E(t) 与读感定稿 |
| 下游 | {downstream} |

### 管辖 / 边界

| ✅ 本文件管 | ❌ 本文件不管 |
|------------|--------------|
| 本情绪的 6+3 滑杆定稿 | 品种/人格 `style.json`（见 `05_人格化/` 各独立 md） |
| 本情绪的 **PAD (P,A,D)** 定稿 | 04 扩散 Prompt 文案 |
| 本情绪的 E(t) peak / 帧轴 | 其他情绪预设 |
| 本情绪的读感与混淆 | |

### 资产与分组

| 项 | 值 |
|----|-----|
| 物种 | `{species}` |
| 分组 | {group or "🧠 待补"} |
| emotion id | `{raw.get("emotion", display_name)}` |
| note | {note} |

---

## 二、理论依据（Theory）

### E(t) 四段（本情绪共用公式，数值因滑杆而异）

```text
蓄力(0～t_peak) → 启动(t_peak～t_settle) → 保持(t_hold0～t_hold1) → 缓和(t_hold1～149)
```

- 实现：[`gaze_engine/_shared/envelope_compile.py`](../../../gaze_engine/_shared/envelope_compile.py) → `build_energy_envelope()`
- **本情绪**：peak={peak:.5f}，t_peak={tm["t_peak"]}，保持段 [{t_hold0}, {t_hold1}]

### 滑杆 → E(t)

| 阶段 | 主要滑杆 |
|------|----------|
| 起 | push · power · speed |
| 盯住 | steady · grip · hold_seg |
| 收场 | outro |

{extra_theory}

### PAD → 12 通道（与 E(t) 正交）

- PAD **不进** E(t) 公式；只参与 `compute_pad_scale()` → 各通道整段 scale。
- 实现：[`emotion_pad.py`](../../../gaze_engine/_shared/emotion_pad.py) · [`{species}/pad_weights.py`](../../../gaze_engine/{species}/pad_weights.py)
- **本情绪 PAD**：P={P}，A={A}，D={D} → {position}

---

## 三、为什么这样做（Why）

| 键 | 客户语义 | 备选方向 | 定稿 | 理由 |
|----|----------|----------|------|------|
{_macro_why_rows(pkt)}
| `pad.P/A/D` | 通道性格 | 各轴 -1～1 | **({P}, {A}, {D})** | 🧠 与 JSON `pad` 同步；不改 E(t) |

⚠️ **历史教训**：同组情绪若 push/power/hold.shape 三者全同，门户与 02 烘焙无法区分 → 必须在本文件 §4.{sec_conf} 写清「别像谁」。

---

## 四、怎么实现（How）

### 4.1 输入

| 项 | 规格 |
|----|------|
| 文件 | `{asset}` |
| schema | `slider-packet-v1` |
| 加载 | [`{preset_py}`](../../../{preset_py}) · 工作台 `/api/portal/presets` |

### 4.2 滑杆定稿

| 键 | 定稿值 | 范围 | L1 建议带 | 说明 |
|----|--------|------|-----------|------|
{macro_rows}

| hold 键 | 定稿值 |
|---------|--------|
| shape | **{hold.shape}** |
| pulse_rate | **{hold.pulse_rate}** |
| pulse_depth | **{hold.pulse_depth}** |
| swell | **{hold.swell}** |
{ear_block}{pad_block}
### 4.{sec_env} 能量包络 E(t)

| 指标 | 值 | 说明 |
|------|-----|------|
| peak_level | **{peak}** | 全轨峰值 |
| t_peak | **{tm["t_peak"]}** | 蓄力结束 |
| t_settle | **{tm["t_settle"]}** | 启动结束 |
| t_hold0 / t_hold1 | **{t_hold0}** / **{t_hold1}** | 保持段 |
| E[0] / E[149] | **{env[0]}** / **{env_tail}** | 起/收 |
| 保持段 E | **{hold_min:.4f} ~ {hold_max:.4f}** | hold 纹理 |

### 4.{sec_read} 观众读感（🧠 待审）

{read_lines}

### 4.{sec_conf} 避免混淆（🧠 待审）

| 别像 | 区分要点 |
|------|----------|
{conf_rows}

### 4.{sec_code} 代码映射

| 模块 | 职责 |
|------|------|
| [`envelope_compile.py`](../../../{compile_py}) | E(t) × PAD → 12 通道 |
| [`delivery_pipeline.py`](../../../gaze_engine/delivery_pipeline.py) | 物种交付 / 02 写出 |
| [`rhythm_compiler.py`](../../../gaze_engine/_shared/rhythm_compiler.py) | 节拍表 / blink 抽样 |

```text
{asset}
  → SliderPacket.from_dict
  → build_energy_envelope() → E(t)
  → {species} envelope_compile → 02_烘焙
```

---

## 五、检查点（Checkpoints）

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| JSON 与 §4.2/§4.{sec_pad} 一致 | diff 资产与本文表格 | 滑杆 + pad 全键相等 | P0 |
| peak_level | `export_envelope_series` | ≈ **{peak}**（±0.01） | P0 |
| E[149] | 同上 | **{env_tail}**（目标 0 或合同允差） | P0 |
| hold.shape | 目视 02 保持段 | 符合 **{hold.shape}** 纹理 | P1 |
| 读感 / 混淆 | 门户预览 5s | §4.{sec_read}/§4.{sec_conf} 人工打勾 | P1 |
| PAD 与通道 | 对比同组它情绪 PAD | P/A/D 至少一轴差异 ≥0.15 | P1 |
| 与同组它情绪 | 对比 peak+push+shape | 至少一项差异显著 | P1 |

```bash
python3 -c "
import sys; sys.path.insert(0,'{ROOT}')
import json
from pathlib import Path
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine._shared.envelope_compile import export_envelope_series
raw=json.loads(Path('{asset}').read_text())
pkt=SliderPacket.from_dict(raw)
m=export_envelope_series(pkt)
assert abs(m['peak_level']-{peak})<0.02, m['peak_level']
print('peak OK', m['peak_level'])
"
```

---

## 修改记录

| 日期 | 改了什么 | 原因 |
|------|----------|------|
| 2026-05-27 | 🧠 补 PAD 块 + §4.{sec_pad} | 预设资产缺 per-emotion PAD 定义 |
"""


def render_style_md(species: str, style: dict, folder: str) -> str:
    sp_label = SPECIES_LABEL[species]
    sid = style.get("id", folder)
    label = style.get("label", sid)
    asset = f"预设资产/风格包/{species}/{folder}/style.json"
    kind = "人格" if species == "human" else "品种"
    bo = style.get("base_offset") or {}
    sf = style.get("scale_factor") or {}
    keys = sorted(set(bo) | set(sf))
    matrix = _load_matrix_entry(species, sid) or {}
    archetype = _style_archetype_text(sid, style.get("notes") or "")

    ch_rows = "\n".join(_channel_style_row(k, bo.get(k, 0.5), sf.get(k, 0.1)) for k in keys)

    geom_block = ""
    tpl = matrix.get("template_scales") or {}
    if tpl:
        scale_rows = "\n".join(
            f"| `{k}` | **{v}** | 几何模板乘数 |"
            for k, v in tpl.items()
            if not str(k).startswith("_")
        )
        geom_block = f"""
### 4.4 几何模板（`breed_matrix` / persona_matrix）

| 键 | 值 | 说明 |
|----|-----|------|
{scale_rows}

> 控制点结构见 `gaze_engine/{species}/breed_matrix.json` 内 `template_structure`（如有）。
"""

    matrix_py = (
        "persona_matrix.json"
        if species == "human"
        else f"{species}/breed_matrix.json"
    )

    return f"""# {label} — {sp_label}{kind}风格合同（独立）

> **状态：🧠 脑补初稿（可逐份审定）** — 本文 **只管辖「{label}」**（id=`{sid}`）；不与其它{kind}合并修订。
> **数值真源**：`{asset}` · schema `ecursor_style_v1`
> **兄弟规范**：[`公共层边界合同.md`](../../06_架构/公共层边界合同.md)

---

## 一、概述（What）

### 本文件用途

定义 **{label}** 的 **12 通道 base_offset / scale_factor**（及几何偏移如有），描述气质与验收。  
改风格只改 **本文件 + 对应 style.json + 矩阵 JSON**，勿改情绪 md。

### 管线位置

| 环节 | 内容 |
|------|------|
| 上游 | 任意情绪 E(t)（`02_情绪/` 各独立 md） |
| **本合同** | 动态偏置 + 几何模板 |
| 下游 | 02 通道 styled 曲线 · OpenCV 底膜 · 04 Prompt 物种形容词 |

### 管辖 / 边界

| ✅ 本文件管 | ❌ 本文件不管 |
|------------|--------------|
| 本{kind}的 base/scale 定稿 | 情绪 macro/hold（各情绪独立 md） |
| 本{kind}的气质与通道读感 | E(t) 四段时间轴 |
| 与矩阵 JSON 同步 | 客户单次标定覆盖项 |

### 标识

| 项 | 值 |
|----|-----|
| id | `{sid}` |
| label | {label} |
| species | `{species}` |
| notes | {style.get("notes") or "🧠 待补"} |

---

## 二、理论依据（Theory）

### 动态层公式（与情绪正交）

```text
styled[ch, t] = clamp01( base_offset[ch] + scale_factor[ch] × pulse[ch, t] )
```

- `pulse` 来自情绪 E(t) 编译结果；**本{kind}不改变 E(t) 形状**。
- 实现入口：[`delivery_pipeline.py`](../../../gaze_engine/delivery_pipeline.py) · [`gaze_engine/{species}/`](../../../gaze_engine/{species}/)

### 几何层（如有）

- `template_scales` / `template_structure` → [`gaze_engine/{species}/{matrix_py}`](../../../gaze_engine/{species}/{matrix_py})
- 与客户 `SpeciesTemplate` 标定叠加，见 [`公共层边界合同.md`](../../06_架构/公共层边界合同.md)

---

## 三、为什么这样做（Why）

### 气质总述（🧠 待审）

{archetype}

### 通道级决策（🧠 脑补）

| 通道 | 中文 | base | scale | 🧠 意图 |
|------|------|------|-------|--------|
{ch_rows}

⚠️ **历史教训**：base 与 scale 同时拉满会导致 02 饱和 clippng → 先定 base 再定 scale。

---

## 四、怎么实现（How）

### 4.1 资产文件

`{asset}`

### 4.2 base_offset（静态偏置）

| 通道 | 值 |
|------|-----|
{chr(10).join(f'| `{k}` | **{bo.get(k, "-")}** |' for k in keys)}

### 4.3 scale_factor（动态增益）

| 通道 | 值 |
|------|-----|
{chr(10).join(f'| `{k}` | **{sf.get(k, "-")}** |' for k in keys)}
{geom_block}
### 4.{'5' if geom_block else '4'} 叠加示例

```text
情绪：任意（如 委屈·幼犬眼 / 魅惑·勾人）
  + 本{kind}：{sid}
  → pulse[ch,t]  --×scale + base--> styled[ch,t]
  → affine_renderer → 工程底膜
```

### 4.{'6' if geom_block else '5'} 代码映射

| 模块 | 职责 |
|------|------|
| [`{matrix_py}`](../../../gaze_engine/{species}/{matrix_py}) | 矩阵真源（应与 style.json 一致） |
| [`envelope_compile.py`](../../../gaze_engine/{species}/envelope_compile.py) | styled 公式（逐步接入 Pomot 路径） |
| 门户 `/api/portal/presets` | 风格包列表与路径 |

---

## 五、检查点（Checkpoints）

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| style.json 与 §4.2/4.3 一致 | diff | 全键相等 | P0 |
| 与矩阵 JSON 一致 | diff `{matrix_py}` | base/scale 一致 | P0 |
| 12 通道齐全 | 键集合 | 无缺失 | P0 |
| 叠加任意情绪 | 门户 ③→⑤ | 气质可辨、无 clippng | P1 |
| §3 气质描述 | 人工 | 已审定 | P1 |

---

## 修改记录

| 日期 | 改了什么 | 原因 |
|------|----------|------|
| 2026-05-27 | 🧠 生成器初稿 | 独立单项风格合同 |
"""


def write_species_emotion_overview(species: str, items: list[tuple]) -> None:
    sp_cn = SPECIES_DIR[species]
    out_dir = ROOT / "contracts" / "02_情绪" / sp_cn
    fname = PARENT_EMOTION[species]
    groups = _load_groups(species)
    group_txt = "\n".join(f"- **{g}**" for g in sorted(set(groups.values())))

    rows = "\n".join(
        f"| [{d}]({Path(d).stem}.md) | {groups.get(d, '🧠')} | `{fn}` | {pad} | {pk:.4f} | {sh} |"
        for d, fn, pad, pk, sh in items
    )

    content = f"""# {SPECIES_LABEL[species]}情绪 — 索引（非正文）

> ⚠️ **本文件不是情绪正文**。每一种情绪各有 **独立 md**，请打开链接逐份修订。
> 生成器：`python3 tools/03_工具脚本/generate_species_contracts.py`
> **PAD 总览**：[`PAD定位索引.md`](PAD定位索引.md)

**资产目录**：`预设资产/预设情绪包/{species}/`（每 JSON 含 `pad` 块）

---

## 分组一览

{group_txt}

---

## 单项合同链接（共 {len(items)} 个）

| 合同 | 分组 | 资产 | PAD (P,A,D) | peak | hold |
|------|------|------|-------------|------|------|
{rows}

---

## 相关规范

- [`滑杆规范.md`](../../01_总纲/滑杆规范.md)
- [`全量帧指令集规范.md`](../../01_总纲/全量帧指令集规范.md)
- [`合同规范.md`](../../合同规范.md)
"""
    (out_dir / fname).write_text(content, encoding="utf-8")


def write_species_pad_overview(species: str, items: list[tuple]) -> None:
    """各物种 PAD 定位索引（非正文）。"""
    sp_cn = SPECIES_DIR[species]
    out_dir = ROOT / "contracts" / "02_情绪" / sp_cn
    sp_label = SPECIES_LABEL[species]
    rows = "\n".join(
        f"| [{d}]({Path(d).stem}.md) | `{fn}` | {pad} | {pos} |"
        for d, fn, pad, pos in items
    )
    content = f"""# {sp_label} PAD 定位 — 索引（非正文）

> ⚠️ **本文件不是 PAD 正文**。每种情绪的 PAD 定稿见各单项 md 的 **§4 PAD 定位**。
> **数值真源**：`预设资产/预设情绪包/{species}/{{情绪}}.json` → `pad` 块。

---

## PAD 三轴说明

| 轴 | 含义 | 值域 | 作用 |
|----|------|------|------|
| **P** | 愉悦度 | [-1, 1] | 正=吸引/甜，负=不悦/压 |
| **A** | 激活度 | [-1, 1] | 正=急/警觉，负=软/困 |
| **D** | 控制度 | [-1, 1] | 正=支配/压人，负=顺从/退缩 |

**物种权重**：[`gaze_engine/{species}/pad_weights.py`](../../../gaze_engine/{species}/pad_weights.py)  
**与 E(t) 关系**：PAD **不参与**能量主钟；只分配 12 通道 scale。

---

## 全量 PAD 表（共 {len(items)} 个）

| 合同 | 资产 | PAD (P,A,D) | 一句话定位 |
|------|------|-------------|------------|
{rows}

---

## 相关规范

- [`{PARENT_EMOTION[species]}`]({PARENT_EMOTION[species]})
- [`滑杆规范.md`](../../01_总纲/滑杆规范.md)
- [`狗150帧全量编译合同_上篇.md`](../../06_架构/狗150帧全量编译合同_上篇.md) §S1（PAD 查表逻辑）
"""
    (out_dir / "PAD定位索引.md").write_text(content, encoding="utf-8")


def sync_pad_json(species: str, path: Path, raw: dict) -> dict:
    """若 JSON 缺 pad 或与真源不一致，写回 pad 块。"""
    emotion = str(raw.get("emotion") or path.stem)
    pad = pad_dict_for_json(emotion, species)
    if raw.get("pad") != pad:
        raw = dict(raw)
        raw["pad"] = pad
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return raw


def write_species_style_overview(species: str, items: list[tuple[str, str]]) -> None:
    sp_cn = SPECIES_DIR[species]
    out_dir = ROOT / "contracts" / "05_人格化" / sp_cn
    fname = PARENT_STYLE[species]
    kind = "人格" if species == "human" else "品种"
    rows = "\n".join(f"| [{lb}]({fid}.md) | `{fid}/style.json` |" for lb, fid in items)

    content = f"""# {SPECIES_LABEL[species]}{kind}风格 — 索引（非正文）

> ⚠️ **本文件不是风格正文**。每一种{kind}各有 **独立 md**，请打开链接逐份修订。

**资产目录**：`预设资产/风格包/{species}/` · schema `ecursor_style_v1`

---

## 单项合同链接（共 {len(items)} 个）

| 合同 | 资产 |
|------|------|
{rows}

---

## 相关规范

- [`公共层边界合同.md`](../../06_架构/公共层边界合同.md)
- [`合同规范.md`](../../合同规范.md)
"""
    (out_dir / fname).write_text(content, encoding="utf-8")


def write_redirect_stubs() -> None:
    stubs = {
        ROOT / "contracts/02_情绪/狗情绪与能量曲线.md": (
            "# 已迁移\n\n"
            "狗情绪 **单项正文** 见 [`02_情绪/狗/`](狗/) 下各 `{情绪名}.md`。\n\n"
            "索引（非正文）：[`02_情绪/狗/狗情绪与能量曲线.md`](狗/狗情绪与能量曲线.md)\n"
        ),
        ROOT / "contracts/02_情绪/魅惑勾人.md": (
            "# 已迁移\n\n"
            "独立正文：[`02_情绪/人/魅惑·勾人.md`](人/魅惑·勾人.md)\n"
        ),
        ROOT / "contracts/05_人格化/狗品种风格偏向.md": (
            "# 已迁移\n\n"
            "狗品种 **单项正文** 见 [`05_人格化/狗/`](狗/) 下各 `{id}.md`。\n\n"
            "索引：[`05_人格化/狗/狗品种风格偏向.md`](狗/狗品种风格偏向.md)\n"
        ),
    }
    for path, text in stubs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main() -> None:
    for species in ("human", "cat", "dog"):
        sp_cn = SPECIES_DIR[species]
        emo_out = ROOT / "contracts" / "02_情绪" / sp_cn
        emo_out.mkdir(parents=True, exist_ok=True)
        preset_dir = ROOT / "预设资产" / "预设情绪包" / species
        emo_items: list[tuple] = []
        pad_items: list[tuple] = []
        for f in sorted(preset_dir.glob("*.json")):
            if f.name.startswith("_"):
                continue
            raw = json.loads(f.read_text(encoding="utf-8"))
            raw = sync_pad_json(species, f, raw)
            pkt = SliderPacket.from_dict(raw)
            meta = export_envelope_series(pkt)
            display = raw.get("label") or raw.get("emotion") or f.stem
            if species in ("human", "dog"):
                display = f.stem
            P, A, D = resolve_pad(pkt)
            pad_str = f"({P}, {A}, {D})"
            pos = (raw.get("pad") or {}).get("position") or pad_position_text(P, A, D)
            md = render_emotion_md(species, display, f.name, pkt, raw, meta)
            (emo_out / f"{display}.md").write_text(md, encoding="utf-8")
            emo_items.append((display, f.name, pad_str, meta["peak_level"], pkt.hold_seg.shape))
            pad_items.append((display, f.name, pad_str, pos))
        write_species_emotion_overview(species, emo_items)
        write_species_pad_overview(species, pad_items)

        sty_out = ROOT / "contracts" / "05_人格化" / sp_cn
        sty_out.mkdir(parents=True, exist_ok=True)
        style_root = ROOT / "预设资产" / "风格包" / species
        sty_items: list[tuple[str, str]] = []
        for sf in sorted(style_root.glob("*/style.json")):
            st = json.loads(sf.read_text(encoding="utf-8"))
            label = st.get("label", sf.parent.name)
            md = render_style_md(species, st, sf.parent.name)
            (sty_out / f"{sf.parent.name}.md").write_text(md, encoding="utf-8")
            sty_items.append((label, sf.parent.name))
        write_species_style_overview(species, sty_items)

    write_redirect_stubs()
    print("OK: 38 emotion + 14 style standalone contracts + 6 index + 3 PAD index")


if __name__ == "__main__":
    main()
