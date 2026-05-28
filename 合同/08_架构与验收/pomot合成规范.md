# 预设 Prompt 模板（Pomot）合成规范

> **管线位置**：客户自然语言 → **本环节（Pomot 合成）** → 扩散引擎输入
>
> **核心角色**：将客户一句话拆解为「叙事动作」和「情绪」两路——叙事动作直接送扩散引擎作为视频内容描述，情绪走眼眉管线生成滑杆脉冲 → 经 affine_renderer 渲染为 OpenCV 线条图 MP4（视觉控制信号）+ 经 rhythm_compiler + assembler 拼装为 04_Prompt.txt（语义控制信号），**两路合并**送扩散引擎。
>
> **一句话**：Pomot = 客户 NL → 拆解两路 → 叙事动作 + 眼眉线条图 MP4 + 04_Prompt.txt → 合并送扩散引擎

**本文件是 `合同/合同规范.md` 的实例，遵循五段格式。**

**引用本合同的兄弟文件**：

| 文件 | 关系 |
|------|------|
| [`全量帧指令集规范.md`](../04_通道与先验/全量帧指令集规范.md) | 下游：定义 12 通道 × 150 帧的工程真值 |
| [`节奏说明书.md`](../04_通道与先验/节奏说明书.md) | 下游：定义 05_扩散节拍表.txt 的格式 |
| [`眼眉指令集_全局情绪节奏主钟.md`](../04_通道与先验/眼眉指令集_全局情绪节奏主钟.md) | 下游：定义 12 通道指令集协议 |
| [`流程设计.md`](流程设计.md) | 上层：双模驱动管线架构 |
| [`工程底膜合同.md`](../06_工程底膜/工程底膜合同.md) | 下游：定义线条图渲染协议——工程底膜是 OpenCV 渲染的 150 帧 RGB 三色分离 PNG/MP4 |
| [`工程底膜驱动规范.md`](../06_工程底膜/工程底膜驱动规范.md) | 下游：定义 affine_renderer 驱动规范 |
| [`扩散引擎包组装专篇.md`](../07_输出与扩散/扩散引擎包组装专篇.md) | 下游：MP4 已渲染后，NL + 正反向 + **底膜解读** → `扩散引擎包/` |
| [`channel_contract.py`](../../gaze_engine/_shared/channel_contract.py) | 代码真源：`CANONICAL_KEYS`、`DIFFUSION_HINTS` |
| [`rhythm_compiler.py`](../../gaze_engine/_shared/rhythm_compiler.py) | 代码真源：节奏说明书生成器 |
| [`delivery_pipeline.py`](../../gaze_engine/delivery_pipeline.py) | 代码真源：管线执行入口 |
| [`affine_renderer.py`](../../gaze_engine/human/affine_renderer.py) | 代码真源：12 通道 → 线条图渲染 |

---

## 一、概述（What）

### 1.1 本文件管什么

本文定义 **Pomot 合成系统** 的完整规范，包括：

| 环节 | 范围 |
|------|------|
| ✅ NL 拆解 | 客户一句话拆成「叙事动作」和「情绪」 |
| ✅ 情绪路由 | 情绪词 → 系统预设名 + 物种/品种 |
| ✅ 第一轮合成 | 预设模板 + 客户 NL → SliderPacket |
| ✅ 第二轮微调 | 上一轮 SliderPacket + 客户修饰语 → 新版 SliderPacket |
| ✅ 最终拼装 | 02_烘焙.json + 客户叙事 + 元信息 → 04_Prompt.txt → 与线条图 MP4 合并送扩散引擎 |

### 1.2 最终送扩散引擎的是什么

**扩散引擎收到的不是 JSON，而是两样东西：**

```
送 Wan 扩散引擎的输入 = {
    ① OpenCV 线条图 MP4（或 PNG 序列）  ← 视觉控制信号
       (150帧 × 690×361, RGB三色分离)
       R=眼眶, G=眉脊/耳廓, B=瞳孔
       ↑ 由 affine_renderer 从 12×150 数值渲染

    ② 04_给视频生成的Prompt.txt          ← 语义控制信号
       = 正向Prompt + 扩散节拍表 + 客户叙事 + 负向Prompt
       ↑ 由 assembler 拼装
}
```

**流程图：**

