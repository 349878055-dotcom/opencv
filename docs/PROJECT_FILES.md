# 👁️ jintao_node_eye · 全量文件清单

> **生成日期**: 2026-05-26 · **最后更新**: 2026-05-28
> **入口**: [`tools/01_工作台服务/serve_workbench.py`](tools/01_工作台服务/serve_workbench.py)（HTTP API v13）+ [`tools/01_工作台服务/客户门户.html`](tools/01_工作台服务/客户门户.html) + [`static/portal.js`](tools/01_工作台服务/static/portal.js)
> **启动**: [`一键打开创作门户.sh`](一键打开创作门户.sh) → `http://127.0.0.1:8765/portal`
> **架构**: 唯一宏观 [`合同/00_管线导读/00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md)（编译序 `01`→`08`）
> **门户测试（当前）**: 点情绪/品种按钮 → `预设资产/情绪包/{物种}/{名}.json`；输入框只写场景；NL-A 未接

---

## 目录

- [一、根目录文件](#一根目录文件)
- [二、核心引擎 (`gaze_engine/`)](#二核心引擎-gaze_engine)
- [三、合同规范 (`合同/`)](#三合同规范-合同)
- [四、UI 与工具 (`tools/`)](#四ui-与工具-tools)
- [五、脚本 (`scripts/`)](#五脚本-scripts)
- [六、预设资产 (`预设资产/`)](#六预设资产-预设资产)
- [七、客户资产库 (`客户资产库/`)](#七客户资产库-客户资产库)
- [八、文档 (`docs/`)](#八文档-docs)
- [九、计划文档 (`plans/`)](#九计划文档-plans)
- [十、数据流转全图](#十数据流转全图)

---

## 一、根目录文件

| 文件 | 作用 |
|------|------|
| [`__init__.py`](__init__.py) | Python 包初始化 / ComfyUI 节点注册入口 |
| [`AI_INDEX.md`](AI_INDEX.md) | **AI 代码图谱**：结构、入口函数、改参指南 |
| [`README.md`](README.md) | 项目简介 |
| [`.clinerules`](.clinerules) | Roo Code AI 行为规则 |
| [`.cursorrules`](.cursorrules) | Cursor AI 行为规则 |
| [`.env`](.env) | 环境变量（运行态，不入库） |
| [`.env.example`](.env.example) | 环境变量示例 |
| [`.gitignore`](.gitignore) | Git 忽略规则 |
| [`asset_lib.py`](asset_lib.py) | **预设资产路径**：情绪包/风格包/底膜包、`load_emotion_slider_packet()`、物种烘焙文件名 |
| [`yolov8n-cls.pt`](yolov8n-cls.pt) | YOLOv8 品种分类权重 |
| [`一键打开创作门户.sh`](一键打开创作门户.sh) | 启动 `serve_workbench.py` 并打开 `/portal` |

---

## 二、核心引擎 (`gaze_engine/`)

### 2.1 公共共享层 (`_shared/`)

| 文件 | 作用 |
|------|------|
| [`channel_contract.py`](gaze_engine/_shared/channel_contract.py) | 12 通道定义、校验、`validate_baked_delivery()` |
| [`slider_schema.py`](gaze_engine/_shared/slider_schema.py) | `SliderPacket`、macro、hold_seg、EarParams |
| [`slider_bounds.py`](gaze_engine/_shared/slider_bounds.py) | L1 禁区 G1–G8、`load_rules()` |
| [`packet_finalize.py`](gaze_engine/_shared/packet_finalize.py) | 滑杆包收口 |
| [`envelope_compile.py`](gaze_engine/_shared/envelope_compile.py) | E(t) 能量包络（物种无关数学层） |
| [`emotion_pad.py`](gaze_engine/_shared/emotion_pad.py) | **PAD 真源**：`EMOTION_PAD`、`resolve_pad()` |
| [`micro_jitter.py`](gaze_engine/_shared/micro_jitter.py) | 微颤动引擎 |
| [`oculomotor_prior.py`](gaze_engine/_shared/oculomotor_prior.py) | 扫视动力学共享核心 |
| [`pulse_quality_core.py`](gaze_engine/_shared/pulse_quality_core.py) | Q01–Q03 共享质检逻辑 |
| [`style_compose.py`](gaze_engine/_shared/style_compose.py) | S5 `apply_style_offset()`，不改 E(t) |
| [`project_archive.py`](gaze_engine/_shared/project_archive.py) | 门户 `save_project_profile` / `build_diffusion_bundle` |
| [`pipeline_io.py`](gaze_engine/_shared/pipeline_io.py) | 各阶段 JSON 读写常量 |
| [`workbench_io.py`](gaze_engine/_shared/workbench_io.py) | 操作台滑杆包读写 |
| [`workbench_context.py`](gaze_engine/_shared/workbench_context.py) | 操作台上下文 |
| [`node1_defaults.py`](gaze_engine/_shared/node1_defaults.py) | 节点 1 默认 Prompt |
| [`llm_openai.py`](gaze_engine/_shared/llm_openai.py) | LLM 集成（NL-A 待接） |
| [`rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py) | 02 → 05 扩散节拍表 |
| [`species_template.py`](gaze_engine/_shared/species_template.py) | 17 参数底膜模板 |
| [`species_detector.py`](gaze_engine/_shared/species_detector.py) | MediaPipe + Haar + YOLOv8 标定 |
| [`customer_db.py`](gaze_engine/_shared/customer_db.py) | 客户/项目 CRUD、认证 |
| [`assets/eyelid_raw.png`](gaze_engine/_shared/assets/eyelid_raw.png) | 眼睑素材 |

