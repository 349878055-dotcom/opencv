# macro 与 hold_seg — 表演节奏滑杆专篇

> **状态：2026-05-28 定稿专篇**  
> **读者**：产品、合同审定、门户培训、工程实现  
> **编译序**：`macro`/`hold` → **E(t)**（在 PAD 之前）；宏观架构见 [`00_从门户到扩散_管线总览.md`](../00_管线导读/00_从门户到扩散_管线总览.md)。  
> **目的**：把 **`macro`（宏观六滑杆）** 与 **`hold_seg`（盯住段花纹）** 的来龙去脉讲透——它们从哪来、管什么、不管什么、怎么变成 **E(t)**，以及和 **PAD / 12 通道** 的边界。

**兄弟合同**（分工，本文不重复全文）：

| 文件 | 只管 |
|------|------|
| [`滑杆规范.md`](../01_输入与收口/滑杆规范.md) | 字段定义、16 预设、L1 禁区 G1～G8、LLM 步进规则 |
| [`../03_情绪坐标/03_12通道映射与编译链.md`](../03_情绪坐标/03_12通道映射与编译链.md) | E(t) 与 PAD 正交、12 通道合成、客户改什么 |
| [`01_十二通道与全量帧格式.md`](../04_通道编译/01_十二通道与全量帧格式.md) | 150 帧四段语义、12 通道名单、烘焙 02 |
| [`08_架构与验收/公共层边界合同.md`](../09_架构与验收/公共层边界合同.md) | E(t) 在 `_shared/`，物种层只映射通道 |
| [`02_情绪与能量/{物种}/{情绪}.md`](../02_情绪与能量/) | 单情绪的 macro/hold 定稿数值 |

**代码真源**：

| 对象 | 文件 · 函数 |
|------|-------------|
| 数据结构 | `gaze_engine/_shared/slider_schema.py` · `MacroSliders` / `HoldSegment` / `SliderPacket` |
| E(t) 编译 | `gaze_engine/_shared/envelope_compile.py` · `build_energy_envelope()` · `_hold_texture()` |
| L1 禁区 | `gaze_engine/_shared/packet_finalize.py` · `gaze_engine/_shared/slider_bounds.py` |
| 人类 steady 后效 | `gaze_engine/human/human_prior.py`（盯住段微抖，**不进 E(t) 公式**） |
| 狗通道展开 | `gaze_engine/dog/envelope_compile.py` · `channels_from_envelope()` |

---

## 一、概述（What）

### 本文件用途

本文 **只管辖** `SliderPacket` 里与客户/LLM 直接相关的 **表演节奏控制面**：

- **`macro`**：6 根 0～100 整数滑杆，决定 **5 秒戏的整体节拍**（多用力、多快起、盯住多久、怎么收场）。
- **`hold_seg`**：4 项盯住段参数，决定 **平顶段内的纹理**（平 / 泄 / 拱 / 脉冲 / 发颤）。

一句话：**macro + hold_seg = 客户能理解的「起—盯—收」；系统把它们编译成一条 E(t)，再驱动 12 通道。**

### 管线位置

```text
上游：客户选预设 / Pomot NL / 01_滑杆包.json
  │
  ▼
① SliderPacket.macro + hold_seg（本合同管辖）
  │ finalize_packet（L1 禁区）
  ▼
② build_energy_envelope() → E(t) 150 点（本合同输出目标）
  │
  ├─ resolve_pad() → PAD（❌ 不进 E(t)，见兄弟合同）
  ▼
③ channels_from_envelope() → pulse 12×150
  │ apply_style / prior / quality
  ▼
④ 02_烘焙_*.json
```

### 管辖 / 边界

| ✅ 本文件管 | ❌ 本文件不管 |
|------------|--------------|
| macro 六根的定义、语义、→ E(t) 映射 | PAD (P,A,D) 三维气质（见 [`../03_情绪坐标/03_12通道映射与编译链.md`](../03_情绪坐标/03_12通道映射与编译链.md)） |
| hold_seg 四字段、五种 shape、L1 shape 白名单 | 12 通道逐帧数值（出厂物，见 [`01_十二通道与全量帧格式.md`](../04_通道编译/01_十二通道与全量帧格式.md)） |
| 6+4 与 E(t) 四段（蓄力/启动/保持/缓和）的对应 | 品种/人格 style.json（S5，不改 E(t)） |
| 与 16 情绪预设、L1 禁区的关系 | 耳位 `ear`（并行注入 eyebrow，不进 E(t)） |
| 客户/LLM 应改哪几根、不应改什么 | 扩散 Prompt、工程底膜几何 |

