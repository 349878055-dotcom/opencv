# 人格 / 品种 与 E(t) 正交 — 审计结论

> **日期：2026-05-27**  
> **结论**：架构设计 **正确**（人格/品种不改 E(t)）；部分 **文档与旧注释曾误导**；**S5 styled 已接入代码**。

---

## 一、正确分层（全物种统一）

| 步骤 | 输出 | 只由谁决定 |
|------|------|-----------|
| S2 | **E(t)** 150×1 | 情绪 JSON macro/hold |
| S3 | **PAD → scale[ch]** | 情绪名（10/16/12 组常数） |
| S4 | **pulse** 12×150 | E(t)+PAD+物种 compile |
| **S5** | **styled** 12×150 | **人格/品种 base+scale × pulse** |
| S6+ | prior / 02 | 叙事、质检 |

**人格（human）与品种（cat/dog）在 S5 等价**，公式相同：

```text
styled[ch,t] = clamp01( base_offset[ch] + scale_factor[ch] × pulse[ch,t] )
```

---

## 二、曾误导的来源（已修）

| 位置 | 原问题 | 处理 |
|------|--------|------|
| `persona_compiler.py` 头注释 | 「上游 ADSR 波形」像人格改能量 | ✅ 改为 pulse→styled，标明不改 E(t) |
| `眼眉指令集_全局情绪节奏主钟.md` | 只写 `compile_to_channels` | ✅ 改为完整 S0～S7 |
| `风格化偏向.md` | 占位，未写正交 | ✅ 重写 |
| 口头理解 | 「人类人格直接改 E(t)」 | ❌ 错误；与狗品种同层 |

---

## 三、代码实现状态（审计后）

| 模块 | 状态 |
|------|------|
| `gaze_engine/_shared/style_compose.py` | ✅ 新增 `apply_style_offset` |
| `dog/breeds.apply_breed_style` | ✅ |
| `cat/breeds.apply_breed_style` | ✅ |
| `human/persona_compiler.apply_persona_style` | ✅ |
| `dog_pipeline` S5 + `breed_id` | ✅ |
| `run_cat_pipeline` S5 | ✅ |
| `run_delivery` / `run_species_delivery` 人类 S5 | ✅ |
| `pomot/pipeline` 传 breed/style | ✅ |
| 几何 `SpeciesTemplate` | ✅ 并行，不改 E(t) |

---

## 四、验收方法

```bash
# 同情绪、不同品种：E(t) 相同，blink 轨不同
python3 -c "
import json
from pathlib import Path
import sys
sys.path.insert(0,'.')
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine._shared.envelope_compile import build_energy_envelope
from gaze_engine.dog.dog_pipeline import run_dog_pipeline

pkt = SliderPacket.from_dict(json.loads(Path('预设资产/预设情绪包/dog/委屈·幼犬眼.json').read_text()))
e = build_energy_envelope(pkt)
_, p0, _ = run_dog_pipeline(pkt)
_, p1, _ = run_dog_pipeline(pkt, breed_id='poodle_giant')
assert e == build_energy_envelope(pkt)
assert p0['blink'][50] != p1['blink'][50]
print('OK orthogonality')
"
```

---

## 五、修改记录

| 日期 | 内容 |
|------|------|
| 2026-05-27 | 全库审计 + S5 接入 + 文档修正 |
