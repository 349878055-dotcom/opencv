# AI_INDEX · jintao_node_eye 代码依赖图谱

> **核心架构（唯一宏观）**：[`合同/00_管线导读/00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md) — 目录编号 = 编译序：`01`→`08`
>
> **门户手动测试（当前）**：第②步 **点情绪按钮** → `emotion` 参数 = 情绪包 JSON 文件名（`EmotionRouter.preset_override` 直连，不经猜词表）；输入框 **只写场景**。NL-A（一句话选情绪）**未接**。
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
├── .rooignore              ← Roo Code 忽略规则（减少 Token 消耗）
├── .env / .env.example     ← 环境变量
├── .gitignore              ← Git 忽略规则
├── 一键打开创作门户.sh       ← 启动入口
├── __init__.py              ← 项目初始化 / ComfyUI 节点注册入口
├── asset_lib.py             ← 预设资产+客户资产路径工具
│
├── portal/                  ← 🌐 网页门户（HTTP 后端 + 前端页面）
│   ├── serve_workbench.py   ← 🏆 HTTP 后端：门户 API + 认证 + Pomot + 标定 + 底膜渲染 + 扩散导出
│   ├── serve_auth.py        ← 认证 API
│   ├── serve_customer.py    ← 客户/项目 CRUD API
│   ├── serve_portal.py      ← 门户创作 API
│   ├── serve_render.py      ← 渲染辅助函数
│   ├── 客户门户.html        ← 客户创作工作室（登录→项目→预设→脉冲图→Pomot→导出）
│   └── static/
│       ├── portal.js        ← 门户前端逻辑
│       └── style.css        ← 共享按钮/工具类样式
│
├── tools/                   ← 🛠 辅助工具
│   └── mediapipe_models/    ← MediaPipe 人脸检测模型
│
├── gaze_engine/             ← ⭐ 核心引擎（按管线模块分目录，见 [`00_MODULE_MAP.md`](gaze_engine/00_MODULE_MAP.md)）
│   │
│   ├── 00_MODULE_MAP.md         ← 模块分类地图
│   ├── __init__.py              ← 包初始化
│   │
│   ├── input/                   ← 01_输入与收口
│   │   ├── control_surface.py       ← 🏆 16预设唯一真源
│   │   ├── slider_schema.py         ← SliderPacket 数据类
│   │   ├── slider_bounds.py         ← L1 禁区
│   │   ├── packet_finalize.py       ← 收口校验
│   │   ├── channel_contract.py      ← 🧹 校验函数
│   │   └── node1_defaults.py        ← 默认值加载
│   │
│   ├── envelope/                ← 02_情绪与能量 → E(t)
│   │   ├── envelope_compile.py      ← ⭐ E(t) 主钟 + 通道编译
│   │   └── emotion_pad.py           ← PAD 真源表
│   │
│   ├── pad/                     ← 03_情绪坐标
│   │   └── pad_weights.py           ← PAD 权重表
│   │
│   ├── channel/                 ← 04_通道编译 → pulse
│   │   ├── micro_jitter.py          ← 微颤动引擎
│   │   └── oculomotor_prior.py      ← 眼动先验
│   │
│   ├── style/                   ← 05_风格化 → styled
│   │   ├── style_compose.py         ← pulse→styled
│   │   ├── persona_compiler.py      ← 九大人格
│   │   ├── persona_matrix.json      ← 人格矩阵
│   │   └── persona_style_catalog.json ← 风格真源
│   │
│   ├── prior_qc/                ← 06_先验与质检
│   │   ├── human_prior.py           ← 真人化先验
│   │   ├── pulse_quality_core.py    ← 平庸三检核心
│   │   └── pulse_quality.py         ← 平庸三检包装
│   │
│   ├── render/                  ← 07_工程底膜 → MP4
│   │   ├── affine_renderer.py       ← 🏆 主渲染器
│   │   ├── affine_gloss.py          ← 眼湿润高光
│   │   ├── species_template.py      ← 底膜模板 17参数
│   │   ├── species_detector.py      ← MediaPipe 检测
│   │   ├── spatial_calibration.py   ← 空间标定
│   │   ├── geometry_adapter.py      ← 几何适配
│   │   ├── base_mesh_gen.py         ← 基础网格
│   │   └── assets/                  ← 素材（eyelid_raw.png）
│   │
│   ├── delivery/                ← 08_输出与扩散
│   │   ├── delivery_pipeline.py     ← 🏆 主交付链
│   │   ├── project_archive.py       ← 项目归档
│   │   ├── rhythm_compiler.py       ← 节奏编译器
│   │   ├── rhythm_data.py           ← 节奏文案
│   │   ├── pipeline_io.py           ← JSON 读写
│   │   ├── workbench_io.py          ← 操作台读写
│   │   ├── workbench_context.py     ← 上下文管理
│   │   ├── audio_compiler.py        ← ⚠️ 禁用
│   │   └── pomot/                   ← 🏆 预设 Prompt 合成引擎
│   │       ├── pipeline.py, nl_splitter.py, emotion_router.py
│   │       ├── registry.py, templates.py, composer.py
│   │       ├── delta.py, assembler.py
│   │
│   ├── nl/                      ← NL 自然语言
│   │   ├── nl_intent.py             ← 意图分类
│   │   ├── nl_router.py             ← NL 路由
│   │   └── nl_to_packet.py          ← 关键词→预设
│   │
│   ├── _shared/                 ← 🏗 基础设施
│   │   ├── customer_db.py           ← 客户资产库 CRUD
│   │   └── llm_openai.py            ← LLM 集成
│   │
│   └── test_persona_integrity.py← 🧪 人格完整性自检
│
├── 合同/                ← 合同规范（按管线阶段编号；一种情绪/风格 = 一份独立 md）
│   ├── 合同规范.md            ← 统一合同模板（五段格式）
│   ├── README.md              ← 合同 索引 + 生成器说明
│   ├── 00_管线导读/           ← 从门户到扩散阅读地图 + 演技理论_张力三层解耦模型
│   ├── 01_输入与收口/         ← SliderPacket、L1、macro/hold_seg 专篇
│   ├── 02_情绪与能量/         ← macro→E(t)（含 委屈类别 3 变体）
│   ├── 03_情绪坐标/           ← 情绪坐标 (PAD)（含 委屈 PAD 类别导读）
│   ├── 04_通道编译/           ← pulse、02 烘焙（含 通道演算速查手册）
│   ├── 05_风格化/             ← styled（含 ecursor_style_v1 规范）
│   ├── 06_先验与质检/         ← prior + QC（含 双质量标准）
│   ├── 07_工程底膜/           ← 底膜 MP4 + MediaPipe 画布映射（含 标定/眼睑专篇）
│   └── 08_输出与扩散/         ← 扩散包、Prompt、Pomot 编辑专篇
│
└── 预设资产/             ← 🔵 预设资产（四大分类 + 情绪坐标 JSON）
    ├── 情绪包/           ← ① 情绪包（macro+hold_seg+pad）
    │   ├── 16 种情绪 JSON     ← 每种情绪一份（含怒视·压人等）
    │   ├── _groups.json       ← 情绪分组
    │   ├── _neutral.json      ← 中性默认值
    │   └── 委屈/              ← 委屈类别 3 变体（缓慢泄气、隐忍微颤、迟疑试探）
    │
    ├── 风格包/               ← ② 风格偏移（base_offset+scale_factor）
    │   ├── 天选者_大祭司/style.json
    │   ├── 魅惑者_部落巫医/style.json
    │   ├── 魅惑者_温碧霞/style.json
    │   ├── 狠厉者_铁血将军/style.json
    │   ├── 怯弱者_逃兵/style.json
    │   ├── 悲悯者_圣徒/style.json
    │   ├── 呆滞者_傀儡/style.json
    │   ├── 癫狂者_疯僧/style.json
    │   └── 天真者_幼童/style.json
    │
    ├── 底膜包/               ← ④ 物种底膜几何参数
    │   ├── species_default.json
    │   └── README.txt
    │
    ├── 情绪坐标/             ← PAD 真源 JSON（同步自合同）
    │   ├── 16 种情绪 JSON     ← 每种情绪一份
    │   ├── _index.json
    │   └── README.txt
    │
    └── README.txt
```

> **预设资产分层**：
>
> | 层级 | 目录 | 内容 | 作用于 | 数据来源 |
> |------|------|------|--------|---------|
> | ① 情绪包 | `情绪包/` | macro+hold_seg+pad，滑杆与气质基准 | 单情绪 | `input/control_surface.PRESETS` |
> | ② 人格包 | `风格包/` | base_offset+scale_factor，12通道偏移 | 指定演员+情绪 | `style/persona_style_catalog.json`（真源）→ `persona_matrix.json` + `风格包/` |
> | ③ 底膜包 | `底膜包/` | 物种底膜几何参数（species_default） | 人类物种 | → `底膜包/` |
> | 情绪坐标 JSON | `情绪坐标/` | PAD 真实值 JSON（同步自 `合同/03_情绪坐标/`） | 存档/校验 | → `情绪坐标/` |
> | — | 合同正文 | 16 情绪 + 9 人格独立 md | 审定真源 | `合同/02_情绪与能量/` + `合同/05_风格化/` |

---

## 二、数据流

### 2A. 客户创作工作室流程（新门户）

```
客户浏览器 → /portal → 客户门户.html + portal.js
     │
     ├─ POST /api/auth/register  ─→ 创建账号（名称+密码）→ customer_db.py
     ├─ POST /api/auth/login     ─→ 密码验证 → token（7天有效）
     │
     ▼  登录后
     ├─ GET /api/portal/presets   ─→ 读取 预设资产/ 下的情绪包+风格包
     ├─ POST /api/portal/pomot/round1  ─→ PomotPipeline 管线
     │     ├─ nl_splitter        ─→ 拆解: action + emotion
     │     ├─ emotion_router     ─→ 路由: 情绪词→预设名+物种
     │     ├─ composer + registry ─→ 加载预设+品种微调 → SliderPacket
     │     ├─ delivery_pipeline  ─→ 12通道×150帧 → 02_烘焙.json
     │     ├─ rhythm_compiler    ─→ 05_节拍表.txt
     │     └─ assembler          ─→ 04_Prompt.txt
     │
     ├─ POST /api/portal/pomot/round2  ─→ 第二轮微调（delta 叠加，锁定 preset）
     │
     ├─ POST /api/portal/save    ─→ 保存到 客户资产库/（01+02+05 归档）
     │
     └─ POST /api/portal/export  ─→ 最终payload = { video: 03_工程底模.mp4, prompt: 04_Prompt.txt,
                                    wan_positive_clip, wan_negative_clip }
                                    → 送 Wan 扩散引擎

门户情绪按钮 → 资产（2026-05）：
  GET /api/portal/presets 列出 id = 情绪包 JSON 文件名
  POST /api/portal/pomot/round1 传 emotion=S.activeEmotion
    → EmotionRouter.route(preset_override=emotion) 命中 预设资产/情绪包 则直接用该 preset
    → PomotRegistry
```

### 2B. 核心管线数据流（引擎内部，门户经 Pomot 调用）

```
API: POST /api/run-pipeline
    │
    ├─ (可选) 先 POST /api/nl-to-packet  → 自然语言 → SliderPacket
    │
    ▼
┌─ 1. finalize_packet() ──────────────────────────────┐
│  input/packet_finalize.finalize_packet(pkt)          │
│    → 本戏数值盒检查 → G1-G8 硬禁区 → 弹性弹回        │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 2. build_energy_envelope() ────────────────────────┐
│  envelope/envelope_compile.build_energy_envelope()    │
│    → E(t) 能量曲线 (6 macro → 4 段: 起/蓄/盯/收)     │
│    纯数学层, 所有物种共用                             │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 3. channels_from_packet() ─────────────────────────┐
│  envelope/envelope_compile.channels_from_packet()     │
│    → E(t) + PAD投影 → 12 通道 × 150 帧              │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 4. apply_human_prior() ────────────────────────────┐
│  prior_qc/human_prior.apply_human_prior(dense)       │
│    → 二阶欠阻尼扫视(过冲) + 盯住微漂微颤 + 眉眼延迟  │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 5. fix_pulse_quality() ────────────────────────────┐
│  prior_qc/pulse_quality.fix_pulse_quality(dense)     │
│    → Q01 能量不足抬升 + Q02 杂乱平滑 + Q03 眉峰延后  │
└──────────────────────────────────────────────────────┘
    │
    ▼
╔═ 6. 视觉封装层 (The Articulator) ══════════════════╗
║  [dense_to_baked_sparse()] ───────────────────────║
║  prior_qc/human_prior.dense_to_baked_sparse()     ║
║  → 02_烘焙_真人律.json (12通道逐帧关键帧)         ║
║                                                    ║
║  [工程底膜 (Asset for Diffusion)] ──────────────║
║  render/affine_renderer (RGB三色分离)              ║
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
║  delivery/rhythm_compiler.build_metronome_text()    ║
║  → 扩散节拍表 (文本辅助 · 给 Wan 的脉冲语义)        ║
║                                                     ║
║  底层控制点（12 通道数据）永远不变                    ║
╚══════════════════════════════════════════════════════╝
```

---

## 三、核心入口函数（含精确行号）

| 函数 | 文件:行号 | 被谁调用 | 建议读取范围 |
|------|----------|---------|-------------|
| `_nl_to_packet()` | [`serve_workbench.py:438`](portal/serve_workbench.py:438) | POST /api/nl-to-packet | 整函数 ~50 行 |
| `_run_full_pipeline()` | [`serve_workbench.py:493`](portal/serve_workbench.py:493) | POST /api/run-pipeline | 整函数 ~70 行 |
| `chatgpt_customer_nl()` | [`_shared/llm_openai.py:127`](gaze_engine/_shared/llm_openai.py:127) | serve_workbench.py | 整函数 ~75 行 |
| `chatgpt_nl_to_packet()` | [`_shared/llm_openai.py:223`](gaze_engine/_shared/llm_openai.py:223) | serve_workbench.py | 整函数 ~40 行 |
| `_router_system_prompt()` | [`_shared/llm_openai.py:23`](gaze_engine/_shared/llm_openai.py:23) | node1_defaults.py | 整函数 ~15 行 |
| `finalize_packet()` | [`input/packet_finalize.py:161`](gaze_engine/input/packet_finalize.py:161) | delivery_pipeline.py | 整函数 ~30 行 |
| `channels_from_packet()` | [`envelope/envelope_compile.py:210`](gaze_engine/envelope/envelope_compile.py:210) | delivery_pipeline.py | 整函数 ~30 行 |
| `build_energy_envelope()` | [`envelope/envelope_compile.py:129`](gaze_engine/envelope/envelope_compile.py:129) | channels_from_packet | 整函数 ~45 行 |
| `apply_human_prior()` | [`prior_qc/human_prior.py:275`](gaze_engine/prior_qc/human_prior.py:275) | delivery_pipeline.py | 整函数 ~50 行 |
| `dense_to_baked_sparse()` | [`prior_qc/human_prior.py:329`](gaze_engine/prior_qc/human_prior.py:329) | delivery_pipeline.py | 整函数 ~40 行 |
| `fix_pulse_quality()` | [`prior_qc/pulse_quality.py:347`](gaze_engine/prior_qc/pulse_quality.py:347) | delivery_pipeline.py | 整函数 ~35 行 |
| `run_delivery()` | [`delivery/delivery_pipeline.py:62`](gaze_engine/delivery/delivery_pipeline.py:62) | serve_workbench.py | 整函数 ~60 行 |
| `run_delivery_from_packet()` | [`delivery/delivery_pipeline.py:123`](gaze_engine/delivery/delivery_pipeline.py:123) | serve_workbench.py | 整函数 ~20 行 |
| `_export_metronome()` | [`serve_workbench.py:651`](portal/serve_workbench.py:651) | POST /api/export-metronome | 整函数 ~30 行 |
| `_asset_browser()` | [`serve_workbench.py:682`](portal/serve_workbench.py:682) | GET /api/asset-browser | 整函数 ~80 行 |
| `_asset_load_baked()` | [`serve_workbench.py:771`](portal/serve_workbench.py:771) | POST /api/asset-load-baked | 整函数 ~50 行 |
| `_customer_upload_photo()` | [`serve_workbench.py:1097`](portal/serve_workbench.py:1097) | POST /api/customer/upload-photo | 整函数 ~80 行 |
| `_customer_template_estimate()` | [`serve_workbench.py:1077`](portal/serve_workbench.py:1077) | POST /api/customer/template-estimate | 整函数 ~20 行 |
| `auto_detect_for_customer()` | [`render/species_detector.py:587`](gaze_engine/render/species_detector.py:587) | serve_workbench.py | 整函数 ~80 行 |
| `process_customer_nl()` | [`nl/nl_router.py:47`](gaze_engine/nl/nl_router.py:47) | serve_workbench.py | 整函数 ~55 行 |
| `packet_from_natural_language()` | [`nl/nl_to_packet.py:240`](gaze_engine/nl/nl_to_packet.py:240) | serve_workbench.py | 整函数 ~25 行 |
| `compile_to_channels()` (人格→通道) | [`style/persona_compiler.py:152`](gaze_engine/style/persona_compiler.py:152) | 人格编译管线 | 整函数 ~60 行 |
| `template_to_renderer_constants()` | [`render/species_template.py:272`](gaze_engine/render/species_template.py:272) | affine_renderer | 整函数 ~80 行 |
| `auth_register()` | [`serve_workbench.py:784`](portal/serve_workbench.py:784) | POST /api/auth/register | 整函数 ~20 行 |
| `auth_login()` | [`serve_workbench.py:806`](portal/serve_workbench.py:806) | POST /api/auth/login | 整函数 ~25 行 |
| `auth_verify()` | [`serve_workbench.py:831`](portal/serve_workbench.py:831) | POST /api/auth/verify | 整函数 ~15 行 |
| `portal_presets()` | [`serve_workbench.py:851`](portal/serve_workbench.py:851) | GET /api/portal/presets | 整函数 ~50 行 |
| `portal_pomot_round1()` | [`serve_workbench.py:900`](portal/serve_workbench.py:900) | POST /api/portal/pomot/round1 | 整函数 ~25 行 |
| `portal_pomot_round2()` | [`serve_workbench.py:924`](portal/serve_workbench.py:924) | POST /api/portal/pomot/round2 | 整函数 ~20 行（**不传** `emotion_override`，改按钮情绪需重跑 round1） |
| `EmotionRouter.route()` | [`delivery/pomot/emotion_router.py`](gaze_engine/delivery/pomot/emotion_router.py) | `preset_override` | 情绪包 id 存在则跳过 NL 词表 |
| `portal_save()` | [`serve_workbench.py:944`](portal/serve_workbench.py:944) | POST /api/portal/save | 整函数 ~55 行 |
| `portal_export()` | [`serve_workbench.py`](portal/serve_workbench.py) | POST /api/portal/export | handler ~40 行 |
| `DiffusionPromptAssembler.assemble()` | [`delivery/pomot/assembler.py`](gaze_engine/delivery/pomot/assembler.py) | delivery / portal / export | ~80 行 |
| `DiffusionPromptAssembler.split_for_wan()` | [`delivery/pomot/assembler.py`](gaze_engine/delivery/pomot/assembler.py) | portal export / 验收脚本 | ~35 行 |
| `save_project_profile()` | [`delivery/project_archive.py:38`](gaze_engine/delivery/project_archive.py:38) | portal save | 整函数 ~90 行 |
| `build_diffusion_bundle()` | [`delivery/project_archive.py:151`](gaze_engine/delivery/project_archive.py:151) | portal export | 整函数 ~60 行 |
| `apply_style_offset()` | [`style/style_compose.py:22`](gaze_engine/style/style_compose.py:22) | envelope_compile | 整函数 ~25 行 |
| `resolve_pad()` | [`envelope/emotion_pad.py`](gaze_engine/envelope/emotion_pad.py) | delivery_pipeline | ~20 行 |
| `compute_spatial_calibration()` | [`render/spatial_calibration.py:136`](gaze_engine/render/spatial_calibration.py:136) | serve_workbench.py | 整函数 ~80 行 |
| `standard_model_anchors()` | [`render/spatial_calibration.py:98`](gaze_engine/render/spatial_calibration.py:98) | compute_spatial_calibration | 整函数 ~30 行 |
| `load_project_spatial_calibration()` | [`render/spatial_calibration.py:206`](gaze_engine/render/spatial_calibration.py:206) | serve_workbench.py | 整函数 ~20 行 |
| `adapt_geometry()` | [`render/geometry_adapter.py`](gaze_engine/render/geometry_adapter.py) | serve_workbench.py | 整函数 ~60 行 |
| `draw_eye_gloss()` | [`render/affine_gloss.py`](gaze_engine/render/affine_gloss.py) | affine_renderer | 整函数 ~30 行 |
| `apply_oculomotor_prior()` | [`channel/oculomotor_prior.py`](gaze_engine/channel/oculomotor_prior.py) | delivery_pipeline | 整函数 ~80 行 |
| `fix_pulse_quality_core()` | [`prior_qc/pulse_quality_core.py`](gaze_engine/prior_qc/pulse_quality_core.py) | delivery_pipeline | 整函数 ~80 行 |
| `apply_micro_jitter()` | [`channel/micro_jitter.py`](gaze_engine/channel/micro_jitter.py) | delivery_pipeline | 整函数 ~40 行 |

---

## 四、关键数据类

| 类/结构 | 文件 | 字段 | 说明 |
|---------|------|------|------|
| `SliderPacket` | [`input/slider_schema.py:84`](gaze_engine/input/slider_schema.py:84) | emotion, macro, hold_seg, species, **pad** | 核心数据单元 |
| `MacroSliders` | [`input/slider_schema.py:25`](gaze_engine/input/slider_schema.py:25) | push, power, speed, steady, grip, outro | 6 根宏观滑杆 (0-100) |
| `HoldSegment` | [`input/slider_schema.py:39`](gaze_engine/input/slider_schema.py:39) | shape, pulse_rate, pulse_depth, swell | 盯住段形态 |
| `EarParams` | [`input/slider_schema.py:57`](gaze_engine/input/slider_schema.py:57) | left_angle, right_angle | 耳位参数 |
| `CustomerNLResult` | [`nl/nl_intent.py:56`](gaze_engine/nl/nl_intent.py:56) | intent, reply, packet, meta | 节点1 输出 |
| `PriorReport` | [`prior_qc/human_prior.py:27`](gaze_engine/prior_qc/human_prior.py:27) | (过冲/底噪/延迟 统计) | 人类真人化报告 |
| `PulseQualityReport` | [`prior_qc/pulse_quality.py:64`](gaze_engine/prior_qc/pulse_quality.py:64) | (Q01-Q03 检测结果) | 人类平庸质检报告 |
| `PulseQualityMetrics` | [`prior_qc/pulse_quality.py:37`](gaze_engine/prior_qc/pulse_quality.py:37) | 各项质检指标 | 质检度量 |
| `EyeMesh` | [`render/affine_renderer.py:91`](gaze_engine/render/affine_renderer.py:91) | 眼/眉/瞳孔 网格顶点 | 人类工程底膜网格类 |
| `Persona` | [`style/persona_compiler.py:65`](gaze_engine/style/persona_compiler.py:65) | 人格参数 | 人格编译数据类 |
| `SpeciesTemplate` | [`render/species_template.py:76`](gaze_engine/render/species_template.py:76) | 17个几何参数 | 物种底膜模板 |
| `PomotPipeline` | [`delivery/pomot/pipeline.py:16`](gaze_engine/delivery/pomot/pipeline.py:16) | 管线控制 | Prompt 模板合成管线 |
| `FinalizeReport` | [`input/packet_finalize.py:16`](gaze_engine/input/packet_finalize.py:16) | 收口报告 | 滑杆收口校验报告 |
| `NLSplitResult` | [`delivery/pomot/templates.py:11`](gaze_engine/delivery/pomot/templates.py:11) | action, emotion, species_hint, breed_hint | NL 拆解结果 |
| `EmotionRoute` | [`delivery/pomot/templates.py:33`](gaze_engine/delivery/pomot/templates.py:33) | species, preset_name, breed | 情绪路由结果 |
| `PresetPromptTemplate` | [`delivery/pomot/templates.py:49`](gaze_engine/delivery/pomot/templates.py:49) | emotion_id, species, slider_packet | 预设模板数据类 |
| `GeometryAdaptResult` | [`render/geometry_adapter.py`](gaze_engine/render/geometry_adapter.py) | scale, affine_matrix, adjustments | 几何适配结果 |
| `SpatialCalibrationResult` | [`render/spatial_calibration.py`](gaze_engine/render/spatial_calibration.py) | scale, affine_matrix | 空间标定结果 |
| `SpatialCalibration` | [`render/spatial_calibration.py:40`](gaze_engine/render/spatial_calibration.py:40) | — | 空间标定数据类 |
| `OculomotorReport` | [`channel/oculomotor_prior.py`](gaze_engine/channel/oculomotor_prior.py) | 扫视/盯住/耦合统计 | 眼动先验报告 |
| `PulseQualityCoreReport` | [`prior_qc/pulse_quality_core.py`](gaze_engine/prior_qc/pulse_quality_core.py) | Q01-Q03 检测结果 | 平庸三检核心报告 |

---

## 五、情绪预设体系

| 物种 | 预设数 | 定义位置 |
|------|--------|---------|
| 人类 | 16 | [`input/control_surface.py:18`](gaze_engine/input/control_surface.py:18) `PRESETS` |
| 委屈 3 变体 | 3 | [`预设资产/情绪包/委屈/`](预设资产/情绪包/委屈/)（`变体1_缓慢泄气.json` / `变体2_隐忍微颤.json` / `变体3_迟疑试探.json`） |

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
| "加 API 端点" | [`serve_workbench.py`](portal/serve_workbench.py) | `do_POST` 或 `do_GET` | ~20 行 handler |
| "改能量包络数学" | [`envelope/envelope_compile.py`](gaze_engine/envelope/envelope_compile.py) | `def build_energy_envelope` | ~45 行 |
| "改人类通道编译（含 eyebrow 滞后）" | [`envelope/envelope_compile.py`](gaze_engine/envelope/envelope_compile.py) | `def channels_from_packet` | ~80 行 |
| "改 4 真人律（人类）" | [`prior_qc/human_prior.py`](gaze_engine/prior_qc/human_prior.py) | `def apply_human_prior` | 目标函数 ~50 行 |
| "改预设数值（人类）" | [`input/control_surface.py:18`](gaze_engine/input/control_surface.py:18) | `PRESETS[` | 具体预设 ~8 行 |
| "改滑杆 schema" | [`input/slider_schema.py`](gaze_engine/input/slider_schema.py) | `class SliderPacket` | 类定义 ~90 行 |
| "改 L1 禁区" | [`input/slider_bounds.py`](gaze_engine/input/slider_bounds.py) | `G1` ~ `G8` | 具体禁区 ~10 行 |
| "加新人类预设" | [`input/control_surface.py:18`](gaze_engine/input/control_surface.py:18) + [`input/slider_bounds.py`](gaze_engine/input/slider_bounds.py) | `PRESETS` + `load_rules` | 各 ~10 行 |
| "改门户前端 UI" | [`portal/客户门户.html`](portal/客户门户.html) + [`portal/static/portal.js`](portal/static/portal.js) | 步骤面板 / `paintEnergyPulse` | 目标区块 ~50 行 |
| "改人格矩阵" | [`style/persona_matrix.json`](gaze_engine/style/persona_matrix.json) | 人格 ID | 具体人格 ~15 行 |
| "启用/停用驱动引擎（人类）" | [`render/affine_renderer.py:86`](gaze_engine/render/affine_renderer.py:86) | `_AFFINE_DISABLED` | 当前 `False`（已启用） |
| "启用音频编译" | [`delivery/audio_compiler.py:12`](gaze_engine/delivery/audio_compiler.py:12) | `_AUDIO_DISABLED` | 改 `True`→`False` |
| "改工程底膜驱动（人类）" | [`render/affine_renderer.py`](gaze_engine/render/affine_renderer.py) | `EyeMesh.deform` / `render_frame` | ~340 行 |
| "看工程底膜合同" | [`合同/07_工程底膜/工程底膜合同.md`](合同/07_工程底膜/工程底膜合同.md) | 全文 | 格式协议+验收标准 |
| "看驱动引擎规范" | [`合同/07_工程底膜/工程底膜驱动规范.md`](合同/07_工程底膜/工程底膜驱动规范.md) | 全文 | 核心机制+注意事项 |
| "改 6 输出分流" | [`delivery/rhythm_compiler.py`](gaze_engine/delivery/rhythm_compiler.py) | `build_metronome_text` | ~100 行 |
| "改节奏说明书编译器" | [`delivery/rhythm_compiler.py`](gaze_engine/delivery/rhythm_compiler.py) | `build_metronome_text` | ~100 行 |
| "改宏观架构/编译顺序" | [`合同/00_管线导读/00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md) | 全文 | 全文 |
| "改某一情绪合同（人类）" | [`合同/02_情绪与能量/{情绪名}.md`](合同/02_情绪与能量/) | 五段格式正文 | 全文 |
| "改某一风格/人格合同（人类）" | [`合同/05_风格化/{id}.md`](合同/05_风格化/) | 五段格式正文 | 全文 |
| "改项目归档/导出包" | [`delivery/project_archive.py`](gaze_engine/delivery/project_archive.py) | `save_project_profile` / `build_diffusion_bundle` | ~120 行 |
| "改 S5 风格合成" | [`style/style_compose.py`](gaze_engine/style/style_compose.py) | `apply_style_offset` / `load_style_from_asset` | ~75 行 |
| "改合同索引" | [`合同/README.md`](合同/README.md) | 全文 | 全文 |
| "改节奏说明书合同" | [`合同/08_输出与扩散/节奏说明书.md`](合同/08_输出与扩散/节奏说明书.md) | 全文 | 全文 |
| "改全局情绪节奏主钟" | [`合同/04_通道编译/01_十二通道与全量帧格式.md`](合同/04_通道编译/01_十二通道与全量帧格式.md) | 全文 | 全文 |
| "改工程底膜合同" | [`合同/07_工程底膜/工程底膜合同.md`](合同/07_工程底膜/工程底膜合同.md) | 全文 | 全文 |
| "改工程底膜驱动规范" | [`合同/07_工程底膜/工程底膜驱动规范.md`](合同/07_工程底膜/工程底膜驱动规范.md) | 全文 | 全文 |
| "改 NL 路由" | [`nl/nl_router.py`](gaze_engine/nl/nl_router.py) | `process_customer_nl` | 整函数 ~55 行 |
| "改 LLM 集成" | [`_shared/llm_openai.py`](gaze_engine/_shared/llm_openai.py) | `chatgpt_customer_nl` / `chatgpt_nl_to_packet` | 各 ~50 行 |
| "改人格编译器" | [`style/persona_compiler.py`](gaze_engine/style/persona_compiler.py) | `Persona` / `compile_to_channels` | ~80 行 |
| "改物种底膜模板" | [`render/species_template.py`](gaze_engine/render/species_template.py) | `SpeciesTemplate` / `template_to_renderer_constants` | ~260 行 |
| "改自动化检测" | [`render/species_detector.py`](gaze_engine/render/species_detector.py) | `auto_detect_for_customer` | ~140 行 |
| "改客户资产库" | [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) | `create_customer` / `save_adjustment` | 整文件 ~542 行 |
| "改资产路径（预设+客户）" | [`asset_lib.py`](asset_lib.py) | `customer_dir` / `project_dir` | 客户路径段 ~60 行 |
| "加客户 API 端点" | [`serve_workbench.py`](portal/serve_workbench.py) | `_customer_create` / `_customer_list` | handler ~15 行 |
| "改资产浏览器（双栏）" | [`serve_workbench.py`](portal/serve_workbench.py) | `_asset_browser` | 整函数 ~80 行 |
| "改 04 Prompt 拼装" | [`delivery/pomot/assembler.py`](gaze_engine/delivery/pomot/assembler.py) | `_build_positive_prompt` / `split_for_wan` | ~120 行 |
| "改 L2 情绪视觉词（人类）" | [`delivery/rhythm_data.py`](gaze_engine/delivery/rhythm_data.py) | `EMOTION_VISUAL_PROMPTS` | 全文 |
| "改 PAD 真源" | [`envelope/emotion_pad.py`](gaze_engine/envelope/emotion_pad.py) | `EMOTION_PAD` / `resolve_pad` | 全文 |
| "改 Prompt 模板合成" | [`delivery/pomot/`](gaze_engine/delivery/pomot/) | `PomotPipeline` / `composer` | 各文件 ~50 行 |
| "改客户密码认证" | [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) | `verify_customer_password` / `create_auth_token` | 各函数 ~15 行 |
| "改客户创作门户 UI" | [`portal/客户门户.html`](portal/客户门户.html) + [`portal/static/portal.js`](portal/static/portal.js) | 按钮 ID / 函数名 | 各文件 ~60 行 |
| "加认证 API" | [`serve_workbench.py`](portal/serve_workbench.py) | `auth_register` / `auth_login` / `portal_pomot_round1` | handler ~20 行 |
| "改人类节奏说明书文案" | [`delivery/rhythm_data.py`](gaze_engine/delivery/rhythm_data.py) | `EMOTION_VISUAL_PROMPTS` | 全文 |
| "改门户情绪按钮→JSON" | [`delivery/pomot/emotion_router.py`](gaze_engine/delivery/pomot/emotion_router.py) + [`delivery/pomot/pipeline.py`](gaze_engine/delivery/pomot/pipeline.py) + [`portal/static/portal.js`](portal/static/portal.js) | `preset_override` / `emotion_override` | 各 ~30 行 |
| "改情绪包滑杆真源" | [`预设资产/情绪包/`](预设资产/情绪包/) + [`asset_lib.py`](asset_lib.py) | `load_emotion_slider_packet` | JSON + loader |
| "改空间标定" | [`render/spatial_calibration.py`](gaze_engine/render/spatial_calibration.py) | `compute_spatial_calibration` | 整函数 ~80 行 |
| "改几何适配" | [`render/geometry_adapter.py`](gaze_engine/render/geometry_adapter.py) | `adapt_geometry` | 整函数 ~60 行 |
| "改眼湿润高光" | [`render/affine_gloss.py`](gaze_engine/render/affine_gloss.py) | `draw_eye_gloss` | 整函数 ~30 行 |
| "改眼动先验核心" | [`channel/oculomotor_prior.py`](gaze_engine/channel/oculomotor_prior.py) | `apply_oculomotor_prior` | 整函数 ~80 行 |
| "改平庸三检核心" | [`prior_qc/pulse_quality_core.py`](gaze_engine/prior_qc/pulse_quality_core.py) | `fix_pulse_quality_core` | 整函数 ~80 行 |
| "改微颤动引擎" | [`channel/micro_jitter.py`](gaze_engine/channel/micro_jitter.py) | `apply_micro_jitter` | 整函数 ~40 行 |
| "看演技理论" | [`合同/00_管线导读/演技理论_张力三层解耦模型.md`](合同/00_管线导读/演技理论_张力三层解耦模型.md) | 全文 | 全文 |

---

## 七、审计线索

- 12 通道定义（人类）: [`envelope/envelope_compile.py`](gaze_engine/envelope/envelope_compile.py) `HUMAN_CHANNELS`
- 通道校验函数（共4个）: [`input/channel_contract.py`](gaze_engine/input/channel_contract.py) — 纯函数，无全局数据
- 空间标定入口: [`render/spatial_calibration.py:136`](gaze_engine/render/spatial_calibration.py:136) `compute_spatial_calibration()`
- 演技理论: [`合同/00_管线导读/演技理论_张力三层解耦模型.md`](合同/00_管线导读/演技理论_张力三层解耦模型.md) — Fext/Fint → 戏剧张力 → E(t) 图形诊断
- 委屈 3 变体: [`预设资产/情绪包/委屈/`](预设资产/情绪包/委屈/) — `变体1_缓慢泄气.json` / `变体2_隐忍微颤.json` / `变体3_迟疑试探.json`
- 底膜包: [`预设资产/底膜包/`](预设资产/底膜包/) — 物种底膜几何参数（human）
- 情绪坐标 JSON: [`预设资产/情绪坐标/`](预设资产/情绪坐标/) — PAD 真源 JSON（human）
- 人类节奏说明书文案: [`delivery/rhythm_data.py`](gaze_engine/delivery/rhythm_data.py)
- 节奏说明书编译器: [`delivery/rhythm_compiler.py`](gaze_engine/delivery/rhythm_compiler.py)
- 合同管线导读: [`合同/00_管线导读/00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md)
- 合同物种索引: [`合同/README.md`](合同/README.md) — 02_情绪与能量 16 份 + 03_情绪坐标 16 份 + 05_风格化 9 份
- PAD 专题目录: [`合同/03_情绪坐标/00_情绪坐标导读.md`](合同/03_情绪坐标/00_情绪坐标导读.md)
- 人类情绪索引: [`合同/02_情绪与能量/人类情绪与能量曲线.md`](合同/02_情绪与能量/人类情绪与能量曲线.md)
- 人格/品种与 E(t) 边界: [`合同/03_情绪坐标/04_四层表演栈与style边界.md`](合同/03_情绪坐标/04_四层表演栈与style边界.md)
- S5 风格合成: [`style/style_compose.py`](gaze_engine/style/style_compose.py) — `apply_style_offset()` 不改 E(t)
- 项目归档: [`delivery/project_archive.py`](gaze_engine/delivery/project_archive.py) — `save_project_profile()` / `build_diffusion_bundle()`
- 合同规范模板: [`合同/合同规范.md`](合同/合同规范.md)
- 十二通道与 02 格式: [`合同/04_通道编译/01_十二通道与全量帧格式.md`](合同/04_通道编译/01_十二通道与全量帧格式.md)
- 人眼眉先验与三检: [`合同/06_先验与质检/眼眉先验与平庸三检.md`](合同/06_先验与质检/眼眉先验与平庸三检.md)
- MediaPipe 画布映射: [`合同/07_工程底膜/MediaPipe到OpenCV画布映射_零默认值管线.md`](合同/07_工程底膜/MediaPipe到OpenCV画布映射_零默认值管线.md)
- 节奏说明书: [`合同/08_输出与扩散/节奏说明书.md`](合同/08_输出与扩散/节奏说明书.md)
- 节奏说明书编译器合同: [`合同/08_输出与扩散/节奏说明书编译器.md`](合同/08_输出与扩散/节奏说明书编译器.md)
- 工程底膜合同: [`合同/07_工程底膜/工程底膜合同.md`](合同/07_工程底膜/工程底膜合同.md)
- 工程底膜驱动规范: [`合同/07_工程底膜/工程底膜驱动规范.md`](合同/07_工程底膜/工程底膜驱动规范.md)
- 宏观架构（唯一）: [`合同/00_管线导读/00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md)
- 5 秒气质精品成片: [`合同/00_管线导读/00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md)
- Pomot 编辑专篇: [`合同/08_输出与扩散/Pomot编辑专篇.md`](合同/08_输出与扩散/Pomot编辑专篇.md)
- 扩散输出流程: [`合同/08_输出与扩散/扩散输出流程专篇.md`](合同/08_输出与扩散/扩散输出流程专篇.md)
- PAD 真源: [`envelope/emotion_pad.py`](gaze_engine/envelope/emotion_pad.py)
- 交付链入口文档: [`delivery/delivery_pipeline.py`](gaze_engine/delivery/delivery_pipeline.py) docstring
- 客户密码认证: [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) `verify_customer_password()` / `create_auth_token()` — PBKDF2-SHA256 密码哈希 + HMAC token
- 客户创作工作室 UI: [`portal/客户门户.html`](portal/客户门户.html) + [`portal/static/portal.js`](portal/static/portal.js) — 登录→标定→Pomot→04+Wan→导出
- 门户 API 端点: [`portal/serve_workbench.py`](portal/serve_workbench.py) — `POST /api/auth/register|login|verify` + `GET /api/portal/presets` + `POST /api/portal/pomot/round1|round2` + `POST /api/portal/save|export`
- 客户资产库模块: [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) — CRUD + 调整版本管理
- 客户资产库根目录: [`客户资产库/`](客户资产库/) — 每个客户独立文件夹
- 自动化底膜检测: [`render/species_detector.py`](gaze_engine/render/species_detector.py) — MediaPipe + OpenCV
- 物种底膜模板: [`render/species_template.py`](gaze_engine/render/species_template.py) — 17参数模板
- 人格编译器: [`style/persona_compiler.py`](gaze_engine/style/persona_compiler.py) — 九大人格编译
- Pomot 合成引擎: [`delivery/pomot/`](gaze_engine/delivery/pomot/) — pipeline / nl_splitter / emotion_router / composer / delta / assembler
- 物种专属通道编译: [`envelope/envelope_compile.py`](gaze_engine/envelope/envelope_compile.py) — 人类通道编译
- 空间标定: [`render/spatial_calibration.py`](gaze_engine/render/spatial_calibration.py) — 标准底膜锚点 → 客户参考图像素对齐
- 几何适配: [`render/geometry_adapter.py`](gaze_engine/render/geometry_adapter.py) — 照片/锚点 → 模板参数 + Delta 微调
- 眼湿润高光: [`render/affine_gloss.py`](gaze_engine/render/affine_gloss.py) — eye_gloss 通道 → OpenCV B 通道
- 眼动先验核心: [`channel/oculomotor_prior.py`](gaze_engine/channel/oculomotor_prior.py) — 扫视动力学 + 盯住活劲 + 通道耦合
- 平庸三检核心: [`prior_qc/pulse_quality_core.py`](gaze_engine/prior_qc/pulse_quality_core.py) — Q01-Q03
- 微颤动引擎: [`channel/micro_jitter.py`](gaze_engine/channel/micro_jitter.py) — 微振动与颤动
- 人格风格真源: [`style/persona_style_catalog.json`](gaze_engine/style/persona_style_catalog.json) — 同步到 persona_matrix.json + 预设资产

---

## 八、合同目录结构

```
合同/
├── 合同规范.md              ← 统一合同模板（五段格式）
├── README.md               ← 合同 索引 + 生成器说明
├── 00_管线导读/
│   ├── 00_从门户到扩散_管线总览.md   ← 宏观架构（唯一）
│   └── 演技理论_张力三层解耦模型.md   ← Fext/Fint 演技理论
├── 01_输入与收口/
│   ├── 滑杆规范.md                   ← SliderPacket、L1 规范
│   └── macro与hold_seg专篇.md        ← macro/hold_seg 专篇
├── 02_情绪与能量/
│   ├── 人类情绪与能量曲线.md          ← 人类情绪索引
│   ├── 委屈/                         ← 委屈类别 3 变体
│   │   ├── 00_类别导读.md
│   │   ├── 变体1_缓慢泄气.md
│   │   ├── 变体2_隐忍微颤.md
│   │   └── 变体3_迟疑试探.md
│   └── 16 份情绪独立 md              ← 每种情绪一份
├── 03_情绪坐标/
│   ├── 00_PAD情绪坐标.md                  ← 主文档：PAD 理论 + 公式 + 边界
│   ├── 01_三层分工与编译链专篇.md         ← 概念专篇：macro/PAD/style 三层 + S4 编译链
│   ├── 情绪坐标定位索引.md                ← 索引
│   ├── 委屈/                              ← 委屈 PAD
│   │   ├── 00_PAD类别导读.md
│   │   └── 人.md
│   └── 16 份情绪 PAD md                  ← 每种情绪一份
├── 04_通道编译/
│   ├── 00_通道编译.md                     ← 主文档：E(t)×PAD→通道，人类全量
│   └── 01_12通道分流与RGB渲染专篇.md       ← RGB 三色分离与渲染顺序
├── 05_风格化/
│   ├── 00_风格化导读.md
│   ├── 情绪与人格耦合专篇.md
│   ├── 人类人格风格偏向.md
│   ├── ecursor_style_v1规范.md
│   └── 9 份人格独立 md               ← 每种人格一份
├── 06_先验与质检/
│   ├── 00_先验与质检.md                     ← 主文档：人类 S6+S7 先验与质检全量
│   └── 01_双质量标准专篇.md                   ← 理论：不要假·不要平庸 双标准
├── 07_工程底膜/
│   ├── 00_工程底膜.md                           ← 主文档：MediaPipe→空间校准→OpenCV 渲染全链
│   └── 01_空间校准与仿射映射专篇.md               ← 概念专篇：仿射变换数学与空间校准
└── 08_输出与扩散/
    ├── 节奏说明书.md
    ├── 节奏说明书编译器.md
    ├── 扩散输出流程专篇.md
    └── Pomot编辑专篇.md
```

**合同目录（与代码对齐）**：`04_通道编译`、`06_先验与质检`、`07_工程底膜`；已平铺子目录、删除冗余 README。