### 命名澄清（常见混淆）

| 说法 | 正误 | 说明 |
|------|------|------|
| **macro** | ✅ | 正式字段名；口语「宏观滑杆」「六根杆」 |
| maro / 宏杆 | ⚠️ 笔误 | 均指 **macro** |
| **hold_seg** | ✅ | 「盯住段花纹」；**不是** macro 里的某一杆 |
| grip | ✅ 但不同义 | macro 的「定得住」；与 hold_seg **分工不同** |
| hold / 按住 | ❌ 易混 | 勿与 hold_seg 混称；hold_seg 只管 **形状纹理** |

---

## 二、理论依据（Theory）

### 2.1 理论依据链

```text
① 戏剧节拍（Beat）与分镜「起—持—收」
   → 5 秒单镜头需要可复述的节奏，而非 1800 个自由关键帧
   → 推导出：用少量宏观参数控制整段 envelope

② 动画 Timing Curve / 缓动（smoothstep、ease-in-out）
   → 人眼对「急起慢收」「慢拱脉冲」有稳定读感
   → 推导出：E(t) 分段插值 + hold 段乘性纹理

③ 拉班 Effort 四维（力 Weight · 时 Time · 空 Space · 流 Flow）的简化
   → 表演指导常用「更狠 / 更急 / 更钉 / 更泄」等可教语言
   → 推导出：macro 六根的客户语义（非 1:1 学术映射，见 §5.1 分级）

④ PAD / 气质与 **时间节奏** 在心理学上可分离
   → 「委屈」vs「凶狠」是气质差；「5 秒内何时到峰」是节拍差
   → 推导出：macro/hold **不进 PAD**；PAD **不进** build_energy_envelope()

⑤ 维度灾难（12×150）与可验收性
   → 客户无法维护 12 通道；合同需要 L1 禁区
   → 推导出：唯一编辑入口 = SliderPacket，而非 channel_tracks
```

### 2.2 macro — 六根宏观滑杆在说什么

**本质**：把 **5 秒表演** 拆成客户能操作的 **六个旋钮**，全部 **0～100 整数**。

| id | 客户语义（表演语言） | 理论锚（简化） | 主要作用的 E(t) 段 |
|----|---------------------|----------------|-------------------|
| `push` | 往哪使劲（内收 / 外放） | Effort **方向** | 峰高公式（内收压低整体幅度） |
| `power` | 力度（轻 / 狠） | Effort **Weight** | 蓄力→启动→保持的 **整体高度** |
| `speed` | 快慢（戏眼早晚） | Effort **Time** | `t_peak`（约 14～20 帧）、`t_settle` |
| `steady` | 盯得稳（飘 / 钉死） | Effort **Space** | ⚠️ **E(t) 主公式不直接吃**；人类 `human_prior` 调盯住微抖 |
| `grip` | 定得住（泄 / 憋住） | Effort **Flow** | 平顶高度 `plateau = peak × lerp(0.88, 1.0, grip)` |
| `outro` | 收场（快落 / 慢收） | Beat **Release** | `t_hold1`（92 vs 110 帧）、尾段衰减曲线 |

### 2.3 hold_seg — 盯住段在说什么

**本质**：E(t) 进入 **保持段**（约 25～92 或 25～110 帧）后，在 **已定的平顶高度** 上再乘一层 **纹理**。

| id | 客户语义 | 取值 | 理论锚 |
|----|----------|------|--------|
| `shape` | 盯住段长什么样 | `flat` `decay` `swell` `pulse` `tremble` | 平顶 / 泄劲 / 慢拱 / 节律勾人 / 恐惧微颤 |
| `pulse_rate` | 一波多密 | 0～100 | 脉冲/颤振 **频率** |
| `pulse_depth` | 一波多深 | 0～100 | 脉冲/颤振 **幅度**（tremble 也复用 depth 定振幅） |
| `swell` | 段内慢拱强弱 | 0～100 | 仅 `shape=swell` 时主导拱形 |

