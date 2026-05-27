# 👁️ jintao_node_eye · 全量文件清单

> **生成日期**: 2026-05-26 · 最后更新: 2026-05-26
> **入口**: [`tools/01_工作台服务/serve_workbench.py`](tools/01_工作台服务/serve_workbench.py)（HTTP API）+ [`tools/01_工作台服务/能量工作台.html`](tools/01_工作台服务/能量工作台.html)（前端）
> **架构**: 双模驱动中间件（Eye-Figma Engine）— 详见 [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md)

---

## 目录

- [一、根目录文件](#一根目录文件)
- [二、核心引擎 (`gaze_engine/`)](#二核心引擎-gaze_engine)
  - [2.1 公共共享层 (`_shared/`)](#21-公共共享层-_shared)
  - [2.2 人类物种 (`human/`)](#22-人类物种-human)
  - [2.3 猫物种 (`cat/`)](#23-猫物种-cat)
  - [2.4 狗物种 (`dog/`)](#24-狗物种-dog)
  - [2.5 Prompt 模板合成引擎 (`pomot/`)](#25-prompt-模板合成引擎-pomot)
  - [2.6 顶层引擎模块](#26-顶层引擎模块)
- [三、合同规范 (`contracts/`)](#三合同规范-contracts)
- [四、UI 与工具 (`tools/`)](#四ui-与工具-tools)
  - [4.1 工作台服务](#41-工作台服务)
  - [4.2 前端插件](#42-前端插件)
  - [4.3 工具脚本](#43-工具脚本)
- [五、脚本 (`scripts/`)](#五脚本-scripts)
- [六、预设资产 (`预设资产/`)](#六预设资产-预设资产)
  - [6.1 预设情绪包](#61-预设情绪包)
  - [6.2 风格包](#62-风格包)
- [七、客户资产库 (`客户资产库/`)](#七客户资产库-客户资产库)
- [八、文档 (`docs/`)](#八文档-docs)
- [九、计划文档 (`plans/`)](#九计划文档-plans)
- [十、数据流转全图](#十数据流转全图)

---

## 一、根目录文件

| 文件 | 作用 |
|------|------|
| [`__init__.py`](__init__.py) | Python 包初始化 / ComfyUI 节点注册入口 |
| [`AI_INDEX.md`](AI_INDEX.md) | **AI 代码图谱**：供 AI Agent 快速理解全项目结构（~200 tokens） |
| [`README.md`](README.md) | 项目简介 |
| [`.clinerules`](.clinerules) | Roo Code AI 行为规则（最小 Token 消耗原则） |
| [`.cursorrules`](.cursorrules) | Cursor AI 行为规则 |
| [`.env`](.env) | 环境变量（运行态） |
| [`.env.example`](.env.example) | 环境变量示例（OpenAI API Key 等） |
| [`.gitignore`](.gitignore) | Git 忽略规则 |
| [`asset_lib.py`](asset_lib.py) | **预设资产 + 客户资产路径工具函数** |
| [`yolov8n-cls.pt`](yolov8n-cls.pt) | YOLOv8 品种分类模型权重文件 |
| [`一键打开能量工作台.sh`](一键打开能量工作台.sh) | 一键启动脚本（桌面入口，启动工作台服务） |

---

## 二、核心引擎 (`gaze_engine/`)

### 2.1 公共共享层 (`_shared/`)

物种无关的核心逻辑、数据类、编译链。

| 文件 | 作用 | 被谁调用 |
|------|------|---------|
| [`channel_contract.py`](gaze_engine/_shared/channel_contract.py) | **12 操作通道定义**（pupil_x/y, blink, eyebrow 等 12 轨），中文标签，扩散提示语，`validate_baked_delivery()` 出厂校验 | 所有渲染 & 编译模块 |
| [`slider_schema.py`](gaze_engine/_shared/slider_schema.py) | **SliderPacket 数据类**（macro 6 杆 + hold_seg 4 属性），EarParams 耳位参数，LLM 增量合并，情绪→滑杆包映射 | `envelope_compile`, `human_prior`, `packet_finalize` |
| [`slider_bounds.py`](gaze_engine/_shared/slider_bounds.py) | **L1 滑杆禁区机器真源**：戏种分组（压·慑/悲·怯/媚·勾）、预设数值盒半径、G1-G8 全剧种硬禁区、`load_rules()` 供浏览器 JS 和 Python 共用 | `packet_finalize`, 前端 JS |
| [`packet_finalize.py`](gaze_engine/_shared/packet_finalize.py) | **滑杆包收口**：本戏数值盒检查 → 全剧种硬禁区（G1-G8）→ 路人中间带弹回 | `delivery_pipeline.py` |
| [`envelope_compile.py`](gaze_engine/_shared/envelope_compile.py) | **能量包络编译**：SliderPacket → E(t) 能量曲线 → 12×150 全量通道 | `delivery_pipeline.py` |
| [`micro_jitter.py`](gaze_engine/_shared/micro_jitter.py) | **微颤动引擎**：分阶段（蓄力/启动/保持/缓和）的 Hz 和幅度 | `human_prior.py` |
| [`pipeline_io.py`](gaze_engine/_shared/pipeline_io.py) | **各阶段 JSON 读写**：文件名常量（01\_自然语言.txt, 01\_滑杆包.json, 03\_能量包络.json...），读写封装 | 几乎所有管线模块 |
| [`workbench_io.py`](gaze_engine/_shared/workbench_io.py) | **操作台滑杆包读写**：`read_slider_packet()` / `write_slider_packet()`，同步到 `tools/` 目录 | 工作台后端 |
| [`workbench_context.py`](gaze_engine/_shared/workbench_context.py) | **操作台上下文管理**：自然语言 + 能量图说明 + 知识库 + L1 附件 | 工作台后端 |
| [`node1_defaults.py`](gaze_engine/_shared/node1_defaults.py) | **节点 1 默认值加载**：系统 Prompt 和知识库默认文本，占位符检测 | LLM 路由 |
| [`llm_openai.py`](gaze_engine/_shared/llm_openai.py) | **LLM 集成**：OpenAI/ChatGPT 调用，客户自然语言 → SliderPacket，含系统 Prompt 和结构化输出 | `nl_router.py` |
| [`rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py) | **节奏说明书编译器**：从 02\_烘焙\_真人律.json 自动编译为 05\_扩散节拍表.txt | `delivery_pipeline.py` |
| [`export_diffusion_metronome.py`](gaze_engine/_shared/export_diffusion_metronome.py) | **扩散节拍表导出（旧版）**：从烘焙 02 提取节奏时刻 + 通道提示语，⚠️ DEPRECATED 改用 rhythm_compiler | 工作台 / 脚本 |
| [`species_template.py`](gaze_engine/_shared/species_template.py) | **物种底膜模板参数**：`SpeciesTemplate` 数据类（17个可调几何参数）、`species_default_template()` 标准底膜、`template_to_renderer_constants()` 模板→渲染器常量、品种偏移继承 | `customer_db.py`, 三个物种 AffineRenderer |
| [`species_detector.py`](gaze_engine/_shared/species_detector.py) | **自动化底膜检测**：MediaPipe Face Mesh（人脸468关键点）+ OpenCV Haar（猫狗兜底）+ YOLOv8 品种分类。核心 `auto_detect_for_customer()` = 找照片→检测→计算→一键保存 | `serve_workbench.py` |
| [`customer_db.py`](gaze_engine/_shared/customer_db.py) | **客户资产库 CRUD**：客户/项目/调整版本管理、`get_effective_template()` 有效底膜模板获取、`update_template_params()` 自动保存检测参数 | `serve_workbench.py` |
| [`assets/eyelid_raw.png`](gaze_engine/_shared/assets/eyelid_raw.png) | 眼睑原始素材（工程底膜视觉资产） | `affine_renderer.py` |

### 2.2 人类物种 (`human/`)

| 文件 | 作用 | 关键函数 |
|------|------|---------|
| [`control_surface.py`](gaze_engine/human/control_surface.py) | **16 情绪预设唯一真源**（压·慑 5 + 悲·怯 6 + 媚·勾 5），三区滑杆定义（起/动/收），交付链段定义，工作台 JSON 导出 | ⭐ 几乎所有模块依赖 |
| [`affine_renderer.py`](gaze_engine/human/affine_renderer.py) | **人类仿射渲染**：RGB 三色分离（R=眼, G=眉, B=瞳孔）、闭合路径、0-noise ✅ 已启用 | 工程底膜生成 |
| [`human_prior.py`](gaze_engine/human/human_prior.py) | **真人化先验**：二阶欠阻尼扫视动力学（过冲）、盯住段微漂 + 微颤底噪、眉眼延迟耦合、频道跟随 | `delivery_pipeline.py` |
| [`pulse_quality.py`](gaze_engine/human/pulse_quality.py) | **平庸化三检**：Q01 能量不足自动抬升（×1.42 上限）、Q02 保持段杂乱轻平滑、Q03 眉峰不晚于眼自动延后 | `delivery_pipeline.py` |
| [`pad_weights.py`](gaze_engine/human/pad_weights.py) | **人类 PAD 权重表**：愉悦度(P)/唤醒度(A)/支配度(D) 三轴权重 | `human_prior.py` |
| [`envelope_compile.py`](gaze_engine/human/envelope_compile.py) | **人类通道编译**：E(t) + PAD 投影 + eyebrow 滞后 + pulse 耦合 → 12 通道 × 150 帧 | `delivery_pipeline.py` |
| [`persona_compiler.py`](gaze_engine/human/persona_compiler.py) | **九大人格编译**：从预设资产人格包加载人格定义，生成人格化参数 | 工作台管线 |
| [`persona_matrix.json`](gaze_engine/human/persona_matrix.json) | **9 人格矩阵**：人格 ID → 性格偏向的映射数据（JSON 静态） | `persona_compiler.py` |
| [`rhythm_data.py`](gaze_engine/human/rhythm_data.py) | **节奏说明书人类文案**：各通道中文短语模板 | `rhythm_compiler.py` |

### 2.3 猫物种 (`cat/`)

| 文件 | 作用 |
|------|------|
| [`presets.py`](gaze_engine/cat/presets.py) | **12 猫情绪预设**（警觉瞪视、狩猎锁定、委屈呜咽…） |
| [`breeds.py`](gaze_engine/cat/breeds.py) | 猫品种配置（布偶/暹罗/英短/田园） |
| [`breed_matrix.json`](gaze_engine/cat/breed_matrix.json) | 猫品种风格矩阵 |
| [`channel_adapter.py`](gaze_engine/cat/channel_adapter.py) | **EarParams → 12 通道映射**：left_angle→eyebrow, right_angle→brow_raise（-1~1→0~1） |
| [`affine_renderer.py`](gaze_engine/cat/affine_renderer.py) | **猫仿射渲染**：CatEyeMesh + 耳位渲染 |
| [`prior.py`](gaze_engine/cat/prior.py) | 猫扫视 + 三眼睑 + 耳耦合 |
| [`detect.py`](gaze_engine/cat/detect.py) | **猫面部检测**：基于 OpenCV Haar 猫脸检测 + 耳位估计 + YOLOv8 品种推断 |
| [`pulse_quality.py`](gaze_engine/cat/pulse_quality.py) | 猫质检规则 |
| [`pad_weights.py`](gaze_engine/cat/pad_weights.py) | 猫 PAD 权重表 |
| [`rhythm_data.py`](gaze_engine/cat/rhythm_data.py) | 节奏说明书猫文案 |
| [`envelope_compile.py`](gaze_engine/cat/envelope_compile.py) | 猫通道编译：通用 scale×envelope，耳位由 channel_adapter 注入 |

### 2.4 狗物种 (`dog/`)

| 文件 | 作用 |
|------|------|
| [`presets.py`](gaze_engine/dog/presets.py) | **10 狗情绪预设**（警觉·竖耳、委屈·幼犬眼、凶狠·威吓…） |
| [`breeds.py`](gaze_engine/dog/breeds.py) | 狗品种配置（巨型贵宾等） |
| [`breed_matrix.json`](gaze_engine/dog/breed_matrix.json) | 狗品种风格矩阵 |
| [`channel_adapter.py`](gaze_engine/dog/channel_adapter.py) | **EarParams → 12 通道映射**：与猫版对称，区别是狗版 brow_raise 保留给眉脊（狗有眉毛肌） |
| [`affine_renderer.py`](gaze_engine/dog/affine_renderer.py) | **狗仿射渲染**：DogEyeMesh + 耳位渲染 |
| [`prior.py`](gaze_engine/dog/prior.py) | 狗扫视 + 耳耦合 |
| [`detect.py`](gaze_engine/dog/detect.py) | **狗面部检测**：基于 OpenCV Haar 狗脸检测 + 耳位估计 + YOLOv8 品种推断 |
| [`pulse_quality.py`](gaze_engine/dog/pulse_quality.py) | 狗质检规则 |
| [`pad_weights.py`](gaze_engine/dog/pad_weights.py) | 狗 PAD 权重表 |
| [`rhythm_data.py`](gaze_engine/dog/rhythm_data.py) | 节奏说明书狗文案 |
| [`envelope_compile.py`](gaze_engine/dog/envelope_compile.py) | 狗通道编译：通用 scale×envelope，耳位由 channel_adapter 注入 |
| [`dog_pipeline.py`](gaze_engine/dog/dog_pipeline.py) | **狗完整管线**：SliderPacket → 12 通道 → EarParams 注入 → 工程底膜 → Wan 输出 |

### 2.5 Prompt 模板合成引擎 (`pomot/`)

> 预设 Prompt 模板合成引擎（面向扩散引擎的提示词生成）

| 文件 | 作用 |
|------|------|
| [`pipeline.py`](gaze_engine/pomot/pipeline.py) | **管线入口**：round1（预设+NL→SliderPacket）/ round2（delta 微调） |
| [`nl_splitter.py`](gaze_engine/pomot/nl_splitter.py) | **NL 拆解器**：一句话 → 动作 + 情绪 |
| [`emotion_router.py`](gaze_engine/pomot/emotion_router.py) | **情绪路由**：情绪词 → 预设名 + 物种 |
| [`registry.py`](gaze_engine/pomot/registry.py) | **预设注册表**：按 (species, breed, preset) 加载 |
| [`templates.py`](gaze_engine/pomot/templates.py) | **数据类**：NLSplitResult, EmotionRoute, PresetPromptTemplate |
| [`composer.py`](gaze_engine/pomot/composer.py) | **第一轮合成**：预设 + NL → SliderPacket |
| [`delta.py`](gaze_engine/pomot/delta.py) | **第二轮微调**：delta 叠加 |
| [`assembler.py`](gaze_engine/pomot/assembler.py) | **最终拼装**：02\_json → 04\_Prompt.txt → 送扩散引擎 |

### 2.6 顶层引擎模块

| 文件 | 作用 | 关键函数 |
|------|------|---------|
| [`delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) | **主交付链入口**（人类 + 物种路由）：SliderPacket → 编译 → prior → pulse_quality → 烘焙定稿 02 | `run_delivery()`:62, `run_delivery_from_packet()`:123 |
| [`nl_intent.py`](gaze_engine/nl_intent.py) | **NL 意图分类**：咨询(consult) vs 生成/修改(apply)，关键词 + 正则匹配 + 物种识别 | `classify_intent_keyword()`:35 |
| [`nl_router.py`](gaze_engine/nl_router.py) | **NL 路由主入口**：`process_customer_nl()` 分发到 LLM 或关键词回退，整合知识库 | `process_customer_nl()`:47 |
| [`nl_to_packet.py`](gaze_engine/nl_to_packet.py) | **关键词 → 预设匹配**：18 个中文关键词 → 16 预设名，关键词回退生成 SliderPacket | `packet_from_natural_language()`:240 |
| [`base_mesh_gen.py`](gaze_engine/base_mesh_gen.py) | **基础网格生成**：眼眉区域三角网格顶点定义 | `generate()`:63 |
| [`audio_compiler.py`](gaze_engine/audio_compiler.py) | **音频编译**：音频脉冲与视觉节拍对齐 ⚠️ 当前 `_AUDIO_DISABLED`，重建中 | — |
| [`test_persona_integrity.py`](gaze_engine/test_persona_integrity.py) | 人格完整性自检 | — |

---

## 三、合同规范 (`contracts/`)

> 📐 全部使用统一五段格式（目的/数据流/合同条款/验收标准/审计）

| 目录 | 文件 | 内容 |
|------|------|------|
| — | [`合同规范.md`](contracts/合同规范.md) | 统一合同模板规范 |
| — | [`README.md`](contracts/README.md) | `contracts/` 目录说明 |
| **01\_总纲** | [`滑杆规范.md`](contracts/01_总纲/滑杆规范.md) | **滑杆总规范**：设计原则、SliderPacket 格式、宏观六滑杆、16 预设、L1 禁区 G1-G8、Python 映射链 |
| | [`节奏说明书.md`](contracts/01_总纲/节奏说明书.md) | **节奏说明书规范**：Wan 扩散引擎消费的节奏说明书格式与语义 |
| | [`节奏说明书编译器.md`](contracts/01_总纲/节奏说明书编译器.md) | **节奏说明书编译器合同**：`rhythm_compiler.py` 的编译规则和验收标准 |
| | [`全量帧指令集规范.md`](contracts/01_总纲/全量帧指令集规范.md) | **12 轨全量帧规范**：时间容器、真值层级、12 通道定义、分通道节奏合同 R01-R07、验收清单 |
| | [`眼眉真人默认律.md`](contracts/01_总纲/眼眉真人默认律.md) | **Human Prior 合同**：正常人原则（过冲/底噪/延迟）、二阶扫视动力学、平庸三检 Q01-Q03 |
| | [`眼眉指令集_全局情绪节奏主钟.md`](contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md) | **全局情绪节奏主钟**：眼眉指令集情绪节奏主钟定义 |
| **02\_情绪** | [`魅惑勾人.md`](contracts/02_情绪/魅惑勾人.md) | 魅惑·勾人情绪的专项规范 |
| **03\_工程底膜** | [`工程底膜合同.md`](contracts/03_工程底膜/工程底膜合同.md) | **工程底膜合同**：RGB 三色分离格式协议 + 验收标准 |
| | [`工程底膜驱动规范.md`](contracts/03_工程底膜/工程底膜驱动规范.md) | **工程底膜驱动规范**：`affine_renderer` 核心机制 + 注意事项 |
| **04\_接口** | [`UI设计原则.md`](contracts/04_接口/UI设计原则.md) | 工作台交互设计原则 |
| | [`扩散引擎提示词拼装规范.md`](contracts/04_接口/扩散引擎提示词拼装规范.md) | 扩散引擎提示词拼装规范 |
| **05\_人格化** | [`风格化偏向.md`](contracts/05_人格化/风格化偏向.md) | 人格风格化偏向规则 |
| **06\_架构** | [`流程设计.md`](contracts/06_架构/流程设计.md) | **顶层架构设计**：双模驱动中间件架构说明 |
| | [`pomot合成规范.md`](contracts/06_架构/pomot合成规范.md) | Prompt 模板合成引擎规范 |
| | [`公共层边界合同.md`](contracts/06_架构/公共层边界合同.md) | **公共层边界合同**：公共层与物种层之间的接口边界 |

---

## 四、UI 与工具 (`tools/`)

### 4.1 工作台服务

| 文件 | 作用 |
|------|------|
| [`serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) | **HTTP 后端主入口**（v12）：管线 API + **客户资产库 CRUD + 照片上传/底膜检测**。端点：`POST /api/customer/upload-photo`（base64 上传→自动检测→保存模板）、`GET /api/customer/photos/{cid}`（照片列表）、`GET /api/customer/photo-preview/{cid}/{name}`（预览） |
| [`workbench_backend.py`](tools/01_工作台服务/workbench_backend.py) | ⭐ **管线后端核心**：`_compile_pipeline_all()` 管线全量编译（:249），旧版客户数据库 FastAPI 端点 |
| [`能量工作台.html`](tools/01_工作台服务/能量工作台.html) | **前端 UI**：情绪选择、滑杆调节、管线运行、3D 视口预览、客户照片上传区 |
| [`static/app.js`](tools/01_工作台服务/static/app.js) | 前端 JS 逻辑（工作台交互、API 调用、**照片上传+自动底膜检测**） |
| [`static/style.css`](tools/01_工作台服务/static/style.css) | 前端样式 |

### 4.2 前端插件

| 文件 | 作用 |
|------|------|
| [`packet_finalize_ui.js`](tools/02_前端插件/packet_finalize_ui.js) | 前端 L1 滑杆禁区校验 JS |
| [`slider_forbidden_bounds.js`](tools/02_前端插件/slider_forbidden_bounds.js) | 滑杆禁区边界渲染（由 Python 导出） |
| [`workbench_pipeline_ui.js`](tools/02_前端插件/workbench_pipeline_ui.js) | 工作台管线交互 UI 逻辑 |

### 4.3 工具脚本

| 文件 | 作用 |
|------|------|
| [`build_standalone_share.py`](tools/03_工具脚本/build_standalone_share.py) | 从能量工作台.html 生成单文件分享版（内嵌 pipeline\_cache） |
| [`build_workbench_pipeline_cache.py`](tools/03_工具脚本/build_workbench_pipeline_cache.py) | **管线缓存生成**：为 16 个预设预编译全量 JSON 缓存（pipeline\_cache/*.json） |
| [`estimate_template_from_photo.py`](tools/03_工具脚本/estimate_template_from_photo.py) | 从照片估算底膜模板参数 |
| [`ssh_autodl.py`](tools/03_工具脚本/ssh_autodl.py) | SSH 连接 AutoDL 远程服务器 |
| [`ssh_check_dirs.py`](tools/03_工具脚本/ssh_check_dirs.py) | SSH 远程目录检查 |
| [`ssh_check_models.py`](tools/03_工具脚本/ssh_check_models.py) | SSH 远程模型文件检查 |
| [`ssh_check_storage.py`](tools/03_工具脚本/ssh_check_storage.py) | SSH 远程存储空间检查 |
| [`ssh_download_models.py`](tools/03_工具脚本/ssh_download_models.py) | SSH 远程模型下载 |
| [`ssh_fast_setup.py`](tools/03_工具脚本/ssh_fast_setup.py) | SSH 远程快速环境搭建 |
| [`ssh_find_python.py`](tools/03_工具脚本/ssh_find_python.py) | SSH 查找远端 Python 解释器 |
| [`ssh_restart_dl.py`](tools/03_工具脚本/ssh_restart_dl.py) | SSH 重启远端下载服务 |
| [`ssh_start_downloads.py`](tools/03_工具脚本/ssh_start_downloads.py) | SSH 启动远端下载任务 |

---

## 五、脚本 (`scripts/`)

| 文件 | 作用 |
|------|------|
| [`s01_从能量生成02.sh`](scripts/s01_从能量生成02.sh) | **主出厂 CLI**：从 03\_能量包络.json → 04\_Prompt.txt + 工程底膜 (各种变体) |
| [`s01_五样本烘焙02.sh`](scripts/s01_五样本烘焙02.sh) | **批量烘焙**：5 个预设样本 → 02\_烘焙\_真人律.json |
| [`s01_导出扩散节拍表.sh`](scripts/s01_导出扩散节拍表.sh) | 导出扩散引擎节拍表 |
| [`s01_设置OpenAI密钥.sh`](scripts/s01_设置OpenAI密钥.sh) | 配置 OpenAI API Key |
| [`s01_env.sh`](scripts/s01_env.sh) | 环境变量加载 |

---

## 六、预设资产 (`预设资产/`)

### 6.1 预设情绪包

**人类 (16种)**：施压·凝视、冷压·决心、威慑·一瞬、怒视·压人、鄙夷·冷瞥、可怜·委屈、要哭未哭、崩溃·泄劲、哀求·仰望、惊惧·一怔、空竭·死心、魅惑·勾人、纯甜·含情、媚杀·一眼、若即若离、打量·玩味

**猫 (12种)**：警觉瞪视、狩猎锁定、委屈呜咽、受惊炸毛、亲昵眯眼、满足幸福、困倦垂眼、恐惧贴耳、好奇歪头、愤怒嘶哈、烦闷甩尾、玩耍扑击

**狗 (10种)**：警觉·竖耳、委屈·幼犬眼、凶狠·威吓、兴奋·期待、满足·眯眼、困倦·犯懒、守护·凝视、困惑·歪头、渴望·仰望、害怕·退缩

### 6.2 风格包

| 物种 | 风格 | 路径 |
|------|------|------|
| 人类 | 天选者_大祭司 | [`预设资产/风格包/human/天选者_大祭司/style.json`](预设资产/风格包/human/天选者_大祭司/style.json) |
| 人类 | 魅惑者_部落巫医 | [`预设资产/风格包/human/魅惑者_部落巫医/style.json`](预设资产/风格包/human/魅惑者_部落巫医/style.json) |
| 人类 | 魅惑者_温碧霞 | [`预设资产/风格包/human/魅惑者_温碧霞/style.json`](预设资产/风格包/human/魅惑者_温碧霞/style.json) |
| 人类 | 狠厉者_铁血将军 | [`预设资产/风格包/human/狠厉者_铁血将军/style.json`](预设资产/风格包/human/狠厉者_铁血将军/style.json) |
| 人类 | 怯弱者_逃兵 | [`预设资产/风格包/human/怯弱者_逃兵/style.json`](预设资产/风格包/human/怯弱者_逃兵/style.json) |
| 人类 | 悲悯者_圣徒 | [`预设资产/风格包/human/悲悯者_圣徒/style.json`](预设资产/风格包/human/悲悯者_圣徒/style.json) |
| 人类 | 呆滞者_傀儡 | [`预设资产/风格包/human/呆滞者_傀儡/style.json`](预设资产/风格包/human/呆滞者_傀儡/style.json) |
| 人类 | 癫狂者_疯僧 | [`预设资产/风格包/human/癫狂者_疯僧/style.json`](预设资产/风格包/human/癫狂者_疯僧/style.json) |
| 人类 | 天真者_幼童 | [`预设资产/风格包/human/天真者_幼童/style.json`](预设资产/风格包/human/天真者_幼童/style.json) |
| 猫 | 布偶猫（温顺型） | [`预设资产/风格包/cat/ragdoll_cat/style.json`](预设资产/风格包/cat/ragdoll_cat/style.json) |
| 猫 | 暹罗猫（高冷型） | [`预设资产/风格包/cat/siamese_cat/style.json`](预设资产/风格包/cat/siamese_cat/style.json) |
| 猫 | 田园猫（机敏型） | [`预设资产/风格包/cat/stray_cat/style.json`](预设资产/风格包/cat/stray_cat/style.json) |
| 猫 | 英短（憨厚型） | [`预设资产/风格包/cat/british_cat/style.json`](预设资产/风格包/cat/british_cat/style.json) |
| 狗 | 巨型贵宾（优雅型） | [`预设资产/风格包/dog/poodle_giant/style.json`](预设资产/风格包/dog/poodle_giant/style.json) |

---

## 七、客户资产库 (`客户资产库/`)

| 路径 | 说明 |
|------|------|
| [`客户资产库/客户_C001/`](客户资产库/客户_C001/) | 客户 C001 根目录 |
| [`客户资产库/客户_C001/客户信息.json`](客户资产库/客户_C001/客户信息.json) | 客户档案（物种、品种、备注） |
| [`客户资产库/客户_C001/项目_P001/项目配置.json`](客户资产库/客户_C001/项目_P001/项目配置.json) | 项目 P001 配置 |
| [`客户资产库/客户_C001/项目_P001/滑杆调整记录.json`](客户资产库/客户_C001/项目_P001/滑杆调整记录.json) | 滑杆调整版本历史 |
| [`客户资产库/客户_C001/项目_P001/调整过程/`](客户资产库/客户_C001/项目_P001/调整过程/) | 版本快照目录 |
| [`客户资产库/客户_C001/项目_P001/参考素材/`](客户资产库/客户_C001/项目_P001/参考素材/) | 参考素材（上传照片、处理结果预览） |
| [`客户资产库/客户_C001/项目_P001/计划文档/`](客户资产库/客户_C001/项目_P001/计划文档/) | 项目计划文档 |

---

## 八、文档 (`docs/`)

| 文件 | 作用 |
|------|------|
| [`PROJECT_FILES.md`](docs/PROJECT_FILES.md) | **本文件**：全量文件清单 |
| [`AI_INDEX.md`](AI_INDEX.md) | **AI 代码图谱**（位于根目录，供 AI Agent 消费） |
| [`TOKEN_BUDGET.md`](docs/TOKEN_BUDGET.md) | **Token 优化指南**：优化措施、量化方法、最佳实践 |
| [`GAZE_ENGINE_MINDMAP.md`](docs/GAZE_ENGINE_MINDMAP.md) | **凝视引擎脑图**：架构脑图、模块关系 |
| [`开源社区对比调研.md`](docs/开源社区对比调研.md) | **开源社区对比调研**：同类项目对比分析 |

---

## 九、计划文档 (`plans/`)

| 文件 | 作用 |
|------|------|
| [`automated_template_detection.md`](plans/automated_template_detection.md) | 自动化底膜检测计划 |
| [`refactor_envelope_compile.md`](plans/refactor_envelope_compile.md) | 能量包络编译重构计划 |

---

## 十、数据流转全图

```
自然语言 / UI滑杆
      │
      ▼
┌─ nl_intent.py / nl_router.py ─────────────┐
│  意图分类 (consult / apply)                │
│  → LLM / 关键词回退                        │
│  → SliderPacket                            │
└────────────────────────────────────────────┘
      │
      ▼
┌─ packet_finalize.py ──────────────────────┐
│  L1 禁区校验 (G1-G8)                       │
│  弹性弹回 → 合格 SliderPacket              │
└────────────────────────────────────────────┘
      │
      ▼
┌─ envelope_compile.py (_shared) ───────────┐
│  E(t) 能量曲线 (4 段时序)                   │
│  纯数学层 (物种无关)                        │
└────────────────────────────────────────────┘
      │
      ▼
┌─ channels_from_packet() ──────────────────┐
│  human/cat/dog/envelope_compile.py         │
│  E(t) + PAD投影 → 12通道 × 150帧          │
└────────────────────────────────────────────┘
      │
      ▼
┌─ apply_prior() ───────────────────────────┐
│  human_prior / cat/prior / dog/prior       │
│  物理仿真 (扫视/微颤/延迟/耳耦合)            │
└────────────────────────────────────────────┘
      │
      ▼
┌─ fix_pulse_quality() ─────────────────────┐
│  pulse_quality (各物种独立)                 │
│  Q01/Q02/Q03 质量控制                      │
└────────────────────────────────────────────┘
      │
      ▼
┌─ 视觉封装 ────────────────────────────────┐
│  02_烘焙_真人律.json (12通道关键帧)          │
│  工程底膜 (RGB三色分离 PNG)                 │
│  扩散节拍表 (rhythm_compiler)              │
│  Prompt 模板 (pomot/assembler)             │
└────────────────────────────────────────────┘
      │
      ▼
    Wan 扩散引擎 → 视频生成