```
02_烘焙_真人律.json (12×150 数值)  ← 内部中间文件，不送扩散
        │
        ├──→ affine_renderer.py → ① OpenCV 线条图 MP4/PNG → 送扩散
        │
        └──→ rhythm_compiler.py → 05_节拍表.txt
                 └──→ assembler.py (拼入客户叙事+元信息) → ② 04_Prompt.txt → 送扩散
```

### 1.3 边界（非管辖）

| ❌ 不管 | 原因 |
|---------|------|
| 12 通道指令集的数值生成 | 见 [`全量帧指令集规范.md`](../04_通道与先验/全量帧指令集规范.md) |
| 节奏说明书（05_节拍表.txt）的生成 | 见 [`节奏说明书.md`](../04_通道与先验/节奏说明书.md)，由 [`rhythm_compiler.py`](../../gaze_engine/_shared/rhythm_compiler.py) 实现 |
| 工程底膜/线条图的渲染 | 见 [`工程底膜合同.md`](../06_工程底膜/工程底膜合同.md)，由 [`affine_renderer.py`](../../gaze_engine/human/affine_renderer.py) 实现 |
| 物种预设的具体数值 | 见 [`dog/presets.py`](../../gaze_engine/dog/presets.py) 等 |
| 客户资产库的存储 | 见 [`customer_db.py`](../../gaze_engine/_shared/customer_db.py) |

### 1.4 客户可见的交互面

Pomot 系统对客户暴露的唯一界面是**纯文本对话框 + 照片上传**。客户看不到：

- ❌ 滑杆数值
- ❌ 预设名称
- ❌ 12 通道曲线
- ❌ 02_烘焙_真人律.json
- ❌ 任何技术参数

客户能做的只有：**说一句话 → 收到结果 → 再说一句话微调**。

### 1.5 关键术语

| 术语 | 含义 |
|------|------|
| **Pomot** | Preset Prompt Template，预设资产的 Prompt 模板 |
| **NL 拆解** | 把客户一句话拆成「叙事动作」和「情绪」 |
| **叙事动作** | 送扩散引擎的视频主体内容描述（如 "走回笼子回头"），拼入 04_Prompt.txt |
| **情绪路由** | 客户情绪词映射到系统内部的预设名 + 物种/品种 |
| **第一轮** | 从零生成 SliderPacket，走完整管线 |
| **第二轮** | 基于上一轮 SliderPacket 叠加 delta 修饰，不走完整管线 |
| **最终拼装** | 02_烘焙.json + 客户叙事 + 元信息 → 04_给视频生成的Prompt.txt（与 OpenCV 线条图 MP4 一起送扩散） |

---

## 二、理论依据（Theory）

### 2.1 理论依据链

```
① 扩散引擎（Wan）需要两路输入：
     - 像素级控制：工程底膜线条图序列（150 帧 RGB 三色分离 PNG/MP4）
     - 语义级控制：自然语言 Prompt（描述场景、情绪、节奏）
   → 两路缺一不可（引用: 节奏说明书.md §二）

② 客户只能表达"想要什么"，不能直接操作技术参数：
     - "狗子再委屈一点" → 不能要求客户填滑杆数值
   → 必须有 NL → 技术参数的自动翻译层

③ 同一情绪在不同物种/品种上有不同表现：
     - 委屈 = 狗:耳位耷拉 + 瞳孔略放大 + 慢眨
     - 委屈 = 人:眉压低垂 + 视线下垂 + 眼眶湿润
   → 必须有情绪路由，按物种/品种选择对应的预设模板

④ 提示词模板、线条图、节奏说明书必须同源同版本：
     - 管线生成 02_烘焙.json（12×150 数值）
     - 该数值 → 节奏说明书 + 线条图 + 04_Prompt.txt
     - 三者必须从同一份 02、同一 revision 生成（导出时重渲 MP4）
   → 拼装器必须从 02_烘焙.json 实时生成 04_Prompt.txt，而不是用静态模板
```

### 2.2 设计依据

```
设计决策                   依据
─────────────────────────────────────────────────────
NL 拆解                   客户只说一句话，但扩散引擎需要分开
                          处理叙事动作和情绪微表情

情绪路由                  同一词"委屈"在狗/猫/人上对应不同预设
                          （狗:耳位耷拉；人:眉压低垂）

第一轮+第二轮              客户第一轮说场景，第二轮说微调
                          不需要重新走完整管线，只改 delta

最终拼装                  05_节拍表 已有（rhythm_compiler），
                          OpenCV 线条图已有（affine_renderer），
                          唯一缺的是把 + 客户叙事 + 元信息 拼成 04_Prompt.txt
```

