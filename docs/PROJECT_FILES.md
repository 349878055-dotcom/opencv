# 能量控制台 · 全量文件清单

> 生成日期: 2026-05-25 · 最后更新: 2026-05-25
> 架构变更：已脱离 ComfyUI，全 Web 模式。`nodes_v1.py` → `_archive/`，`workflows/` 已删除。
> 新入口：[`tools/01_工作台服务/serve_workbench.py`](tools/01_工作台服务/serve_workbench.py)（HTTP API）+ [`tools/01_工作台服务/能量工作台.html`](tools/01_工作台服务/能量工作台.html)（前端）

---

## 🧠 一、核心Python引擎 (`gaze_engine/`)

共 30 个 Python 模块 + 1 个 JSON 矩阵 + 1 个测试文件。

### 数据模型 & 预设（唯一真源）

| 文件 | 作用 | 谁在用 |
|------|------|--------|
| [`gaze_engine/human/control_surface.py`](gaze_engine/human/control_surface.py) | **16情绪预设唯一真源**（压·慑5 + 悲·怯6 + 媚·勾5），三区滑杆定义(起/动/收)，交付链段定义，工作台JSON导出 | 几乎所有模块 |
| [`gaze_engine/_shared/slider_schema.py`](gaze_engine/_shared/slider_schema.py) | SliderPacket 数据类定义（macro 6杆 + hold_seg 4属性），EarParams 耳位参数，LLM增量合并，情绪→滑杆包映射 | envelope_compile, human_prior, packet_finalize |
| [`gaze_engine/_shared/slider_bounds.py`](gaze_engine/_shared/slider_bounds.py) | **L1滑杆禁区机器真源**：戏种分组(压·慑/悲·怯/媚·勾)、预设数值盒半径、G1-G8全剧种硬禁区、load_rules()供浏览器JS和Python共用 | packet_finalize, export_slider_forbidden_js.py |

### 编译链（滑杆 → 全量帧）

| 文件 | 作用 | 步骤 |
|------|------|------|
| [`gaze_engine/_shared/packet_finalize.py`](gaze_engine/_shared/packet_finalize.py) | **滑杆包收口**：本戏数值盒检查 → 全剧种硬禁区(G1-G8) → 路人中间带弹回 | ①→②之间 |
| [`gaze_engine/_shared/envelope_compile.py`](gaze_engine/_shared/envelope_compile.py) | **能量包络编译**：SliderPacket → E(t)能量曲线 → 12×150全量通道(pupil_x/y/blink/eyebrow/squint等12轨) | ③ |
| [`gaze_engine/human/human_prior.py`](gaze_engine/human/human_prior.py) | **真人化**：二阶欠阻尼扫视动力学(过冲)、盯住段微漂+微颤底噪、眉眼延迟耦合、频道跟随 | ④ |
| [`gaze_engine/human/pulse_quality.py`](gaze_engine/human/pulse_quality.py) | **平庸化三检**：Q01能量不足自动抬升(×1.42上限)、Q02保持段杂乱轻平滑、Q03眉峰不晚于眼自动延后 | ④b |
| [`gaze_engine/_shared/micro_jitter.py`](gaze_engine/_shared/micro_jitter.py) | **微颤动引擎**：分阶段(蓄力/启动/保持/缓和)的Hz和幅度，human_prior调用 | human_prior |

### 12通道合同

| 文件 | 作用 |
|------|------|
| [`gaze_engine/_shared/channel_contract.py`](gaze_engine/_shared/channel_contract.py) | **12操作通道定义**(pupil_x/y, blink, eyebrow, pupil_scale, iris_scale, cornea_bulge, squint, brow_raise, lid_upper, lid_lower, eye_gloss)，中文标签，扩散提示语，validate_baked_delivery()出厂校验 |

### 交付链 & 批量

