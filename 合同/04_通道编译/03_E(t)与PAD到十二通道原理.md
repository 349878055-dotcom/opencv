# E(t) 与 PAD 到十二通道 — 原理导读

> **状态：2026-05-29** · 本目录 = 管线 **`04_通道编译`**  
> **格式**：遵循 [`合同规范.md`](../合同规范.md) 五段  
> **读者**：产品、合同审定、第一次读代码的人  
> **目的**：用**白话**讲清「一条能量曲线 + 三个 PAD 数，怎么变成 12 条动画通道」

**兄弟合同**（分工，本文不重复全文）：

| 文件 | 只管 |
|------|------|
| [`00_通道编译导读.md`](00_通道编译导读.md) | 本目录怎么读、S4 边界 |
| [`01_十二通道与全量帧格式.md`](01_十二通道与全量帧格式.md) | 12 通道名单、150 帧、02 JSON 格式 |
| [`02_代码映射_共享核心.md`](02_代码映射_共享核心.md) | 共享骨架与代码文件表 |
| [`03_情绪坐标/03_12通道映射与编译链.md`](../03_情绪坐标/03_12通道映射与编译链.md) | PAD 理论、正交边界 |
| [`狗/动态层编译与代码映射.md`](狗/动态层编译与代码映射.md) | 狗 S4 特例与函数表 |

**代码真源（狗为例）**：

| 步骤 | 文件 | 函数 |
|------|------|------|
| E(t) | [`gaze_engine/_shared/envelope_compile.py`](../../gaze_engine/_shared/envelope_compile.py) | `build_energy_envelope()` |
| PAD 解析 | [`gaze_engine/_shared/emotion_pad.py`](../../gaze_engine/_shared/emotion_pad.py) | `resolve_pad()` |
| PAD → 12 系数 | [`gaze_engine/dog/pad_weights.py`](../../gaze_engine/dog/pad_weights.py) | `DOG_PAD_WEIGHTS` · `DOG_BASE_SCALE` |
| E×PAD → pulse | [`gaze_engine/dog/envelope_compile.py`](../../gaze_engine/dog/envelope_compile.py) | `channels_from_envelope()` |
| 总入口 | [`gaze_engine/dog/dog_pipeline.py`](../../gaze_engine/dog/dog_pipeline.py) | `run_dog_pipeline()` |

---

## 一、概述（What）

### 本文件管什么

**通道编译（S4）** 做一件事：把

- **1 条能量曲线 E(t)**（150 个数，管「5 秒内多用力、何时起峰、盯住多久」）
- **3 个 PAD 数 (P, A, D)**（管「这种脸的气质：偏压抑还是偏兴奋、谁更眯、谁更亮」）

合成 **12 条通道动画 pulse[12×150]**（共 1800 个数），供后续风格化、先验、写入 `02_烘焙_*.json`。

### 管线位置

```text
上一步 02：macro + hold_seg  →  E(t)           [150×1]
上一步 03：情绪 PAD           →  (P, A, D)       [3×1]
本步   04：E(t) + PAD         →  pulse           [12×150]  ⭐ 本文
下一步 05：品种/人格           →  styled          [12×150]
下一步 06：先验 + QC           →  02_烘焙_*.json
```

### 边界（非管辖）

- ❌ **不管** E(t) 怎么从 6 根 macro 算出来 → 见 [`02_情绪与能量/`](../02_情绪与能量/)
- ❌ **不管** 每种情绪的 PAD 定多少 → 见 [`03_情绪坐标/`](../03_情绪坐标/) 与 `预设资产/情绪包/`
- ❌ **不管** 品种偏移、先验扫视、质检 → 见 `05` / `06`
- ❌ **不管** 02 怎么渲染成 MP4 → 见 `07_工程底膜/`

### 30 秒版（先读这段）

可以把它想成 **调音台**：

| 对象 | 类比 | 数量 |
|------|------|------|
| **E(t)** | 总音量推子：随时间起伏 | 1 条 × 150 帧 |
| **PAD** | 12 个通道各自的「性格旋钮」 | 3 个数 → 展开成 12 个系数 |
| **pulse** | 最终 12 路输出波形 | 12 条 × 150 帧 |

