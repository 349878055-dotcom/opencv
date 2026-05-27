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
├── .env / .env.example     ← 环境变量
├── .gitignore              ← Git 忽略规则
├── yolov8n-cls.pt          ← YOLOv8 品种分类模型权重
├── 一键打开能量工作台.sh     ← 启动入口
├── __init__.py              ← 项目初始化 / ComfyUI 节点注册入口
├── asset_lib.py             ← 预设资产+客户资产路径工具
│
├── gaze_engine/_shared/assets/  ← 工程底膜视觉素材（eyelid_raw.png）
│
├── tools/                   ← 网页工作台 + HTTP 服务
│   ├── 01_工作台服务/        ← 主应用
│   │   ├── serve_workbench.py   ← 🏆 HTTP 后端主入口 v13：管线API + 客户CRUD + **照片上传/底膜自动检测** + **认证API** + **Pomot创作API**
│   │   ├── workbench_backend.py ← 旧版管线后端（FastAPI，已不推荐）
│   │   ├── 能量工作台.html      ← 前端 UI（含客户照片上传+底膜检测区域）
│   │   ├── 客户门户.html        ← 🆕 客户创作工作室（登录→项目→预设→创作→导出）
│   │   └── static/
│   │       ├── app.js           ← 能量工作台前端逻辑
│   │       ├── portal.js        ← 🆕 客户创作工作室前端逻辑（认证+预设+Pomot+保存导出）
│   │       └── style.css        ← 通用样式
│   ├── 02_前端插件/          ← JS 底层插件（工作台自动加载）
│   ├── 03_工具脚本/          ← 构建/维护脚本
│   │   ├── generate_species_contracts.py  ← 从预设资产同步 → contracts/02_情绪 + 05_人格化
│   │   ├── build_workbench_pipeline_cache.py
│   │   ├── estimate_template_from_photo.py
│   │   └── build_standalone_share.py + ssh_*.py
│   ├── 04_缓存数据/          ← 运行时数据（gitignore）
│   └── 05_其他工具/
│       └── 底模视觉几何调校器.html
│
├── gaze_engine/             ← 核心引擎（物种分区: shared/human/cat/dog）
│   │
│   ├── _shared/                 ← ⭐ 公共区域（物种无关）
│   │   ├── channel_contract.py      ← 🧹 纯校验函数（4个函数均接收 channel_keys 参数）
│   │   ├── slider_schema.py         ← 数据类: SliderPacket + EarParams + MacroSliders + HoldSegment
│   │   ├── slider_bounds.py         ← L1 禁区
│   │   ├── packet_finalize.py       ← 滑杆包收口校验
│   │   ├── envelope_compile.py      ← ⚡纯数学层: macro→能量曲线E(t) + clamp_to_safe_range（物种无关）
│   │   ├── style_compose.py         ← S5: pulse→styled（人格/品种 base+scale×pulse，不改 E(t)）
│   │   ├── micro_jitter.py          ← 微颤动引擎（算法骨架，各物种 envelope_compile 调用并传入物种生理参数）
│   │   ├── pipeline_io.py           ← JSON 读写
│   │   ├── workbench_io.py          ← 操作台读写
│   │   ├── workbench_context.py     ← 上下文管理
│   │   ├── node1_defaults.py        ← 默认值加载
│   │   ├── llm_openai.py            ← LLM 集成 (含 CHEAP_MODEL)
│   │   ├── rhythm_compiler.py       ← 节奏说明书编译器（算法骨架，文案来自各物种 rhythm_data.py）
│   │   ├── emotion_pad.py           ← 38 情绪 PAD 真源表 + resolve_pad()
│   │   ├── species_template.py      ← 物种底膜模板：SpeciesTemplate(17参数)、品种偏移、→渲染器常量
│   │   ├── species_detector.py      ← 自动化检测：MediaPipe 人脸468点/OpenCV猫狗兜底/YOLOv8品种分类
│   │   ├── project_archive.py       ← 项目归档：save_project_profile() + build_diffusion_bundle()
│   │   ├── assets/                  ← 工程底膜素材（eyelid_raw.png）
│   │   └── customer_db.py           ← 客户资产库 CRUD + 认证 + get_effective_template()
│   │
│   ├── human/                   ← ⭐ 人类物种（16情绪预设 + 九大人格）
│   │   ├── control_surface.py       ← 唯一真源: 16预设 (行 18)
│   │   ├── envelope_compile.py      ← 🆕 人类通道编译（含 eyebrow 滞后 + pulse 耦合）
│   │   ├── persona_compiler.py      ← 九大人格 S5 apply_persona_style（不改 E(t)）
│   │   ├── persona_matrix.json      ← 🆕 九大人格矩阵（原 _shared/ → 迁入 human/）
│   │   ├── rhythm_data.py           ← 🆕 节奏说明书人类文案 + EMOTION_VISUAL_PROMPTS + NEGATIVE_EXTRA
│   │   ├── affine_renderer.py       ← 工程底膜驱动引擎
│   │   ├── human_prior.py           ← 真人化先验
│   │   ├── pulse_quality.py         ← 平庸三检
│   │   └── pad_weights.py           ← 人类 PAD 权重表
│   │
│   ├── cat/                     ← ⭐ 猫物种（12情绪预设 + 品种风格）
│   │   ├── __init__.py
│   │   ├── envelope_compile.py      ← 🆕 猫通道编译（通用 scale×envelope，耳位由 channel_adapter 注入）
│   │   ├── presets.py               ← 12 猫情绪预设
│   │   ├── breeds.py                ← 猫品种配置（读本地 breed_matrix.json）
│   │   ├── breed_matrix.json        ← 猫品种风格矩阵
│   │   ├── rhythm_data.py           ← 🆕 节奏说明书猫文案 + EMOTION_VISUAL_PROMPTS + NEGATIVE_EXTRA
│   │   ├── channel_adapter.py       ← EarParams→12通道映射
│   │   ├── affine_renderer.py       ← CatEyeMesh + 耳位渲染
│   │   ├── prior.py                 ← 猫扫视+三眼睑+耳耦合
│   │   ├── detect.py                ← 🆕 猫面部检测 + 品种推断（YOLO兜底）
│   │   ├── pulse_quality.py         ← 猫质检规则
│   │   └── pad_weights.py           ← 猫 PAD 权重表
│   │
│   ├── dog/                     ← ⭐ 狗物种（10情绪预设 + 品种风格）
│   │   ├── __init__.py
│   │   ├── envelope_compile.py      ← 🆕 狗通道编译（通用 scale×envelope，耳位由 channel_adapter 注入）
│   │   ├── presets.py               ← 10 狗情绪预设
│   │   ├── breeds.py                ← 狗品种配置（读本地 breed_matrix.json）
│   │   ├── breed_matrix.json        ← 狗品种风格矩阵
│   │   ├── rhythm_data.py           ← 🆕 节奏说明书狗文案 + EMOTION_VISUAL_PROMPTS + NEGATIVE_EXTRA
│   │   ├── channel_adapter.py       ← EarParams→12通道（保留眉脊语义）
│   │   ├── affine_renderer.py       ← DogEyeMesh + 耳位渲染
│   │   ├── prior.py                 ← 狗扫视+耳耦合
│   │   ├── detect.py                ← 🆕 狗面部检测 + 品种推断（YOLO兜底）
│   │   ├── pulse_quality.py         ← 狗质检规则
│   │   ├── pad_weights.py           ← 狗 PAD 权重表
│   │   └── dog_pipeline.py          ← 狗完整管线（SliderPacket→02烘焙）
│   │
│   ├── delivery_pipeline.py     ← 主交付链 (物种路由)
│   ├── nl_intent.py             ← 意图分类 + 物种识别
│   ├── pomot/                   ← 预设 Prompt 模板合成引擎
│   │   ├── pipeline.py              ← 管线入口（round1 / round2）
│   │   ├── nl_splitter.py           ← NL 拆解器：一句话→动作+情绪
│   │   ├── emotion_router.py        ← 情绪路由：情绪词→预设名+物种
│   │   ├── registry.py              ← 预设注册表：按(species,breed,preset)加载
│   │   ├── templates.py             ← 数据类：NLSplitResult, EmotionRoute, PresetPromptTemplate
│   │   ├── composer.py              ← 第一轮合成：预设+NL→SliderPacket
│   │   ├── delta.py                 ← 第二轮微调：delta 叠加
│   │   └── assembler.py             ← 最终拼装：02_json→04_Prompt.txt→split_for_wan()→送扩散引擎
│   │
│   ├── nl_router.py             ← NL 路由
│   ├── nl_to_packet.py          ← 关键词→预设
│   ├── base_mesh_gen.py         ← 基础网格（底图生成）
│   ├── audio_compiler.py        ← ⚠️ 禁用中
│   ├── __init__.py              ← Python 包初始化
│   └── test_persona_integrity.py ← 人格完整性自检
│
├── contracts/                ← 合同规范（一种情绪/风格 = 一份独立 md）
│   ├── 合同规范.md            ← 统一合同模板（五段格式）
│   ├── README.md              ← contracts 索引 + 生成器说明
│   ├── 01_总纲/               ← 全局理论+工程（6 份，物种通用）
│   │   ├── 滑杆规范.md
│   │   ├── 节奏说明书.md
│   │   ├── 节奏说明书编译器.md
│   │   ├── 全量帧指令集规范.md
│   │   ├── 眼眉真人默认律.md
│   │   └── 眼眉指令集_全局情绪节奏主钟.md
│   ├── 02_情绪/               ← 按物种分目录，38 份独立情绪合同
│   │   ├── 人/                ← 16 份 + 人类情绪与能量曲线.md（索引）+ PAD定位索引.md
│   │   ├── 猫/                ← 12 份 + 猫情绪与能量曲线.md（索引）+ PAD定位索引.md
│   │   ├── 狗/                ← 10 份 + 狗情绪与能量曲线.md（索引）+ PAD定位索引.md
│   │   └── 魅惑勾人.md          ← 根目录 stub 重定向
│   ├── 03_工程底膜/           ← 工程底膜（扩散引擎消费的视觉骨架）
│   │   ├── 工程底膜合同.md
│   │   └── 工程底膜驱动规范.md
│   ├── 04_接口/               ← 上下游对接
│   │   ├── UI设计原则.md
│   │   └── 扩散引擎提示词拼装规范.md
│   ├── 05_人格化/             ← 按物种分目录，每风格一份独立 md
│   │   ├── 人/                ← 9 份人格 + 人类人格风格偏向.md（索引）
│   │   ├── 猫/                ← 4 份品种 + 猫品种风格偏向.md（索引）
│   │   ├── 狗/                ← poodle_giant + 狗品种风格偏向.md + 情绪与品种合成约定.md
│   │   └── 风格化偏向.md        ← 根目录总纲
│   └── 06_架构/               ← 顶层设计（核心）
│       ├── 流程设计.md
│       ├── pomot合成规范.md
│       ├── 公共层边界合同.md
│       ├── 狗150帧全量编译合同_上篇.md
│       ├── 5秒气质精品成片合同.md   ← C端第一步：5s气质+Wan定稿精品P1
│       ├── 扩散Prompt全链路方案_导读.md
│       └── 人格品种与Et正交审计.md
│
├── scripts/                  ← 工具脚本
│   ├── s01_从能量生成02.sh        ← 主出厂（CLI）
│   ├── s01_导出扩散节拍表.sh       ← 导出
│   ├── verify_dog_150_compile_contract.py  ← 狗 150 帧 P0 验收
│   ├── verify_diffusion_prompt_contract.py ← Prompt 全链路 P0 验收
│   ├── export_prompt_samples.py            ← 38 套 04 样例 → _runtime/prompt_samples/
│   ├── s01_设置OpenAI密钥.sh      ← 配置
│   └── s01_env.sh                 ← 环境变量
│
├── _runtime/                 ← 运行时输出（gitignore 可选）
│   └── prompt_samples/       ← export_prompt_samples.py 导出的 04/Wan 样例
│
├── docs/                     ← 文档
│   ├── PROJECT_FILES.md      ← 文件清单
│   ├── TOKEN_BUDGET.md       ← Token 优化指南
│   ├── GAZE_ENGINE_MINDMAP.md← 凝视引擎脑图
│   └── 开源社区对比调研.md    ← 开源社区对比调研
│
├── 预设资产/                 ← 🔵 预设资产（两大分类）
│   ├── 预设情绪包/           ← ① 基本情绪包（macro+hold_seg 基准值）
│   │   ├── human/            ← 16种（含怒视·压人）
│   │   ├── cat/              ← 12种 警觉瞪视、狩猎锁定…
│   │   └── dog/              ← 10种 警觉·竖耳、委屈·幼犬眼…
│   │
│   ├── 风格包/               ← ② 风格偏移（base_offset+scale_factor）
│   │   ├── human/            ← 10个人类人格风格（含魅惑者_温碧霞）
│   │   │   ├── 天选者_大祭司/style.json
│   │   │   ├── 魅惑者_部落巫医/style.json
│   │   │   ├── 魅惑者_温碧霞/style.json
│   │   │   ├── 狠厉者_铁血将军/style.json
│   │   │   ├── 怯弱者_逃兵/style.json
│   │   │   ├── 悲悯者_圣徒/style.json
│   │   │   ├── 呆滞者_傀儡/style.json
│   │   │   ├── 癫狂者_疯僧/style.json
│   │   │   └── 天真者_幼童/style.json
│   │   ├── cat/              ← 4个猫品种风格
│   │   │   ├── ragdoll_cat/  布偶猫/温顺型
│   │   │   ├── siamese_cat/  暹罗猫/高冷型
│   │   │   ├── stray_cat/    田园猫/机敏型
│   │   │   └── british_cat/  英短/憨厚型
│   │   └── dog/              ← 狗品种风格
│   │       └── poodle_giant/ 巨型贵宾/优雅型
│   │
│   └── README.txt
│
├── 客户资产库/               ← 客户私有数据（临时编译结果）
│   ├── 客户_C001/
│   │   ├── 客户信息.json          ← 客户档案（物种、品种、底膜参数）
│   │   ├── 参考素材/              ← 客户上传的正面照（用于 MediaPipe 检测）
│   │   └── 项目_P001_项目名/
│   │       ├── 项目配置.json      ← 关联预设、物种
│   │       ├── 滑杆调整记录.json   ← 版本历史
│   │       ├── 调整过程/          ← 版本快照
│   │       └── 输出/              ← 管线结果
│   └── ...
└──
    └── plans/                 ← 计划文档
        └── autodl_gpu_rental_and_smoke_test.md