---

## 三、为什么这样做（Why）

### 3.1 关键决策

#### 决策 1：NL 拆解为「叙事动作」和「情绪」两路

```
备选方案:
  方案 A（选中）: 拆成两路
     - 叙事动作 → 拼入 04_Prompt.txt 的叙事段（扩散引擎的视频主体）
     - 情绪 → 走眼眉管线（滑杆脉冲 → 线条图 + 节拍表）
  方案 B: 不拆，整句送眼眉管线
     - 问题: "走回笼子"不是眼眉能控制的内容
  方案 C: 不拆，整句送扩散引擎
     - 问题: 失去了眼眉脉冲对微表情的精细控制

选择理由:
  两路分工最合理——叙事动作决定"演什么"，
  眼眉管线决定"怎么演这个情绪的表情"。
```

#### 决策 2：第二轮用 delta 叠加，不走完整管线

```
备选方案:
  方案 A（选中）: 解析修饰词（"再委屈一点"）→ delta 叠加
     - 轻量，不需要重新过 LLM
     - 保留上一轮所有结构，只改幅度
  方案 B: 重新走 NL → 预设 → 管线
     - 浪费，客户只改了情绪强度
     - 可能选到不同的预设，导致风格不一致

选择理由:
  ⚠️ 经验教训: 第二轮重新走 LLM 经常换预设，
  导致两版之间风格断裂。delta 叠加保证一致性。
```

#### 决策 3：04_Prompt.txt 动态生成而非静态模板

```
备选方案:
  方案 A（选中）: 从 02_烘焙.json 实时拼装
     - 保证 04_Prompt 与 02_数值、05_节拍表、线条图 同源
  方案 B: 预设资产里放静态 04_Prompt.txt
     - 问题: 第二轮微调后，02_更新了、线条图变了，但 04_还是旧的
     - ⚠️ 静态模板与管线产出不同步是大坑

选择理由:
  Pomot 的核心价值就是"自动拼装，版本同步"。
  每次管线执行后重新拼装，确保三件套（线图+节拍表+04_Prompt）一致。
```

### 3.2 历史教训

⚠️ **静态模板陷阱**：之前的 `04_给视频生成的Prompt.txt` 是手写静态文件，管线和 prompt 不同步——改滑杆后 02_更新了、线条图变了，但 04_没变。Pomot 合成必须**从 02_烘焙.json 实时生成 04_，不允许静态模板**。

⚠️ **第二轮换预设**：客户说"再委屈一点"，LLM 可能理解成"换一个更委屈的预设"，导致选到"要哭未哭"。第二轮必须**锁定第一轮的 preset，只改宏滑杆数值，不换预设**。

⚠️ **把 JSON 当最终输出**：`02_烘焙_真人律.json` 是**内部中间文件**，不是送扩散引擎的最终产物。最终产物只有**两种线条图 MP4 + 04_Prompt.txt 文本**。任何认为"送 JSON 给扩散引擎"的理解都是错误的。

---

## 四、怎么实现（How）

### 4.1 完整数据流

