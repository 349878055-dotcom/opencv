# 扩散 Prompt 全链路方案 · 导读（04 + 05 + Wan 接线）

> **范围**：从 **6+3 滑杆 + 02 烘焙** → **节奏说明书（05）** → **04_Prompt.txt** → **Wan 正负 CLIP**；与 **工程底膜 MP4** 并行送扩散。  
> **不写**：底膜几何标定、OpenCV 渲染细节（见 [`狗150帧全量编译合同_上篇.md`](狗150帧全量编译合同_上篇.md) 下篇预告）。  
> **状态**：核心代码 **已接入**；狗正向情感词、负向分层、品种中文名等待审定。

**兄弟规范**：[`扩散引擎提示词拼装规范.md`](../04_接口/扩散引擎提示词拼装规范.md) · [`节奏说明书.md`](../01_总纲/节奏说明书.md) · [`pomot合成规范.md`](pomot合成规范.md)

---

## 零、导读（30 秒读懂）

### 0.1 Wan 吃什么

```text
送扩散引擎 = 两路，必须同一次 revision 同源：

  ① 03_工程底膜.mp4     像素控制（R眼 G眉/耳 B瞳孔，150帧）
  ② 04_Prompt.txt       语义控制（正向 + 节拍说明书 + 叙事 + 负向）

不送：01 滑杆包、02 JSON（02 只作编译真源，不直接进 Wan）
```

### 0.2 从滑杆到「说明书」的一条链

```text
预设 JSON（macro×6 + hold×4 + pad + ear）
        ↓  dog_pipeline S0～S7
02_烘焙.channel_tracks[12][150]
        ↓  rhythm_compiler.build_metronome_text()
05_扩散节拍表（自然语言说明书，嵌入 04）
        ↓  DiffusionPromptAssembler.assemble()
04_Prompt.txt（五段归档）
        ↓  split_for_wan()
wan_positive = 正向 + 节拍表 + 叙事
wan_negative = 负向模板
```

**关键**：说明书 **不是手写**，是从 02 的 12 通道数值 **自动编译** 出来的；滑杆改 → 02 变 → 节拍表变 → Prompt 变。

### 0.3 04 文件五段结构

| 段 | 作用 | 谁写 | 动态/固定 |
|----|------|------|-----------|
| 文件头 | 情绪/物种/品种/revision | assembler | 动态 |
| **正向 Prompt** | 导演总要求（物种+质感+情绪） | assembler + `rhythm_data` | 动态 |
| **扩散节拍表** | 12 通道说明书（=05 全文） | `rhythm_compiler` | **全动态** |
| **叙事** | 客户 action 原文 | `nl_splitter` | 动态，**禁止 LLM 改写** |
| **负向 Prompt** | 质量与同步禁区 | 固定模板 | 固定（可分层扩展） |

---

## 一、概述（What）

### 1.1 本方案管什么

| ✅ 管 | ❌ 不管 |
|------|--------|
| 04 五段内容与来源 | 02 怎么算（见狗150帧上篇） |
| 05 节拍表如何从 12 通道编译 | MP4 怎么渲染 |
| 正向/负向怎么写、狗猫人差异 | 客户参考图 identity 训练 |
| Wan positive/negative 怎么拆 | Comfy 节点 UI 布局 |

### 1.2 三个交付文本的关系

```text
02_烘焙.json          → 机器真源（1800 float）
05_扩散节拍表.txt      → 从 02 导出，可单独落盘；通常嵌入 04
04_给视频生成的Prompt.txt → 归档 + 送 Wan 前的完整文本
```

---

## 二、理论依据（Theory）

### 2.1 为什么 MP4 不够还要 Prompt

| 输入 | Wan 读到什么 | 缺了会怎样 |
|------|-------------|-----------|
| MP4 底膜 | 几何在哪、怎么动 | 形状对但 **不知道在演什么情绪** |
| 正向 + 节拍表 | 情绪名 + 每通道 pulse 语义 | 有动作但 **方向错**（凶/媚混淆） |
| 叙事 | 故事情节（回头、跑回笼子） | 缺 **场景意图** |
| 负向 | 不要过曝/乱动/换脸 | 默认 **质量崩、不同步** |

### 2.2 「说明书」在链路中的位置

节奏说明书 = **把 12 通道数字翻译成人话**，让扩散模型知道：

```text
pupil_x  t49=0.737  →  「扫视方向；牵动注视与头部微转暗示」
blink    t52 峰值   →  「眼睑脉冲；唇颊放松/微收节奏」
eyebrow  高值       →  「耳位竖耳；与全身姿态联动」（狗）
```

文案真源：`gaze_engine/{species}/rhythm_data.py` → `DIFFUSION_HINTS` + `CHANNEL_LABELS`

---

## 三、为什么这样做（Why）