```

> **预设资产分层**：
>
> | 层级 | 目录 | 内容 | 作用于 | 数据来源 |
> |------|------|------|--------|---------|
> | ① 基本情绪包 | `预设情绪包/{human,cat,dog}/` | macro+hold_seg，滑杆基准值 | 单情绪 | `control_surface.py` / `cat/dog presets.py` |
> | ② 品种风格包 | `风格包/{cat,dog}/` | base_offset+scale_factor，12通道偏移 | 该物种所有情绪 | `breed_matrix.json` + `style_compose` |
> | ③ 人格包 | `风格包/human/` | base_offset+scale_factor，12通道偏移 | 指定演员+情绪 | `persona_matrix.json` + style.json |
> | — | 合同正文 | 38 情绪 + 14 风格独立 md | 审定真源 | `contracts/02_情绪/` + `contracts/05_人格化/` |

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
```

### 2B. 核心管线数据流（能量工作台旧版）

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
┌─ 2. build_energy_envelope() ────────────────────────┐
│  _shared/envelope_compile.build_energy_envelope()     │
│    → E(t) 能量曲线 (6 macro → 4 段: 起/蓄/盯/收)     │
│    纯数学层, 所有物种共用                                  │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 3. channels_from_packet() ─────────────────────────┐
│  human/cat/dog/envelope_compile.channels_from_packet()│
│    → E(t) + PAD投影 → 12 通道 × 150 帧               │
│    各物种独立实现（人类含 eyebrow 滞后, 猫狗无）      │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─ 4. apply_human_prior() ────────────────────────────┐
│  human_prior.apply_human_prior(dense)                │
│    → 二阶欠阻尼扫视(过冲) + 盯住微漂微颤 + 眉眼延迟   │
│  (或 cat/prior.apply_cat_prior / dog/prior.apply_dog_prior)│
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
║  rhythm_compiler.build_metronome_text()             ║
║  → 扩散节拍表 (文本辅助 · 给 Wan 的脉冲语义)        ║
║                                                     ║
║  底层控制点（12 通道数据）永远不变                    ║
╚══════════════════════════════════════════════════════╝
```

---

## 三、核心入口函数（含精确行号）

| 函数 | 文件:行号 | 被谁调用 | 建议读取范围 |
|------|----------|---------|-------------|
| `_nl_to_packet()` | [`serve_workbench.py:438`](tools/01_工作台服务/serve_workbench.py:438) | POST /api/nl-to-packet | 整函数 ~50 行 |
| `_run_full_pipeline()` | [`serve_workbench.py:493`](tools/01_工作台服务/serve_workbench.py:493) | POST /api/run-pipeline | 整函数 ~70 行 |
| `_compile_pipeline_all()` | [`workbench_backend.py:249`](tools/01_工作台服务/workbench_backend.py:249) | serve_workbench.py | 整函数 ~80 行 |
| `chatgpt_customer_nl()` | [`_shared/llm_openai.py:127`](gaze_engine/_shared/llm_openai.py:127) | serve_workbench.py | 整函数 ~75 行 |
| `chatgpt_nl_to_packet()` | [`_shared/llm_openai.py:223`](gaze_engine/_shared/llm_openai.py:223) | serve_workbench.py | 整函数 ~40 行 |
| `_router_system_prompt()` | [`_shared/llm_openai.py:23`](gaze_engine/_shared/llm_openai.py:23) | node1_defaults.py | 整函数 ~15 行 |
| `finalize_packet()` | [`_shared/packet_finalize.py:161`](gaze_engine/_shared/packet_finalize.py:161) | delivery_pipeline.py | 整函数 ~30 行 |
| `channels_from_packet()` (人类) | [`human/envelope_compile.py:210`](gaze_engine/human/envelope_compile.py:210) | delivery_pipeline.py | 整函数 ~30 行 |
| `channels_from_packet()` (狗) | [`dog/envelope_compile.py:161`](gaze_engine/dog/envelope_compile.py:161) | dog/dog_pipeline.py | 整函数 ~30 行 |
| `channels_from_packet()` (猫) | [`cat/envelope_compile.py:150`](gaze_engine/cat/envelope_compile.py:150) | delivery_pipeline.py | 整函数 ~30 行 |
| `build_energy_envelope()` | [`_shared/envelope_compile.py:129`](gaze_engine/_shared/envelope_compile.py:129) | human/cat/dog/envelope_compile | 整函数 ~45 行 |
| `apply_human_prior()` | [`human/human_prior.py:275`](gaze_engine/human/human_prior.py:275) | delivery_pipeline.py | 整函数 ~50 行 |
| `apply_cat_prior()` | [`cat/prior.py:10`](gaze_engine/cat/prior.py:10) | delivery_pipeline.py | 整函数 ~10 行 |
| `apply_dog_prior()` | [`dog/prior.py:10`](gaze_engine/dog/prior.py:10) | dog/dog_pipeline.py | 整函数 ~10 行 |
| `dense_to_baked_sparse()` | [`human/human_prior.py:329`](gaze_engine/human/human_prior.py:329) | delivery_pipeline.py | 整函数 ~40 行 |
| `fix_pulse_quality()` | [`human/pulse_quality.py:347`](gaze_engine/human/pulse_quality.py:347) | delivery_pipeline.py | 整函数 ~35 行 |
| `run_delivery()` | [`delivery_pipeline.py:62`](gaze_engine/delivery_pipeline.py:62) | serve_workbench.py, scripts | 整函数 ~60 行 |
| `run_delivery_from_packet()` | [`delivery_pipeline.py:123`](gaze_engine/delivery_pipeline.py:123) | serve_workbench.py | 整函数 ~20 行 |
| `run_dog_pipeline()` | [`dog/dog_pipeline.py:61`](gaze_engine/dog/dog_pipeline.py:61) | delivery_pipeline.py | 整函数 ~70 行 |
| `_export_metronome()` | [`serve_workbench.py:651`](tools/01_工作台服务/serve_workbench.py:651) | POST /api/export-metronome | 整函数 ~30 行 |
| `_asset_browser()` | [`serve_workbench.py:682`](tools/01_工作台服务/serve_workbench.py:682) | GET /api/asset-browser | 整函数 ~80 行 |
| `_asset_load_baked()` | [`serve_workbench.py:771`](tools/01_工作台服务/serve_workbench.py:771) | POST /api/asset-load-baked | 整函数 ~50 行 |
| `_customer_upload_photo()` | [`serve_workbench.py:1097`](tools/01_工作台服务/serve_workbench.py:1097) | POST /api/customer/upload-photo | 整函数 ~80 行 |
| `_customer_template_estimate()` | [`serve_workbench.py:1077`](tools/01_工作台服务/serve_workbench.py:1077) | POST /api/customer/template-estimate | 整函数 ~20 行 |
| `auto_detect_for_customer()` | [`_shared/species_detector.py:615`](gaze_engine/_shared/species_detector.py:615) | serve_workbench.py | 整函数 ~140 行 |
| `selectEmotion()` | [`能量工作台.html:309`](tools/01_工作台服务/能量工作台.html:309) | 前端点击事件 | 整函数 ~25 行 |
| `renderNeonControlVideo()` | [`能量工作台.html:568`](tools/01_工作台服务/能量工作台.html:568) | 前端点击事件 | 整函数 ~40 行 |
| `process_customer_nl()` | [`nl_router.py:47`](gaze_engine/nl_router.py:47) | serve_workbench.py | 整函数 ~55 行 |
| `packet_from_natural_language()` | [`nl_to_packet.py:240`](gaze_engine/nl_to_packet.py:240) | serve_workbench.py | 整函数 ~25 行 |
| `compile_to_channels()` (人格→通道) | [`human/persona_compiler.py:152`](gaze_engine/human/persona_compiler.py:152) | 人格编译管线 | 整函数 ~60 行 |
| `template_to_renderer_constants()` | [`_shared/species_template.py:272`](gaze_engine/_shared/species_template.py:272) | affine_renderer | 整函数 ~80 行 |
| `auth_register()` | [`serve_workbench.py:784`](tools/01_工作台服务/serve_workbench.py:784) | POST /api/auth/register | 整函数 ~20 行 |
| `auth_login()` | [`serve_workbench.py:806`](tools/01_工作台服务/serve_workbench.py:806) | POST /api/auth/login | 整函数 ~25 行 |
| `auth_verify()` | [`serve_workbench.py:831`](tools/01_工作台服务/serve_workbench.py:831) | POST /api/auth/verify | 整函数 ~15 行 |
| `portal_presets()` | [`serve_workbench.py:851`](tools/01_工作台服务/serve_workbench.py:851) | GET /api/portal/presets | 整函数 ~50 行 |
| `portal_pomot_round1()` | [`serve_workbench.py:900`](tools/01_工作台服务/serve_workbench.py:900) | POST /api/portal/pomot/round1 | 整函数 ~25 行 |
| `portal_pomot_round2()` | [`serve_workbench.py:924`](tools/01_工作台服务/serve_workbench.py:924) | POST /api/portal/pomot/round2 | 整函数 ~20 行 |
| `portal_save()` | [`serve_workbench.py:944`](tools/01_工作台服务/serve_workbench.py:944) | POST /api/portal/save | 整函数 ~55 行 |
| `portal_export()` | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) | POST /api/portal/export | handler ~40 行 |
| `DiffusionPromptAssembler.assemble()` | [`pomot/assembler.py`](gaze_engine/pomot/assembler.py) | delivery / portal / export | ~80 行 |
| `DiffusionPromptAssembler.split_for_wan()` | [`pomot/assembler.py`](gaze_engine/pomot/assembler.py) | portal export / 验收脚本 | ~35 行 |
| `save_project_profile()` | [`_shared/project_archive.py:38`](gaze_engine/_shared/project_archive.py:38) | portal save | 整函数 ~90 行 |
| `build_diffusion_bundle()` | [`_shared/project_archive.py:151`](gaze_engine/_shared/project_archive.py:151) | portal export | 整函数 ~60 行 |
| `apply_style_offset()` | [`_shared/style_compose.py:22`](gaze_engine/_shared/style_compose.py:22) | envelope_compile / dog_pipeline | 整函数 ~25 行 |
| `resolve_pad()` | [`_shared/emotion_pad.py`](gaze_engine/_shared/emotion_pad.py) | delivery_pipeline / dog_pipeline | ~20 行 |

---

## 四、关键数据类

| 类/结构 | 文件 | 字段 | 说明 |
|---------|------|------|------|
| `SliderPacket` | [`_shared/slider_schema.py:84`](gaze_engine/_shared/slider_schema.py:84) | emotion, macro, hold_seg, species, **pad** | 核心数据单元 |
| `MacroSliders` | [`_shared/slider_schema.py:25`](gaze_engine/_shared/slider_schema.py:25) | push, power, speed, steady, grip, outro | 6 根宏观滑杆 (0-100) |
| `HoldSegment` | [`_shared/slider_schema.py:39`](gaze_engine/_shared/slider_schema.py:39) | shape, pulse_rate, pulse_depth, swell | 盯住段形态 |
| `EarParams` | [`_shared/slider_schema.py:57`](gaze_engine/_shared/slider_schema.py:57) | left_angle, right_angle | 耳位参数（宠物版） |
| `CustomerNLResult` | [`nl_intent.py:56`](gaze_engine/nl_intent.py:56) | intent, reply, packet, meta | 节点1 输出 |
| `PriorReport` | [`human/human_prior.py:27`](gaze_engine/human/human_prior.py:27) | (过冲/底噪/延迟 统计) | 人类真人化报告 |
| `PulseQualityReport` | [`human/pulse_quality.py:64`](gaze_engine/human/pulse_quality.py:64) | (Q01-Q03 检测结果) | 人类平庸质检报告 |
| `PulseQualityMetrics` | [`human/pulse_quality.py:37`](gaze_engine/human/pulse_quality.py:37) | 各项质检指标 | 质检度量 |
| `EyeMesh` | [`human/affine_renderer.py:91`](gaze_engine/human/affine_renderer.py:91) | 眼/眉/瞳孔 网格顶点 | 人类工程底膜网格类 |
| `CatEyeMesh` | [`cat/affine_renderer.py:78`](gaze_engine/cat/affine_renderer.py:78) | 眼/眉/瞳孔/耳位 网格顶点 | 猫工程底膜网格类 |
| `DogEyeMesh` | [`dog/affine_renderer.py:78`](gaze_engine/dog/affine_renderer.py:78) | 眼/眉/瞳孔/耳位 网格顶点 | 狗工程底膜网格类 |
| `Persona` | [`human/persona_compiler.py:65`](gaze_engine/human/persona_compiler.py:65) | 人格参数 | 人格编译数据类 |
| `SpeciesTemplate` | [`_shared/species_template.py:76`](gaze_engine/_shared/species_template.py:76) | 17个几何参数 | 物种底膜模板 |
| `DogPipelineReport` | [`dog/dog_pipeline.py:39`](gaze_engine/dog/dog_pipeline.py:39) | 狗管线报告 | 狗交付质检报告 |
| `PomotPipeline` | [`pomot/pipeline.py:16`](gaze_engine/pomot/pipeline.py:16) | 管线控制 | Prompt 模板合成管线 |
| `FinalizeReport` | [`_shared/packet_finalize.py:16`](gaze_engine/_shared/packet_finalize.py:16) | 收口报告 | 滑杆收口校验报告 |
| `NLSplitResult` | [`pomot/templates.py:11`](gaze_engine/pomot/templates.py:11) | action, emotion, species_hint, breed_hint | NL 拆解结果 |
| `EmotionRoute` | [`pomot/templates.py:33`](gaze_engine/pomot/templates.py:33) | species, preset_name, breed | 情绪路由结果 |
| `PresetPromptTemplate` | [`pomot/templates.py:49`](gaze_engine/pomot/templates.py:49) | emotion_id, species, slider_packet | 预设模板数据类 |

---

## 五、情绪预设体系（多物种）

| 物种 | 预设数 | 定义位置 |
|------|--------|---------|
| 人类 | 16 | [`human/control_surface.py:18`](gaze_engine/human/control_surface.py:18) `PRESETS` |
| 猫 | 12 | [`cat/presets.py:10`](gaze_engine/cat/presets.py:10) `CAT_PRESETS` |
| 狗 | 10 | [`dog/presets.py:10`](gaze_engine/dog/presets.py:10) `DOG_PRESETS` |

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
| "改能量包络数学（影响所有物种）" | [`_shared/envelope_compile.py`](gaze_engine/_shared/envelope_compile.py) | `def build_energy_envelope` | ~45 行 |
| "改人类通道编译（含 eyebrow 滞后）" | [`human/envelope_compile.py`](gaze_engine/human/envelope_compile.py) | `def channels_from_packet` | ~80 行 |
| "改狗通道编译" | [`dog/envelope_compile.py`](gaze_engine/dog/envelope_compile.py) | `def channels_from_packet` | ~100 行 |
| "改猫通道编译" | [`cat/envelope_compile.py`](gaze_engine/cat/envelope_compile.py) | `def channels_from_packet` | ~100 行 |
| "改 4 真人律（人类）" | [`human/human_prior.py`](gaze_engine/human/human_prior.py) | `def apply_human_prior` | 目标函数 ~50 行 |
| "改预设数值（人类）" | [`human/control_surface.py:18`](gaze_engine/human/control_surface.py:18) | `PRESETS[` | 具体预设 ~8 行 |
| "改滑杆 schema" | [`_shared/slider_schema.py`](gaze_engine/_shared/slider_schema.py) | `class SliderPacket` | 类定义 ~90 行 |
| "改猫情绪预设" | [`cat/presets.py`](gaze_engine/cat/presets.py) | `CAT_PRESETS[` | 具体预设 ~8 行 |
| "改猫品种配置" | [`cat/breeds.py`](gaze_engine/cat/breeds.py) | `BREEDS[` | 具体品种 ~15 行 |
| "改猫底膜渲染" | [`cat/affine_renderer.py`](gaze_engine/cat/affine_renderer.py) | `CatEyeMesh` | ~160 行 |
| "改狗情绪预设" | [`dog/presets.py`](gaze_engine/dog/presets.py) | `DOG_PRESETS[` | 具体预设 ~8 行 |
| "改 L1 禁区" | [`_shared/slider_bounds.py`](gaze_engine/_shared/slider_bounds.py) | `G1` ~ `G8` | 具体禁区 ~10 行 |
| "加新人类预设" | [`human/control_surface.py:18`](gaze_engine/human/control_surface.py:18) + [`_shared/slider_bounds.py`](gaze_engine/_shared/slider_bounds.py) | `PRESETS` + `load_rules` | 各 ~10 行 |
| "改前端 UI" | [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) | 按钮 ID / 函数名 | 具体函数 ~30 行 |
| "改人格矩阵" | [`human/persona_matrix.json`](gaze_engine/human/persona_matrix.json) | 人格 ID | 具体人格 ~15 行 |
| "启用/停用驱动引擎（人类）" | [`human/affine_renderer.py:86`](gaze_engine/human/affine_renderer.py:86) | `_AFFINE_DISABLED` | 当前 `False`（已启用） |
| "启用音频编译" | [`audio_compiler.py:12`](gaze_engine/audio_compiler.py:12) | `_AUDIO_DISABLED` | 改 `True`→`False` |
| "改工程底膜驱动（人类）" | [`human/affine_renderer.py`](gaze_engine/human/affine_renderer.py) | `EyeMesh.deform` / `render_frame` | ~340 行 |
| "看工程底膜合同" | [`contracts/03_工程底膜/工程底膜合同.md`](contracts/03_工程底膜/工程底膜合同.md) | 全文 | 格式协议+验收标准 |
| "看驱动引擎规范" | [`contracts/03_工程底膜/工程底膜驱动规范.md`](contracts/03_工程底膜/工程底膜驱动规范.md) | 全文 | 核心机制+注意事项 |
| "改 6 输出分流" | [`_shared/rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py) | `build_metronome_text` | ~100 行 |
| "改节奏说明书编译器" | [`_shared/rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py) | `build_metronome_text` | ~100 行 |
| "改猫通道适配器" | [`cat/channel_adapter.py`](gaze_engine/cat/channel_adapter.py) | `ear_to_channel_values` | ~30 行 |
| "改狗通道适配器" | [`dog/channel_adapter.py`](gaze_engine/dog/channel_adapter.py) | `ear_to_channel_values` | ~30 行 |
| "改狗完整管线" | [`dog/dog_pipeline.py`](gaze_engine/dog/dog_pipeline.py) | `run_dog_pipeline` | ~70 行 |
| "改猫面部检测" | [`cat/detect.py`](gaze_engine/cat/detect.py) | `estimate_cat_ear` | ~80 行 |
| "改狗面部检测" | [`dog/detect.py`](gaze_engine/dog/detect.py) | `estimate_dog_ear` | ~80 行 |
| "改架构设计" | [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md) | 全文 | 全文 |
| "改某一情绪合同" | [`contracts/02_情绪/{人\|猫\|狗}/{情绪名}.md`](contracts/02_情绪/) | 五段格式正文 | 全文 |
| "同步情绪合同数值" | [`tools/03_工具脚本/generate_species_contracts.py`](tools/03_工具脚本/generate_species_contracts.py) | `main()` | 全文 |
| "改某一风格/人格合同" | [`contracts/05_人格化/{人\|猫\|狗}/{id}.md`](contracts/05_人格化/) | 五段格式正文 | 全文 |
| "改项目归档/导出包" | [`_shared/project_archive.py`](gaze_engine/_shared/project_archive.py) | `save_project_profile` / `build_diffusion_bundle` | ~120 行 |
| "改 S5 风格合成" | [`_shared/style_compose.py`](gaze_engine/_shared/style_compose.py) | `apply_style_offset` / `load_style_from_asset` | ~75 行 |
| "改合同索引" | [`contracts/README.md`](contracts/README.md) | 全文 | 全文 |
| "改节奏说明书合同" | [`contracts/01_总纲/节奏说明书.md`](contracts/01_总纲/节奏说明书.md) | 全文 | 全文 |
| "改公共层边界合同" | [`contracts/06_架构/公共层边界合同.md`](contracts/06_架构/公共层边界合同.md) | 全文 | 全文 |
| "改全局情绪节奏主钟" | [`contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md`](contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md) | 全文 | 全文 |
| "改工程底膜合同" | [`contracts/03_工程底膜/工程底膜合同.md`](contracts/03_工程底膜/工程底膜合同.md) | 全文 | 全文 |
| "改工程底膜驱动规范" | [`contracts/03_工程底膜/工程底膜驱动规范.md`](contracts/03_工程底膜/工程底膜驱动规范.md) | 全文 | 全文 |
| "改 NL 路由" | [`nl_router.py`](gaze_engine/nl_router.py) | `process_customer_nl` | 整函数 ~55 行 |
| "改 LLM 集成" | [`_shared/llm_openai.py`](gaze_engine/_shared/llm_openai.py) | `chatgpt_customer_nl` / `chatgpt_nl_to_packet` | 各 ~50 行 |
| "改人格编译器" | [`human/persona_compiler.py`](gaze_engine/human/persona_compiler.py) | `Persona` / `compile_to_channels` | ~80 行 |
| "改物种底膜模板" | [`_shared/species_template.py`](gaze_engine/_shared/species_template.py) | `SpeciesTemplate` / `template_to_renderer_constants` | ~260 行 |
| "改自动化检测" | [`_shared/species_detector.py`](gaze_engine/_shared/species_detector.py) | `auto_detect_for_customer` | ~140 行 |
| "改客户资产库" | [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) | `create_customer` / `save_adjustment` | 整文件 ~542 行 |
| "改资产路径（预设+客户）" | [`asset_lib.py`](asset_lib.py) | `customer_dir` / `project_dir` | 客户路径段 ~60 行 |
| "加客户 API 端点" | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) | `_customer_create` / `_customer_list` | handler ~15 行 |
| "改资产浏览器（双栏）" | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) + [`workbench_backend.py`](tools/01_工作台服务/workbench_backend.py) | `_asset_browser` | 整函数 ~80 行 |
| "改前端客户面板" | [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) + [`static/app.js`](tools/01_工作台服务/static/app.js) | `customer-select` / `window.app` | 各 ~50 行 |
| "改 04 Prompt 拼装" | [`pomot/assembler.py`](gaze_engine/pomot/assembler.py) | `_build_positive_prompt` / `split_for_wan` | ~120 行 |
| "改 L2 情绪视觉词" | [`{dog,cat,human}/rhythm_data.py`](gaze_engine/dog/rhythm_data.py) | `EMOTION_VISUAL_PROMPTS` | 各物种 |
| "改 PAD 真源" | [`_shared/emotion_pad.py`](gaze_engine/_shared/emotion_pad.py) | `EMOTION_PAD` / `resolve_pad` | 全文 |
| "跑 Prompt 验收" | [`scripts/verify_diffusion_prompt_contract.py`](scripts/verify_diffusion_prompt_contract.py) | `main()` | 全文 |
| "跑狗150帧验收" | [`scripts/verify_dog_150_compile_contract.py`](scripts/verify_dog_150_compile_contract.py) | `main()` | 全文 |
| "气质精品成片验收" | [`contracts/06_架构/5秒气质精品成片合同.md`](contracts/06_架构/5秒气质精品成片合同.md) | §5.2 P1 | 全文 |
| "导出 Prompt 样例" | [`scripts/export_prompt_samples.py`](scripts/export_prompt_samples.py) | `export_species()` | 全文 |
| "改 Prompt 模板合成" | [`pomot/`](gaze_engine/pomot/) | `PomotPipeline` / `composer` | 各文件 ~50 行 |
| "改客户密码认证" | [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) | `verify_customer_password` / `create_auth_token` | 各函数 ~15 行 |
| "改客户创作门户 UI" | [`客户门户.html`](tools/01_工作台服务/客户门户.html) + [`static/portal.js`](tools/01_工作台服务/static/portal.js) | 按钮 ID / 函数名 | 各文件 ~60 行 |
| "加认证 API" | [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) | `auth_register` / `auth_login` / `portal_pomot_round1` | handler ~20 行 |
| "改人类节奏说明书文案" | [`human/rhythm_data.py`](gaze_engine/human/rhythm_data.py) | `EMOTION_VISUAL_PROMPTS` | 全文 |
| "改猫节奏说明书文案" | [`cat/rhythm_data.py`](gaze_engine/cat/rhythm_data.py) | `EMOTION_VISUAL_PROMPTS` | 全文 |
| "改狗节奏说明书文案" | [`dog/rhythm_data.py`](gaze_engine/dog/rhythm_data.py) | `EMOTION_VISUAL_PROMPTS` | 全文 |

---

## 七、审计线索

- 12 通道定义（人类）: [`human/envelope_compile.py`](gaze_engine/human/envelope_compile.py) `HUMAN_CHANNELS`
- 12 通道定义（狗）: [`dog/envelope_compile.py`](gaze_engine/dog/envelope_compile.py) `DOG_CHANNELS`
- 12 通道定义（猫）: [`cat/envelope_compile.py`](gaze_engine/cat/envelope_compile.py) `CAT_CHANNELS`
- 通道校验函数（共4个）: [`_shared/channel_contract.py`](gaze_engine/_shared/channel_contract.py) — 纯函数，无全局数据
- 猫 PAD 权重表: [`cat/pad_weights.py`](gaze_engine/cat/pad_weights.py)
- 猫通道适配器: [`cat/channel_adapter.py`](gaze_engine/cat/channel_adapter.py)
- 猫面部检测: [`cat/detect.py`](gaze_engine/cat/detect.py)
- 猫节奏说明书文案: [`cat/rhythm_data.py`](gaze_engine/cat/rhythm_data.py)
- 狗 PAD 权重表: [`dog/pad_weights.py`](gaze_engine/dog/pad_weights.py)
- 狗通道适配器: [`dog/channel_adapter.py`](gaze_engine/dog/channel_adapter.py)
- 狗面部检测: [`dog/detect.py`](gaze_engine/dog/detect.py)
- 狗节奏说明书文案: [`dog/rhythm_data.py`](gaze_engine/dog/rhythm_data.py)
- 狗完整管线: [`dog/dog_pipeline.py`](gaze_engine/dog/dog_pipeline.py)
- 人类节奏说明书文案: [`human/rhythm_data.py`](gaze_engine/human/rhythm_data.py)
- 节奏说明书编译器: [`_shared/rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py)
- 合同物种索引: [`contracts/README.md`](contracts/README.md) — 02_情绪 38 份 + 05_人格化 14 份
- 人类情绪索引: [`contracts/02_情绪/人/人类情绪与能量曲线.md`](contracts/02_情绪/人/人类情绪与能量曲线.md)
- 猫情绪索引: [`contracts/02_情绪/猫/猫情绪与能量曲线.md`](contracts/02_情绪/猫/猫情绪与能量曲线.md)
- 狗情绪索引: [`contracts/02_情绪/狗/狗情绪与能量曲线.md`](contracts/02_情绪/狗/狗情绪与能量曲线.md)
- 人格品种正交审计: [`contracts/06_架构/人格品种与Et正交审计.md`](contracts/06_架构/人格品种与Et正交审计.md)
- 合同生成器: [`tools/03_工具脚本/generate_species_contracts.py`](tools/03_工具脚本/generate_species_contracts.py) — 预设资产 → contracts 同步
- S5 风格合成: [`gaze_engine/_shared/style_compose.py`](gaze_engine/_shared/style_compose.py) — `apply_style_offset()` 不改 E(t)
- 项目归档: [`gaze_engine/_shared/project_archive.py`](gaze_engine/_shared/project_archive.py) — `save_project_profile()` / `build_diffusion_bundle()`
- 合同规范模板: [`contracts/合同规范.md`](contracts/合同规范.md)
- 全量帧指令集规范: [`contracts/01_总纲/全量帧指令集规范.md`](contracts/01_总纲/全量帧指令集规范.md)
- 眼眉真人默认律: [`contracts/01_总纲/眼眉真人默认律.md`](contracts/01_总纲/眼眉真人默认律.md)
- 眼眉指令集·全局情绪节奏主钟: [`contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md`](contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md)
- 节奏说明书: [`contracts/01_总纲/节奏说明书.md`](contracts/01_总纲/节奏说明书.md)
- 节奏说明书编译器合同: [`contracts/01_总纲/节奏说明书编译器.md`](contracts/01_总纲/节奏说明书编译器.md)
- 工程底膜合同: [`contracts/03_工程底膜/工程底膜合同.md`](contracts/03_工程底膜/工程底膜合同.md)
- 工程底膜驱动规范: [`contracts/03_工程底膜/工程底膜驱动规范.md`](contracts/03_工程底膜/工程底膜驱动规范.md)
- 双模驱动架构: [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md)
- 公共层边界合同: [`contracts/06_架构/公共层边界合同.md`](contracts/06_架构/公共层边界合同.md)
- 狗 150 帧编译合同: [`contracts/06_架构/狗150帧全量编译合同_上篇.md`](contracts/06_架构/狗150帧全量编译合同_上篇.md)
- 5 秒气质精品成片: [`contracts/06_架构/5秒气质精品成片合同.md`](contracts/06_架构/5秒气质精品成片合同.md) — Wan 定稿 P1 + 连续 3 次精品
- 扩散 Prompt 全链路导读: [`contracts/06_架构/扩散Prompt全链路方案_导读.md`](contracts/06_架构/扩散Prompt全链路方案_导读.md)
- 04 拼装规范: [`contracts/04_接口/扩散引擎提示词拼装规范.md`](contracts/04_接口/扩散引擎提示词拼装规范.md)
- PAD 真源: [`gaze_engine/_shared/emotion_pad.py`](gaze_engine/_shared/emotion_pad.py)
- Prompt P0 验收: [`scripts/verify_diffusion_prompt_contract.py`](scripts/verify_diffusion_prompt_contract.py)
- 狗 150 帧 P0 验收: [`scripts/verify_dog_150_compile_contract.py`](scripts/verify_dog_150_compile_contract.py)
- Prompt 样例导出: [`scripts/export_prompt_samples.py`](scripts/export_prompt_samples.py) → `_runtime/prompt_samples/`
- 交付链入口文档: [`delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) docstring
- 后端编译入口: [`workbench_backend.py:249`](tools/01_工作台服务/workbench_backend.py:249) `_compile_pipeline_all`
- Token 优化策略: [`docs/TOKEN_BUDGET.md`](docs/TOKEN_BUDGET.md)
- 完整文件清单: [`docs/PROJECT_FILES.md`](docs/PROJECT_FILES.md)
- 凝视引擎脑图: [`docs/GAZE_ENGINE_MINDMAP.md`](docs/GAZE_ENGINE_MINDMAP.md)
- 🆕 客户密码认证: [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) `verify_customer_password()` / `create_auth_token()` — PBKDF2-SHA256 密码哈希 + HMAC token
- 🆕 客户创作工作室 UI: [`客户门户.html`](tools/01_工作台服务/客户门户.html) + [`static/portal.js`](tools/01_工作台服务/static/portal.js) — 登录→标定→Pomot→04+Wan→导出
- 🆕 门户 API 端点: [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) — `POST /api/auth/register|login|verify` + `GET /api/portal/presets` + `POST /api/portal/pomot/round1|round2` + `POST /api/portal/save|export`
- 🆕 客户资产库模块: [`_shared/customer_db.py`](gaze_engine/_shared/customer_db.py) — CRUD + 调整版本管理
- 🆕 客户资产库根目录: [`客户资产库/`](客户资产库/) — 每个客户独立文件夹
- 🆕 自动化底膜检测: [`_shared/species_detector.py`](gaze_engine/_shared/species_detector.py) — MediaPipe + YOLOv8 + OpenCV
- 🆕 物种底膜模板: [`_shared/species_template.py`](gaze_engine/_shared/species_template.py) — 17参数模板
- 🆕 人格编译器: [`human/persona_compiler.py`](gaze_engine/human/persona_compiler.py) — 九大人格编译（原 _shared/ → 迁入 human/）
- 🆕 Pomot 合成引擎: [`pomot/`](gaze_engine/pomot/) — pipeline / nl_splitter / emotion_router / composer / delta / assembler
- 🆕 前端客户选择器: [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) + [`static/app.js`](tools/01_工作台服务/static/app.js)
- 🆕 物种专属通道编译: [`human/envelope_compile.py`](gaze_engine/human/envelope_compile.py) / [`cat/envelope_compile.py`](gaze_engine/cat/envelope_compile.py) / [`dog/envelope_compile.py`](gaze_engine/dog/envelope_compile.py) — 从 `_shared` 迁入各物种