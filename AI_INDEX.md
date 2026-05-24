# AI_INDEX · jintao_node_eye 代码依赖图谱

> **核心架构**：双模驱动中间件（Eye-Figma Engine）— 详见 [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md)
>
> **用途**：AI Agent 首次进入项目时读取此文件，一次性理解全项目结构、依赖关系、入口函数。
> **无需遍历目录**，读完此文件即可精准定位代码。
> **使用方式**：用户给 NL 指令 → 你读此文件（~200 tokens）→ 只读目标文件 → 改代码。

---

## 一、全景概览

```
根目录（AI 第一眼看到）
├── AI_INDEX.md             ← 本文件（代码图谱）
├── README.md               ← 项目简介
├── .cursorrules            ← Cursor AI 行为规则
├── 一键打开能量工作台.sh     ← 启动入口
├── __init__.py              ← 项目初始化
├── asset_lib.py             ← 资产库路径工具
│
├── tools/                   ← 网页工作台 + HTTP 服务
│   ├── 01_工作台服务/        ← 主应用
│   │   ├── serve_workbench.py   ← HTTP 后端（API 主入口）
│   │   └── 能量工作台.html      ← 前端 UI
│   ├── 02_前端插件/          ← JS 底层插件（工作台自动加载）
│   ├── 03_工具脚本/          ← 构建/维护脚本
│   ├── 04_缓存数据/          ← 运行时数据
│   └── 05_其他工具/          ← 独立辅助工具
│
├── gaze_engine/             ← 核心引擎 (19 模块)
│   ├── control_surface.py       ← 唯一真源: 16预设
│   ├── slider_schema.py         ← 数据类: SliderPacket
│   ├── slider_bounds.py         ← L1 禁区
│   ├── packet_finalize.py       ← 滑杆包收口校验
│   ├── envelope_compile.py      ← 能量包络: SliderPacket→12×150
│   ├── human_prior.py           ← 真人化
│   ├── pulse_quality.py         ← 平庸三检
│   ├── micro_jitter.py          ← 微颤动
│   ├── delivery_pipeline.py     ← 主交付链
│   ├── llm_openai.py            ← LLM 集成 (含 CHEAP_MODEL)
│   ├── nl_intent.py             ← 意图分类
│   ├── nl_router.py             ← NL 路由
│   ├── nl_to_packet.py          ← 关键词→预设
│   ├── node1_defaults.py        ← 默认值加载
│   ├── pipeline_io.py           ← JSON 读写
│   ├── workbench_io.py          ← 操作台读写
│   ├── workbench_context.py     ← 上下文管理
│   ├── channel_contract.py      ← 12通道定义
│   ├── export_diffusion_metronome.py ← 扩散节拍表
│   ├── batch_presets.py         ← 五样本烘焙
│   ├── persona_compiler.py      ← 人格编译
│   ├── base_mesh_gen.py         ← 基础网格
│   ├── affine_renderer.py       ← ⚠️ 禁用中 (_AFFINE_DISABLED)
│   ├── audio_compiler.py        ← ⚠️ 禁用中 (_AUDIO_DISABLED)
│   └── persona_matrix.json      ← 9人格矩阵
│
├── contracts/                ← 合同规范
│   ├── 01_总纲/               ← 全局理论+工程
│   ├── 02_情绪/               ← 每个情绪一个文件
│   ├── 04_接口/               ← 上下游对接
│   ├── 05_人格化/             ← 人格风格化偏向
│   └── 06_架构/               ← 顶层设计（核心）
│
├── prompts/                  ← LLM Prompt
│   ├── node1_system_prompt.txt    ← 系统 Prompt（已压缩至15行）
│   └── node1_knowledge_base.txt   ← 知识库（已压缩至16行）
│
├── scripts/                  ← 工具脚本
│   ├── s01_从能量生成02.sh        ← 主出厂（CLI）
│   ├── s01_五样本烘焙02.sh        ← 批量烘焙
│   ├── s01_导出扩散节拍表.sh       ← 导出
│   └── s01_设置OpenAI密钥.sh      ← 配置
│
├── docs/                     ← 非 AI 直接需求
│   ├── PROJECT_FILES.md      ← 文件清单
│   └── TOKEN_BUDGET.md       ← Token 优化指南
│
└── 资产库/                   ← 数据存储
    └── 人格包/S01_林青霞_东方不败/
```

---

## 二、数据流（Pipeline DAG）