```
客户一句话 + 照片
       │
       ▼
┌──────────────────────┐
│  1. NL 拆解           │
│  (nl_splitter)       │
└────────┬─────────────┘
         │
    ┌────┴────┬───────────┐
    ▼         ▼           ▼
 action    emotion     species/breed
 "走回笼子"  "委屈"     "狗/贵宾犬"
    │         │           │
    │         ▼           │
    │  ┌────────────────┐ │
    │  │ 2. 情绪路由     │ │
    │  │(emotion_router) │ │
    │  │ 委屈→可怜·委屈  │ │
    │  │ 狗→DOG_PRESETS │ │
    │  └────────┬───────┘ │
    │           │         │
    │           ▼         │
    │  ┌────────────────┐ │
    │  │ 3. 加载预设     │ │
    │  │ (registry)     │ │
    │  │ dog/presets.py │ │
    │  │ dog/breeds.py  │ │
    │  └────────┬───────┘ │
    │           │         │
    │           ▼         │
    │  ┌────────────────┐ │
    │  │ 4. 第一轮合成   │ │
    │  │ (composer)     │ │
    │  │ → SliderPacket │ │
    │  └────────┬───────┘ │
    │           │         │
    │           ▼         │
    │  ┌────────────────┐ │
    │  │ 5. 管线执行     │ │
    │  │ (delivery_     │ │
    │  │  pipeline)     │ │
    │  │ → 02_烘焙.json │ │
    │  └────────┬───────┘ │
    │           │         │
    └─────┬─────┴─────────┘
          │
          ▼
┌──────────────────────────────────┐
│  6. 最终拼装 (assembler)         │
│                                  │
│  输入:                            │
│    · 02_烘焙.json (12×150 数值)  │
│    · 客户叙事 (action)           │
│    · 元信息 (物种/品种/情绪)      │
│                                  │
│  处理:                            │
│    · 02_烘焙.json → 05_节拍表.txt │
│      （rhythm_compiler · 底膜解读）│
│    · 05_节拍表 + 叙事 + 元信息     │
│      → 04_Prompt.txt             │
│    · export 时：affine_renderer   │
│      → 03_工程底模.mp4            │
│    · build_diffusion_bundle()    │
│      → 扩散引擎包/               │
│                                  │
│  输出（送扩散引擎）:               │
│    ① OpenCV 线条图 MP4           │
│    ② 04 + wan±（含底膜解读）     │
│                                  │
│  详见 [`扩散引擎包组装专篇.md`](../07_输出与扩散/扩散引擎包组装专篇.md) │
└──────────────────────────────────┘
```

### 4.2 最终送扩散引擎的内容

#### ① OpenCV 线条图 MP4

由 [`affine_renderer.py`](../../gaze_engine/human/affine_renderer.py) 渲染。150 帧 RGB 三色分离图像：

| 通道 | 颜色 | 内容 |
|------|------|------|
| R | RGB(255,0,0) | 眼眶轮廓（闭合路径） |
| G | RGB(0,255,0) | 眉脊线 / 耳廓线（物种自适应） |
| B | RGB(0,0,255) | 虹膜 + 瞳孔（实心区域） |

扩散引擎在**对应的像素位置**生成真实画面。没有面部时，线条图不可见但节奏依然有效。

#### ② 04_给视频生成的Prompt.txt

拼装后的文本结构：

```
【正向】
{物种/品种描述}，{场景/灯光/质感由 LLM 补充}，
情绪浓度 100，{情绪标签}，
眉毛与耳朵的运动严格跟随控制序列的节奏与幅度，
整体节奏紧跟眉眼控制序列的节奏与幅度，
眉眼以外可自然发挥，情绪起伏每一拍与眉眼对齐，
{景别}，单人/单动物，高清。

【扩散节拍表】
{05_扩散节拍表.txt 的完整内容}

【叙事】
{客户原始叙事文本，如"委屈的跑回了笼子再回头看了一眼"}

【负向】
色调艳丽，过曝，模糊，字幕，低质量，丑陋，畸形，脸变形，...
```

### 4.3 模块规范

#### 4.3.1 `nl_splitter.py` — NL 拆解器

**输入**：
```json
{
  "customer_nl": "想看到整个狗子被打了一顿，最后委屈的跑回了笼子再回头看了一眼",
  "photo_hint": "参考照片（可选，用于提取物种/品种）"
}
```

**输出**：
```json
{
  "action": "走回笼子再回头",
  "emotion": "委屈",
  "species_hint": "dog",
  "breed_hint": "贵宾犬"
}
```

**拆解规则**（关键词/LLM）：

| 拆解项 | 规则 |
|--------|------|
| 动作提取 | 匹配"走回、回头、跑、看、打"等动词短语 |
| 情绪提取 | 匹配"委屈、可怜、魅惑、施压"等情绪词 |
| 物种识别 | 匹配"狗、猫、人、贵宾犬、布偶猫"等 |
| 品种识别 | 从物种+照片/关键词推断具体品种 |

**当无法拆解时**：
- 无动作：默认为"中性注视"
- 无情绪：默认为"中性"
- 无法识别物种：提示客户补充描述

#### 4.3.2 `emotion_router.py` — 情绪路由