| 文件 | 作用 |
|------|------|
| [`gaze_engine/delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) | **主交付链入口**（人类+物种路由）：SliderPacket → 编译 → human_prior → pulse_quality → 烘焙定稿02。`run_delivery_from_packet()` / `run_delivery()` |
| [`gaze_engine/dog/dog_pipeline.py`](gaze_engine/dog/dog_pipeline.py) | **狗完整管线**：SliderPacket → 12通道 → EarParams注入 → 工程底膜 → Wan输出。与人类 delivery_pipeline.py 对称但使用 DOG_PAD_WEIGHTS |
| [`gaze_engine/_shared/batch_presets.py`](gaze_engine/_shared/batch_presets.py) | **五样本批量烘焙**：施压·凝视/可怜·委屈/魅惑·勾人/惊惧·一怔/崩溃·泄劲 → 五个02烘焙JSON |

### 自然语言 → 情绪

| 文件 | 作用 |
|------|------|
| [`gaze_engine/nl_intent.py`](gaze_engine/nl_intent.py) | **NL意图分类**：咨询(consult) vs 生成/修改(apply)，关键词+正则匹配 |
| [`gaze_engine/nl_router.py`](gaze_engine/nl_router.py) | **NL路由主入口**：`process_customer_nl()` 分发到LLM或关键词回退，整合知识库 |
| [`gaze_engine/nl_to_packet.py`](gaze_engine/nl_to_packet.py) | **关键词→预设匹配**：18个中文关键词(施压/魅惑/可怜/惊惧…) → 16预设名，关键词回退生成SliderPacket |
| [`gaze_engine/_shared/llm_openai.py`](gaze_engine/_shared/llm_openai.py) | **LLM集成**：OpenAI/ChatGPT调用，客户自然语言→SliderPacket，包含系统Prompt和结构化输出 |

### 文件IO & 上下文

| 文件 | 作用 |
|------|------|
| [`gaze_engine/_shared/pipeline_io.py`](gaze_engine/_shared/pipeline_io.py) | **各阶段JSON读写**：文件名常量(01_自然语言.txt, 01_滑杆包.json, 03_能量包络.json, 04_全量_包络展开.json, 05_全量_真人律.json, 06_全量_平庸纠正.json, 02_烘焙_真人律.json)，读写封装 |
| [`gaze_engine/_shared/workbench_io.py`](gaze_engine/_shared/workbench_io.py) | **操作台滑杆包读写**：`read_slider_packet()` / `write_slider_packet()`，同步到tools/目录 |
| [`gaze_engine/_shared/workbench_context.py`](gaze_engine/_shared/workbench_context.py) | **操作台上下文管理**：自然语言+能量图说明+知识库+L1附件，与Comfy节点同步 |
| [`gaze_engine/_shared/node1_defaults.py`](gaze_engine/_shared/node1_defaults.py) | **节点1默认值加载**：系统Prompt和知识库默认文本，占位符检测 |

### 扩散 & 人格 & 视觉模块

| 文件 | 作用 |
|------|------|
| [`gaze_engine/_shared/export_diffusion_metronome.py`](gaze_engine/_shared/export_diffusion_metronome.py) | **扩散节拍表导出**：从烘焙02提取节奏时刻+通道提示语，生成05_扩散节拍表.txt，供Wan扩散引擎使用 |
| [`gaze_engine/_shared/rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py) | **节奏说明书编译器**：从02_烘焙_真人律.json自动编译为05_扩散节拍表.txt，双向兼容旧版 metronome 签名。合同规范：[`contracts/01_总纲/节奏说明书编译器.md`](contracts/01_总纲/节奏说明书编译器.md) |
| [`gaze_engine/_shared/persona_compiler.py`](gaze_engine/_shared/persona_compiler.py) | **人格编译**：从预设资产人格包加载人格定义，生成人格化参数 |
| [`gaze_engine/_shared/persona_matrix.json`](gaze_engine/_shared/persona_matrix.json) | **9人格矩阵**：人格ID→性格偏向的映射数据（JSON静态） |
| [`gaze_engine/base_mesh_gen.py`](gaze_engine/base_mesh_gen.py) | **基础网格生成**：眼眉区域三角网格顶点定义 |
| [`gaze_engine/human/affine_renderer.py`](gaze_engine/human/affine_renderer.py) | **人类仿射渲染**：RGB三色分离(R=眼,G=眉,B=瞳孔)、闭合路径、0-noise。⚠️ 已启用 |
| [`gaze_engine/cat/affine_renderer.py`](gaze_engine/cat/affine_renderer.py) | **猫仿射渲染**：CatEyeMesh + 耳位渲染 |
| [`gaze_engine/dog/affine_renderer.py`](gaze_engine/dog/affine_renderer.py) | **狗仿射渲染**：DogEyeMesh + 耳位渲染 |
| [`gaze_engine/audio_compiler.py`](gaze_engine/audio_compiler.py) | **音频编译**：音频脉冲与视觉节拍对齐。⚠️ 当前 `_AUDIO_DISABLED`，重建中 |