### 2.2 人类物种 (`human/`)

| 文件 | 作用 |
|------|------|
| [`control_surface.py`](gaze_engine/human/control_surface.py) | **16 情绪** `PRESETS`（代码真源；亦可同步 JSON） |
| [`affine_renderer.py`](gaze_engine/human/affine_renderer.py) | RGB 三色分离工程底膜 |
| [`human_prior.py`](gaze_engine/human/human_prior.py) | 真人化先验 → `02_烘焙_真人律.json` |
| [`pulse_quality.py`](gaze_engine/human/pulse_quality.py) | 平庸三检 Q01–Q03 |
| [`pad_weights.py`](gaze_engine/human/pad_weights.py) | 人类 PAD 权重 |
| [`envelope_compile.py`](gaze_engine/human/envelope_compile.py) | 人 S4：眉滞后 + pulse |
| [`persona_compiler.py`](gaze_engine/human/persona_compiler.py) | 9 人格编译 |
| [`persona_matrix.json`](gaze_engine/human/persona_matrix.json) | 人格矩阵 |
| [`rhythm_data.py`](gaze_engine/human/rhythm_data.py) | L2 情绪视觉词 + 节奏文案 |

### 2.3 猫物种 (`cat/`)

| 文件 | 作用 |
|------|------|
| [`presets.py`](gaze_engine/cat/presets.py) | 预设注册别名（**数值真源**：`预设资产/情绪包/cat/*.json`） |
| [`breeds.py`](gaze_engine/cat/breeds.py) | 9 品种配置 |
| [`breed_matrix.json`](gaze_engine/cat/breed_matrix.json) | 品种风格矩阵 |
| [`channel_adapter.py`](gaze_engine/cat/channel_adapter.py) | EarParams → 12 通道 |
| [`affine_renderer.py`](gaze_engine/cat/affine_renderer.py) | CatEyeMesh 渲染 |
| [`prior.py`](gaze_engine/cat/prior.py) | 猫先验 |
| [`detect.py`](gaze_engine/cat/detect.py) | 猫脸 + 耳位检测 |
| [`pulse_quality.py`](gaze_engine/cat/pulse_quality.py) | 猫质检 |
| [`pad_weights.py`](gaze_engine/cat/pad_weights.py) | 猫 PAD 权重 |
| [`rhythm_data.py`](gaze_engine/cat/rhythm_data.py) | 猫节奏 / L2 文案 |
| [`envelope_compile.py`](gaze_engine/cat/envelope_compile.py) | 猫 S4 通道编译 |

### 2.4 狗物种 (`dog/`)

| 文件 | 作用 |
|------|------|
| [`presets.py`](gaze_engine/dog/presets.py) | 预设注册别名（**数值真源**：`预设资产/情绪包/dog/*.json`） |
| [`breeds.py`](gaze_engine/dog/breeds.py) | 10 品种配置 |
| [`breed_matrix.json`](gaze_engine/dog/breed_matrix.json) | 品种风格矩阵 |
| [`channel_adapter.py`](gaze_engine/dog/channel_adapter.py) | EarParams → 12 通道 |
| [`affine_renderer.py`](gaze_engine/dog/affine_renderer.py) | DogEyeMesh 渲染 |
| [`prior.py`](gaze_engine/dog/prior.py) | 狗先验 |
| [`detect.py`](gaze_engine/dog/detect.py) | 狗脸 + 耳位检测 |
| [`pulse_quality.py`](gaze_engine/dog/pulse_quality.py) | 狗质检 |
| [`pad_weights.py`](gaze_engine/dog/pad_weights.py) | 狗 PAD 权重 |
| [`rhythm_data.py`](gaze_engine/dog/rhythm_data.py) | 狗节奏 / L2 文案 |
| [`envelope_compile.py`](gaze_engine/dog/envelope_compile.py) | 狗 S4 通道编译 |
| [`dog_pipeline.py`](gaze_engine/dog/dog_pipeline.py) | **狗完整管线** `run_dog_pipeline()` → `02_烘焙_狗律.json` |