**不是**「3 + 1 = 12」，也 **不是**「PAD 有 12 维」。  
是：**E(t) 决定每一帧有多强；PAD 决定 12 个通道各自强多少；再按物种规则打补丁。**

---

## 二、理论依据（Theory）

### 2.1 为什么要拆成两条轴

理论依据链：

```text
① 表演时间（何时起、盯多久）和 气质（委屈 vs 凶狠的脸型）是两件不同的事
   → 拆成 E(t) 与 PAD 两轴，才能独立审定

② 动画行业常见做法：一条 master 曲线 + 各属性 bias/scale
   → E(t) ≈ master curve；PAD ≈ 各通道静态权重

③ 扩散控制需要稳定、可解释的数值轨，不能让人手改 1800 个数
   → 必须从少量滑杆 + 情绪坐标编译出全量帧

④ 12 通道是眼眉扩散控制专用接口（比 ARKit 52 blendshape 窄，比纯 PAD 细）
   → 名单固定，人/猫/狗共用同一套通道名
```

### 2.2 三个输入各自管什么

| 输入 | 从哪来 | 管什么 | 不管什么 |
|------|--------|--------|----------|
| **macro + hold_seg** | 情绪预设 JSON | → **E(t)** 时间形状 | 不决定「委屈还是愤怒」的静态脸型 |
| **(P, A, D)** | 预设 `pad` 块 / `emotion_pad.py` | → **12 个 scale 系数** | **不**决定第几秒到峰 |
| **物种规则** | `{human,cat,dog}/envelope_compile.py` | blink 锚点、lag、耳位等 | 不改 150 帧长度 |

### 2.3 PAD 三维的含义（复习）

| 轴 | 含义 | 举例 |
|----|------|------|
| **P** 愉悦度 | 偏正 / 偏负 | 委屈 P 偏低 |
| **A** 激活度 | 偏静 / 偏动 | 警觉 A 偏高 |
| **D** 支配度 | 偏退缩 / 偏压人 | 委屈 D 偏低 |

PAD 来自心理学 **Mehrabian PAD 量表**；落到每个通道的系数 **Wp/Wa/Wd 是本项目工程标定**，需读感验收。

---

## 三、为什么这样做（Why）

### 决策 1：E(t) 与 PAD 分开算，再相乘

| 方案 | 问题 | 结论 |
|------|------|------|
| PAD 直接写进 E(t) 公式 | 换品种会改变节拍 | ❌ |
| 客户直接拖 12 通道 | 1800 个数无法操作 | ❌ |
| **E(t) 管时间，PAD 管通道权重，再相乘** | 可解释、可正交验收 | ✅ |

⚠️ **规则**：品种/人格只在 S5 改通道偏移，**不得**改变 E(t)。

### 决策 2：PAD 是 3 个数，不是 12 个数

| 方案 | 问题 | 结论 |
|------|------|------|
| 每种情绪手填 12 个通道强度 | 维度过高、难审定 | ❌ |
| **3 维 PAD + 权重表投影到 12 通道** | 情绪用坐标描述，通道用表展开 | ✅ |

### 决策 3：人/猫/狗各写一份 `channels_from_envelope`

| 方案 | 问题 | 结论 |
|------|------|------|
| 一个函数通吃三物种 | 人类眉滞后、猫狗耳位无法表达 | ❌ |
| **12 通道名相同，编译函数分物种** | 接口统一、规则可分叉 | ✅ |

### 决策 4：blink 不走「E×scale」简单公式

| 方案 | 问题 | 结论 |
|------|------|------|
| blink[t] = E(t) × scale | 眨眼像「随能量渐开渐闭」，不像真实眨眼 | ❌ |
| **独立 blink 锚点序列** | 在 t_peak、保持段等时刻插入快闭快开 | ✅ |

---

## 四、怎么实现（How）

### 4.1 总流程（狗，一步不漏）

```text
情绪 JSON（macro / hold_seg / pad）
        │
        ├─► build_energy_envelope()     →  E[0..149]        （1 条）
        │
        └─► resolve_pad()               →  P, A, D          （3 个数）
                    │
                    ▼
            compute_pad_scale() ×12     →  scale[ch]       （12 个系数）
                    │
                    ▼
            channels_from_envelope()      →  pulse[ch][t]    （12×150）
                    │
                    ├─► inject_ear（猫狗）
                    ├─► tremble / 委屈湿眼等补丁
                    └─► micro_jitter 微颤
                    │
                    ▼
            02_烘焙_*.json 的 channel_tracks
```