**输入**：`{ emotion: "委屈", species_hint: "dog", breed_hint: "贵宾犬" }`

**输出**：`{ species: "dog", preset_name: "可怜·委屈", breed: "贵宾犬" }`

**映射规则**：

| 客户情绪词 | 狗预设 | 猫预设 | 人预设 |
|-----------|--------|--------|--------|
| 委屈/可怜 | 可怜·委屈 | 可怜·委屈 | 可怜·委屈 |
| 魅惑/勾人 | 魅惑·勾人 | 魅惑·勾人 | 魅惑·勾人 |
| 施压/凝视 | — | — | 施压·凝视 |
| 怒/瞪 | — | — | 怒视·压人 |
| 惊/吓 | — | 惊惧·一怔 | 惊惧·一怔 |

**品种路由**：

| 物种 | 品种配置来源 | 品种加载函数 |
|------|-------------|-------------|
| `dog` | [`dog/breeds.py`](../../gaze_engine/dog/breeds.py) `BREEDS` | `breeds.get(品种名)` |
| `cat` | [`cat/breeds.py`](../../gaze_engine/cat/breeds.py) `BREEDS` | `breeds.get(品种名)` |
| `human` | 无品种差异 | — |

#### 4.3.3 `composer.py` — 第一轮合成

**输入**：
```json
{
  "preset_name": "可怜·委屈",
  "species": "dog",
  "breed": "贵宾犬",
  "emotion_nl": "委屈"
}
```

**输出**：`SliderPacket`

**合成流程**：
```
1. 加载预设: dog/presets.py[可怜·委屈] → SliderPacket(基础版)
2. 加载品种微调: dog/breeds.py[贵宾犬] → 品种通道调整
3. 加载 NL 修饰: _parse_modifiers("委屈") → delta(可选)
4. 合成: 基础版 + 品种调整 + NL delta → 最终 SliderPacket
```

#### 4.3.4 `delta.py` — 第二轮微调

**输入**：
```json
{
  "previous_slider_packet": { ... },
  "customer_nl": "希望狗子再委屈一点"
}
```

**输出**：`SliderPacket` (微调版)

**delta 解析规则**（继承自 [`nl_to_packet.py`](../../gaze_engine/nl_to_packet.py)）：

| 客户说法 | delta |
|---------|-------|
| 再委屈一点 | `{ power: -8, push: -8 }` |
| 再可怜一点 | `{ power: -5, push: -5 }` |
| 再冷一点 | `{ power: 5, steady: 5, grip: 5 }` |
| 再狠一点 | `{ power: 8, push: 4 }` |
| 再急一点 | `{ speed: 8 }` |

⚠️ **禁止行为**：
- 禁止换 preset（锁定第一轮的 `emotion` 不变）
- 禁止改 hold_seg.shape（锁定第一轮的 shape）
- 只允许修改 macro 6 键 + hold_seg 的 pulse_rate/pulse_depth/swell

#### 4.3.5 `assembler.py` — 最终拼装器

**输入**：
```json
{
  "baked_json": "02_烘焙_真人律.json 的完整内容",
  "customer_action": "走回笼子再回头",
  "metadata": {
    "species": "dog",
    "breed": "贵宾犬",
    "emotion": "可怜·委屈",
    "reference_photo_path": "客户上传的照片路径"
  }
}
```

**输出**（送扩散引擎的两样东西）：
```json
{
  "prompt_04": "# 给视频生成引擎的说明\n\n...",
  "wan_positive_clip": "正向 + 扩散节拍表 + 叙事",
  "wan_negative_clip": "负向模板",
  "payload": {
    "video": "",
    "prompt": "04_Prompt.txt 内容"
  }
}
```

> ⚠️ **当前实现**：`assembler.assemble()` **只出 04 与 wan± 文本**，`payload.video` 为空。  
> MP4 由 `POST /api/portal/export` 调用 `_render_opencv_video()` 生成，再经 `build_diffusion_bundle()` 打包。见 [`扩散引擎包组装专篇.md`](../07_输出与扩散/扩散引擎包组装专篇.md)。

**拼装逻辑**：