**戏种与 shape 白名单**（L1，`滑杆规范.md` §10.2）：

| 戏种分组 | 典型预设 | 允许的 shape |
|----------|----------|--------------|
| 压·慑 | 施压、冷压、威慑… | 仅 `flat` |
| 悲·怯 | 委屈、要哭、崩溃… | `tremble` `decay` |
| 媚·勾 | 魅惑、纯甜、媚杀… | `pulse` `swell`（按预设） |

### 2.4 E(t) 四段 — macro + hold_seg 的时间骨架

与 [`01_十二通道与全量帧格式.md`](../04_通道编译/01_十二通道与全量帧格式.md) §1 一致：

```text
帧轴 0 ──────────────────────────────────────────────── 149（5s @ 30fps）

     │← 蓄力/启动 →│←────── 保持（hold） ──────→│← 缓和 →│
     0    t_peak  t_settle  t_hold0          t_hold1    149

     macro: speed, power, push  → 峰时刻与峰高
     macro: grip                → 平顶相对峰高
     macro: outro               → t_hold1 与尾段形状
     hold_seg                   → [t_hold0, t_hold1] 内乘性纹理
```

---

## 三、为什么这样做（Why）

### 3.1 关键决策

**决策 1：为什么是 6 + 4，而不是 12 根或 3 根？**

| 方案 | 问题 | 结论 |
|------|------|------|
| 12 根 = 12 通道各一杆 | 客户不懂 squint；无法保证帧间一致 | ❌ |
| 3 根 = 起/盯/收 | 无法表达魅惑 pulse、委屈 tremble、崩溃 decay | ❌ |
| **6 macro + 4 hold** | 覆盖 16 预设戏种；LLM 可 ±5 步进；可映射 E(t) | ✅ 正选 |

**决策 2：为什么 hold_seg 独立于 macro？**

| 方案 | 问题 | 结论 |
|------|------|------|
| 把 pulse/tremble 并进 `grip` | 「定得住」与「一阵一阵勾」语义冲突 | ❌ |
| 用第 7 根 macro 表示 shape | shape 是 **枚举** 不是 0～100；L1 需按戏种禁 shape | ❌ |
| **`hold_seg` 独立对象** | schema 清晰；魅惑改 pulse 不动 power | ✅ 正选 |

**决策 3：为什么 steady 在 E(t) 里「弱映射」？**

| 方案 | 问题 | 结论 |
|------|------|------|
| steady 直接改 E(t) 平顶形状 | 「钉死」与「平顶高度」和 grip 重复 | ⚠️ 部分弃用 |
| steady 只调 human_prior 微抖 | 保留客户语义「飘 vs 钉」；狗种可另定 prior | ✅ 当前实现 |
| 文档仍写 steady→E(t) | 与代码不一致 → **本文纠偏** | 见 §4.2 诚实现状表 |

**决策 4：为什么 PAD 不能替代 macro？**

若用 PAD 同时管气质和节拍：

- 换情绪会意外改变 `t_peak`（无法独立审定「委屈盯 90 帧」）
- 品种若耦合 PAD 会改变 E(t)（违反正交审计）

→ **macro/hold 专管 E(t)；PAD 专管 pad_scale[ch]**（见 [`04_四层表演栈与style边界.md`](../03_情绪坐标/04_四层表演栈与style边界.md)）。

### 3.2 历史教训

| ⚠️ 坑 | 形成的规则 |
|-------|-----------|
| 客户六杆全在 42～58「路人中间带」 | G1：弹回预设默认 macro |
| flat 戏种误开 pulse_rate | G5/G6：非 pulse shape 清零 pulse 参数 |
| 把 hold_seg 当成「第七根 macro」 | 合同与 UI 必须分块展示：**起/动/收** vs **盯住花纹** |
| LLM 直接改 channel_tracks | 💥 禁止；只能改 SliderPacket |
| 滑杆规范写「steady→E(t)」但代码未接 | 专篇 §4.2 **实现状态表** 为真；改代码或改文档须同步 |

---