```
API: POST /api/run-pipeline
    │
    ├─ (可选) 先 POST /api/nl-to-packet  → 自然语言 → SliderPacket
    │
    ▼
┌─ 1. finalize_packet() ──────────────────────────────┐
│  packet_finalize.finalize_packet(pkt)                │
│    → 本戏数值盒检查 → G1-G8 硬禁区 → 弹性弹回        │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 2. compile_envelope() ─────────────────────────────┐
│  envelope_compile.compile_envelope(packet)            │
│    → E(t) 能量曲线 (6 macro → 4 段: 起/蓄/盯/收)     │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 3. channels_from_packet() ─────────────────────────┐
│  → 12 通道 × 150 帧 (pupil_x/y, blink, eyebrow …)   │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 4. apply_human_prior() ────────────────────────────┐
│  human_prior.apply_human_prior(dense)                │
│    → 二阶欠阻尼扫视(过冲) + 盯住微漂微颤 + 眉眼延迟   │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 5. fix_pulse_quality() ────────────────────────────┐
│  pulse_quality.fix_pulse_quality(dense)              │
│    → Q01 能量不足抬升 + Q02 杂乱平滑 + Q03 眉峰延后   │
└──────────────────────────────────────────────────────┘
    │
    ▼
╔═ 6. 视觉封装层 (The Articulator) ══════════════════╗
║  [dense_to_baked_sparse()] ───────────────────────║
║  human_prior.dense_to_baked_sparse()              ║
║  → 02_烘焙_真人律.json (12通道逐帧关键帧)         ║
║                                                    ║
║  [工程底模 (Asset for Diffusion)] ──────────────║
║  affine_renderer (RGB三色分离)                     ║
║  R=眼, G=眉, B=瞳孔 · 闭合路径 · 0-noise         ║
║  ⚠️ 当前 _AFFINE_DISABLED，重建中                ║
║                                                    ║
║  [艺术皮肤 (Visual Skin for Client)] ───────────║
║  Canvas 叠加 · Bloom/变径/手绘质感                ║
║  ❌ 待建 (加法策略：不碰底层坐标)                  ║
╚══════════════════════════════════════════════════════╝
    │
    ▼
╔═ 7. 输出分流引擎 (The Stream Splitter) ════════════╗
║                                                     ║
║  Stream 1 → Raw_Asset (02.json + 工程底模)          ║
║              → Wan 扩散引擎                         ║
║                                                     ║
║  Stream 2 → Preview_View (艺术皮肤渲染)             ║
║              → 客户预览                             ║
║                                                     ║
║  export_diffusion_metronome.build_metronome_text()  ║
║  → 扩散节拍表 (文本辅助 · 给 Wan 的脉冲语义)        ║
║                                                     ║
║  底层控制点（12 通道数据）永远不变                    ║
╚══════════════════════════════════════════════════════╝
```

---

## 三、核心入口函数（含精确行号）

| 函数 | 文件:行号 | 被谁调用 | 建议读取范围 |
|------|----------|---------|-------------|
| `_nl_to_packet()` | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py:295) | POST /api/nl-to-packet | 整函数 ~50 行 |
| `_run_full_pipeline()` | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py:330) | POST /api/run-pipeline | 整函数 ~80 行 |
| `chatgpt_customer_nl()` | [`llm_openai.py`](gaze_engine/llm_openai.py:137) | serve_workbench.py | 整函数 ~60 行 |
| `_router_system_prompt()` | [`llm_openai.py`](gaze_engine/llm_openai.py:22) | node1_defaults.py | 整函数 ~15 行 |
| `finalize_packet()` | [`packet_finalize.py`](gaze_engine/packet_finalize.py) | delivery_pipeline.py | 整函数 |
| `channels_from_packet()` | [`envelope_compile.py`](gaze_engine/envelope_compile.py) | delivery_pipeline.py | 整函数 |
| `apply_human_prior()` | [`human_prior.py`](gaze_engine/human_prior.py) | delivery_pipeline.py | 整函数 ~80 行 |
| `fix_pulse_quality()` | [`pulse_quality.py`](gaze_engine/pulse_quality.py) | delivery_pipeline.py | 整函数 |
| `run_delivery()` | [`delivery_pipeline.py`](gaze_engine/delivery_pipeline.py:62) | serve_workbench.py, scripts | 整函数 ~60 行 |
| `_export_metronome()` | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py:444) | POST /api/export-metronome | 整函数 ~30 行 |
| `_asset_browser()` | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py:476) | GET /api/asset-browser | 整函数 ~40 行 |
| `_asset_load_baked()` | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py:517) | POST /api/asset-load-baked | 整函数 ~50 行 |
| `selectEmotion()` | [`能量工作台.html`](tools/01_工作台服务/能量工作台.html:309) | 前端点击事件 | 整函数 ~25 行 |
| `renderNeonControlVideo()` | [`能量工作台.html`](tools/01_工作台服务/能量工作台.html:568) | 前端点击事件 | 整函数 ~40 行 |

---

## 四、关键数据类