### 宠物通道适配器

| 文件 | 作用 |
|------|------|
| [`gaze_engine/cat/channel_adapter.py`](gaze_engine/cat/channel_adapter.py) | **猫 EarParams→12通道映射**：left_angle→eyebrow, right_angle→brow_raise（-1~1→0~1） |
| [`gaze_engine/dog/channel_adapter.py`](gaze_engine/dog/channel_adapter.py) | **狗 EarParams→12通道映射**：与猫版对称，区别是狗版 brow_raise 保留给眉脊（狗有眉毛肌） |

### 基础 & 测试

| 文件 | 作用 |
|------|------|
| [`gaze_engine/__init__.py`](gaze_engine/__init__.py) | Python包初始化 |
| [`gaze_engine/test_persona_integrity.py`](gaze_engine/test_persona_integrity.py) | 人格完整性自检 |
| `gaze_engine/.gitkeep` | 保持目录在Git中 |

---

## 🎛️ 二、ComfyUI 节点（已归档）

| 文件 | 作用 |
|------|------|
| （已迁移至 Web 模式，`nodes_v1.py` 已移入 `_archive/`） |

---

## 👁️ 三、工程底膜素材 (`gaze_engine/_shared/assets/`)

| 路径 | 内容 |
|------|------|
| [`eye_asset/derived/eyelid_raw.png`](eye_asset/derived/eyelid_raw.png) | 眼睑原始素材（派生资产） |

> 用于仿射渲染管线的视觉资产。

---

## 🖥️ 四、UI & 工具 (`tools/`)

### 工作台服务（主入口）