## 四、怎么实现（How）

### 4.1 输入规格 — SliderPacket 片段

```json
{
  "schema": "slider-packet-v1",
  "emotion": "委屈·幼犬眼",
  "macro": {
    "push": 15,
    "power": 26,
    "speed": 22,
    "steady": 62,
    "grip": 68,
    "outro": 22
  },
  "hold_seg": {
    "shape": "tremble",
    "pulse_rate": 18,
    "pulse_depth": 22,
    "swell": 8
  }
}
```

| 约束 | 规则 |
|------|------|
| 数值范围 | macro / hold 数值项：0～100 整数 |
| shape | 必须是五枚举之一；须通过 preset 的 `allowed_shapes` |
| 持久化 | `01_滑杆包.json` 存 macro+hold；pad 可选（见兄弟合同） |
| LLM 输出 | 绝对值 `{"macro":{"power":90}}` 或增量 `{"macro_delta":{"power":"+10"}}` |

### 4.2 macro → E(t) — 代码级映射（真源）

实现：[`build_energy_envelope()`](../../gaze_engine/_shared/envelope_compile.py)

#### 4.2.1 时间轴 `_timing()`

```python
speed = macro.speed / 100.0
t_peak    = round(lerp(20, 14, speed))      # speed↑ → 更早到峰
t_settle  = t_peak + round(lerp(8, 4, speed))
t_hold0   = max(t_settle, 25)
t_hold1   = 92 if outro < 50 else 110        # outro 低=快收 → 保持段更短
```

#### 4.2.2 峰高 `_peak_level()`

```python
power, push = macro.power/100, macro.push/100
outward = 0.78 + 0.45 * abs(push - 0.5)
peak = 0.06 + 0.38 * power * outward
if push < 0.35:   # 内收（委屈类）
    peak = 0.04 + 0.26 * power
plateau = peak * lerp(0.88, 1.0, grip/100)  # grip↑ → 平顶更接近峰
```

#### 4.2.3 分段填充

| 帧区间 | 公式要点 |
|--------|----------|
| `0 … t_peak` | `peak × smoothstep(t/t_peak)` — 蓄力上升 |
| `t_peak+1 … t_settle` | 从 `peak` smoothstep 过渡到 `plateau` |
| `t_hold0 … t_hold1` | `plateau × _hold_texture(u, hold_seg)` |
| `t_hold1+1 … 149` | 快收：`tail × (1 - smoothstep(u))`；慢收：线性 0.85 衰减 |

#### 4.2.4 实现状态表（诚实分级）

| macro 键 | 直接影响 `build_energy_envelope` | 间接影响（物种层） |
|----------|----------------------------------|-------------------|
| push | ✅ 峰高公式 | `_direction()` → pupil_x 符号 |
| power | ✅ 峰高 | 全通道幅度 |
| speed | ✅ t_peak, t_settle | 人类 prior 扫视窗 |
| grip | ✅ plateau | — |
| outro | ✅ t_hold1, 尾段曲线 | — |
| steady | ❌ 不进 E(t) | 人类：`human_prior` 盯住 jitter 幅度 |

> **审定注意**：对外培训可说 steady「盯得稳不稳」；工程验收 E(t) 曲线时 **不要指望** 只改 steady 就能看见 E(t) 形状大变——应看 **prior 后** 的 12 通道或人类专检。

### 4.3 hold_seg → 盯住段纹理 — `_hold_texture()`

`u = (t - t_hold0) / (t_hold1 - t_hold0)` ∈ [0, 1]

| shape | 返回乘子（相对平顶） | pulse_rate / pulse_depth / swell |
|-------|---------------------|----------------------------------|
| `flat` | `1.0` | 忽略 |
| `decay` | `1.0 - 0.55 × u` | 忽略 |
| `swell` | `1.0 + (swell/100)×0.35×sin(πu)` | swell 主导 |
| `pulse` | `1.0 + depth×sin(2π×rate×u)` | rate=`max(1, pulse_rate/100×4)`；depth=`0.06+(pulse_depth/100)×0.20` |
| `tremble` | `1.0 + tremble_amp×sin(2π×rate×u)` | rate=`6+pulse_rate/100×10`；amp=`0.03+(pulse_depth/100)×0.05` |

