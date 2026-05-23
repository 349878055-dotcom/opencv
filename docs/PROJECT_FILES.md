# 能量控制台 · 全量文件清单

> 生成日期: 2026-05-21 · 最后更新: 2026-05-23
> 架构变更：已脱离 ComfyUI，全 Web 模式。`nodes_v1.py` → `_archive/`，`workflows/` 已删除。
> 新入口：[`tools/01_工作台服务/serve_workbench.py`](tools/01_工作台服务/serve_workbench.py)（HTTP API）+ [`tools/01_工作台服务/能量工作台.html`](tools/01_工作台服务/能量工作台.html)（前端）

---

## 🧠 一、核心Python引擎 (`gaze_engine/`)

### 数据模型 & 预设（唯一真源）

| 文件 | 作用 | 谁在用 |
|------|------|--------|
| [`gaze_engine/control_surface.py`](gaze_engine/control_surface.py) | **16情绪预设唯一真源**（压·慑5 + 悲·怯6 + 媚·勾5），三区滑杆定义(起/动/收)，交付链段定义，工作台JSON导出 | 几乎所有模块 |
| [`gaze_engine/slider_schema.py`](gaze_engine/slider_schema.py) | SliderPacket 数据类定义（macro 6杆 + hold_seg 4属性），LLM增量合并，情绪→滑杆包映射，→ compile参数转换 | envelope_compile, human_prior, packet_finalize |
| [`gaze_engine/slider_bounds.py`](gaze_engine/slider_bounds.py) | **L1滑杆禁区机器真源**：戏种分组(压·慑/悲·怯/媚·勾)、预设数值盒半径、G1-G8全剧种硬禁区、load_rules()供浏览器JS和Python共用 | packet_finalize, export_slider_forbidden_js.py |

### 编译链（滑杆 → 全量帧）

| 文件 | 作用 | 步骤 |
|------|------|------|
| [`gaze_engine/packet_finalize.py`](gaze_engine/packet_finalize.py) | **滑杆包收口**：本戏数值盒检查 → 全剧种硬禁区(G1-G8) → 路人中间带弹回 | ①→②之间 |
| [`gaze_engine/envelope_compile.py`](gaze_engine/envelope_compile.py) | **能量包络编译**：SliderPacket → E(t)能量曲线 → 12×150全量通道(pupil_x/y/blink/eyebrow/squint等12轨) | ③ |
| [`gaze_engine/human_prior.py`](gaze_engine/human_prior.py) | **真人化**：二阶欠阻尼扫视动力学(过冲)、盯住段微漂+微颤底噪、眉眼延迟耦合、频道跟随 | ④ |
| [`gaze_engine/pulse_quality.py`](gaze_engine/pulse_quality.py) | **平庸化三检**：Q01能量不足自动抬升(×1.42上限)、Q02保持段杂乱轻平滑、Q03眉峰不晚于眼自动延后 | ④b |
| [`gaze_engine/micro_jitter.py`](gaze_engine/micro_jitter.py) | **微颤动引擎**：分阶段(蓄力/启动/保持/缓和)的Hz和幅度，human_prior调用 | human_prior |

### 12通道合同

| 文件 | 作用 |
|------|------|
| [`gaze_engine/channel_contract.py`](gaze_engine/channel_contract.py) | **12操作通道定义**(pupil_x/y, blink, eyebrow, pupil_scale, iris_scale, cornea_bulge, squint, brow_raise, lid_upper, lid_lower, eye_gloss)，中文标签，扩散提示语，validate_baked_delivery()出厂校验 |

### 交付链 & 批量

| 文件 | 作用 |
|------|------|
| [`gaze_engine/delivery_pipeline.py`](gaze_engine/delivery_pipeline.py) | **主交付链入口**：SliderPacket → 编译 → human_prior → pulse_quality → 烘焙定稿02。`run_delivery_from_packet()` / `run_delivery()` |
| [`gaze_engine/batch_presets.py`](gaze_engine/batch_presets.py) | **五样本批量烘焙**：施压·凝视/可怜·委屈/魅惑·勾人/惊惧·一怔/崩溃·泄劲 → 五个02烘焙JSON |

### 自然语言 → 情绪

