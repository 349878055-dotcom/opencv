# PAD 情绪坐标 — 主文档

> **一句话**：PAD（愉悦–激活–控制）是情绪的「性格」轴，与 E(t)（表演时间轴）正交，共同驱动 12 通道 pulse。

---

## 一、什么是 PAD

PAD（Pleasure–Arousal–Dominance）是一套三维情绪描述体系：

| 轴 | 全称 | 范围 | 物理含义 |
|----|------|------|----------|
| **P** | Pleasure（愉悦度） | [-1, 1] | 正 = 喜悦/亲近；负 = 厌恶/排斥 |
| **A** | Arousal（激活度） | [-1, 1] | 正 = 紧张/专注；负 = 松弛/涣散 |
| **D** | Dominance（控制度） | [-1, 1] | 正 = 强势/压迫；负 = 弱势/退缩 |

PAD **不是**情绪的"标签"，而是情绪的**连续坐标**。每种情绪对应一个 (P, A, D) 三元组。

### 1.1 本目录已有资源

本目录已包含 16 个具体情绪的 PAD 定义文件（`*.md`）及 `情绪坐标定位索引.md`，记录了每个人类的 (P, A, D) 值和特征描述。本文不再重复。

→ **查具体情绪值**：看 [`情绪坐标定位索引.md`](合同/03_情绪坐标/情绪坐标定位索引.md)  
→ **查情绪预设 JSON**：看 [`预设资产/情绪坐标/`](预设资产/情绪坐标/)

---

## 二、PAD → 12 通道：公式与计算

PAD 通过**线性投影**影响 12 个通道的幅度，公式如下：

```
scale[ch] = base[ch] + P × Wp[ch] + A × Wa[ch] + D × Wd[ch]
最终结果 clamped ≥ 0.0
```

### 2.1 参数说明

| 参数 | 来源 | 说明 |
|------|------|------|
| `base[ch]` | `HUMAN_BASE_SCALE` | 所有通道默认 0.30（中性值） |
| `Wp[ch], Wa[ch], Wd[ch]` | `HUMAN_PAD_WEIGHTS` | 每个通道对 P/A/D 的敏感度 |
| `P, A, D` | 情绪预设 | 从情绪名或 `SliderPacket` 解析 |

### 2.2 人类 PAD 权重表（精确值）

代码真源：[`gaze_engine/pad/pad_weights.py`](gaze_engine/pad/pad_weights.py:12)

| 通道 | Wp | Wa | Wd | 语义 |
|------|----|----|----|------|
| pupil_x | 0.0 | 0.50 | 0.40 | 高 A/D → 眼神聚焦向前（"迎"） |
| pupil_y | 0.0 | 0.50 | 0.40 | 同上 |
| blink | 0.0 | 0.30 | 0.10 | 高 A → 眨眼频率略升 |
| eyebrow | 0.0 | 0.30 | -0.35 | D 负 → 负负得正 → 眉压下（"拒"） |
| pupil_scale | 0.10 | 0.30 | 0.20 | 高 P 瞳孔略大（愉悦睁大） |
| iris_scale | 0.10 | 0.20 | 0.10 | 微调虹膜视觉大小 |
| cornea_bulge | 0.0 | 0.40 | 0.30 | 高 A/D → 眼角紧绷 |
| squint | 0.10 | 0.35 | 0.20 | 高 P+A → 眯眼（喜悦/专注） |
| brow_raise | 0.10 | 0.20 | -0.20 | 低 D → 挑眉抬起（惊讶/示弱） |
| lid_upper | 0.0 | 0.50 | 0.40 | 高 A/D → 上眼睑紧张 |
| lid_lower | 0.0 | 0.30 | 0.20 | 微调下眼睑 |
| eye_gloss | 0.30 | 0.10 | 0.0 | 高 P → 湿润光泽（喜悦含泪） |

### 2.3 算例：委屈 (P=-0.1, A=0.6, D=-0.5)

```
pupil_scale = 0.30 + (-0.1)×0.10 + 0.60×0.30 + (-0.5)×0.20
           = 0.30 - 0.01 + 0.18 - 0.10
           = 0.37

eyebrow = 0.30 + (-0.1)×0.0 + 0.60×0.30 + (-0.5)×(-0.35)
        = 0.30 + 0.0 + 0.18 + 0.175
        = 0.655  → 眉压显著
```

---

## 三、管线位置

PAD 在管线中的位置是 **S1 → S4**：

