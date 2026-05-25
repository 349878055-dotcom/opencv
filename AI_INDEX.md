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
├── .clinerules             ← Roo Code AI 行为规则
├── .cursorrules            ← Cursor AI 行为规则
├── .env.example            ← 环境变量示例
├── .gitignore              ← Git 忽略规则
├── 一键打开能量工作台.sh     ← 启动入口
├── __init__.py              ← 项目初始化
├── asset_lib.py             ← 预设资产+客户资产路径工具
│
├── gaze_engine/_shared/assets/  ← 工程底膜视觉素材（eyelid_raw.png）
│
├── tools/                   ← 网页工作台 + HTTP 服务
│   ├── 01_工作台服务/        ← 主应用
│   │   ├── serve_workbench.py   ← HTTP 后端（API 主入口，含客户数据库 API）
│   │   ├── workbench_backend.py ← ⭐ 管线后端（+客户数据库 FastAPI 端点）
│   │   └── 能量工作台.html      ← 前端 UI（新增客户选择器面板）
│   ├── 02_前端插件/          ← JS 底层插件（工作台自动加载）
│   ├── 03_工具脚本/          ← 构建/维护脚本
│   ├── 04_缓存数据/          ← 运行时数据
│   └── 05_其他工具/          ← 独立辅助工具
│
├── gaze_engine/             ← 核心引擎 (物种分区: shared/human/cat/dog)
│   │
│   ├── _shared/                 ← ⭐ 公共区域 (物种无关)
│   │   ├── channel_contract.py      ← 通道定义 + 物种路由
│   │   ├── slider_schema.py         ← 数据类: SliderPacket + EarParams
│   │   ├── slider_bounds.py         ← L1 禁区
│   │   ├── packet_finalize.py       ← 滑杆包收口校验
│   │   ├── envelope_compile.py      ← 能量包络: SliderPacket→12×150
│   │   ├── micro_jitter.py          ← 微颤动
│   │   ├── pipeline_io.py           ← JSON 读写
│   │   ├── workbench_io.py          ← 操作台读写
│   │   ├── workbench_context.py     ← 上下文管理
│   │   ├── export_diffusion_metronome.py ← 扩散节拍表
│   │   ├── batch_presets.py         ← 五样本烘焙
│   │   ├── node1_defaults.py        ← 默认值加载
│   │   ├── llm_openai.py            ← LLM 集成 (含 CHEAP_MODEL)
│   │   ├── persona_compiler.py      ← 人格编译
│   │   ├── persona_matrix.json      ← 人格矩阵
│   │   ├── rhythm_compiler.py       ← 节奏说明书编译器（兼容 metronome 签名）
│   │   │   ├── assets/              ← 工程底膜素材（eyelid_raw.png）
│   │   │   └── customer_db.py       ← 🆕 客户资产库 CRUD（客户/项目/调整版本管理）
│   │
│   ├── human/                   ← ⭐ 人类物种
│   │   ├── control_surface.py       ← 唯一真源: 16预设 (行 18)
│   │   ├── affine_renderer.py       ← 工程底膜驱动引擎
│   │   ├── human_prior.py           ← 真人化先验
│   │   ├── pulse_quality.py         ← 平庸三检
│   │   └── pad_weights.py           ← 人类 PAD 权重表
│   │
│   ├── cat/                     ← ⭐ 猫物种
│   │   ├── __init__.py
│   │   ├── presets.py               ← 12 猫情绪预设
│   │   ├── breeds.py                ← 猫品种配置
│   │   ├── channel_adapter.py       ← EarParams→12通道映射
│   │   ├── affine_renderer.py       ← CatEyeMesh + 耳位渲染
│   │   ├── prior.py                 ← 猫扫视+三眼睑+耳耦合
│   │   ├── pulse_quality.py         ← 猫质检规则
│   │   └── pad_weights.py           ← 猫 PAD 权重表
│   │
│   ├── dog/                     ← ⭐ 狗物种
│   │   ├── __init__.py
│   │   ├── presets.py               ← 10 狗情绪预设
│   │   ├── breeds.py                ← 狗品种配置
│   │   ├── channel_adapter.py       ← EarParams→12通道（保留眉脊语义）
│   │   ├── affine_renderer.py       ← DogEyeMesh + 耳位渲染
│   │   ├── prior.py                 ← 狗扫视+耳耦合
│   │   ├── pulse_quality.py         ← 狗质检规则
│   │   ├── pad_weights.py           ← 狗 PAD 权重表
│   │   └── dog_pipeline.py          ← 狗完整管线（SliderPacket→02烘焙）
│   │
│   ├── delivery_pipeline.py     ← 主交付链 (物种路由)
│   ├── nl_intent.py             ← 意图分类 + 物种识别
│   ├── pomot/                   ← 🆕 预设 Prompt 模板合成引擎
│   │   ├── pipeline.py              ← 管线入口（round1 / round2）
│   │   ├── nl_splitter.py           ← NL 拆解器：一句话→动作+情绪
│   │   ├── emotion_router.py        ← 情绪路由：情绪词→预设名+物种
│   │   ├── registry.py              ← 预设注册表：按(species,breed,preset)加载
│   │   ├── templates.py             ← 数据类：NLSplitResult, EmotionRoute, PresetPromptTemplate
│   │   ├── composer.py              ← 第一轮合成：预设+NL→SliderPacket
│   │   ├── delta.py                 ← 第二轮微调：delta 叠加
│   │   └── assembler.py             ← 最终拼装：02_json→04_Prompt.txt→送扩散引擎
│   │
│   ├── nl_router.py             ← NL 路由
│   ├── nl_to_packet.py          ← 关键词→预设
│   ├── base_mesh_gen.py         ← 基础网格（底图生成）
│   ├── audio_compiler.py        ← ⚠️ 禁用中
│   ├── __init__.py              ← Python 包初始化
│   └── test_persona_integrity.py ← 人格完整性自检
│
├── contracts/                ← 合同规范
│   ├── 合同规范.md            ← 📐 统一合同模板（五段格式）
│   ├── 01_总纲/               ← 全局理论+工程
│   │   ├── 滑杆规范.md
│   │   ├── 节奏说明书.md
│   │   ├── 节奏说明书编译器.md
│   │   ├── 全量帧指令集规范.md
│   │   ├── 眼眉真人默认律.md
│   │   └── 眼眉指令集_全局情绪节奏主钟.md
│   ├── 02_情绪/               ← 每个情绪一个文件
│   │   └── 魅惑勾人.md
│   ├── 03_工程底膜/           ← 工程底膜（扩散引擎消费的视觉骨架）
│   │   ├── 工程底膜合同.md     ← RGB 三色分离格式协议
│   │   └── 工程底膜驱动规范.md ← affine_renderer 驱动引擎
│   ├── 04_接口/               ← 上下游对接
│   │   └── UI设计原则.md
│   ├── 05_人格化/             ← 人格风格化偏向
│   │   └── 风格化偏向.md
│   └── 06_架构/               ← 顶层设计（核心）
│       └── 流程设计.md
│
├── scripts/                  ← 工具脚本
│   ├── s01_从能量生成02.sh        ← 主出厂（CLI）
│   ├── s01_五样本烘焙02.sh        ← 批量烘焙
│   ├── s01_导出扩散节拍表.sh       ← 导出
│   ├── s01_设置OpenAI密钥.sh      ← 配置
│   └── s01_env.sh                 ← 环境变量
│
├── docs/                     ← 非 AI 直接需求
│   ├── PROJECT_FILES.md      ← 文件清单
│   ├── TOKEN_BUDGET.md       ← Token 优化指南
│   └── 开源社区对比调研.md    ← 开源社区对比调研
│
├── 预设资产/                 ← 🔵 预设资产（两大分类）
│   ├── 预设情绪包/           ← ① 基本情绪包（macro+hold_seg 基准值）
│   │   ├── human/            ← 16种 施压·凝视、可怜·委屈…
│   │   ├── cat/              ← 12种 警觉瞪视、狩猎锁定…
│   │   └── dog/              ← 10种 警觉·竖耳、委屈·幼犬眼…
│   │
│   ├── 风格包/               ← ② 风格偏移（base_offset+scale_factor）
│   │   ├── human/            ← 🆕 9个人类人格风格
│   │   │   ├── 天选者_大祭司/style.json
│   │   │   ├── 魅惑者_部落巫医/style.json
│   │   │   ├── 魅惑者_温碧霞/style.json
│   │   │   ├── 狠厉者_铁血将军/style.json
│   │   │   ├── 怯弱者_逃兵/style.json
│   │   │   ├── 悲悯者_圣徒/style.json
│   │   │   ├── 呆滞者_傀儡/style.json
│   │   │   ├── 癫狂者_疯僧/style.json
│   │   │   └── 天真者_幼童/style.json
│   │   ├── cat/              ← 🆕 4个猫品种风格
│   │   │   ├── ragdoll_cat/  布偶猫/温顺型
│   │   │   ├── siamese_cat/  暹罗猫/高冷型
│   │   │   ├── stray_cat/    田园猫/机敏型
│   │   │   └── british_cat/  英短/憨厚型
│   │   └── dog/              ← 🆕 狗品种风格
│   │       └── poodle_giant/ 巨型贵宾/优雅型
│   │
│   └── README.txt
│
└── 客户资产库/               ← 🆕 客户私有数据（临时编译结果）
    ├── 客户_C001/
    │   ├── 客户信息.json          ← 客户档案
    │   ├── 参考素材/              ← 客户照片/视频
    │   └── 项目_P001_项目名/
    │       ├── 项目配置.json      ← 关联预设、物种
    │       ├── 滑杆调整记录.json   ← 版本历史
    │       ├── 调整过程/          ← 版本快照
    │       └── 输出/              ← 管线结果
    └── ...