### 2.5 Prompt 模板合成 (`pomot/`)

| 文件 | 作用 |
|------|------|
| [`pipeline.py`](gaze_engine/pomot/pipeline.py) | round1/round2；`emotion_override` → `preset_override` |
| [`emotion_router.py`](gaze_engine/pomot/emotion_router.py) | **情绪路由**：`preset_override` 命中情绪包则直连，跳过词表 |
| [`registry.py`](gaze_engine/pomot/registry.py) | `cat_packet_from_file` / `dog_packet_from_file` |
| [`nl_splitter.py`](gaze_engine/pomot/nl_splitter.py) | 场景 NL 拆解（动作/情绪词） |
| [`composer.py`](gaze_engine/pomot/composer.py) | 预设 + NL → SliderPacket |
| [`delta.py`](gaze_engine/pomot/delta.py) | round2 微调（**不传** emotion_override） |
| [`assembler.py`](gaze_engine/pomot/assembler.py) | 02 → 04 Prompt + Wan 正负向 |
| [`templates.py`](gaze_engine/pomot/templates.py) | NLSplitResult、EmotionRoute 等数据类 |

### 2.6 顶层引擎模块

| 文件 | 作用 |
|------|------|
| [`delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) | 人类/猫交付链 `run_delivery()` |
| [`nl_intent.py`](gaze_engine/nl_intent.py) | NL 意图分类 |
| [`nl_router.py`](gaze_engine/nl_router.py) | NL 路由（工作台遗留路径） |
| [`nl_to_packet.py`](gaze_engine/nl_to_packet.py) | 人类关键词 → 预设 |
| [`base_mesh_gen.py`](gaze_engine/base_mesh_gen.py) | 基础网格 |
| [`audio_compiler.py`](gaze_engine/audio_compiler.py) | ⚠️ 音频编译禁用中 |
| [`test_persona_integrity.py`](gaze_engine/test_persona_integrity.py) | 人格完整性自检 |

---

## 三、合同规范 (`合同/`)

> 索引真源：[`合同/README.md`](合同/README.md) · 五段格式：[`合同规范.md`](合同/合同规范.md)

| 目录 | 份数/说明 | 关键文件 |
|------|-----------|----------|
| **00_管线导读** | 宏观唯一 | [`00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md) |
| **01_输入与收口** | L1 + macro | [`滑杆规范.md`](合同/01_输入与收口/滑杆规范.md) · [`macro与hold_seg专篇.md`](合同/01_输入与收口/macro与hold_seg专篇.md) |
| **02_情绪与能量** | 38 情绪 | 人16 / 猫12 / 狗10；狗 MVP：[`委屈·幼犬眼.md`](合同/02_情绪与能量/狗/委屈·幼犬眼.md) |
| **03_情绪坐标** | 5 理论 + 38 | [`00_情绪坐标导读.md`](合同/03_情绪坐标/00_情绪坐标导读.md) … [`04_四层表演栈与style边界.md`](合同/03_情绪坐标/04_四层表演栈与style边界.md) |
| **04_通道编译** | S4 | [`README.md`](合同/04_通道编译/README.md) · [`01_十二通道与全量帧格式.md`](合同/04_通道编译/01_十二通道与全量帧格式.md) · 人/猫/狗 [`动态层编译与代码映射.md`](合同/04_通道编译/狗/动态层编译与代码映射.md) |
| **05_风格化** | S5 | 人9人格 + 猫9品种 + 狗10品种；[`人/情绪与人格耦合专篇.md`](合同/05_风格化/人/情绪与人格耦合专篇.md) |
| **06_先验与质检** | S6+S7 | [`00_先验质检导读.md`](合同/06_先验与质检/00_先验质检导读.md) · 人/猫/狗先验与三检 |
| **07_工程底膜** | 03 MP4 | [`工程底膜合同.md`](合同/07_工程底膜/工程底膜合同.md) · [`12通道到底膜MP4专篇.md`](合同/07_工程底膜/12通道到底膜MP4专篇.md) |
| **08_输出与扩散** | S8 | [`Pomot编辑专篇.md`](合同/08_输出与扩散/Pomot编辑专篇.md) · [`扩散输出流程专篇.md`](合同/08_输出与扩散/扩散输出流程专篇.md) · [`节奏说明书.md`](合同/08_输出与扩散/节奏说明书.md) |
| **09_架构与验收** | 边界 | [`公共层边界合同.md`](合同/09_架构与验收/公共层边界合同.md) |