| 决策 | 理由 |
|------|------|
| 节拍表从 02 自动生成 | LLM 会乱编 t/v；必须数值精确 |
| 叙事客户原文直出 | LLM 改写会丢「跑回笼子再回头」细节 |
| 正向短 + 节拍表长 | CLIP 窗口有限；约束放节拍表 |
| 负向固定模板 | 质量项跨项目通用 |
| 狗正向用 `EMOTION_VISUAL_PROMPTS` | 补「湿润大眼」等扩散友好词；🔧 待与「跟随控制序列」句合并 |

---

## 四、怎么实现（How）

### 4.1 编译链逐步（狗示例）

| 步 | 输入 | 函数 | 输出 |
|----|------|------|------|
| A | `委屈·幼犬眼.json` | `run_dog_pipeline` | `02_烘焙` |
| B | `02_烘焙` | `build_metronome_text(02, species="dog")` | 05 文本 |
| C | `02` + `action` | `DiffusionPromptAssembler.assemble` | `04_Prompt.txt` |
| D | `04` | `split_for_wan` | positive / negative |
| E | `02` | `render_dog_batch` | `03_工程底膜.mp4` |

### 4.2 05 节拍表 · 六段模板（`rhythm_compiler`）

```text
① 文件头（情绪、来源、物种、形态）
② ## 全局阶段（蓄力→启动→保持→缓和）
③ ## 各通道脉冲
     - **pupil_x**（视线左右）: t0=…, t49=…
       → 节拍：…（DIFFUSION_HINTS）
     … 12 通道 …
④ ## 时间轴汇合（变帧时刻）
⑤ ## 给扩散的硬约束（摘要）（DOG_CONSTRAINT 等）
⑥ ## 出厂质检（若有 pulse_quality_report）
```

**降采样规则**：烘焙定稿 150 帧时，每通道显示约 20 个采样点；`blink` 强制保留非零峰。

### 4.3 正向 Prompt · 怎么写

#### 4.3.1 三层内容（推荐结构）

```text
[L1 身份层]  品种 + 真实毛发/皮肤
[L2 情绪层]  情绪名 + 视觉气质（EMOTION_VISUAL_PROMPTS 或 mood_tags）
[L3 约束层]  眼耳/眉眼严格跟随控制序列；情绪起伏与控制序列对齐
[L4 画幅层]  近景/半身 + 高清
```

#### 4.3.2 物种差异

| 物种 | L1 | L3 约束句 |
|------|-----|-----------|
| **dog** | `{品种}犬，真实毛发` | 眼耳与控制序列对齐；耳位跟随 eyebrow 通道 |
| **cat** | `{品种}猫，真实毛发` | 同狗 |
| **human** | `{人格}（气质参考，不换客户脸）` | 眉眼与控制序列对齐 |

#### 4.3.3 狗 · 定稿表（`dog/rhythm_data.py` → `EMOTION_VISUAL_PROMPTS`）

| 情绪 | 正向情感词（L2，已实现） |
|------|-------------------------|
| 委屈·幼犬眼 | 近景特写，湿润大眼，眼睑微垂，泪光，耳下垂，恳求感 |
| 害怕·退缩 | 畏缩，耳后贴，瞳孔略放大 |
| 渴望·仰望 | 仰视，湿润眼，期待，耳尖微动 |
| … | 见 `EMOTION_VISUAL_PROMPTS` 全表 |

🔧 **待补**：每条情绪在 L2 后 **追加 L3 约束句**（与猫/人一致），避免只有美术词、缺少「跟随控制序列」硬约束。

#### 4.3.4 可选 LLM 场景句

`use_llm_scene=True` → 15 字内质感（「柔和室内暖光」）；**默认关闭**，避免漂移。

### 4.4 负向 Prompt · 怎么写

#### 4.4.1 三层负向（推荐扩展方向）

| 层 | 内容 | 现状 |
|----|------|------|
| **N1 画质** | 过曝、模糊、低质量、畸形 | ✅ `_NEGATIVE_PROMPT` |
| **N2 同步** | 眉眼/眼耳与画面不同步、乱动脱节 | ✅ 已有 |
| **N3 身份/语义** | 换脸、多余人物、情绪浓度不足、夸张鬼脸 | ✅ 已有 |
| **N4 物种** | 狗：人类五官、猫耳；猫：狗耳 | 🔧 待加 `DOG_NEGATIVE_EXTRA` |

#### 4.4.2 当前固定负向（代码真源）

```text
色调艳丽，过曝，模糊，字幕，整体发灰，低质量，丑陋，畸形，
脸变形，换脸，多余人物，眉眼与画面不同步，
乱动脱节，情绪浓度不足，涣散无神，夸张鬼脸，杂乱背景
```

**原则**：负向 **不写** 节拍表、不写叙事；只写「不要什么」。

### 4.5 叙事段 · 怎么写

