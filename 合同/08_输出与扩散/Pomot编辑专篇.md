# Pomot 编辑专篇 — 客户怎么改、滑杆怎么变节拍表

> **只管编辑侧**：NL 怎么拆、两轮怎么改、**滑杆 → 02 → 节拍表** 的原理。  
> **打包、送 Wan、export API** → [`扩散输出流程专篇.md`](扩散输出流程专篇.md)  
> **宏观管线** → [`00_从门户到扩散_管线总览.md`](../00_管线导读/00_从门户到扩散_管线总览.md)

---

## 一、核心原理：滑杆变节拍器

### 1.1 链路（节拍表不手写）

```text
SliderPacket（macro×6 + hold×4 + pad + ear）
        ↓  delivery_pipeline（01～06）
02_烘焙_*.json   channel_tracks[12][t].v
        ↓  rhythm_compiler.build_metronome_text()   ← 「滑杆变节拍器」
扩散节拍表（嵌入 04 的 ## 扩散节拍表）
        ↓  DiffusionPromptAssembler.assemble() → split_for_wan()
04 / wan±（见流程专篇 §二）
```

改任一 **macro/hold** → 02 变 → 节拍表全文变 → Prompt 变。  
**禁止**手写节拍表顶替 02；**禁止** 04 与 02 不同 revision。

### 1.2 滑杆在 Prompt 链里的角色

| 滑杆 | 进 02 | 节拍表里 |
|------|-------|----------|
| push/power/speed | E(t) 峰与起势 | 全局阶段、幅度 |
| steady/grip | 盯住 plateau | 保持段 |
| hold_seg.shape/pulse | 盯住纹理 | tremble/pulse/flat |
| pad | **不进** E(t)，改通道 scale | 委屈/施压等配比 |

**NL-A**（情绪）→ 将来编译成 `SliderPacket`；**NL-B**（叙事 `action`）不进眼眉链，只进 04 `## 叙事`。

### 1.3 三份真源

| 产物 | 角色 |
|------|------|
| `02_烘焙_*.json` | 机器真源，**不送** Wan |
| `## 扩散节拍表` | 02 的人话翻译 |
| `04` / `wan±` | 归档 + CLIP |

节拍表格式细则：[`节奏说明书.md`](../08_输出与扩散/节奏说明书.md) · [`节奏说明书编译器.md`](../08_输出与扩散/节奏说明书编译器.md)

---

## 二、Pomot 怎么编辑

### 2.1 客户界面

- 只见 **对话框 + 参考图**；不见滑杆、02、通道名。
- **round1**：戏 + 情绪（测试期手选预设+滑杆；产品态整句 NL）。
- **round2**：只微调（「再委屈一点」），**不换 preset、不换 hold_seg.shape**。

### 2.2 NL 两路

| 路 | 字段 | 去向 |
|----|------|------|
| 叙事 | `action` 原文 | `04` `## 叙事` → `wan_positive`；**禁止 LLM 改写** |
| 情绪 | `emotion` → preset | `SliderPacket` → 02 → 节拍表 |

整句 NL 里「跑回笼子」是场景，不能整句只进眼眉链。

### 2.3 两轮规则

| 轮次 | 行为 | 锁定 |
|------|------|------|
| round1 | 拆解 → 路由 → 预设 → `run_species_delivery` → `assemble` | — |
| round2 | `delta` 宏滑杆 | preset 名、`hold_seg.shape` |

| 说法 | delta（示意） |
|------|----------------|
| 再委屈一点 | power↓ push↓ |
| 再狠一点 | power↑ |
| 再急一点 | speed↑ |

round2 **禁止**重走路由换 preset。

### 2.4 API

```text
POST /api/portal/pomot/round1|round2
  → pomot/pipeline.py → nl_splitter · emotion_router · composer|delta
  → delivery_pipeline → 02
  → assembler.assemble → prompt_04 + wan±
（无 MP4；MP4 在 export，见流程专篇）
```

---

## 三、节拍表编译（`rhythm_compiler`）

```python
beat_text = build_metronome_text(baked_json, species="dog")
```

写入 `04` 的 `## 扩散节拍表`，六块结构：

```text
① 文件头  ② ## 全局阶段  ③ ## 各通道脉冲（t,v + → 节拍：hint）
④ ## 时间轴汇合  ⑤ ## 给扩散的硬约束  ⑥ ## 出厂质检（若有）
```

- 150 帧定稿：每通道约 **20** 个采样点；**blink** 强制保留非零峰。
- hint 真源：`{species}/rhythm_data.py` 的 `DIFFUSION_HINTS`；**LLM 不编** t/v。

---

## 四、代码映射

| 职责 | 文件 |
|------|------|
| NL 拆解 | `pomot/nl_splitter.py` |
| 情绪→preset | `pomot/emotion_router.py` |
| round1 | `pomot/composer.py` · `nl_to_packet.py` |
| round2 | `pomot/delta.py` |
| 02 | `delivery_pipeline.py` |
| 节拍表 | `_shared/rhythm_compiler.py` |
| 04 拼装 | `pomot/assembler.py` |
| 门户 | `serve_workbench.py` `portal_pomot_round1/2` |

---

## 五、检查点

| 检查 | 合格 |
|------|------|
| `build_metronome_text(02)` | 12 通道、含 `→ 节拍：` |
| 叙事 = `action` 原文 | 未被改写 |
| round2 前后 emotion id | 相同 |
| 02/04 revision | 一致 |

```bash
python3 scripts/verify_diffusion_prompt_contract.py
```

---

> | 日期 | 说明 |
> |------|------|
> | 2026-05-28 | 自 `09/Pomot编辑与Prompt编译专篇` 迁入 `08`；与流程专篇去重 |
