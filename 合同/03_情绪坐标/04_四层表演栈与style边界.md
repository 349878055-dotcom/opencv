# 四层表演栈 — PAD 与人格化 / 狗种偏移分工

> **位置**：[`03_情绪坐标/`](.) · 本目录为 PAD 专题理论合同（遵循 [`合同规范.md`](../合同规范.md) 五段格式）

> **状态：2026-05-28 定稿专篇**  
> **读者**：觉得「PAD、表演力、人格化、品种偏移」缠在一起的人  
> **目的**：用 **一条管线、四层分工** 回答——**品种/人格偏移在整体情绪里算什么？PAD 是不是只剩表演力修正、已经不算人格化了？**

**兄弟合同**（分工，本文不重复全文）：

| 文件 | 只管 |
|------|------|
| [`01_三层分工与边界.md`](01_三层分工与边界.md) | **入门必读**：macro / PAD / style 一句口诀 |
| [`macro与hold_seg专篇.md`](../01_输入与收口/macro与hold_seg专篇.md) | 第①层：macro/hold → E(t) |
| [`02_三轴与情绪坐标.md`](02_三轴与情绪坐标.md) | 第②层：PAD → 情绪气质 |
| [`03_12通道映射与编译链.md`](03_12通道映射与编译链.md) | 三层「数」总览 + 12 通道合成 |
| [`05_风格化/狗/狗品种风格偏向.md`](../05_风格化/狗/狗品种风格偏向.md) | 狗：通用情绪 × 品种 → styled |
| [`04_四层表演栈与style边界.md`](04_四层表演栈与style边界.md) | 品种/人格不改 E(t) 的审计结论 |

**代码真源（狗管线 S0～S7 摘要）**：

| 层 | 步骤 | 函数 |
|----|------|------|
| ① 节拍 | S2 | `build_energy_envelope()` |
| ② 气质 | S1+S4 | `resolve_pad()` → `channels_from_envelope()` |
| ③ 脸框 | S5 | `apply_breed_style()` / `apply_persona_style()` |
| ④ 出厂 | S6～S7 | prior / quality → `02_烘焙` |

---

## 一、概述（What）

### 本文件用途

给整条 **5 秒眼眉表演** 一张 **分层地图**，并直接判定常见误解：

| 误解 | 正解（一句话） |
|------|----------------|
| PAD = 人格化 | ❌ **PAD = 情绪气质**；人格化/狗种 = **S5 style 偏移** |
| PAD = 表演力修正 | ❌ **表演力（节拍）= E(t) = macro/hold**；PAD 不管第几秒到峰 |
| 品种偏移 = 另一种情绪 | ❌ 品种 **不改** 情绪 JSON；只改 **pulse 怎么吃进这张脸** |
| 门户「能量曲线」= E(t) | ⚠️ 客户看到的组合曲线多半是 **styled**，不是裸 E(t) |

### 四层表演栈（全文核心图）

```text
┌─────────────────────────────────────────────────────────────────┐
│  客户/门户勾选：情绪预设  +  （可选）品种/人格  +  （可选）NL微调   │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
   ① 表演节拍              ② 情绪气质              ③ 脸框人格化
   macro + hold_seg         PAD (P,A,D)            style.json
   「多用力·何时峰」         「像委屈还是像凶狠」      「贵宾脸怎么吃戏」
        │                       │                       │
        └───────────┬───────────┘                       │
                    ▼                                   │
              E(t) 150点                                 │
                    │                                   │
                    └────────→ pulse 12×150 ────────────┘
                                    │
                                    ▼
                              styled 12×150  ← ③ 品种/人格偏移
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
              ④ prior / 质检                   几何底膜（并行）
                    ▼
              02_烘焙 → 扩散引擎
```

### 每层一句话

| 层 | 名字 | 算什么 | 数据从哪来 |
|----|------|--------|-----------|
| **①** | **表演节拍 / 表演力（时间）** | 5 秒内 **强弱与时间** | `macro` + `hold_seg` → **E(t)** |
| **②** | **情绪气质** | 这种 **情绪** 的通道性格配比 | **PAD** + 情绪特例补丁 → `pad_scale` |
| **③** | **人格化 / 狗种偏移** | 这张 **脸** 的默认吃戏方式 | `style.json` **base_offset + scale_factor** |
| **④** | **出厂曲线** | 门户/02 的 **定稿动态** | **styled** = f(pulse, ③) |