**下游联动（狗，非 E(t) 本体）**：

- `hold_seg.shape=tremble` → `_dog_blink_series` 增加眨眼锚点、略提高峰值
- 委屈类情绪 + tremble → `_apply_moist_sad_baseline` 在保持段叠加 squint/lid/gloss

### 4.4 从 SliderPacket 到出厂 — 调用链

```text
SliderPacket
  → finalize_packet()          # L1：G1～G8 + preset box + shape 白名单
  → build_energy_envelope()    # 仅读 macro + hold_seg
  → channels_from_envelope()   # E(t) × pad_scale × 物种规则
  → apply_breed_style()        # 不改 E(t)
  → prior / pulse_quality
  → 02_烘焙
```

`packet_to_compile_params()`（`slider_schema.py`）仍导出 `space_scale` 等 legacy 系数，供 prior / 旧路径；**E(t) 主链以 `build_energy_envelope` 为准**。

### 4.5 十六预设 — macro/hold 打包方式

预设 **不是新控件** = 一份默认 `SliderPacket`（`emotion` = 预设名）。

| 分组 | 预设示例 | macro 要点 | hold_seg 要点 |
|------|----------|------------|---------------|
| 压·慑 | 施压·凝视 | 高 push/power/speed/steady/grip | `flat` |
| 悲·怯 | 委屈·幼犬眼 | 低 push/power，高 steady/grip | `tremble` + 低 pulse |
| 媚·勾 | 魅惑·勾人 | 中 power，高 grip/outro | `pulse` + 中高 rate/depth |

风格 `style` 通过 `macro_delta` / `hold_seg` 局部覆盖（见 `EMOTION_DEFAULTS`），**不新建 emotion id**。

### 4.6 客户改参数 — 决策表

| 想达到的效果 | 应改 | 不应改 |
|--------------|------|--------|
| 整体更狠 | `power`↑，必要时 `push`↑ | 手改 12 通道 |
| 戏眼更早 | `speed`↑ | PAD |
| 盯住更久、少泄 | `grip`↑、`steady`↑（人类 prior） | 改品种期望变 E(t) |
| 收尾更拖 | `outro`↑（≥50 → t_hold1=110） | — |
| 更颤、更可怜 | `hold_seg.shape=tremble`，`pulse_depth`↑ | 只改 eye_gloss 一轨 |
| 魅惑一阵一阵 | `shape=pulse`，`pulse_rate/depth` | 压·慑 preset 强行 pulse（L1 会弹回） |
| 更压抑气质 | 审定 **PAD** 或换情绪预设 | 用 macro 冒充 PAD |

---

## 五、检查点（Checkpoints）

### 5.1 概念验收（读本文即可）

| 检查项 | 合格标准 | 优先级 |
|--------|----------|--------|
| 说出 macro 与 hold_seg 分工 | macro=整体节拍；hold_seg=平顶纹理 | P0 |
| 说出与 PAD 边界 | macro/hold → E(t)；PAD → pad_scale，不进 E(t) | P0 |
| 纠正 steady 误解 | steady 不直接改 E(t) 形状（人类 prior 除外） | P1 |
| 纠正 grip vs hold_seg | grip=平顶高度；hold_seg.shape=平顶花纹 | P0 |

### 5.2 数值验收 — E(t) 随 macro 单调

在固定预设上 **只改一根**，其余不变，重算 E(t)：

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|----------|----------|--------|
| power↑ → 峰更高 | `build_energy_envelope` | `max(E)` 严格增大（同 push 区） | P0 |
| speed↑ → 更早峰 | 同上 | `argmax(E)` 帧号减小 | P0 |
| grip↑ → 平顶更高 | 同上 | `mean(E[t_hold0:t_hold1])` 增大 | P0 |
| outro 低 → 更短保持 | 同上 | `t_hold1==92` vs `110` | P0 |
| tremble vs flat | 同上 | 保持段方差：tremble > flat | P1 |