| 类/结构 | 文件 | 字段 | 说明 |
|---------|------|------|------|
| `SliderPacket` | [`slider_schema.py`](gaze_engine/slider_schema.py) | emotion, macro, hold_seg, L1 | 核心数据单元 |
| `MacroSliders` | [`slider_schema.py`](gaze_engine/slider_schema.py) | push, power, speed, steady, grip, outro | 6 根宏观滑杆 (0-100) |
| `HoldSegment` | [`slider_schema.py`](gaze_engine/slider_schema.py) | shape, pulse_rate, pulse_depth, swell | 盯住段形态 |
| `CustomerNLResult` | [`nl_intent.py`](gaze_engine/nl_intent.py) | intent, reply, packet, meta | 节点1 输出 |
| `PriorReport` | [`human_prior.py`](gaze_engine/human_prior.py) | (过冲/底噪/延迟 统计) | 真人化报告 |
| `PulseQualityReport` | [`pulse_quality.py`](gaze_engine/pulse_quality.py) | (Q01-Q03 检测结果) | 平庸质检报告 |

---

## 五、16 情绪预设（唯一真源）

定义在 [`control_surface.py`](gaze_engine/control_surface.py:18) `PRESETS` 字典。

三区分组:
| 组 | 情绪 | 典型 macro 特征 |
|----|------|----------------|
| 压·慑 | 施压·凝视, 冷压·决心, 威慑·一瞬, 怒视·压人, 鄙夷·冷瞥 | push↑, power↑, steady↑, flat 平顶 |
| 悲·怯 | 可怜·委屈, 要哭未哭, 崩溃·泄劲, 哀求·仰望, 惊惧·一怔, 空竭·死心 | push↓, power↓, tremble/decay |
| 媚·勾 | 魅惑·勾人, 纯甜·含情, 媚杀·一眼, 若即若离, 打量·玩味 | push 中, pulse 形, slow 收 |

---

## 六、文件修改指南

| 我要改什么 | 去哪个文件 | 搜什么 | 建议只读范围 |
|-----------|-----------|--------|-------------|
| "加 API 端点" | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) | `do_POST` 或 `do_GET` | ~20 行 handler |
| "改 3 包络" | [`envelope_compile.py`](gaze_engine/envelope_compile.py) | `def compile_envelop` | 目标函数 ~50 行 |
| "改 5 真人律" | [`human_prior.py`](gaze_engine/human_prior.py) | `def apply_human_prior` | 目标函数 ~80 行 |
| "改预设数值" | [`control_surface.py`](gaze_engine/control_surface.py:18) | `PRESETS[` | 具体预设 ~8 行 |
| "改滑杆 schema" | [`slider_schema.py`](gaze_engine/slider_schema.py) | `class SliderPacket` | 类定义 ~50 行 |
| "改系统 Prompt" | [`prompts/node1_system_prompt.txt`](prompts/node1_system_prompt.txt) | 全文 | 全文 15 行 |
| "改知识库" | [`prompts/node1_knowledge_base.txt`](prompts/node1_knowledge_base.txt) | 全文 | 全文 16 行 |
| "改 L1 禁区" | [`slider_bounds.py`](gaze_engine/slider_bounds.py) | `G1` ~ `G8` | 具体禁区 ~10 行 |
| "加新预设" | [`control_surface.py`](gaze_engine/control_surface.py:18) + [`slider_bounds.py`](gaze_engine/slider_bounds.py) | `PRESETS` + `load_rules` | 各 ~10 行 |
| "改前端 UI" | [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) | 按钮 ID / 函数名 | 具体函数 ~30 行 |
| "改人格矩阵" | [`persona_matrix.json`](gaze_engine/persona_matrix.json) | 人格 ID | 具体人格 ~15 行 |
| "启用渲染引擎" | [`affine_renderer.py`](gaze_engine/affine_renderer.py:37) | `_AFFINE_DISABLED` | 改 `True`→`False` |
| "启用音频编译" | [`audio_compiler.py`](gaze_engine/audio_compiler.py:12) | `_AUDIO_DISABLED` | 改 `True`→`False` |
| "改 6 视觉封装" | [`affine_renderer.py`](gaze_engine/affine_renderer.py) + [`human_prior.py`](gaze_engine/human_prior.py) | `dense_to_baked_sparse` / `render_control_mesh` | 各 ~50 行 |
| "改 7 输出分流" | [`export_diffusion_metronome.py`](gaze_engine/export_diffusion_metronome.py) + [`delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) | `build_metronome_text` / `run_delivery` | 各 ~50 行 |
| "改架构设计" | [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md) | 全文 | 全文 |
| "改合同索引" | [`contracts/README.md`](contracts/README.md) | 全文 | 全文 |

---

## 七、审计线索

- 12 通道定义唯一真源: [`channel_contract.py`](gaze_engine/channel_contract.py)
- 全量帧指令集规范: [`contracts/01_总纲/全量帧指令集规范.md`](contracts/01_总纲/全量帧指令集规范.md)
- 眼眉真人默认律: [`contracts/01_总纲/眼眉真人默认律.md`](contracts/01_总纲/眼眉真人默认律.md)
- 双模驱动架构: [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md)
- 交付链入口文档: [`delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) docstring
- Token 优化策略: [`docs/TOKEN_BUDGET.md`](docs/TOKEN_BUDGET.md)
- 完整文件清单: [`docs/PROJECT_FILES.md`](docs/PROJECT_FILES.md)