**并行（不算一层动态曲线，但算「脸」）**：

| 几何底膜 | 眼距/眼位/耳位（配准） | `底膜包/` + `breed.template_*` + **`物种底膜模板.json`** | 与 styled **同时使用**；**禁止**客户美颜滑杆 |

### 对你问题的直接回答

**Q：品种/人格偏移在整体情绪上算什么？**  
**A：第③层「脸框人格化」** —— 在 **同一种情绪 pulse 已经定稿** 之后，用 `base + scale × pulse` 把戏 **装进贵宾/祭司/田园这张脸**。它 **不是** 新情绪，也 **不是** PAD。

**Q：PAD 是不是只是表演力修正？是不是已经不算人格化了？**  
**A：两个都否。**

- PAD **不是** 表演力修正 → 表演力修正是 **① macro/hold（E(t)）**
- PAD **本来就不是** 人格化 → 它是 **② 情绪气质**（选「委屈」就带委屈的 PAD）
- 人格化在 **③**，与 PAD **正交叠加**，不是替代关系

---

## 二、理论依据（Theory）

### 2.1 为什么要拆成四层（而不是一个大旋钮）

```text
① 表演学：「何时发力」和「演成什么情绪」是可分开教的
   → 导演可以先定节拍，再定读感

② 产品：客户选「委屈」= 节拍+气质打包；选「贵宾」= 脸框叠加
   → 改委屈只改 1 份情绪 JSON，10 个狗种自动跟上

③ 工程：E(t) 物种无关；PAD 情绪级；style 脸级
   → 各层可单测、可合同验收

④ 扩散：02 控制视频要「组合定稿」styled
   → 对外一条曲线 = 情绪×品种，不是裸 pulse
```

### 2.2 三层「力」的精确含义（别混词）

项目中「表演力」常被口语混用，合同里请拆开：

| 口语 | 合同层 | 控制对象 | 典型旋钮 |
|------|--------|----------|----------|
| **表演力 / 节奏 / 能量** | ① E(t) | 时间轴强弱 | power, speed, grip, hold_seg |
| **气质 / 情绪读感** | ② PAD | 通道静态配比 | 情绪预设里的 P,A,D |
| **脸框 / 品种感 / 人格** | ③ style | 基线+增益 | blink base=0.55, scale=0.25 |

**PAD 不在「表演力修正」这一列** —— 它修正的是 **「同样力度的动，像哪种情绪」**，不是 **「何时多用力」**。

### 2.3 人格化在本项目指什么

| 物种 | 合同目录 | 资产 | 作用层 |
|------|----------|------|--------|
| 狗 | `05_风格化/狗/` | `style.json` / `breed_matrix.json` | S5 `apply_breed_style` |
| 人 | `05_风格化/人/` | 人格 style | S5 `apply_persona_style` |
| 猫 | `05_风格化/猫/` | 品种 style | 同公式 |

**统一公式**（全物种）：

```text
styled[ch, t] = clamp01( base_offset[ch] + scale_factor[ch] × pulse[ch, t] )
```

- `pulse` 已含 **① E(t)** 与 **② PAD**
- `base_offset / scale_factor` 是 **③ 人格化/狗种** 专属
- **不改** E(t) 帧轴（正交审计 ✅）

### 2.4 PAD 与人格化的关系（不是替代，是串联）

```text
同一条 E(t) 曲线
    × 不同 PAD  →  pulse_A（像委屈） vs pulse_B（像凶狠）     ← 换情绪
同一条 pulse
    × 不同 style →  styled_贵宾 vs styled_田园                 ← 换品种
```

**数值故事（blink 通道，保持段）**：

| 量 | 委屈·幼犬眼 | × 贵宾 poodle_giant |
|----|------------|----------------------|
| E(t) | ~0.10 | **相同**（同情绪 macro） |
| PAD | (-0.35, 0.25, -0.55) | **相同** |
| pulse[blink] | ≈ 0.12 | **相同** |
| base_offset[blink] | — | **0.55**（贵宾默认更半阖） |
| scale_factor[blink] | — | **0.25** |
| **styled[blink]** | — | clamp(0.55 + 0.25×0.12) ≈ **0.58** |

