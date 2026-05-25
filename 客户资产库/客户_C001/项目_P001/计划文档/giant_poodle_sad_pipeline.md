# 巨型贵宾犬 · 委屈表情全链路实施计划

> 目标：从一张贵宾犬参考图 → 定义品种 → 委屈脉冲曲线 → OpenCV 底膜 → 滑杆驱动 → 扩散引擎输出
> 范围：dog/ 目录 6 个文件 + persona_matrix.json + API 路由

---

## 一、当前状态（基线）

| 组件 | 状态 | 说明 |
|------|:----:|------|
| `dog/presets.py` | ❌ 空壳 | 10 个预设全部注释，`dog_packet_from_preset()` 抛 `NotImplementedError` |
| `dog/breeds.py` | ❌ 空壳 | 4 品种全部注释 |
| `dog/pad_weights.py` | ❌ **不兼容** | 定义了 13 通道 `CANONICAL_KEYS_DOG`（含 `ear_left/ear_right`），与标准 12 通道合同冲突 |
| `dog/affine_renderer.py` | ❌ 空壳 | `DogAffineRenderer.render_frame()` 抛 `NotImplementedError` |
| `dog/prior.py` | ❌ 空壳 | `apply_dog_prior()` 抛 `NotImplementedError` |
| `dog/pulse_quality.py` | ❌ 空壳 | `DogPulseQualityReport` 只有骨架 |
| `persona_matrix.json` | ❌ 缺失 | `breed_personas` 没有狗品种条目 |
| `delivery_pipeline.py` | ❌ 硬编码 | `run_delivery()` 只调用了 human_prior，没有物种路由 |

---

## 二、完整数据流

```
用户: 贵宾犬参考图 + "委屈"
        │
        ▼
[Phase 1] 品种定义
  ① 确定巨型贵宾犬的解剖参数
  ② 填入 persona_matrix.json → poodle_giant

        │
        ▼
[Phase 2] 委屈预设
  ③ 填充 dog/presets.py → dog_sad_puppy
     Macro: push=15, power=26, speed=22, steady=62, grip=68, outro=22
     Hold: tremble/decay
     Ear: [-0.6, -0.2]（耳朵耷拉）

        │
        ▼
[Phase 3] 编译与狗耳适配
  ④ 修复 dog/pad_weights.py → 重用标准 12 通道
  ⑤ 新增 dog/channel_adapter.py（类似 cat/channel_adapter.py）
  ⑥ persona_compiler 编译 → 12通道×150帧

        │
        ▼
[Phase 4] 底膜渲染 ← 核心
  ⑦ 读取 eye_asset/elid_raw.png（复用人类底图 RGB 分离方案）
  ⑧ 增加狗眼 mesh（圆形瞳孔、可见巩膜）
  ⑨ G 通道改为狗耳位线（垂耳 vs 立耳）
  ⑩ DogAffineRenderer.render_frame() 实现

        │
        ▼
[Phase 5] 后处理
  ⑪ DogPrior: 扫视动力学 (zeta=0.60, omega=14.0)
  ⑫ DogPulseQuality
  ⑬ delivery_pipeline 增加 species 路由

        │
        ▼
[Phase 6] 扩散引擎输出
  ⑭ 渲染 150 帧底膜视频
  ⑮ 导出 diffusion metronome → ComfyUI
```

---

## 三、实施步骤（按执行顺序）

### Step ①：修复 pad_weights.py — 狗版 12 通道适配

当前问题：`CANONICAL_KEYS_DOG` 定义了 13 通道（含 `ear_left/ear_right`），但标准合同是 12 通道（用 `eyebrow`/`brow_raise` 兼耳位）。

改动：
- 删除 `CANONICAL_KEYS_DOG`，import 标准 `CANONICAL_KEYS`
- `DOG_PAD_WEIGHTS` 中 `ear_left` → `eyebrow`，`ear_right` → `brow_raise`
- 保留 PAD 数值不变

文件：`gaze_engine/dog/pad_weights.py`

### Step ②：新增 dog/channel_adapter.py

与猫的 [`cat/channel_adapter.py`](gaze_engine/cat/channel_adapter.py) 完全对称：
- `ear_to_channel_values(ear)`: 狗耳角度 `[-1,1]` → `eyebrow`/`brow_raise` `[0,1]`
- `inject_ear_into_channels(channels, ear)`: 编译后注入耳通道