### 4.2 第一步：macro → E(t)

**输入**：`SliderPacket.macro`（6 根）+ `hold_seg`（盯住段花纹）  
**输出**：`E[t]`，`t = 0..149`，每个值在 0～1 附近  
**代码**：[`build_energy_envelope()`](../../gaze_engine/_shared/envelope_compile.py)

**白话**：  
6 根滑杆决定「5 秒表演的主旋律」——什么时候蓄力、什么时候到顶、盯住段是平的还是颤的、最后怎么收。  
这条旋律 **只有 1 根线**，不是 12 根。

四段标签：**蓄力 → 启动 → 保持 → 缓和**（门户脉冲图看到的就是它的近似）。

### 4.3 第二步：(P,A,D) → 12 个 scale

**输入**：`(P, A, D)`，每个 ∈ [-1, 1]  
**输出**：`scale[ch]`，12 个通道各一个数  
**代码**：[`compute_pad_scale()`](../../gaze_engine/_shared/envelope_compile.py) + [`DOG_PAD_WEIGHTS`](../../gaze_engine/dog/pad_weights.py)

**核心公式**（每个通道 ch 各算一次）：

```text
scale[ch] = base[ch] + P×Wp[ch] + A×Wa[ch] + D×Wd[ch]
scale[ch] = max(0, scale[ch])    // 不允许负权重
```

**举例（狗 · squint 通道）**：

```text
Wp=0.10, Wa=0.35, Wd=0.20, base=0.31

若 委屈 PAD = (P=-0.35, A=0.25, D=-0.55)：

scale[squint] = 0.31 + (-0.35×0.10) + (0.25×0.35) + (-0.55×0.20)
              ≈ 0.31 - 0.035 + 0.0875 - 0.11
              ≈ 0.25
```

**白话**：  
PAD 不直接变成动画，先变成 **12 个「这路通道大概开多大」的系数**。  
同一种 PAD，在 `squint` 和 `eye_gloss` 上系数不同，因为权重表不同。

### 4.4 第三步：E(t) × scale → pulse[12×150]

**代码**：[`channels_from_envelope()`](../../gaze_engine/dog/envelope_compile.py)（人/猫在同名文件，逻辑各自不同）

#### 4.4.1 默认公式（大多数通道）

```text
pulse[ch, t] = clamp( E[t - lag[ch]] × scale[ch] × gain[ch] , 0, 1 )
```

| 符号 | 含义 | 狗默认示例 |
|------|------|------------|
| `lag[ch]` | 该通道比 E(t) 晚几帧启动，避免 12 轨同步拉伸 | iris_scale lag=3 |
| `gain[ch]` | 该通道额外倍率 | squint gain=1.10 |

**白话**：  
每一帧，用 **当前能量 E(t)** 去乘 **该通道的 PAD 系数**，得到这一帧这一通道的值。  
150 帧就算 150 次，12 个通道各算一条，得到 12×150。

#### 4.4.2 例外通道（不能只用一行公式）

| 通道 | 怎么算 | 为什么 |
|------|--------|--------|
| **blink** | 独立锚点序列 `_dog_blink_series` | 眨眼是离散事件，不是随 E 平滑升降 |
| **pupil_x / pupil_y** | `sign × E(t) × scale` + 方向偏置 | 视线有左右/上下方向 |
| **eyebrow / brow_raise**（猫狗） | 编译后再 `inject_ear` 注入耳位 | 狗没有「眉」语义，槽位复用为耳 |
| **委屈类** | 保持段叠加 `_apply_moist_sad_baseline` | 额外眯眼 + 湿润高光 |
| **hold=tremble** | `_apply_tremble_hold_coupling` | 保持段各通道不同幅度 ripple |

#### 4.4.3 12 通道名单（三物种相同）