| 文件 | 作用 |
|------|------|
| [`tools/01_工作台服务/serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) | **HTTP后端主入口**：POST /api/run-pipeline, POST /api/nl-to-packet, GET /api/asset-browser 等端点 |
| [`tools/01_工作台服务/能量工作台.html`](tools/01_工作台服务/能量工作台.html) | **前端UI**：情绪选择、滑杆调节、管线运行、3D视口预览 |

### 前端插件（工作台自动加载）

| 文件 | 作用 |
|------|------|
| [`tools/02_前端插件/packet_finalize_ui.js`](tools/02_前端插件/packet_finalize_ui.js) | 前端L1滑杆禁区校验JS |
| [`tools/02_前端插件/slider_forbidden_bounds.js`](tools/02_前端插件/slider_forbidden_bounds.js) | 滑杆禁区边界渲染（由 `export_slider_forbidden_js.py` 导出） |
| [`tools/02_前端插件/workbench_pipeline_ui.js`](tools/02_前端插件/workbench_pipeline_ui.js) | 工作台管线交互UI逻辑 |

### 工具脚本

| 文件 | 作用 |
|------|------|
| [`tools/03_工具脚本/build_standalone_share.py`](tools/03_工具脚本/build_standalone_share.py) | 从能量工作台.html生成单文件分享版（内嵌pipeline_cache） |
| [`tools/03_工具脚本/build_workbench_pipeline_cache.py`](tools/03_工具脚本/build_workbench_pipeline_cache.py) | **管线缓存生成**：为16个预设预编译全量JSON缓存(pipeline_cache/*.json)，供工作台加载 |

### 缓存数据（运行时）

| 路径 | 内容 |
|------|------|
| `tools/04_缓存数据/pipeline_cache/` | 16预设的预编译全量JSON缓存，供工作台高速加载 |
| `tools/04_缓存数据/preview_cache/` | 预览帧缓存（_bench_cap, _bench_ff, five_frames, skeleton_frames） |

### 其他工具

| 文件 | 作用 |
|------|------|
| [`tools/05_其他工具/底模视觉几何调校器.html`](tools/05_其他工具/底模视觉几何调校器.html) | 独立视觉几何调校工具 |
| [`tools/05_其他工具/dog_full_body_test.py`](tools/05_其他工具/dog_full_body_test.py) | **狗管线 Wan 资产打包测试**：输出工程底膜视频 + 02烘焙 + 扩散节拍表 + Wan Prompt |

---

## 📜 五、合同 & 规范 (`contracts/`)

| 文件 | 内容 |
|------|------|
| [`contracts/合同规范.md`](contracts/合同规范.md) | 📐 统一合同模板（五段格式：目的/数据流/合同条款/验收标准/审计） |
| [`contracts/README.md`](contracts/README.md) | contracts目录说明 |
| [`contracts/01_总纲/滑杆规范.md`](contracts/01_总纲/滑杆规范.md) | **滑杆总规范**：设计原则、SliderPacket格式、宏观六滑杆(起/动/收)、盯住段三属性、16预设、L1禁区G1-G8、Python映射链 |
| [`contracts/01_总纲/节奏说明书.md`](contracts/01_总纲/节奏说明书.md) | **节奏说明书规范**：Wan扩散引擎消费的节奏说明书格式与语义 |
| [`contracts/01_总纲/节奏说明书编译器.md`](contracts/01_总纲/节奏说明书编译器.md) | **节奏说明书编译器合同**：[`rhythm_compiler.py`](gaze_engine/_shared/rhythm_compiler.py) 的编译规则和验收标准 |
| [`contracts/01_总纲/全量帧指令集规范.md`](contracts/01_总纲/全量帧指令集规范.md) | **12轨全量帧规范**：时间容器(30fps×150帧×5s)、真值层级、12通道定义、能量四段、分通道节奏合同R01-R07、烘焙02格式、扩散节拍、验收清单 |
| [`contracts/01_总纲/眼眉真人默认律.md`](contracts/01_总纲/眼眉真人默认律.md) | **Human Prior合同**：正常人原则(过冲/底噪/延迟)、扫视二阶动力学、盯住活劲、12轨耦合、平庸三检Q01-Q03、合格标准 |
| [`contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md`](contracts/01_总纲/眼眉指令集_全局情绪节奏主钟.md) | **全局情绪节奏主钟**：眼眉指令集的情绪节奏主钟定义，OpenCV只输出三色几何控制图 |
| [`contracts/02_情绪/魅惑勾人.md`](contracts/02_情绪/魅惑勾人.md) | 魅惑·勾人情绪的专项规范 |
| [`contracts/03_工程底膜/工程底膜合同.md`](contracts/03_工程底膜/工程底膜合同.md) | **工程底膜合同**：RGB 三色分离格式协议 + 验收标准 |
| [`contracts/03_工程底膜/工程底膜驱动规范.md`](contracts/03_工程底膜/工程底膜驱动规范.md) | **工程底膜驱动规范**：affine_renderer 核心机制 + 注意事项 |
| [`contracts/04_接口/UI设计原则.md`](contracts/04_接口/UI设计原则.md) | 工作台交互设计原则 |
| [`contracts/05_人格化/风格化偏向.md`](contracts/05_人格化/风格化偏向.md) | 人格风格化偏向规则 |
| [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md) | **顶层架构设计**：双模驱动中间件架构说明 |

---

## 📜 六、脚本 (`scripts/`)

### 主流程脚本

| 文件 | 作用 |
|------|------|
| [`scripts/s01_从能量生成02.sh`](scripts/s01_从能量生成02.sh) | **主出厂**：单预设 → 能量包络 → 真人律 → 烘焙02 |
| [`scripts/s01_五样本烘焙02.sh`](scripts/s01_五样本烘焙02.sh) | 五样本批量烘焙（施压/可怜/魅惑/惊惧/崩溃） |
| [`scripts/s01_导出扩散节拍表.sh`](scripts/s01_导出扩散节拍表.sh) | 从烘焙02导出05_扩散节拍表.txt |
| [`scripts/s01_设置OpenAI密钥.sh`](scripts/s01_设置OpenAI密钥.sh) | 设置OpenAI API密钥 |
| [`scripts/s01_env.sh`](scripts/s01_env.sh) | 环境变量配置 |

---

## 🗂️ 七、根目录 & 配置

### 根目录文件

| 文件 | 作用 |
|------|------|
| [`__init__.py`](__init__.py) | 项目/插件初始化 |
| [`AI_INDEX.md`](AI_INDEX.md) | **AI 代码图谱**：供AI Agent快速理解全项目结构 |
| [`README.md`](README.md) | 项目简介 |
| [`.clinerules`](.clinerules) | Roo Code AI行为规则 |
| [`.cursorrules`](.cursorrules) | Cursor AI行为规则 |
| [`.env.example`](.env.example) | 环境变量示例 |
| [`.gitignore`](.gitignore) | Git忽略规则 |
| [`asset_lib.py`](asset_lib.py) | 预设资产+客户资产路径工具函数 |
| [`一键打开能量工作台.sh`](一键打开能量工作台.sh) | 一键启动脚本（桌面入口） |

### 预设资产 (`预设资产/`)

| 路径 | 内容 |
|------|------|
| `资产库/README.txt` | 资产库目录说明 |
| `资产库/人格包/S01_林青霞_东方不败/人格包.json` | 林青霞·东方不败人格定义 |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/情绪.json` | 施压瞬间凝视情绪配置 |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/指令/` | 各阶段产物JSON(01_滑杆包, 02_烘焙, 03_能量包络, 04_全量, 05_扩散节拍表, 06_平庸纠正) |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/脉冲样本_五连/` | 五个情绪样本JSON + manifest.json + blend/ |
| `资产库/人格包/S02_温碧霞_魅惑者/人格包.json` | 温碧霞·魅惑者人格定义 |
| `资产库/人格包/S02_温碧霞_魅惑者/魅惑勾人/情绪.json` | 魅惑勾人情绪配置 |
| `资产库/人格包/S02_温碧霞_魅惑者/魅惑勾人/指令/` | 各阶段产物JSON(01_操作台上下文, 01_滑杆包, 01_自然语言) |

### 文档

| 路径 | 作用 |
|------|------|
| [`docs/PROJECT_FILES.md`](docs/PROJECT_FILES.md) | 全量文件清单（本文件） |
| [`docs/TOKEN_BUDGET.md`](docs/TOKEN_BUDGET.md) | Token 优化指南 |
| [`docs/开源社区对比调研.md`](docs/开源社区对比调研.md) | 开源社区对比调研 |

### 计划文档

| 路径 | 作用 |
|------|------|
| [`plans/贵宾犬委屈_扩散引擎提示词策略.md`](plans/贵宾犬委屈_扩散引擎提示词策略.md) | 贵宾犬委屈情绪的扩散引擎提示词策略 |
| [`plans/架构讨论_通用脉冲+物种偏移.md`](plans/架构讨论_通用脉冲+物种偏移.md) | 通用脉冲框架 + 物种偏移的架构讨论 |
| [`plans/文件结构最终方案.md`](plans/文件结构最终方案.md) | 项目文件结构的最终方案 |
| [`plans/giant_poodle_sad_pipeline.md`](plans/giant_poodle_sad_pipeline.md) | 巨型贵宾犬委屈管线设计方案 |
| [`plans/pet_eye_engine_migration_plan.md`](plans/pet_eye_engine_migration_plan.md) | 宠物眼眉引擎迁移计划 |
| [`plans/pet_file_structure_plan.md`](plans/pet_file_structure_plan.md) | 宠物模块文件结构规划 |

---

## 🔗 八、数据流转全图

```
客户自然语言
    ↓ nl_intent.py → nl_router.py → nl_to_packet.py / llm_openai.py
16情绪预设 (human/control_surface.py)
    ↓ 能量工作台.html 选择 + 拖滑杆
SliderPacket (_shared/slider_schema.py)
    ↓ _shared/packet_finalize.py (L1禁区收口)
能量包络 E(t) (_shared/envelope_compile.py)
    ↓ build_energy_envelope()
全量 12×150 帧 (channels_from_envelope)
    ↓ apply_human_prior() (human/human_prior.py)
    │  ├─ 二阶扫视动力学 (过冲)
    │  ├─ 盯住段底噪+微颤 (_shared/micro_jitter.py)
    │  └─ 12轨耦合延迟 (眉眼晚于眼)
    ↓ fix_pulse_quality() (human/pulse_quality.py)
    │  ├─ Q01 能量抬升
    │  ├─ Q02 杂乱平滑
    │  └─ Q03 眉峰延后
Dense' 全量定稿
    ↓ dense_to_baked_sparse()
烘焙 02_烘焙_真人律.json (_shared/channel_contract.py validate)
    │
    ├──→ human/affine_renderer.py (工程底膜 RGB 三色分离)
    │    └──→ Wan 扩散引擎
    │
    └──→ _shared/rhythm_compiler.py → 05_扩散节拍表.txt → Wan 扩散引擎

狗管线分流:
    dog/dog_pipeline.py
    ↓ EarParams 注入 (dog/channel_adapter.py)
    → dog/affine_renderer.py (狗版工程底膜)
    → Wan 扩散引擎