```
S1 (Energy)         S4 (Channel Compile)
 macro               energy_envelope E(t)  ──┐
  ├─ power                                   │
  ├─ push              ┌──────────────────────┤
  ├─ grip        →     │ pulse[ch,t] =        │ → pulse[12×150]
  ├─ outro             │   E[t-lag[ch]]       │
  └─ hold_seg          │   × scale[ch]        │
                       │   × gain[ch]         │
 PAD            →      │ 其中 scale[ch] =     │
  ├─ P                 │   base + P×Wp + ...  │
  ├─ A                 └──────────────────────┘
  └─ D
```

- **PAD 与 E(t) 是乘法关系**，不是加法。`E(t) × scale[ch]` 意味着：
  - E(t)=0 时（表演未开始/已结束），PAD 不起作用
  - E(t) 大时（表演高潮），PAD 的作用被放大
- **PAD 不影响时间结构**（peak timing、hold 长度、outro 曲线都由 macro 决定）

---

## 四、与 E(t) 的关系（正交）

| 维度 | E(t)（表演时间轴） | PAD（情绪性格轴） |
|------|-------------------|-------------------|
| 管什么 | 何时动、多大力度、多久 | 动的时候是什么"味" |
| 变量 | macro × 6 + hold_seg | (P, A, D) 三元组 |
| 时间依赖 | 强（frame-by-frame 变化） | 弱（全段恒定） |
| 通道影响 | 所有通道同步缩放 | 每个通道独立缩放 |
| 修改场景 | 改表演强度/节奏 | 改情绪气质 |

**核心结论**：改 PAD ≠ 改表演力。PAD 只决定"同样力度的表演，看上去是什么情绪"。

---

## 五、与 style 的关系（S5）

PAD 在 S4 完成后进入 S5（风格化层），style 在 **pulse 层面叠加**：

```
pulse_after_style[ch,t] = base_offset[ch] + scale_factor[ch] × pulse[ch,t]
```

- **PAD 是情绪性格**（全段恒定的气质倾向）
- **style 是脸框人格化**（品种/个体偏移 + 出厂曲线）
- 两者是串联关系：`macro → PAD → style → render`

---

## 六、边界（PAD 不管什么）

| 不属于 PAD 的事 | 归属 | 原因 |
|----------------|------|------|
| 表演峰值/节奏 | macro (S1) | power/push/grip/outro 决定 |
| 脸框形状偏移 | style (S5) | 品种/个体模板差异 |
| 底膜几何 | 工程底膜 (S6) | MediaPipe→OpenCV 几何映射 |
| 微颤/眼跳/滞后 | 先验 (S6) | 生理先验，独立于情绪 |
| 具体通道数值 | 情绪预设文件 | 每个情绪的 (P,A,D) 在独立文件 |
| 渲染像素 | AffineRenderer | OpenCV warpAffine 层 |

---

## 七、代码真源

| 文件 | 内容 | 行号 |
|------|------|------|
| [`pad/pad_weights.py`](gaze_engine/pad/pad_weights.py:12) | `HUMAN_PAD_WEIGHTS` + `HUMAN_BASE_SCALE` | L12-28 |
| [`envelope/envelope_compile.py`](gaze_engine/envelope/envelope_compile.py:64) | `compute_pad_scale()` — PAD 线性投影 | L64-87 |
| [`envelope/envelope_compile.py`](gaze_engine/envelope/envelope_compile.py:28) | `HUMAN_CHANNELS` — 12 通道定义 | L28-32 |
| [`envelope/envelope_compile.py`](gaze_engine/envelope/envelope_compile.py:223) | `channels_from_envelope()` — E(t)×PAD→pulse | L223-352 |
| [`pad/pad_weights.py`](gaze_engine/pad/pad_weights.py:1) | 人类 PAD 权重表（独立模块） | 全文 |

### 7.1 阅读顺序建议

1. 先读本文件（理解 PAD 是什么 + 公式）
2. 再读 [`情绪坐标定位索引.md`](合同/03_情绪坐标/情绪坐标定位索引.md)（查具体情绪 PAD 值）
3. 再读 [`01_三层分工与编译链专篇.md`](合同/03_情绪坐标/01_三层分工与编译链专篇.md)（理解 macro/PAD/style 层次）
4. 有需要时读 [`envelope/envelope_compile.py`](gaze_engine/envelope/envelope_compile.py:223)（看完整编译逻辑）

---

## 八、修改记录

| 日期 | 修改人 | 内容 |
|------|--------|------|
| 2026-06-07 | bot | 从旧 6 文件合并重构：删除狗管线引用，更新代码路径，保留人类 PAD 核心理论 |