```python
def assemble(baked_json, customer_action, metadata):
    # 1. 调用 rhythm_compiler 生成 05_扩散节拍表.txt
    beat_text = build_metronome_text(baked_json, species=metadata.species)
    #    ↑ 已有代码, 来自 gaze_engine/_shared/rhythm_compiler.py

    # 2. MP4 不在 assembler 内渲染 — 见 portal_export → _render_opencv_video()

    # 3. 拼装 04_给视频生成的Prompt.txt（含底膜解读 = ## 扩散节拍表）
    mood_tags = [metadata.emotion]
    prompt_04 = f"""# 给视频生成引擎的说明

## 核心定义
情绪: {metadata.emotion}
物种: {metadata.species}
品种: {metadata.breed}

## 正向 Prompt
{metadata.species}/{metadata.breed}，{{场景/灯光/质感由 LLM 补充}}，
情绪浓度 100，{'、'.join(mood_tags)}，
眉毛与耳朵的运动严格跟随控制序列的节奏与幅度，
整体节奏紧跟眉眼控制序列的节奏与幅度，
眉眼以外可自然发挥，情绪起伏每一拍与眉眼对齐，
{metadata.species == 'dog' and '狗狗' or '单人'}，高清。

## 扩散节拍表
{beat_text}

## 叙事
{customer_action}

## 负向 Prompt
色调艳丽，过曝，模糊，字幕，低质量，丑陋，畸形，脸变形，
换脸，多余人物，眉眼与画面不同步，乱动脱节，
情绪浓度不足，涣散无神，夸张鬼脸，杂乱背景
"""

    # 4. 返回 04（MP4 由 export 另行渲染并打包）
    return {
        "prompt": prompt_04,
    }
```

### 4.4 两轮对话的版本管理

| 轮次 | SliderPacket | 02_烘焙.json | OpenCV 线条图 | 05_节拍表.txt | 04_Prompt.txt |
|------|-------------|-------------|--------------|--------------|--------------|
| 第一轮 | `version_1` | `02_v1.json` | `线条图_v1.mp4` | `05_v1.txt` | `04_v1.txt` |
| 第二轮 | `version_2` (delta) | `02_v2.json` | `线条图_v2.mp4` | `05_v2.txt` | `04_v2.txt` |

**保存路径**：`客户资产库/客户_C{xxx}/项目_P{xxx}/调整过程/` 下依次递增

### 4.5 代码映射

| 模块 | 文件路径 | 状态 |
|------|---------|------|
| NL 拆解器 | [`gaze_engine/pomot/nl_splitter.py`](../../gaze_engine/pomot/nl_splitter.py) | ❌ 待建 |
| 情绪路由 | [`gaze_engine/pomot/emotion_router.py`](../../gaze_engine/pomot/emotion_router.py) | ❌ 待建 |
| 预设注册表 | [`gaze_engine/pomot/registry.py`](../../gaze_engine/pomot/registry.py) | ❌ 待建 |
| 预设模板定义 | [`gaze_engine/pomot/templates.py`](../../gaze_engine/pomot/templates.py) | ❌ 待建 |
| 第一轮合成 | [`gaze_engine/pomot/composer.py`](../../gaze_engine/pomot/composer.py) | ❌ 待建 |
| 第二轮微调 | [`gaze_engine/pomot/delta.py`](../../gaze_engine/pomot/delta.py) | ❌ 待建 |
| 最终拼装器 | [`gaze_engine/pomot/assembler.py`](../../gaze_engine/pomot/assembler.py) | ❌ 待建 |
| 节奏说明书 | [`gaze_engine/_shared/rhythm_compiler.py`](../../gaze_engine/_shared/rhythm_compiler.py) | ✅ 已有 |
| 管线执行 | [`gaze_engine/delivery_pipeline.py`](../../gaze_engine/delivery_pipeline.py) | ✅ 已有 |
| 线条图渲染 | [`gaze_engine/human/affine_renderer.py`](../../gaze_engine/human/affine_renderer.py) | ✅ 已有 |
| NL → 预设映射 | [`gaze_engine/nl_to_packet.py`](../../gaze_engine/nl_to_packet.py) | ✅ 已有 |

### 4.6 调用关系

