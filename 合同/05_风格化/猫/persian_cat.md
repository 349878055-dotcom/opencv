# 波斯猫/慵懒型 — 猫品种风格合同（独立）

> **类型：个性化 · 猫 · 单项** · id=`persian_cat`

> **状态：🧠 脑补初稿（可逐份审定）** — 本文 **只管辖「波斯猫/慵懒型」**（id=`persian_cat`）；不与其它品种合并修订。
> **数值真源**：`预设资产/风格包/cat/persian_cat/style.json` · schema `ecursor_style_v1`
> **兄弟规范**：[`公共层边界合同.md`](../../09_架构与验收/公共层边界合同.md)
> **猫品种真源**：`gaze_engine/cat/breed_style_catalog.json` → `sync_species_style_pack.py`

---

## 一、概述（What）

### 本文件用途

定义 **波斯猫/慵懒型** 的 **12 通道 base_offset / scale_factor**（及几何偏移如有），描述气质与验收。  
改风格只改 **本文件 + 对应 style.json + 矩阵 JSON**，勿改情绪 md。

### 管线位置

| 环节 | 内容 |
|------|------|
| 上游 | 任意情绪 E(t)（`02_情绪与能量/` 各独立 md） |
| **本合同** | 动态偏置 + 几何模板 |
| 下游 | 02 通道 styled 曲线 · OpenCV 底膜 · 04 Prompt 物种形容词 |

### 管辖 / 边界

| ✅ 本文件管 | ❌ 本文件不管 |
|------------|--------------|
| 本品种的 base/scale 定稿 | 情绪 macro/hold（各情绪独立 md） |
| 本品种的气质与通道读感 | E(t) 四段时间轴 |
| 与矩阵 JSON 同步 | 客户单次标定覆盖项 |

### 标识

| 项 | 值 |
|----|-----|
| id | `persian_cat` |
| label | 波斯猫/慵懒型 |
| species | `cat` |
| notes | 扁脸圆眼半阖，慢眨 dignified，扫视幅度极小，眯眼底噪偏高 |

---

## 二、理论依据（Theory）

### 动态层公式（与情绪正交）

```text
styled[ch, t] = clamp01( base_offset[ch] + scale_factor[ch] × pulse[ch, t] )
```

- `pulse` 来自情绪 E(t) 编译结果；**本品种不改变 E(t) 形状**。
- 实现入口：[`delivery_pipeline.py`](../../../gaze_engine/delivery_pipeline.py) · [`gaze_engine/cat/`](../../../gaze_engine/cat/)

### 几何层（如有）

- `template_scales` / `template_structure` → [`gaze_engine/cat/breed_matrix.json`](../../../gaze_engine/cat/breed_matrix.json)
- 与客户 `SpeciesTemplate` 标定叠加，见 [`公共层边界合同.md`](../../09_架构与验收/公共层边界合同.md)

---

## 三、为什么这样做（Why）

### 气质总述（🧠 待审）

波斯：扁脸半阖、慢眨、扫视极低

### 通道级决策（🧠 脑补）

| 通道 | 中文 | base | scale | 🧠 意图 |
|------|------|------|-------|--------|
| `pupil_x` | 瞳孔水平 | **0.46** | **0.02** | 扫视/回头幅度；动态幅度小 |
| `pupil_y` | 瞳孔垂直 | **0.44** | **0.02** | 抬眼/低眉视线；动态幅度小 |
| `blink` | 眨眼 | **0.58** | **0.24** | 眼睑开合动态；基线偏高；动态幅度大 |
| `eyebrow` | 眉形整体 | **0.38** | **0.04** | 眉弓压抬；基线偏低；动态幅度小 |
| `pupil_scale` | 瞳孔缩放 | **0.5** | **0.08** | 惊恐/聚焦；接近物种默认 |
| `iris_scale` | 虹膜缩放 | **0.52** | **0.08** | 眼内圈大小；接近物种默认 |
| `cornea_bulge` | 角膜鼓胀 | **0.5** | **0.1** | 湿润/受光；接近物种默认 |
| `squint` | 眯眼 | **0.56** | **0.14** | 笑眼/不适；接近物种默认 |
| `brow_raise` | 挑眉 | **0.36** | **0.04** | 警觉/疑问；基线偏低；动态幅度小 |
| `lid_upper` | 上睑 | **0.54** | **0.12** | 睁眼度；接近物种默认 |
| `lid_lower` | 下睑 | **0.5** | **0.1** | 眼下缘；接近物种默认 |
| `eye_gloss` | 高光 | **0.52** | **0.04** | 泪膜/湿润感；动态幅度小 |

⚠️ **历史教训**：base 与 scale 同时拉满会导致 02 饱和 clippng → 先定 base 再定 scale。

---

## 四、怎么实现（How）

### 4.1 资产文件

`预设资产/风格包/cat/persian_cat/style.json`

### 4.2 base_offset（静态偏置）

| 通道 | 值 |
|------|-----|
| `pupil_x` | **0.46** |
| `pupil_y` | **0.44** |
| `blink` | **0.58** |
| `eyebrow` | **0.38** |
| `pupil_scale` | **0.5** |
| `iris_scale` | **0.52** |
| `cornea_bulge` | **0.5** |
| `squint` | **0.56** |
| `brow_raise` | **0.36** |
| `lid_upper` | **0.54** |
| `lid_lower` | **0.5** |
| `eye_gloss` | **0.52** |

### 4.3 scale_factor（动态增益）

| 通道 | 值 |
|------|-----|
| `pupil_x` | **0.02** |
| `pupil_y` | **0.02** |
| `blink` | **0.24** |
| `eyebrow` | **0.04** |
| `pupil_scale` | **0.08** |
| `iris_scale` | **0.08** |
| `cornea_bulge` | **0.1** |
| `squint` | **0.14** |
| `brow_raise` | **0.04** |
| `lid_upper` | **0.12** |
| `lid_lower` | **0.1** |
| `eye_gloss` | **0.04** |

### 4.4 叠加示例

```text
情绪：任意（如 委屈·幼犬眼 / 魅惑·勾人）
  + 本品种：persian_cat
  → pulse[ch,t]  --×scale + base--> styled[ch,t]
  → affine_renderer → 工程底膜
```

### 4.5 代码映射

| 模块 | 职责 |
|------|------|
| [`breed_matrix.json`](../../../gaze_engine/cat/breed_matrix.json) | 矩阵真源（应与 style.json 一致） |
| [`envelope_compile.py`](../../../gaze_engine/cat/envelope_compile.py) | styled 公式（逐步接入 Pomot 路径） |
| 门户 `/api/portal/presets` | 风格包列表与路径 |

---

## 五、检查点（Checkpoints）

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|---------|---------|--------|
| style.json 与 §4.2/4.3 一致 | diff | 全键相等 | P0 |
| 与矩阵 JSON 一致 | diff `breed_matrix.json` | base/scale 一致 | P0 |
| 12 通道齐全 | 键集合 | 无缺失 | P0 |
| 叠加任意情绪 | 门户 ③→⑤ | 气质可辨、无 clippng | P1 |
| §3 气质描述 | 人工 | 已审定 | P1 |

---

## 修改记录

| 日期 | 改了什么 | 原因 |
|------|----------|------|
| 2026-05-28 | 从 catalog/style.json 同步 §3/§4 | 补全猫狗品种单项合同 |
| 2026-05-27 | 🧠 生成器初稿 | 独立单项风格合同 |