| 规则 | 说明 |
|------|------|
| 来源 | `nl_splitter` 的 `action` 字段 |
| 示例 | `委屈地跑回笼子再回头看了一眼` |
| 禁止 | LLM 改写、摘要、翻译 |
| 与 prior 关系 | 含「回头」→ `apply_dog_prior` 写 pupil_x；叙事段 **同时** 保留原文给 Wan |

### 4.6 Wan / Comfy 接线

```python
from gaze_engine.pomot.assembler import DiffusionPromptAssembler

result = assembler.assemble(baked_json, customer_action=action, species="dog", ...)
clips = DiffusionPromptAssembler.split_for_wan(result["prompt_04"])

# Comfy 节点
control_video = "03_工程底膜.mp4"
positive_clip = clips["positive"]   # 正向 + 节拍表 + 叙事
negative_clip = clips["negative"]
start_image   = "客户参考照.jpg"
```

### 4.7 代码映射

| 功能 | 文件 | 函数/常量 |
|------|------|-----------|
| 02 编译 | `dog/dog_pipeline.py` | `run_dog_pipeline` |
| 05 说明书 | `_shared/rhythm_compiler.py` | `build_metronome_text` |
| 狗通道文案 | `dog/rhythm_data.py` | `DIFFUSION_HINTS`, `EMOTION_VISUAL_PROMPTS`, `DOG_CONSTRAINT` |
| 04 拼装 | `pomot/assembler.py` | `DiffusionPromptAssembler.assemble` |
| Wan 拆分 | 同上 | `split_for_wan` |
| Pomot 入口 | `pomot/pipeline.py` | `round1` → `_run_delivery` → `assemble` |
| NL 叙事 | `pomot/nl_splitter.py` | `split()` → `action` |

---

## 五、检查点（Checkpoints）

### P0 结构

| 检查 | 方法 |
|------|------|
| 04 五段齐全 | grep `## 正向` `## 扩散节拍表` `## 叙事` `## 负向` |
| 节拍表 12 通道 | 05 段含 `pupil_x`…`eye_gloss` |
| 叙事 = action 原文 | diff nl_splitter 输出 |
| MP4 与 02 同 revision | `baked["revision"]` 一致 |

### P1 语义

| 检查 | 合格 |
|------|------|
| 狗正向含情绪视觉词 | 匹配 `EMOTION_VISUAL_PROMPTS` |
| 节拍 hint 为中文语义 | 每通道有 `→ 节拍：` |
| 负向非空 | >20 字 |

### 一键验收（待建脚本）

```bash
# 建议下一步：scripts/verify_diffusion_prompt_contract.py
python3 -c "
import json, sys
from pathlib import Path
sys.path.insert(0,'.')
from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine.dog.dog_pipeline import run_dog_pipeline
from gaze_engine.pomot.assembler import DiffusionPromptAssembler

pkt = SliderPacket.from_dict(json.loads(Path('预设资产/预设情绪包/dog/委屈·幼犬眼.json').read_text()))
baked, _, _ = run_dog_pipeline(pkt, breed_id='poodle_giant', narrative_action='回头看了一眼')
r = DiffusionPromptAssembler().assemble(baked, customer_action='回头看了一眼', species='dog', breed='poodle_giant')
w = DiffusionPromptAssembler.split_for_wan(r['prompt_04'])
assert '## 扩散节拍表' in r['prompt_04']
assert 'pupil_x' in w['positive']
assert '回头看了一眼' in w['positive']
assert len(w['negative']) > 20
print('OK prompt chain')
"
```

---

## 六、实施优先级

| 优先级 | 任务 | 状态 | 位置 |
|--------|------|------|------|
| **P0** | 狗/猫/人 04 结构验收 | ✅ | `scripts/verify_diffusion_prompt_contract.py` |
| **P0** | 全物种 04 样例导出 | ✅ | `scripts/export_prompt_samples.py` → `_runtime/prompt_samples/` |
| **P1** | 正向 L3「跟随控制序列」句 | ✅ | `assembler._build_positive_prompt` |
| **P1** | 品种 id → 中文展示名 | ✅ | `assembler.resolve_breed_display` |
| **P2** | 负向 N4 物种扩展 | ✅ | `{dog,cat,human}/rhythm_data.NEGATIVE_EXTRA` |
| **P2** | 16+12+10 情绪 L2 视觉词 | ✅ 占位 | `EMOTION_VISUAL_PROMPTS`（可逐条微调） |
| **P3** | LLM 场景句默认策略 | 待定 | 项目配置 |

验收命令：

```bash
python3 scripts/verify_diffusion_prompt_contract.py
python3 scripts/export_prompt_samples.py
```

---

## 修改记录

| 日期 | 内容 |
|------|------|
| 2026-05-27 | 初版：全链路导读 + 正反写法 + 滑杆→说明书编译链 + 代码映射 |
| 2026-05-27 | §六实施项全部落地：assembler L2/L3/N4、验收脚本、样例导出 |