| 文件 | 作用 |
|------|------|
| [`gaze_engine/nl_intent.py`](gaze_engine/nl_intent.py) | **NL意图分类**：咨询(consult) vs 生成/修改(apply)，关键词+正则匹配 |
| [`gaze_engine/nl_router.py`](gaze_engine/nl_router.py) | **NL路由主入口**：`process_customer_nl()` 分发到LLM或关键词回退，整合知识库 |
| [`gaze_engine/nl_to_packet.py`](gaze_engine/nl_to_packet.py) | **关键词→预设匹配**：18个中文关键词(施压/魅惑/可怜/惊惧…) → 16预设名，关键词回退生成SliderPacket |
| [`gaze_engine/llm_openai.py`](gaze_engine/llm_openai.py) | **LLM集成**：OpenAI/ChatGPT调用，客户自然语言→SliderPacket，包含系统Prompt和结构化输出 |

### 文件IO & 上下文

| 文件 | 作用 |
|------|------|
| [`gaze_engine/pipeline_io.py`](gaze_engine/pipeline_io.py) | **各阶段JSON读写**：文件名常量(01_自然语言.txt, 01_滑杆包.json, 03_能量包络.json, 04_全量_包络展开.json, 05_全量_真人律.json, 06_全量_平庸纠正.json, 02_烘焙_真人律.json)，读写封装 |
| [`gaze_engine/workbench_io.py`](gaze_engine/workbench_io.py) | **操作台滑杆包读写**：`read_slider_packet()` / `write_slider_packet()`，同步到tools/目录 |
| [`gaze_engine/workbench_context.py`](gaze_engine/workbench_context.py) | **操作台上下文管理**：自然语言+能量图说明+知识库+L1附件，与Comfy节点同步 |
| [`gaze_engine/node1_defaults.py`](gaze_engine/node1_defaults.py) | **节点1默认值加载**：读取prompts/下的系统Prompt和知识库文本，占位符检测 |

### 扩散 & 导出

| 文件 | 作用 |
|------|------|
| [`gaze_engine/export_diffusion_metronome.py`](gaze_engine/export_diffusion_metronome.py) | **扩散节拍表导出**：从烘焙02提取节奏时刻+通道提示语，生成05_扩散节拍表.txt，供Wan扩散引擎使用 |

### 人格 & 视觉模块

| 文件 | 作用 |
|------|------|
| [`gaze_engine/persona_compiler.py`](gaze_engine/persona_compiler.py) | **人格编译**：从资产库人格包加载人格定义，生成人格化参数 |
| [`gaze_engine/persona_matrix.json`](gaze_engine/persona_matrix.json) | **9人格矩阵**：人格ID→性格偏向的映射数据（JSON静态） |
| [`gaze_engine/base_mesh_gen.py`](gaze_engine/base_mesh_gen.py) | **基础网格生成**：眼眉区域三角网格顶点定义 |
| [`gaze_engine/affine_renderer.py`](gaze_engine/affine_renderer.py) | **仿射渲染**：RGB三色分离(R=眼,G=眉,B=瞳孔)、闭合路径、0-noise。⚠️ 当前 `_AFFINE_DISABLED`，重建中 |
| [`gaze_engine/audio_compiler.py`](gaze_engine/audio_compiler.py) | **音频编译**：音频脉冲与视觉节拍对齐。⚠️ 当前 `_AUDIO_DISABLED`，重建中 |

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

## 🖥️ 三、UI & 工具 (`tools/`)

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

### 其他工具

| 文件 | 作用 |
|------|------|
| [`tools/05_其他工具/底模视觉几何调校器.html`](tools/05_其他工具/底模视觉几何调校器.html) | 独立视觉几何调校工具 |

---

## 📜 四、合同 & 规范 (`contracts/`)

| 文件 | 内容 |
|------|------|
| [`contracts/README.md`](contracts/README.md) | contracts目录说明 |
| [`contracts/01_总纲/滑杆规范.md`](contracts/01_总纲/滑杆规范.md) | **滑杆总规范**：设计原则、SliderPacket格式、宏观六滑杆(起/动/收)、盯住段三属性、16预设、L1禁区G1-G8、Python映射链 |
| [`contracts/01_总纲/全量帧指令集规范.md`](contracts/01_总纲/全量帧指令集规范.md) | **12轨全量帧规范**：时间容器(30fps×150帧×5s)、真值层级、12通道定义、能量四段、分通道节奏合同R01-R07、烘焙02格式、扩散节拍、验收清单 |
| [`contracts/01_总纲/眼眉真人默认律.md`](contracts/01_总纲/眼眉真人默认律.md) | **Human Prior合同**：正常人原则(过冲/底噪/延迟)、扫视二阶动力学、盯住活劲、12轨耦合、平庸三检Q01-Q03、合格标准 |
| [`contracts/02_情绪/魅惑勾人.md`](contracts/02_情绪/魅惑勾人.md) | 魅惑·勾人情绪的专项规范 |
| [`contracts/04_接口/UI设计原则.md`](contracts/04_接口/UI设计原则.md) | 工作台交互设计原则 |
| [`contracts/05_人格化/风格化偏向.md`](contracts/05_人格化/风格化偏向.md) | 人格风格化偏向规则 |
| [`contracts/06_架构/流程设计.md`](contracts/06_架构/流程设计.md) | **顶层架构设计**：双模驱动中间件架构说明 |