```

> **预设资产分层**：
>
> | 层级 | 目录 | 内容 | 作用于 | 数据来源 |
> |------|------|------|--------|---------|
> | ① 基本情绪包 | `human/` `cat/` `dog/` | macro+hold_seg，滑杆基准值 | 单情绪 | `control_surface.py` / `cat/dog presets.py` |
> | ② 品种风格包 | `style/cat/` `style/dog/` | base_offset+scale_factor，12通道偏移 | 该物种所有情绪 | `persona_matrix.json` breed_personas |
> | ③ 人格包 | `persona/` | 完整指令/参考/烘焙/脉冲第一线 | 指定演员+情绪 | 已有预烘焙数据 |
> | — | `style/human/` | ❌ 不由预设资产库提供 | — | 客户自定义 |

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
║  ✅ 已启用 (_AFFINE_DISABLED=False)              ║
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
| `_nl_to_packet()` | [`serve_workbench.py:379`](tools/01_工作台服务/serve_workbench.py:379) | POST /api/nl-to-packet | 整函数 ~50 行 |
| `_run_full_pipeline()` | [`serve_workbench.py:434`](tools/01_工作台服务/serve_workbench.py:434) | POST /api/run-pipeline | 整函数 ~70 行 |
| `_compile_pipeline_all()` | [`workbench_backend.py:173`](tools/01_工作台服务/workbench_backend.py:173) | serve_workbench.py | 整函数 ~80 行 |
| `chatgpt_customer_nl()` | [`_shared/llm_openai.py:127`](gaze_engine/_shared/llm_openai.py:127) | serve_workbench.py | 整函数 ~75 行 |
| `chatgpt_nl_to_packet()` | [`_shared/llm_openai.py:223`](gaze_engine/_shared/llm_openai.py:223) | serve_workbench.py | 整函数 ~40 行 |
| `_router_system_prompt()` | [`_shared/llm_openai.py:23`](gaze_engine/_shared/llm_openai.py:23) | node1_defaults.py | 整函数 ~15 行 |
| `finalize_packet()` | [`_shared/packet_finalize.py:161`](gaze_engine/_shared/packet_finalize.py:161) | delivery_pipeline.py | 整函数 ~30 行 |
| `channels_from_packet()` | [`_shared/envelope_compile.py:356`](gaze_engine/_shared/envelope_compile.py:356) | delivery_pipeline.py | 整函数 ~20 行 |
| `compile_envelope()` | [`_shared/envelope_compile.py:130`](gaze_engine/_shared/envelope_compile.py:130) | delivery_pipeline.py | 整函数 ~45 行 |
| `apply_human_prior()` | [`human/human_prior.py:275`](gaze_engine/human/human_prior.py:275) | delivery_pipeline.py | 整函数 ~50 行 |
| `fix_pulse_quality()` | [`human/pulse_quality.py:347`](gaze_engine/human/pulse_quality.py:347) | delivery_pipeline.py | 整函数 ~35 行 |
| `run_delivery()` | [`delivery_pipeline.py:62`](gaze_engine/delivery_pipeline.py:62) | serve_workbench.py, scripts | 整函数 ~60 行 |
| `run_delivery_from_packet()` | [`delivery_pipeline.py:122`](gaze_engine/delivery_pipeline.py:122) | serve_workbench.py | 整函数 ~20 行 |
| `run_dog_delivery()` | [`dog/dog_pipeline.py`](gaze_engine/dog/dog_pipeline.py) | delivery_pipeline.py | 整函数 ~100 行 |
| `_export_metronome()` | [`serve_workbench.py:506`](tools/01_工作台服务/serve_workbench.py:506) | POST /api/export-metronome | 整函数 ~30 行 |
| `_asset_browser()` | [`serve_workbench.py:537`](tools/01_工作台服务/serve_workbench.py:537) | GET /api/asset-browser | 整函数 ~40 行 |
| `_asset_load_baked()` | [`serve_workbench.py:578`](tools/01_工作台服务/serve_workbench.py:578) | POST /api/asset-load-baked | 整函数 ~50 行 |
| `selectEmotion()` | [`能量工作台.html:309`](tools/01_工作台服务/能量工作台.html:309) | 前端点击事件 | 整函数 ~25 行 |
| `renderNeonControlVideo()` | [`能量工作台.html:568`](tools/01_工作台服务/能量工作台.html:568) | 前端点击事件 | 整函数 ~40 行 |
| `process_customer_nl()` | [`nl_router.py:47`](gaze_engine/nl_router.py:47) | serve_workbench.py | 整函数 ~55 行 |
| `packet_from_natural_language()` | [`nl_to_packet.py:240`](gaze_engine/nl_to_packet.py:240) | serve_workbench.py | 整函数 ~25 行 |

---

## 四、关键数据类

| 类/结构 | 文件 | 字段 | 说明 |
|---------|------|------|------|
| `SliderPacket` | [`_shared/slider_schema.py`](gaze_engine/_shared/slider_schema.py) | emotion, macro, hold_seg, species | 核心数据单元 |
| `EarParams` | [`_shared/slider_schema.py`](gaze_engine/_shared/slider_schema.py) | left_angle, right_angle | 耳位参数（宠物版） |
| `MacroSliders` | [`_shared/slider_schema.py`](gaze_engine/_shared/slider_schema.py) | push, power, speed, steady, grip, outro | 6 根宏观滑杆 (0-100) |
| `HoldSegment` | [`_shared/slider_schema.py`](gaze_engine/_shared/slider_schema.py) | shape, pulse_rate, pulse_depth, swell | 盯住段形态 |
| `CustomerNLResult` | [`nl_intent.py`](gaze_engine/nl_intent.py) | intent, reply, packet, meta | 节点1 输出 |
| `PriorReport` | [`human/human_prior.py`](gaze_engine/human/human_prior.py) | (过冲/底噪/延迟 统计) | 人类真人化报告 |
| `PulseQualityReport` | [`human/pulse_quality.py`](gaze_engine/human/pulse_quality.py) | (Q01-Q03 检测结果) | 人类平庸质检报告 |
| `EyeMesh` | [`human/affine_renderer.py:90`](gaze_engine/human/affine_renderer.py:90) | 眼/眉/瞳孔 网格顶点 | 工程底膜网格类 |
| `Persona` | [`_shared/persona_compiler.py:66`](gaze_engine/_shared/persona_compiler.py:66) | 人格参数 | 人格编译数据类 |
| `Intent` | [`nl_intent.py:35`](gaze_engine/nl_intent.py:35) | intent enum | 意图分类 |

---

## 五、情绪预设体系（多物种）

| 物种 | 预设数 | 定义位置 |
|------|--------|---------|
| 人类 | 16 | [`human/control_surface.py:18`](gaze_engine/human/control_surface.py:18) `PRESETS` |
| 猫 | 12 | [`cat/presets.py`](gaze_engine/cat/presets.py) `CAT_PRESETS` |
| 狗 | 10 | [`dog/presets.py`](gaze_engine/dog/presets.py) `DOG_PRESETS` |

### 人类三区分组
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
| "改后端编译逻辑" | [`workbench_backend.py`](tools/01_工作台服务/workbench_backend.py) | `_compile_pipeline_all` | 整函数 ~80 行 |
| "改 2 包络" | [`_shared/envelope_compile.py`](gaze_engine/_shared/envelope_compile.py) | `def compile_envelop` | 目标函数 ~45 行 |
| "改 4 真人律（人类）" | [`human/human_prior.py`](gaze_engine/human/human_prior.py) | `def apply_human_prior` | 目标函数 ~50 行 |
| "改预设数值（人类）" | [`human/control_surface.py:18`](gaze_engine/human/control_surface.py:18) | `PRESETS[` | 具体预设 ~8 行 |
| "改滑杆 schema" | [`_shared/slider_schema.py`](gaze_engine/_shared/slider_schema.py) | `class SliderPacket` | 类定义 ~50 行 |
| "改猫情绪预设" | [`cat/presets.py`](gaze_engine/cat/presets.py) | `CAT_PRESETS[` | 具体预设 ~8 行 |
| "改猫品种配置" | [`cat/breeds.py`](gaze_engine/cat/breeds.py) | `BREEDS[` | 具体品种 ~15 行 |
| "改猫底膜渲染" | [`cat/affine_renderer.py`](gaze_engine/cat/affine_renderer.py) | `CatEyeMesh` | ~150 行 |
| "改狗情绪预设" | [`dog/presets.py`](gaze_engine/dog/presets.py) | `DOG_PRESETS[` | 具体预设 ~8 行 |
| "改 L1 禁区" | [`_shared/slider_bounds.py`](gaze_engine/_shared/slider_bounds.py) | `G1` ~ `G8` | 具体禁区 ~10 行 |
| "加新人类预设" | [`human/control_surface.py:18`](gaze_engine/human/control_surface.py:18) + [`_shared/slider_bounds.py`](gaze_engine/_shared/slider_bounds.py) | `PRESETS` + `load_rules` | 各 ~10 行 |
| "改前端 UI" | [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) | 按钮 ID / 函数名 | 具体函数 ~30 行 |
| "改人格矩阵" | [`_shared/persona_matrix.json`](gaze_engine/_shared/persona_matrix.json) | 人格 ID | 具体人格 ~15 行 |
| "启用/停用驱动引擎（人类）" | [`human/affine_renderer.py:85`](gaze_engine/human/affine_renderer.py:85) | `_AFFINE_DISABLED` | 当前 `False`（已启用） |
| "启用音频编译" | [`audio_compiler.py:12`](gaze_engine/audio_compiler.py:12) | `_AUDIO_DISABLED` | 改 `True`→`False` |
| "改工程底膜驱动（人类）" | [`human/affine_renderer.py`](gaze_engine/human/affine_renderer.py) | `EyeMesh.deform` / `render_frame` | ~150 行 |
| "看工程底膜合同" | [`contracts/03_工程底膜/工程底膜合同.md`](contracts/03_工程底膜/工程底膜合同.md) | 全文 | 格式协议+验收标准 |
| "看驱动引擎规范" | [`contracts/03_工程底膜/工程底膜驱动规范.md`](contracts/03_工程底膜/工程底膜驱动规范.md) | 全文 | 核心机制+注意事项 |
| "改 6 输出分流" | [`_shared/export_diffusion_metronome.py`](gaze_engine/_shared/export_diffusion_metronome.py) + [`delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) | `build_metronome_text` / `run_delivery` | 各 ~50 行 |
| "改节奏说明书编译器" | [`_shared/rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py) | `build_metronome_text` | ~50 行 |
| "改猫通道适配器" | [`cat/channel_adapter.py`](gaze_engine/cat/channel_adapter.py) | `ear_to_channel_values` | ~30 行 |
| "改狗通道适配器" | [`dog/channel_adapter.py`](gaze_engine/dog/channel_adapter.py) | `ear_to_channel_values` | ~30 行 |
| "改狗完整管线" | [`dog/dog_pipeline.py`](gaze_engine/dog/dog_pipeline.py) | `run_dog_delivery` | ~100 行 |
| "改架构设计" | [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md) | 全文 | 全文 |
| "改合同索引" | [`contracts/README.md`](contracts/README.md) | 全文 | 全文 |
| "改节奏说明书合同" | [`contracts/01_总纲/节奏说明书.md`](contracts/01_总纲/节奏说明书.md) | 全文 | 全文 |
| "改节奏说明书编译器合同" | [`contracts/01_总纲/节奏说明书编译器.md`](contracts/01_总纲/节奏说明书编译器.md) | 全文 | 全文 |
| "改全局情绪节奏主钟" | [`contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md`](contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md) | 全文 | 全文 |
| "改工程底膜合同" | [`contracts/03_工程底膜/工程底膜合同.md`](contracts/03_工程底膜/工程底膜合同.md) | 全文 | 全文 |
| "改工程底膜驱动规范" | [`contracts/03_工程底膜/工程底膜驱动规范.md`](contracts/03_工程底膜/工程底膜驱动规范.md) | 全文 | 全文 |
| "改 NL 路由" | [`nl_router.py`](gaze_engine/nl_router.py) | `process_customer_nl` | 整函数 ~55 行 |
| "改 LLM 集成" | [`_shared/llm_openai.py`](gaze_engine/_shared/llm_openai.py) | `chatgpt_customer_nl` / `chatgpt_nl_to_packet` | 各 ~50 行 |
| "改人格编译器" | [`_shared/persona_compiler.py`](gaze_engine/_shared/persona_compiler.py) | `Persona` / `compile_to_channels` | ~50 行 |
| "改客户资产库" | [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) | `def create_customer` / `def save_adjustment` | 整文件 ~230 行 |
| "改资产路径（预设+客户）" | [`asset_lib.py`](asset_lib.py) | `customer_dir` / `project_dir` | 客户路径段 ~60 行 |
| "加客户 API 端点" | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) | `_customer_create` / `_customer_list` | handler ~15 行 |
| "改资产浏览器（双栏）" | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) + [`workbench_backend.py`](tools/01_工作台服务/workbench_backend.py) | `_asset_browser` | 整函数 ~50 行 |
| "改前端客户面板" | [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) + [`static/app.js`](tools/01_工作台服务/static/app.js) | `customer-select` / `window.app` | 各 ~50 行 |

---

## 七、审计线索

- 12 通道定义唯一真源: [`_shared/channel_contract.py`](gaze_engine/_shared/channel_contract.py)
- 猫 13 通道定义: [`cat/pad_weights.py`](gaze_engine/cat/pad_weights.py)
- 猫通道适配器: [`cat/channel_adapter.py`](gaze_engine/cat/channel_adapter.py)
- 狗 13 通道定义: [`dog/pad_weights.py`](gaze_engine/dog/pad_weights.py)
- 狗通道适配器: [`dog/channel_adapter.py`](gaze_engine/dog/channel_adapter.py)
- 狗完整管线: [`dog/dog_pipeline.py`](gaze_engine/dog/dog_pipeline.py)
- 节奏说明书编译器: [`_shared/rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py)
- 扩散节拍表: [`_shared/export_diffusion_metronome.py`](gaze_engine/_shared/export_diffusion_metronome.py)
- 合同规范模板: [`contracts/合同规范.md`](contracts/合同规范.md)
- 全量帧指令集规范: [`contracts/01_总纲/全量帧指令集规范.md`](contracts/01_总纲/全量帧指令集规范.md)
- 眼眉真人默认律: [`contracts/01_总纲/眼眉真人默认律.md`](contracts/01_总纲/眼眉真人默认律.md)
- 眼眉指令集·全局情绪节奏主钟: [`contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md`](contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md)
- 节奏说明书: [`contracts/01_总纲/节奏说明书.md`](contracts/01_总纲/节奏说明书.md)
- 节奏说明书编译器合同: [`contracts/01_总纲/节奏说明书编译器.md`](contracts/01_总纲/节奏说明书编译器.md)
- 工程底膜合同: [`contracts/03_工程底膜/工程底膜合同.md`](contracts/03_工程底膜/工程底膜合同.md)
- 工程底膜驱动规范: [`contracts/03_工程底膜/工程底膜驱动规范.md`](contracts/03_工程底膜/工程底膜驱动规范.md)
- 双模驱动架构: [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md)
- 交付链入口文档: [`delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) docstring
- 后端编译入口: [`workbench_backend.py`](tools/01_工作台服务/workbench_backend.py) `_compile_pipeline_all`
- Token 优化策略: [`docs/TOKEN_BUDGET.md`](docs/TOKEN_BUDGET.md)
- 完整文件清单: [`docs/PROJECT_FILES.md`](docs/PROJECT_FILES.md)
- 🆕 客户资产库模块: [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) — CRUD + 调整版本管理
- 🆕 客户资产库根目录: [`客户资产库/`](客户资产库/) — 每个客户独立文件夹
- 🆕 客户资产库分离计划: [`plans/customer_database_separation_plan.md`](plans/customer_database_separation_plan.md)
- 🆕 资产浏览器双栏显示: [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) + [`workbench_backend.py`](tools/01_工作台服务/workbench_backend.py) `_asset_browser`
- 🆕 前端客户选择器: [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) + [`static/app.js`](tools/01_工作台服务/static/app.js)