若换 **凶狠·威吓**（PAD 变、macro 可能变）→ pulse 变 → 同一贵宾 base/scale 下 **styled 整条变**，但 **贵宾仍比田园更半阖**（base 差）。

---

## 三、为什么这样做（Why）

### 3.1 关键决策

| 决策 | 备选 | 为什么选分层 |
|------|------|-------------|
| PAD 放在 pulse 前（乘 pad_scale） | PAD 放在 S5 style 里 | 气质跟 **情绪** 走；10 狗种共用同一 PAD |
| 品种用 base+scale | 每品种复制 10 份情绪 JSON | 改委屈一处，N 品种自动继承 |
| E(t) 不含 PAD、不含 style | 一个大公式全混 | 无法独立审定节拍 vs 气质 vs 脸框 |
| PAD 不叫人格化 | 合并成一个「性格」滑杆 | 产品无法解释「换贵宾不改委屈感」 |

### 3.2 若把 PAD 当成「表演力修正」会怎样（反例）

| 错误理解 | 实际后果 |
|----------|----------|
| 用 PAD 拉「更用力」 | 改的是 squint/gloss **配比**，不是 peak 时刻 → 脸像错了戏 |
| 用 PAD 代替 style | 贵宾/田园 **脸基线** 无法区分 → 品种合同失效 |
| 用 style 代替 PAD | 换情绪时 **情绪坐标读感** 跟不上 → 委屈和凶狠 styled 像 |
| 删掉 PAD 只留 macro | E(t) 对但 **通道像错情绪** → Prompt 与 02 打架 |

### 3.3 若把品种偏移当成「新情绪」会怎样（反例）

| 错误做法 | 后果 |
|----------|------|
| `委屈·幼犬眼_poodle.json` | 改通用委屈要改 N 份 |
| 品种里改 macro 改 E(t) | 同情绪在不同品种 **节拍不一致** |
| 品种 style 写「仅委屈有效」 | 改其它 9 情绪时该品种 **不对齐** |

⚠️ **规则**：品种 md / style.json **只定 base/scale/几何**，**不写** 某一情绪的 macro/PAD。

### 3.4 历史教训

| ⚠️ 坑 | 规则 |
|-------|------|
| 「PAD 就是人格化」 | PAD=②；人格化=③；见本文 §1 栈图 |
| 「能量曲线图 = E(t)」 | 门户组合导出多为 **styled** |
| base 与 scale 同时拉满 | styled 饱和 clipping → 先 base 后 scale |
| 只审 pulse 不审 styled | 出厂看 **styled**；pulse 是中间态 |

---

## 四、怎么实现（How）

### 4.1 狗管线逐步（与四层对应）

[`dog_pipeline.py`](../../gaze_engine/dog/dog_pipeline.py) · `run_dog_pipeline()`

| 步骤 | 层 | 代码 | 输入 | 输出 |
|------|-----|------|------|------|
| S0 | — | `SliderPacket` | 情绪 JSON + 可选 NL | macro, hold, ear, pad? |
| S1 | ② | `resolve_pad(pkt)` | emotion / packet.pad | (P, A, D) |
| S2 | ① | `build_energy_envelope(pkt)` | macro, hold | **E(t)** |
| S4 | ①+② | `channels_from_envelope(...)` | E, PAD, ear | **pulse** 12×150 |
| S5 | ③ | `apply_breed_style(channels, breed_id)` | pulse, style.json | **styled** |
| S6～7 | ④ | prior, quality | styled | styled′ → 02 |

人类链路 **同 S5 公式**，换 `apply_persona_style`；**①② 公共层相同**。

### 4.2 各层改什么资产