狗与猫的区别：
- 狗垂耳品种（贵宾犬）：`angle=-0.6` → `eyebrow=0.2`（耷拉得很低）
- 狗立耳品种（德牧）：`angle=0.8` → `eyebrow=0.9`
- 狗 `brow_raise` 保留给眉毛（狗有眉毛肌，有独立表情）

### Step ③：填充 dog/presets.py — 委屈预设

```python
"dog_sad_puppy": {
    "note": "委屈·幼犬眼：耳朵耷拉、眼湿润、慢眨眼",
    "macro": {"push": 15, "power": 26, "speed": 22,
              "steady": 62, "grip": 68, "outro": 22},
    "hold_seg": {"shape": "tremble", "pulse_rate": 18,
                 "pulse_depth": 22, "swell": 8},
    "ear": {"left": [-0.6, -0.2], "right": [-0.6, -0.2]},
}
```

同时需要额外填充 3 个基础预设以验证管线：
- `dog_alert_bark`（警觉·吠）
- `dog_happy_wag`（开心·摇尾）
- `dog_content_sigh`（满足·叹气）

### Step ④：persona_matrix.json — 巨型贵宾犬品种矩阵

```json
"poodle_giant": {
    "species": "dog",
    "label": "巨型贵宾犬 / 优雅型",
    "base_offset": {
        "pupil_x": 0.50, "pupil_y": 0.48, "blink": 0.55,
        "eyebrow": 0.25,          // 垂耳品种，耳朵自然下垂
        "pupil_scale": 0.50, "iris_scale": 0.45,
        "cornea_bulge": 0.45,
        "squint": 0.50,
        "brow_raise": 0.40,       // 狗有眉毛，保留一定活性
        "lid_upper": 0.48, "lid_lower": 0.52,
        "eye_gloss": 0.55
    },
    "scale_factor": {
        "pupil_x": 0.04, "pupil_y": 0.04, "blink": 0.25,
        "eyebrow": 0.08,          // 垂耳抖动幅度小
        "pupil_scale": 0.12, "iris_scale": 0.10,
        "cornea_bulge": 0.12,
        "squint": 0.15,
        "brow_raise": 0.08,
        "lid_upper": 0.12, "lid_lower": 0.12,
        "eye_gloss": 0.05
    }
}
```

同时额外添加 3 个基础狗品种以便选择：
- `golden_retriever`（金毛/外向型）
- `german_shepherd`（德牧/机警型）
- `corgi`（柯基/活泼型）

### Step ⑤：更新 dog/breeds.py — 委托 persona_compiler

与 [`cat/breeds.py`](gaze_engine/cat/breeds.py) 相同逻辑，从 `persona_compiler.get_persona()` 读取，而不是再从硬编码 dict 读取。

### Step ⑥：狗底膜 — DogAffineRenderer（核心）

这是最复杂的部分。基于 [`human/affine_renderer.py`](gaze_engine/human/affine_renderer.py) 结构，改为狗眼解剖：

**6.1 底图：** 复用 `eye_asset/derived/eyelid_raw.png`
- R 通道 = 眼眶轮廓
- G 通道 = 耳位线 + 眉脊
- B 通道 = 瞳孔/虹膜

**6.2 狗眼与人的差异：**

| 部位 | 人 | 狗（贵宾犬） |
|------|-----|-------------|
| 眼型 | 杏仁形 | **更圆**，略突出 |
| 瞳孔 | 圆形 | 圆形（同人，非猫竖瞳） |
| 虹膜占比 | ~30% | 更大（~40%，狗眼"水汪汪"） |
| 巩膜可见 | 三侧可见 | 更明显（狗常翻白眼） |
| 耳朵 | 无（眉毛取代） | **垂耳/立耳** — 核心区别 |
| 眉脊 | 独立眉毛肌 | 狗有眉脊但不独立 |

**6.3 耳位线绘制（G 通道）：**
- 垂耳：在眼外上方绘制下垂的三角形/水滴形
- 委屈时：角度向下偏移，增加下垂长度
- 动态：耳朵随扫视微转

