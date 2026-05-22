# 能量控制台 · 全量文件清单

> 生成日期: 2026-05-21
> 清理后版本: 能量控制台 v2（纯 envelope-v1 链路）

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

| 文件 | 作用 |
|------|------|

### 扩散 & 导出

| 文件 | 作用 |
|------|------|
| [`gaze_engine/export_diffusion_metronome.py`](gaze_engine/export_diffusion_metronome.py) | **扩散节拍表导出**：从烘焙02提取节奏时刻+通道提示语，生成05_扩散节拍表.txt，供Wan扩散引擎使用 |

### 模板

| 文件 | 作用 |
|------|------|
| [`gaze_engine/templates/S01_林青霞_施压瞬间凝视.json`](gaze_engine/templates/S01_林青霞_施压瞬间凝视.json) | S01模板参考JSON（历史对照） |

### 基础

| 文件 | 作用 |
|------|------|
| [`gaze_engine/__init__.py`](gaze_engine/__init__.py) | Python包初始化 |
| `gaze_engine/.gitkeep` | 保持目录在Git中 |

---

## 🎛️ 二、ComfyUI 节点 (`nodes_v1.py`)

| 文件 | 作用 |
|------|------|

---

## 🖥️ 三、UI & 工具 (`tools/`)

| 文件 | 作用 |
|------|------|
| [`tools/build_standalone_share.py`](tools/build_standalone_share.py) | 从能量工作台.html生成单文件分享版（内嵌pipeline_cache） |
| [`tools/build_workbench_pipeline_cache.py`](tools/build_workbench_pipeline_cache.py) | **管线缓存生成**：为16个预设预编译全量JSON缓存(pipeline_cache/*.json)，供工作台加载 |
| [`tools/control_surface.json`](tools/control_surface.json) | 控制面JSON（由control_surface.py导出，工作台启动时加载） |
| [`tools/packet_finalize_ui.js`](tools/packet_finalize_ui.js) | 前端L1滑杆禁区校验JS |
| [`tools/01_操作台上下文.json`](tools/01_操作台上下文.json) | 操作台上下文缓存 |
| `tools/preview_cache/.gitkeep` | 缓存目录占位 |
| `tools/preview_cache/live_viewport.jpg` | 视口实时预览图 |

---

## 📜 四、合同 & 规范 (`contracts/`)

| 文件 | 内容 |
|------|------|
| [`contracts/滑杆规范.md`](contracts/滑杆规范.md) | **滑杆总规范**：设计原则、SliderPacket格式、宏观六滑杆(起/动/收)、盯住段三属性、16预设、L1禁区G1-G8、Python映射链 |
| [`contracts/全量帧指令集规范.md`](contracts/全量帧指令集规范.md) | **12轨全量帧规范**：时间容器(30fps×150帧×5s)、真值层级、12通道定义、能量四段、分通道节奏合同R01-R07、烘焙02格式、扩散节拍、验收清单 |
| [`contracts/眼眉真人默认律.md`](contracts/眼眉真人默认律.md) | **Human Prior合同**：正常人原则(过冲/底噪/延迟)、扫视二阶动力学、盯住活劲、12轨耦合、平庸三检Q01-Q03、合格标准 |
| [`contracts/UI设计原则.md`](contracts/UI设计原则.md) | 工作台交互设计原则 |
| [`contracts/节点1_系统Prompt_通用版.md`](contracts/节点1_系统Prompt_通用版.md) | 节点1系统Prompt模板 |
| [`contracts/节点1_知识库模板_通用版.md`](contracts/节点1_知识库模板_通用版.md) | 节点1知识库模板 |
| [`contracts/魅惑勾人_标准条.md`](contracts/魅惑勾人_标准条.md) | 魅惑·勾人预设的标准条说明 |
| [`contracts/魅惑勾人_数值闭环.md`](contracts/魅惑勾人_数值闭环.md) | 魅惑·勾人的数值闭环验证 |
| [`contracts/参考片反推规范.md`](contracts/参考片反推规范.md) | 参考片反推规范（旁路，非主链） |
| [`contracts/README.md`](contracts/README.md) | contracts目录说明 |

---

## 📜 五、脚本 (`scripts/`)

### 主出厂命令

| 文件 | 作用 |
|------|------|
| `scripts/s01_从能量生成02.sh` | **主出厂**：单预设 → 能量包络 → 真人律 → 烘焙02 |
| `scripts/s01_五样本烘焙02.sh` | 五样本批量烘焙（施压/可怜/魅惑/惊惧/崩溃） |
| `scripts/s01_导出扩散节拍表.sh` | 从烘焙02导出05_扩散节拍表.txt |
| `scripts/s01_打开能量工作台.sh` | 启动能量工作台（Python HTTP服务+浏览器） |

### 验收 & 预览

| 文件 | 作用 |
|------|------|
| `scripts/s01_过真人律.sh` | 单独运行真人律（human_prior） |
| `scripts/s01_快验全量.sh` | 快速验收全量帧 |
| `scripts/s01_轻量3D预览.sh` | 轻量3D视口预览 |
| `scripts/s01_预览曲线图.sh` | 12通道曲线预览PNG |
| `scripts/s01_指令集示意图.sh` | 生成指令集示意图 |
| `scripts/s01_主验收示意图.sh` | 生成主验收示意图（四通道全轨+视线xy） |

### 配置 & 导出

| 文件 | 作用 |
|------|------|
| `scripts/export_control_surface_json.py` | 导出control_surface.json |
| `scripts/export_slider_forbidden_js.py` | 导出L1禁区JS（slider_forbidden_bounds.js） |
| `scripts/s01_env.sh` | 环境变量配置 |

### LLM & 工具

| 文件 | 作用 |
|------|------|
| `scripts/一键接OpenRouter.sh` | 一键配置OpenRouter API |
| `scripts/s01_设置OpenAI密钥.sh` | 设置OpenAI API密钥 |
| `scripts/配置_开源编程模型.sh` | 配置开源编程模型 |
| `scripts/配置_Cursor_Agent自动执行.sh` | 配置Cursor Agent自动执行 |
| `scripts/同步Cursor_OpenRouter.sh` | 同步Cursor与OpenRouter |
| `scripts/修复Cursor布局_文件左聊天右.sh` | 修复Cursor布局 |

### 环境 & 安装

| 文件 | 作用 |
|------|------|
| `scripts/安装_视口依赖.sh` | 安装视口预览依赖 |
| `scripts/验收_视口预览.sh` | 验收视口预览功能 |
| `scripts/README.md` | scripts目录说明 |

---

## 🗂️ 六、资产 & 配置

### 资产库 (`资产库/`)

| 路径 | 内容 |
|------|------|
| `资产库/人格包/S01_林青霞_东方不败/人格包.json` | 林青霞东方不败人格定义 |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/情绪.json` | 施压瞬间凝视情绪配置 |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/指令/` | 各阶段产物JSON(01_滑杆包, 02_烘焙, 03_能量包络, 04_全量, 05_扩散节拍表, 06_平庸纠正) |
| `资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/脉冲样本_五连/` | 五个情绪样本JSON + manifest.json |

### 眼眉资产 (`eye_asset/`)

| 路径 | 内容 |
|------|------|
| `eye_asset/packs/示例输出/` | 示例输出 |

### Prompt 模板

| 路径 | 作用 |
|------|------|
| `prompts/node1_system_prompt.txt` | 节点1系统Prompt（LLM角色+规则） |
| `prompts/node1_knowledge_base.txt` | 节点1知识库（16情绪+滑杆+） |

### 其他

| 路径 | 作用 |
|------|------|
| `asset_lib.py` | 资产库路径工具函数(cmd_dir/ensure_dirs等) |
| `web/js/jintao_node1_labels.js` | ComfyUI节点标签定义 |
| `ingest/.gitkeep` | 输入目录 |
| `workflows/` | ComfyUI工作流文件 |
| `__init__.py` | 插件包初始化 |
| `README.md` | 项目说明 |
| `.env.example` | 环境变量示例 |
| `.gitignore` | Git忽略规则 |
| `一键打开能量工作台.sh` | 一键启动脚本（桌面入口） |
| `能量工作台.desktop` | Linux桌面快捷方式 |

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
```

---

## 📊 八、清理统计

| 类别 | 删除数量 |
|------|----------|
| 旧UI（微表情控制台） | 1个HTML |
| 旧管线（Comfy v1 + 稀疏链） | 9个.py |
| 旧L0系统（3预设WorkbenchConfig） | 4个.py |

| 旧脚本 | 13个.sh/.py |
| 杂项 + benchmark | 6个文件 + 7个目录 |
| **总计删除** | **~46+ 文件** |
| **修复import** | **8个文件** |
| **gaze_engine/ 精简** | 51 → 24 文件 |

---

> 💡 重做能量控制台UI时，只需要关注 `tools/能量工作台.html` 一个文件，它调用的核心Python模块现在全部干净对齐你的目标流程。