```bash
cd /path/to/jintao_node_eye
python3 -c "
import json
from pathlib import Path
import sys
sys.path.insert(0, '.')
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine._shared.envelope_compile import build_energy_envelope

p = Path('预设资产/情绪包/dog/委屈·幼犬眼.json')
if not p.is_file():
    p = Path('客户资产库/客户_C001/项目_P001/输出/01_滑杆包.json')
pkt = SliderPacket.from_dict(json.loads(p.read_text(encoding='utf-8')))
e0 = build_energy_envelope(pkt)
m = pkt.macro
m.power = min(100, m.power + 15)
e1 = build_energy_envelope(pkt.clamped())
assert max(e1) > max(e0), 'power 应抬高峰'
print('OK: macro→E(t)  smoke')
"
```

### 5.3 L1 禁区验收

| 检查项 | 测试方法 | 合格标准 | 优先级 |
|--------|----------|----------|--------|
| G5 flat + pulse | finalize_packet | pulse_rate/depth 清零 | P0 |
| 施压 preset + tremble | finalize_packet | shape 弹回 flat | P0 |
| G1 六杆中间带 | finalize_packet | macro 弹回预设中心 | P1 |

```bash
python3 -c "
from gaze_engine._shared.slider_schema import SliderPacket, MacroSliders, HoldSegment
from gaze_engine._shared.packet_finalize import finalize_packet
p = SliderPacket(
    emotion='施压·凝视',
    macro=MacroSliders(push=50,power=50,speed=50,steady=50,grip=50,outro=50),
    hold_seg=HoldSegment(shape='tremble', pulse_rate=30, pulse_depth=20),
)
out, rep = finalize_packet(p)
assert out.hold_seg.shape == 'flat', rep.fixes
print('OK: L1 shape 白名单')
"
```

### 5.4 文档一致性

| 检查 | 期望 |
|------|------|
| [`滑杆规范.md`](../01_输入与收口/滑杆规范.md) §3 macro 表 | 与本文 §4.2 一致；steady 标注 prior |
| [`../03_情绪坐标/03_12通道映射与编译链.md`](../03_情绪坐标/03_12通道映射与编译链.md) | 引用本文作 macro/hold 专篇 |
| 各情绪 md §4.2 滑杆定稿 | macro/hold 数值与 JSON 真源一致 |

---

## 六、FAQ

**Q1：macro 和 12 通道有没有对照表？**  
没有 1:1 表。6 macro + hold → **一条 E(t)**；再经 PAD 与物种规则 → 12 通道。见 [`../03_情绪坐标/03_12通道映射与编译链.md`](../03_情绪坐标/03_12通道映射与编译链.md) FAQ。

**Q2：hold_seg 的 pulse_rate 在 tremble 下算什么？**  
在 `_hold_texture` 里 tremble 用 `pulse_rate` 调 **颤频**（不是 pulse shape 的那套 rate 公式）；`pulse_depth` 调 **振幅**。命名历史原因：四字段共用 schema，靠 `shape` 分支区分语义。

**Q3：为什么滑杆规范曾写 hold_seg「v2 才实现」？**  
**已过时**。当前 `build_energy_envelope` **已实现** `_hold_texture`；以本文与代码为准。若门户 SVG 预览与烘焙不一致，查前端是否用同一套公式近似。

**Q4：只改 steady 为什么 E(t) 图不变？**  
因为 steady **不进入** `build_energy_envelope`。人类链路看 `human_prior` 盯住 jitter；狗链路 steady 影响较弱，主要读感仍来自 grip + hold_seg。

**Q5：Pomot 改「更委屈一点」该动 macro 还是 PAD？**  
优先 **macro/hold**（如 power↓、tremble depth↑）或 **换预设**；PAD 走审定，非 C 端默认编辑项。

---

## 七、修改记录

| 日期 | 内容 | 原因 |
|------|------|------|
| 2026-05-28 | 初版：macro/hold_seg 专篇，对齐 envelope_compile 与 L1 | 用户审定能量曲线映射，需独立合同讲清 6+4 来龙去脉 |

---

**一句话对外口径**：

> 客户用 **六根宏观滑杆** 定「多用力、多快、怎么收」，用 **盯住段花纹** 定「中间是平钉、发颤还是一阵一阵」；系统合成 **五秒能量曲线 E(t)**，再驱动十二路眼眉动画——**气质 PAD 与品种风格都不改这条节拍线**。