---

## 📜 五、脚本 (`scripts/`)

### 主流程脚本

| 文件 | 作用 |
|------|------|
| [`scripts/s01_从能量生成02.sh`](scripts/s01_从能量生成02.sh) | **主出厂**：单预设 → 能量包络 → 真人律 → 烘焙02 |
| [`scripts/s01_五样本烘焙02.sh`](scripts/s01_五样本烘焙02.sh) | 五样本批量烘焙（施压/可怜/魅惑/惊惧/崩溃） |
| [`scripts/s01_导出扩散节拍表.sh`](scripts/s01_导出扩散节拍表.sh) | 从烘焙02导出05_扩散节拍表.txt |
| [`scripts/s01_打开能量工作台.sh`](scripts/s01_打开能量工作台.sh) | 启动能量工作台（Python HTTP服务+浏览器） |
| [`scripts/s01_设置OpenAI密钥.sh`](scripts/s01_设置OpenAI密钥.sh) | 设置OpenAI API密钥 |
| [`scripts/s01_env.sh`](scripts/s01_env.sh) | 环境变量配置 |
| [`scripts/README.md`](scripts/README.md) | scripts目录说明 |

---

## 🗂️ 六、根目录 & 配置

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
| [`asset_lib.py`](asset_lib.py) | 资产库路径工具函数(cmd_dir/ensure_dirs等) |
| [`一键打开能量工作台.sh`](一键打开能量工作台.sh) | 一键启动脚本（桌面入口） |

### 资产库 (`资产库/`)

| 路径 | 内容 |
|------|------|
| `资产库/README.txt` | 资产库目录说明 |
| `资产库/人格包/S01_林青霞_东方不败/人格包.json` | 林青霞东方不败人格定义 |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/情绪.json` | 施压瞬间凝视情绪配置 |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/指令/` | 各阶段产物JSON(01_滑杆包, 02_烘焙, 03_能量包络, 04_全量, 05_扩散节拍表, 06_平庸纠正) |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/脉冲样本_五连/` | 五个情绪样本JSON + manifest.json + blend/ |

### Prompt 模板

| 路径 | 作用 |
|------|------|
| [`prompts/node1_system_prompt.txt`](prompts/node1_system_prompt.txt) | 节点1系统Prompt（LLM角色+规则） |
| [`prompts/node1_knowledge_base.txt`](prompts/node1_knowledge_base.txt) | 节点1知识库（16情绪+滑杆） |

---

## 🔗 七、数据流转全图

```
客户自然语言
    ↓ nl_intent.py → nl_router.py → nl_to_packet.py / llm_openai.py
16情绪预设 (control_surface.py)
    ↓ 能量工作台.html 选择 + 拖滑杆
SliderPacket (slider_schema.py)
    ↓ packet_finalize.py (L1禁区收口)
能量包络 E(t) (envelope_compile.py)
    ↓ build_energy_envelope()
全量 12×150 帧 (channels_from_envelope)
    ↓ apply_human_prior() (human_prior.py)
    │  ├─ 二阶扫视动力学 (过冲)
    │  ├─ 盯住段底噪+微颤 (micro_jitter.py)
    │  └─ 12轨耦合延迟 (眉眼晚于眼)
    ↓ fix_pulse_quality() (pulse_quality.py)
    │  ├─ Q01 能量抬升
    │  ├─ Q02 杂乱平滑
    │  └─ Q03 眉峰延后
Dense' 全量定稿
    ↓ dense_to_baked_sparse()
烘焙 02_烘焙_真人律.json (channel_contract.py validate)
    └→ export_diffusion_metronome.py → 05_扩散节拍表 → Wan扩散引擎