`pupil_x` · `pupil_y` · `blink` · `eyebrow` · `pupil_scale` · `iris_scale` · `cornea_bulge` · `squint` · `brow_raise` · `lid_upper` · `lid_lower` · `eye_gloss`

语义差异见 [`01_十二通道与全量帧格式.md`](01_十二通道与全量帧格式.md) §3。

### 4.5 一张心算图（委屈·狗）

```text
时刻 t=80（保持段中段），E(80)=0.6（能量还在）

PAD 委屈 (-0.35, 0.25, -0.55)
  → scale[squint]≈0.25, scale[eye_gloss]≈0.14, ...

pulse[squint, 80]  ≈ E(80) × 0.25 × gain   + tremble补丁 + 委屈湿眼基线
pulse[eye_gloss,80]≈ E(80) × 0.14 × gain   + 湿眼基线
pulse[blink, 80]   ≈ 若 t=80 附近有眨眼锚点则 spike，否则≈0

→ 同一时刻 E 相同，但 12 通道值不同（scale、gain、补丁各不同）
```

### 4.6 三物种公式在哪（不共用 S4）

| 物种 | PAD 权重表 | E×PAD→pulse 函数 |
|------|------------|------------------|
| 狗 | `gaze_engine/dog/pad_weights.py` | `gaze_engine/dog/envelope_compile.py` |
| 人 | `gaze_engine/human/pad_weights.py` | `gaze_engine/human/envelope_compile.py` |
| 猫 | `gaze_engine/cat/pad_weights.py` | `gaze_engine/cat/envelope_compile.py` |

**E(t) 的计算**三物种共用 `build_energy_envelope()`；**变成 12 通道**各物种自己写。

### 4.7 和预设 JSON 的关系

| JSON 字段 | 参与哪一步 |
|-----------|------------|
| `macro` + `hold_seg` | → E(t) |
| `pad` 里的 P/A/D | → 12 个 scale |
| `ear`（猫狗） | → S4 末尾注入 eyebrow/brow_raise |
| **没有** `pulse` 或 12 通道数组 | 12 通道是编译产物，不在预设里手填 |

---

## 五、检查点（Checkpoints）

### 5.1 概念验收（读本文即可）

- [ ] 能说出：**E(t) 1 条，PAD 3 个数，pulse 12×150**
- [ ] 能说出：**不是 6+3=12，也不是 PAD 有 12 维**
- [ ] 能说出：**默认形 = E(t) × scale[ch]；blink 等是例外**
- [ ] 能说出：**狗公式在 `dog/envelope_compile.py`，不是只有一份共用 S4**

### 5.2 数值验收（狗）

```bash
cd /path/to/jintao_node_eye
python3 scripts/verify_dog_150_compile_contract.py
```

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| E(t) 长度 | 脚本 / 断言 | `len(E)==150` | P0 |
| pulse 形状 | 脚本 | 12 通道各 150 帧 | P0 |
| 02 稠密 keyframes | 脚本 | 共 **1800** 点 | P0 |
| 品种不改 E(t) | 正交脚本（见 03 情绪坐标专篇） | 同 packet 换品种 E 完全相同 | P1 |
| 品种改通道 | 同上 | styled/pulse 有差异 | P1 |

### 5.3 改合同时的对照表

| 你想改… | 改文档 | 改代码 |
|---------|--------|--------|
| 起峰早晚、盯住多久 | `02_情绪与能量/` | macro → `build_energy_envelope` |
| 委屈更湿、更眯 | `03_情绪坐标/` + 预设 `pad` | `pad_weights.py` 或 `_apply_moist_sad_baseline` |
| blink 锚点位置 | `04_通道编译/狗/` | `_dog_blink_series` |
| 12 通道改名 | `01_十二通道…` + 渲染器 | `DOG_CHANNELS` 等 + 合同同步 |

---

## 修改记录

| 日期 | 改了什么 | 原因 |
|------|----------|------|
| 2026-05-29 | 初版 | 补 E(t)+PAD→12 通道白话原理，便于审定 04 通道编译 |

---

**一句话**：

> **E(t) 是 5 秒的总音量曲线；PAD 把 3 个气质数展开成 12 个通道系数；通道编译用「E×系数」逐帧算出 12×150，再按物种和情绪打 blink、耳位、颤抖等补丁。**