**同步脚本**：`python3 tools/03_工具脚本/generate_species_contracts.py`（JSON → `02`+`03` 合同）

---

## 四、UI 与工具 (`tools/`)

### 4.1 客户创作门户（主应用）

| 文件 | 作用 |
|------|------|
| [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) | HTTP 后端 v13：认证、标定、Pomot、烘焙、底膜、导出 |
| [`客户门户.html`](tools/01_工作台服务/客户门户.html) | 五步 UI：物种→情绪/品种→场景→生成→导出 |
| [`static/portal.js`](tools/01_工作台服务/static/portal.js) | 前端逻辑；`render-membrane` 传 `preset: activeEmotion` |
| [`static/style.css`](tools/01_工作台服务/static/style.css) | 共享样式 |

**主要 API**（节选）：

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/portal` | 客户门户 HTML |
| GET | `/api/portal/presets` | 情绪/品种列表（id = JSON 文件名） |
| POST | `/api/portal/pomot/round1` | Pomot 生成（`emotion` = 按钮 id） |
| POST | `/api/portal/pomot/round2` | 滑杆微调 |
| POST | `/api/portal/render-membrane` | 狗律烘焙预览 → `02_烘焙_狗律.json` |
| POST | `/api/portal/export` | 扩散包导出 |
| POST | `/api/auth/register` · `login` · `verify` | 客户认证 |

> 旧版 [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) / `workbench_backend.py` 已移除。

### 4.2 前端插件 (`02_前端插件/`)

门户逻辑已迁入 `static/portal.js`；本目录保留 L1 校验等可选插件。

| 文件 | 作用 |
|------|------|
| [`packet_finalize_ui.js`](tools/02_前端插件/packet_finalize_ui.js) | L1 滑杆禁区校验 |
| [`slider_forbidden_bounds.js`](tools/02_前端插件/slider_forbidden_bounds.js) | 禁区边界数据 |
| [`workbench_pipeline_ui.js`](tools/02_前端插件/workbench_pipeline_ui.js) | 管线 UI（遗留） |

### 4.3 工具脚本 (`03_工具脚本/`)

| 文件 | 作用 |
|------|------|
| [`generate_species_contracts.py`](tools/03_工具脚本/generate_species_contracts.py) | 预设资产 → `合同/02`+`03`+`05` |
| [`sync_human_style_pack.py`](tools/03_工具脚本/sync_human_style_pack.py) | 人格 style 同步 |
| [`sync_species_style_pack.py`](tools/03_工具脚本/sync_species_style_pack.py) | 猫狗品种 style 同步 |
| [`sync_membrane_pack.py`](tools/03_工具脚本/sync_membrane_pack.py) | 底膜包同步 |
| [`estimate_template_from_photo.py`](tools/03_工具脚本/estimate_template_from_photo.py) | 照片 → 底膜参数 |
| [`reorganize_contracts.py`](tools/03_工具脚本/reorganize_contracts.py) | 合同目录维护 |
| `ssh_*.py` | AutoDL 远程运维 |

### 4.4 AutoDL 运维 (`tools/autodl/`)

| 文件 | 作用 |
|------|------|
| [`README.md`](tools/autodl/README.md) | GPU 开机 / Comfy 8188 SOP |
| [`已部署实例.json`](tools/autodl/已部署实例.json) | 实例路径备忘（不含密码） |

### 4.5 运行时缓存 (`04_缓存数据/`)

预览 MP4、管线中间产物（gitignore）。

---

## 五、脚本 (`scripts/`)

| 文件 | 作用 |
|------|------|
| [`verify_dog_150_compile_contract.py`](scripts/verify_dog_150_compile_contract.py) | **P0**：狗 `委屈·幼犬眼` 01→07 + 150 帧 |
| [`verify_diffusion_prompt_contract.py`](scripts/verify_diffusion_prompt_contract.py) | **P0**：01→08 Prompt（品种名 = `get_dog_breed().label`） |
| [`export_prompt_samples.py`](scripts/export_prompt_samples.py) | 38 套 04 样例 → `_runtime/prompt_samples/` |
| [`s01_从能量生成02.sh`](scripts/s01_从能量生成02.sh) | CLI 出厂 |
| [`s01_导出扩散节拍表.sh`](scripts/s01_导出扩散节拍表.sh) | 导出节拍表 |
| [`s01_设置OpenAI密钥.sh`](scripts/s01_设置OpenAI密钥.sh) | OpenAI Key |
| [`s01_env.sh`](scripts/s01_env.sh) | 环境变量 |
| [`autodl_bootstrap_wan22.sh`](scripts/autodl_bootstrap_wan22.sh) | AutoDL Wan 环境引导 |

---

## 六、预设资产 (`预设资产/`)

三大分类：**情绪包**（S1–S3 气质）· **风格包**（S5）· **底膜包**（几何默认）

### 6.1 情绪包（`情绪包/{human,cat,dog}/*.json`）

| 物种 | 份数 | 说明 |
|------|------|------|
| 人 | 16 | 可与 `control_surface.PRESETS` 同步 |
| 猫 | 12 | 文件名中文；JSON 内 `emotion` 多为 `cat_*` |
| 狗 | 10 | 门户按钮 id = 文件名（如 `委屈·幼犬眼`） |

### 6.2 风格包（`风格包/`）

| 物种 | 数量 | 示例 |
|------|------|------|
| 人 | 9 | 天选者_大祭司、魅惑者_温碧霞、狠厉者_铁血将军… |
| 猫 | 9 | ragdoll_cat、siamese_cat、british_cat、maine_coon、persian_cat… |
| 狗 | 10 | poodle_giant、golden_retriever、husky、shiba_inu… |

### 6.3 底膜包（`底膜包/`）

| 路径 | 作用 |
|------|------|
| [`底膜包/human/species_default.json`](预设资产/底膜包/human/species_default.json) | 人类默认 17 参数 |
| [`底膜包/cat/species_default.json`](预设资产/底膜包/cat/species_default.json) | 猫默认几何 |
| [`底膜包/dog/species_default.json`](预设资产/底膜包/dog/species_default.json) | 狗默认几何 |

---

## 七、客户资产库 (`客户资产库/`)

| 路径 | 说明 |
|------|------|
| `客户_{id}/客户信息.json` | 物种、品种、底膜参数 |
| `客户_{id}/参考素材/` | 上传正面照 |
| `客户_{id}/项目_{pid}/` | 项目配置、调整记录、输出、扩散包 |

---

## 八、文档 (`docs/`)

| 文件 | 作用 |
|------|------|
| [`PROJECT_FILES.md`](docs/PROJECT_FILES.md) | **本文件** |
| [`TOKEN_BUDGET.md`](docs/TOKEN_BUDGET.md) | Token 优化 |
| [`GAZE_ENGINE_MINDMAP.md`](docs/GAZE_ENGINE_MINDMAP.md) | 凝视引擎脑图 |
| [`开源社区对比调研.md`](docs/开源社区对比调研.md) | 社区对比 |

根目录 [`AI_INDEX.md`](AI_INDEX.md) 供 AI Agent 快速定位代码。

---

## 九、计划文档 (`plans/`)

| 文件 | 作用 |
|------|------|
| [`autodl_gpu_rental_and_smoke_test.md`](plans/autodl_gpu_rental_and_smoke_test.md) | AutoDL 租 GPU + 冒烟测试 |

---

## 十、数据流转全图

### 10A. 门户手动测试（当前主路径）

```
客户门户 /portal
  ② 点情绪按钮 → emotion = 预设资产/情绪包/{species}/{名}.json
  ② 点品种按钮 → breed → 风格包
  ③ 输入框写场景（非情绪词）
       │
       ▼
POST /api/portal/pomot/round1
  EmotionRouter(preset_override) → PomotRegistry → SliderPacket
       │
       ▼
delivery_pipeline / dog_pipeline  (01→07)
  finalize → envelope → channels → prior → pulse_quality
       │
       ▼
02_烘焙_{真人律|狗律}.json  +  03 工程底膜 MP4
       │
       ▼
pomot/assembler → 04 Prompt + wan±
       │
       ▼
POST /api/portal/export → Wan 扩散
```

### 10B. 编译链（物种共用骨架）

```
SliderPacket
  → packet_finalize (L1)
  → build_energy_envelope → E(t)
  → channels_from_packet (人/猫/狗 envelope_compile)
  → apply_*_prior (S6)
  → fix_pulse_quality (S7)
  → 02 烘焙 JSON + affine_renderer → 03 MP4
  → rhythm_compiler → 05 节拍表
  → assembler → 08 扩散 Prompt
```

---

*与 [`AI_INDEX.md`](../AI_INDEX.md)、[`合同/README.md`](../合同/README.md) 保持同步；改目录结构时请一并更新三处。*