| 你想改… | 改合同 | 改资产 | 不要改 |
|---------|--------|--------|--------|
| 更慢、更颤、更用力 | `02_情绪与能量/…` + macro专篇 | 情绪 JSON **macro/hold** | PAD、style |
| 更委屈、更湿、更退缩 | `03_情绪坐标/…` + PAD专篇 | 情绪 JSON **pad** + `emotion_pad.py` | style |
| 贵宾更半阖、扫视更小 | `05_风格化/狗/poodle_giant.md` | **style.json** + breed_matrix | 情绪 JSON |
| 参考照与骨架 **解剖配准**（眼距/眼位/耳位） | [`底膜模板选择与标定专篇.md`](../07_工程底膜/底膜模板选择与标定专篇.md) | 预设 **`底膜包/`** + 客户 **`物种底膜模板.json`** | macro/PAD/style |
| 客户想「眼睛大一点」美颜 | ❌ **禁止** | 非本产品（美图秀秀范畴） | 一切层 |

### 4.3 公式链（工程师版）

```text
# ① 节拍
E(t) = build_energy_envelope(macro, hold_seg)

# ② 气质进入 pulse（简化）
pad_scale[ch] = base_species[ch] + P·Wp + A·Wa + D·Wd
pulse[ch,t]   = f(E, pad_scale, ear, 情绪特例…)

# ③ 人格化 / 狗种
styled[ch,t]  = clamp01( base_offset_breed[ch] + scale_factor_breed[ch] × pulse[ch,t] )

# 几何（并行，OpenCV 底膜 — 预设 底膜包/ + 客户 物种底膜模板.json）
template'     = species_default × breed.template_scales × 客户配准（仅照片/锚点，禁止美颜滑杆）
```

### 4.4 术语对照表（对外 / 对内）

| 对外说法 | 对内层 | 是否 E(t) | 是否 PAD | 是否 style |
|----------|--------|-----------|----------|------------|
| 表演节奏 / 能量脉冲图 | ① | ✅ | ❌ | ❌ |
| 情绪气质 / 脸性格 | ② | ❌ | ✅ | ❌ |
| 贵宾感 / 祭司感 / 品种 | ③ | ❌ | ❌ | ✅ |
| 这条组合的能量曲线 | styled | 含①②③ | 含② | 含③ |
| 5 秒表演力 | ① 为主 | ✅ | ❌ | ❌ |

### 4.5 人类 vs 狗（栈相同，资产不同）

| 层 | 人 | 狗 |
|----|-----|-----|
| ① | macro/hold | 同 |
| ② | PAD + human pad_weights | PAD + DOG_PAD_WEIGHTS |
| ③ | 九大人格 style | 品种 style（poodle_giant…） |
| 几何 | 真人眼眶底图 | 狗 template + 耳位 |

**人格（人）与品种（狗）在 ③ 层等价** —— 都是 `apply_style_offset`，只是 id 与合同目录不同。

---

## 五、检查点（Checkpoints）

### 5.1 概念验收

| 检查项 | 合格标准 | 优先级 |
|--------|----------|--------|
| 说出四层 | 节拍 / 气质 / 脸框 / styled 出厂 | P0 |
| PAD ≠ 人格化 | 能指出 PAD 在 S4，style 在 S5 | P0 |
| PAD ≠ 表演力 | 表演力在 E(t)；PAD 不进 build_energy_envelope | P0 |
| 品种 ≠ 新情绪 | 10 情绪 1 JSON；品种只改 base/scale | P0 |

### 5.2 代码验收

**A. 品种不改 E(t)（① 正交）**

```bash
cd /path/to/jintao_node_eye
python3 -c "
import json
from pathlib import Path
import sys
sys.path.insert(0, '.')
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine._shared.envelope_compile import build_energy_envelope
from gaze_engine.dog.dog_pipeline import run_dog_pipeline

p = Path('预设资产/情绪包/dog/委屈·幼犬眼.json')
pkt = SliderPacket.from_dict(json.loads(p.read_text(encoding='utf-8')))
e0 = build_energy_envelope(pkt)
_, p0, _ = run_dog_pipeline(pkt)
_, p1, _ = run_dog_pipeline(pkt, breed_id='poodle_giant')
assert e0 == build_energy_envelope(pkt)
assert p0['blink'][50] != p1['blink'][50]
print('OK: 品种改 styled 不改 E(t)')
"
```

**B. PAD 改 pulse、style 再叠（②→③ 串联）**