```
serve_workbench.py (API 入口)
  │
  ├→ pomot/nl_splitter.py        # 拆解客户 NL
  ├→ pomot/emotion_router.py     # 情绪 → 预设名
  ├→ pomot/registry.py           # 加载预设模板
  ├→ pomot/composer.py           # 第一轮 → SliderPacket
  │     └→ nl_to_packet.py       # NL → packet (已有)
  │
  ├→ delivery_pipeline.py        # 管线执行 → 02_烘焙.json (已有)
  │     ├→ rhythm_compiler.py    # → 05_节拍表.txt (已有)
  │     └→ affine_renderer.py    # → 线条图 MP4 (已有)
  │
  ├→ pomot/delta.py              # 第二轮: delta 叠加
  │
  └→ pomot/assembler.py          # 最终拼装 → 送扩散引擎
        └→ rhythm_compiler.py    # → 05_节拍表.txt (复用)
        └→ affine_renderer.py    # → 线条图 MP4 (复用)
```

---

## 五、检查点（Checkpoints）

### 5.1 NL 拆解验收

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| 动作提取准确 | 输入 "委屈的跑回笼子" → 输出 action 含"跑回笼子" | action 不为空且包含动词 | P0 |
| 情绪提取准确 | 输入 "委屈的跑回笼子" → 输出 emotion="委屈" | emotion 匹配已知情绪词 | P0 |
| 物种识别准确 | 输入含"狗/贵宾犬" → species="dog" | species 为 dog/cat/human 之一 | P0 |
| 无情绪回退 | 输入 "拍个视频" → 默认 emotion="中性" | 不抛异常 | P1 |

### 5.2 情绪路由验收

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| 预设映射 | emotion="委屈" + species="dog" → preset="可怜·委屈" | 匹配已知预设名 | P0 |
| 品种加载 | breed="贵宾犬" → 成功加载 breeds.py 配置 | 不抛异常 | P1 |
| 无匹配回退 | emotion="未知" → 回退到默认预设 | 不抛异常，返回默认 | P1 |

### 5.3 第一轮合成验收

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| 预设加载完整 | 调用 composer → SliderPacket | 所有字段非空 | P0 |
| 品种微调生效 | 贵宾犬 vs 金毛 → channel 数值有差异 | 品种参数被应用 | P1 |
| NL 修饰生效 | "更冷" → power>50 | delta 被叠加 | P0 |

### 5.4 第二轮微调验收

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| delta 叠加正确 | "再委屈一点" → push↓ power↓ | 数值降低 | P0 |
| preset 锁定 | 第二轮前后 preset 名一致 | 不换预设 | P0 |
| hold_seg 锁定 | 第二轮前后 shape 一致 | 不换 shape | P0 |

### 5.5 最终拼装验收

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| 线条图 MP4 存在 | 调用 assembler 后检查 video 路径 | 文件存在且非空 | P0 |
| 04_Prompt 包含客户叙事 | 拼装后 grep 客户原文 | 原文在 Prompt 中 | P0 |
| 04_Prompt 包含节拍表 | 拼装后包含"各通道脉冲" | 12 通道完整 | P0 |
| 04_Prompt 包含负向 | 拼装后包含"负向 Prompt" | 负向段非空 | P1 |
| 物种/品种正确填入 | 拼装后含 metadata.species | 物种出现在 prompt 中 | P0 |
| 线条图与 04_Prompt 同版本 | 两件产物的版本号一致 | version_1 或 v1 | P0 |

### 5.6 端到端验收

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| 第一轮完整链路 | 客户 NL + 照片 → 送扩散引擎 | payload 含 video 和 prompt | P0 |
| 第二轮完整链路 | 新增 NL → delta → 新线条图+新 prompt | 线条图数值有变化 | P0 |
| 两轮版本独立 | 第一轮和第二轮的线条图/04/05 独立保存 | 文件路径不同 | P1 |

### 5.7 关键认知验收

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| 不把 JSON 当最终输出 | 查看送扩散引擎的 payload | payload 中没有 .json 文件 | P0 |
| 明确两路输入 | 确认送扩散引擎的内容 | 只有线条图 MP4 + 04_Prompt.txt | P0 |

---

## 六、修改记录

| 日期 | 修改内容 | 原因 |
|------|---------|------|
| 2026-05-25 | 初始版本 | 按 `合同规范.md` 五段格式编写 |
| 2026-05-28 | 修正 assembler 不渲染 MP4；链至 [`扩散引擎包组装专篇.md`](../07_输出与扩散/扩散引擎包组装专篇.md) | 与 export 代码对齐 |