### Step ⑦：DogPrior — 狗扫视动力学

实现 `apply_dog_prior()`：
- zeta=0.60, omega=14.0（过冲比人略大，比猫略小）
- 瞳孔扫视时耳朵微滞后（ear-ear coupling）
- 委屈场景：减少扫视幅度，增加眼湿润微抖动

### Step ⑧：DogPulseQuality — 狗质检规则

实现三点检测：
- Q01: 耳-眼耦合度（委屈时耳垂 + 眼上睑半闭）
- Q02: 狗尾情绪参考（预留，第一期可以不依赖尾巴）
- Q03: 瞳孔响应幅度（狗不如猫明显，scale_factor 应 <0.15）

### Step ⑨：delivery_pipeline.py — 增加物种路由

关键改动：
- `run_delivery()` 增加 `species` 参数
- `species == "dog"` 时调用 `apply_dog_prior()` + `DogPulseQuality`
- `species == "cat"` 时调用猫管线

---

## 四、依赖关系图

```
                    ┌──────────────────┐
                    │ 用户提供参考图     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ poodle_giant     │
                    │ breed def        │
                    │ (persona_matrix) │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐       ┌─────▼──────┐     ┌──────▼──────┐
    │ presets │       │ pad_weights│     │ breed def   │
    │ (委屈)  │◄──────│ (12通道)   │     │ (poodle)    │
    └────┬────┘       └─────┬──────┘     └──────┬──────┘
         │                  │                   │
         ▼                  ▼                   │
    ┌──────────────────────────────┐            │
    │ channel_adapter (ear→channel)│            │
    └──────────────┬───────────────┘            │
                   │                            │
                   ▼                            │
    ┌──────────────────────────────┐            │
    │ persona_compiler.compile()   │◄───────────┘
    │ → 12通道 × 150帧            │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ DogAffineRenderer.render()  │
    │ → 底膜图像 (690×361)        │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ DogPrior.apply()            │
    │ → 扫视动力学 + 耳滞后       │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ DogPulseQuality.fix()       │
    │ → 质检修正                   │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ export_diffusion_metronome()│
    │ → ComfyUI 可消费的节拍表    │
    └──────────────────────────────┘
```

---

## 五、风险与决策点

| 风险 | 等级 | 缓解 |
|------|:----:|------|
| 狗耳位线几何难以统一（垂耳 vs 立耳差异大） | 🔴 | MVP 只支持垂耳（贵宾犬），后续品种扩展时用参数化 |
| 复用 human eyelid_raw.png 底图可能不够适配狗眼 | 🟡 | 第一期直接用，若效果差再生成专用狗眼底图 |
| 狗的情绪表达比猫更依赖嘴/尾巴（本项目只做眼耳） | 🟡 | 委屈表情主要靠眼耳，可以覆盖 70% 效果 |
| delivery_pipeline 需物种路由重构 | 🟢 | 加 `species` 参数即可，改动量小 |
| 工作台 API 没有狗预设选择界面 | 🟢 | 先 CLI 验证，界面后续扩展 |

---

## 六、执行顺序建议

| 优先级 | 步骤 | 预估文件数 | 依赖 |
|:------:|------|:---------:|:----:|
| P0 | ① pad_weights.py 12 通道修复 | 1 | 无 |
| P0 | ② channel_adapter.py | 1 | ① |
| P0 | ③ presets.py 委屈预设 | 1 | 无 |
| P0 | ④ persona_matrix.json 品种 | 1 | 无 |
| P0 | ⑤ breeds.py 重构 | 1 | ④ |
| P0 | **⑥ DogAffineRenderer 底膜** | 1 | ①②③ |
| P1 | ⑦ DogPrior | 1 | ⑥ |
| P1 | ⑧ DogPulseQuality | 1 | ⑥ |
| P1 | ⑨ delivery_pipeline 路由 | 1 | ⑦⑧ |
| P2 | 扩散引擎导出 CLI | 2 | ⑨ |

> **P0 = 必须完成才能看到"委屈"表情**  
> **P1 = 必须完成才能通过扩散引擎**  
> **P2 = 可并行或延后**

---

请审阅这个计划，你觉得范围合适吗？需要调整优先级或补充什么吗？