```bash
python3 -c "
import json
from pathlib import Path
import sys
sys.path.insert(0, '.')
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine._shared.envelope_compile import build_energy_envelope
from gaze_engine.dog.dog_pipeline import run_dog_pipeline

base = Path('预设资产/情绪包/dog')
a = SliderPacket.from_dict(json.loads((base/'委屈·幼犬眼.json').read_text(encoding='utf-8')))
b = SliderPacket.from_dict(json.loads((base/'凶狠·威吓.json').read_text(encoding='utf-8')))
b.macro, b.hold_seg = a.macro, a.hold_seg
assert build_energy_envelope(a) == build_energy_envelope(b)
_, pa, _ = run_dog_pipeline(a, breed_id='poodle_giant')
_, pb, _ = run_dog_pipeline(b, breed_id='poodle_giant')
assert pa['squint'][50] != pb['squint'][50], 'PAD 应区分情绪'
assert pa['blink'][50] != pb['blink'][50], '同品种下不同情绪 styled 不同'
print('OK: PAD(情绪) + style(品种) 串联')
"
```

| 检查项 | 合格标准 | 优先级 |
|--------|----------|--------|
| A | 同 pkt 不同 breed：E(t) 相同，blink 不同 | P0 |
| B | 同 macro 不同情绪：E(t) 同，styled 不同 | P0 |
| 改情绪 JSON | 不改 style 时各 breed styled 随 pulse 变 | P0 |
| 改 style.json | 10 情绪 E(t) 不变，styled 基线变 | P0 |

### 5.3 对外口径

| ✅ 推荐 | ❌ 避免 |
|---------|--------|
| 「四层：节拍、情绪气质、脸框人格化、出厂 styled」 | 「PAD 就是人格化」 |
| 「选情绪 = 节拍+气质；选品种 = 脸怎么吃戏」 | 「PAD 调节表演力」 |
| 「门户组合曲线 = styled」 | 「能量图 = 裸 E(t)」且不提品种 |

---

## 六、FAQ

**Q1：我到底该记几个词？**  
记 **四层 + 一句并行**：**节拍（E(t)）· 气质（PAD）· 脸框（style）· 出厂（styled）**；底膜几何并行。

**Q2：PAD 还算「性格」吗？**  
算 **「情绪性格 / 气质」**，不算 **「贵宾/祭司这种脸框人格化」**。

**Q3：没有选品种，③ 层存在吗？**  
`breed_id` 空或 `default` 时 **跳过 S5**，styled ≈ pulse（仍含 ①②）。门户选贵宾后才叠 ③。

**Q4：改「通用委屈」要不要改贵宾 md？**  
**不要。** 改 [`02_情绪与能量/委屈.md`](../02_情绪与能量/委屈.md) + JSON；贵宾 base/scale 不变，styled **自动跟 pulse 变**。

**Q5：「5秒气质精品成片」里的气质指哪层？**  
**整链读感** = ①+②+③+ prior；不是单指 PAD，也不是单指 style。

**Q6：ear 块算哪层？**  
**情绪附属**（狗耳位），在 S4 注入 eyebrow；**不进 E(t)**；与 PAD **并行**，不是人格化 ③。

**Q7：macro / PAD / style 有没有先后顺序？**  
要分两种「顺序」：

| 顺序类型 | 有没有先后 | 说明 |
|----------|------------|------|
| **编译顺序**（代码 S2→S4→S5） | ✅ 有 | 先算 E(t)，再用 PAD 展开 pulse，最后用 style 得 styled |
| **5 秒表演时间轴** | ❌ 没有 | 每一帧 **同时** 含节拍+气质+脸框，不是「前几秒只 macro、后几秒才 PAD」 |

口诀里的「叠出来」指 **编译管线叠加**，不是观众在时间轴上先后看到三层。

---

## 七、修改记录

| 日期 | 内容 | 原因 |
|------|------|------|
| 2026-05-28 | 初版：四层栈、PAD vs 人格化判定、狗管线映射 | 用户混淆 PAD/表演力/品种偏移 |
| 2026-05-28 | 修正口诀 + FAQ Q7：编译顺序 vs 表演时间轴 | 用户指出 PAD 表述与「先后」误解 |

---

**一句话记住（防糊涂版）**：

> **macro 定什么时候、多大幅度用力；PAD 定这份力在各通道上怎么分配才指向这种情绪；style 定这张脸怎么吃这份 pulse——编译时按序叠加，播放时每一帧三层同时在。**
