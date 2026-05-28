# gaze_engine 全量思维导图

> 管线入口 → 公共设施 → 物种专属层  
> **📌 提示：** 本图列出 gaze_engine/ 目录下 **全部文件**，已包含 pomot/ 合成引擎、species_detector 自动检测等最新模块。  
> **🟢 绿色 ⭐ = 核心入口，🟡 黄色 ⚡ = 数学/算法核心，🟣 紫色 🧹 = 校验/工具**

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                           gaze_engine/  根入口文件                                │
│   📌 所有管线调用都从这里开始，按物种分发到 human/cat/dog                         │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  ├── __init__.py               Python 包声明，空                                   │
│  ├── delivery_pipeline.py      ⭐ 主交付管线调度：统一入口 run_delivery()          │
│  │                               按 species 分发到 human/cat/dog 对应管线          │
│  │                               📌 这是整个引擎的「总开关」                       │
│  ├── nl_intent.py              NL 意图分类 + 物种识别（用户说的啥 + 哪个物种）      │
│  ├── nl_router.py              NL 路由：process_customer_nl() → 意图+物种          │
│  │                               📌 nl_intent 的调度器                             │
│  ├── nl_to_packet.py           关键词/简单NL → 情绪预设匹配 → SliderPacket        │
│  │                               📌 旧版方式，pomot/composer 是升级版              │
│  ├── base_mesh_gen.py          基础网格生成（工程底图的底座）                       │
│  ├── audio_compiler.py         ⚠️ 音频编译（当前禁用）                             │
│  └── test_persona_integrity.py 人格完整性自检脚本                                   │
│                                                                                    │
├════════════════════════════════════════════════════════════════════════════════════┤
│                                                                                    │
│  ▼ _shared/   公共基础设施（物种无关，所有物种共用）                               │
│  📌 这是整个引擎的「地基」——所有物种的数学、校验、I/O、AI 都依赖这里              │
│  ─────────────────────────────────────────────────────────────                      │
│                                                                                    │
│  ├── ① 校验工具层（Validation）                                                   │
│  │  │  📌 纯函数，无副作用，只做「检查」和「约束」                                 │
│  │  ├── channel_contract.py    🧹 纯校验函数（无全局通道数据）：                   │
│  │  │                             validate_channel_tracks(sparse, channel_keys)    │
│  │  │                             validate_baked_delivery(sparse, channel_keys)    │
│  │  │                             series_from_baked(sparse, channel_keys)          │
│  │  │                             validate_micro_jitter(sparse)                    │
│  │  │                             └─ 通道名由各物种自己定义（见各物种的 CHANNELS） │
│  │  ├── slider_schema.py       SliderPacket（核心数据结构）                        │
│  │  │                          MacroSliders（push/power/speed/steady/grip/outro）  │
│  │  │                          HoldSegment（shape/pulse_rate/pulse_depth/swell）   │
│  │  │                          EarParams（耳位参数，猫狗专用）                     │
│  │  │                          📌 整个引擎的「数据契约」——所有管线传递这个结构     │
│  │  └── slider_bounds.py       L1禁区：G1~G8八组硬约束规则                         │
│  │                             📌 「滑杆的物理定律」——超出部分自动弹回             │
│  │                                                                                │
│  ├── ② 编译管线层（Pipeline Core）                                                 │
│  │  ├── packet_finalize.py     滑杆包收口：禁区弹回 + 数值裁剪 + 完整性校验        │
│  │  ├── envelope_compile.py    ⚡ 纯数学层（物种无关）：                          │
│  │  │                             build_energy_envelope()   ← macro→4段能量曲线   │
│  │  │                             📌 所有物种共用同一个能量骨架 E(t)              │
│  │  │                             compute_pad_scale()       ← PAD动态投影公式     │
│  │  │                             _timing / _peak_level / _hold_texture / _direction│
│  │  │                             export_envelope_series()  ← 包络序列化           │
│  │  │                             └─ ⚠️ 不含任何物种通道映射（已剥离到各物种）   │
│  │  ├── micro_jitter.py        微颤动算法引擎：按戏段叠噪声，频率/幅度可分段配置  │
│  │  │                          📌 算法骨架在 _shared（数学层），各物种             │
│  │  │                             envelope_compile 调用并传入物种生理参数         │
│  │  │                             让人眼/CG眼看起来「活」——人眼不可能完全静止    │
│  │  └── rhythm_compiler.py     节奏说明书编译器（解析节奏说明书.md合同）            │
│  │                             📌 算法骨架在 _shared，文案来自各物种 rhythm_data.py│
│  │                                                                                │
│  ├── ③ I/O 层（File I/O）                                                         │
│  │  ├── pipeline_io.py         管线各阶段JSON文件读写（01→02→03→04→05→06）        │
│  │  │                          📌 每步产生一个带编号的 JSON，方便调试和缓存        │
│  │  ├── workbench_io.py        能量工作台专属读写                                  │
│  │  └── workbench_context.py   工作台会话上下文管理（物种/品种/客户ID）             │
│  │                                                                                │
│  ├── ④ 智能层（AI / LLM）                                                         │
│  │  ├── llm_openai.py          ⭐ OpenAI封装：                                    │
│  │  │                            chatgpt_customer_nl() → 客户咨询回复             │
│  │  │                            chatgpt_nl_to_packet() → NL→SliderPacket         │
│  │  └── node1_defaults.py      节点1默认值加载（system prompt模板）                │
│  │                                                                                │
│  ├── ⑤ 客户资产层（Customer DB）                                                  │
│  │  └── customer_db.py         客户资产库CRUD：客户/项目/调整版本管理              │
│  │                             📌 关联 客户资产库/ 目录下的客户私有数据            │
│  │                                                                                │
│  ├── ⑥ 物种底膜模板层（Species Template）【🆕 新增】                             │
│  │  ├── species_template.py    ⭐ 物种底膜模板参数（"低膜"）：                    │
│  │  │                            SpeciesTemplate 数据类（17个几何参数）            │
│  │  │                            species_default_template() → 物种标准模板         │
│  │  │                            adjust_template_for_breed() → 品种偏移            │
│  │  │                            apply_customer_adjustments() → 客户个性化调整     │
│  │  │                            template_to_renderer_constants() → 渲染常量        │
│  │  │                            📌 每个客户的眼睛几何（眼距/眼位/大小）都不同    │
│  │  │                              这是「千人千面」的底层数据                      │
│  │  └── species_detector.py    ⭐ 自动化检测：从照片提取底膜参数：                │
│  │                               人类 → MediaPipe Face Mesh (468点)               │
│  │                               猫狗 → OpenCV Haar Cascade + YOLOv8 兜底         │
│  │                               auto_detect_for_customer() → 全自动流程           │
│  │                               📌 客户上传照片 → 自动算参数 → 无需手动调       │
│  │                                                                                │
│  └── assets/                   工程底膜视觉素材（eyelid_raw.png）                   │
│                                                                                    │
├════════════════════════════════════════════════════════════════════════════════════┤
│                                                                                    │
│  ▼ human/   人类物种专属                                                          │
│  📌 人类特征：有眉毛肌 + 九大人格 + 16个情绪预设                                │
│  ──────────────────────────                                                        │
│  │  通道体系：继承标准12通道（eyebrow=眉压, brow_raise=挑眉，语义不变）            │
│  │                                                                                │
│  │  ★ 专属通道编译层：                                                             │
│  │  ├── envelope_compile.py    ⭐ 人类通道编译（含 eyebrow 滞后 + pulse 耦合）：  │
│  │  │                             channels_from_envelope()  ← 含人类eyebrow滞后    │
│  │  │                             _apply_pulse_hold_coupling() ← 眉/眯/瞳耦合      │
│  │  │                             channels_from_packet()    ← 人类完整入口         │
│  │  │                             make_delivery_stub()      ← 人类02 stub         │
│  │  │                             └─ 调用 _shared/envelope_compile 的数学函数      │
│  │  │                             📌 human 比 cat/dog 多一个 eyebrow 滞后逻辑     │
│  │  │                               因为人类眉毛反应比眼睑慢 ~50ms                │
│  │                                                                                │
│  │  ★ 人格层（Persona Layer）：                                                     │
│  │  │  📌 人类专属概念——猫狗没有「人格」，只有「品种风格」                       │
│  │  ├── persona_compiler.py    ⭐ 九大人格编译器：persona_matrix → 通道级delta    │
│  │  │                            compile_to_channels(emotion_pulse, persona_id)    │
│  │  │                            ← 人类专属，猫狗无此概念                          │
│  │  ├── persona_matrix.json    九大人格矩阵（base_offset + scale_factor）          │
│  │  │                           📌 比如「狠厉者」的眉压会加重，瞳孔更聚焦         │
│  │                                                                                │
│  │  ★ 其他专属文件：                                                               │
│  │  │                                                                                │
│  │  ├── control_surface.py    ⭐ 人类情绪真源：16个预设（PRESETS字典）            │
│  │  │                            📌 「唯一真源」——所有人类情绪数据都从这里来     │
│  │  │                            三区分组：压·慑 / 悲·怯 / 媚·勾                  │
│  │  │                            (怒视·压人、媚杀·一眼、可怜·委屈...)             │
│  │  ├── affine_renderer.py    工程底膜驱动引擎（EyeMesh类）                       │
│  │  │                            RGB三色分离：R=眼, G=眉, B=瞳孔                  │
│  │  │                            📌 这是最终「画在画布上」的渲染器               │
│  │  ├── human_prior.py        真人化先验：二阶欠阻尼扫视(过冲) + 微漂微颤 + 眉眼延迟│
│  │  │                            📌 让 CG 眼睛像真人——扫视会过头再回弹           │
│  │  ├── pulse_quality.py      平庸三检：Q01能量不足→抬升, Q02杂乱→平滑, Q03眉峰→延后│
│  │  │                            📌 质检员——保证输出不「平庸」                    │
│  │  ├── pad_weights.py        人类PAD权重表（Pleasure/Arousal/Dominance）         │
│  │  │                            📌 每个通道对不同情绪维度的敏感度不同            │
│  │  └── rhythm_data.py        节奏说明书人类文案【🆕 新增】                       │
│  │                               📌 提供人类物种的节奏描述文案                    │
│  │                                 被 _shared/rhythm_compiler 调用                 │
│  │                                                                                │
├════════════════════════════════════════════════════════════════════════════════════┤
│                                                                                    │
│  ▼ cat/   猫物种专属                                                              │
│  📌 猫特征：无眉毛肌（耳位代替眉毛）+ 三眼睑 + 瞳孔更敏感                       │
│  ───────────────────────                                                           │
│  │  通道体系→ 内部13通道（去掉eyebrow，拆成ear_left + ear_right）                 │
│  │           ↓ channel_adapter 再将耳位映射回标准12通道的eyebrow/brow_raise位置    │
│  │           📌 猫的「耳朵=眉毛」——因为猫没有眉毛肌，情绪靠耳朵表达              │
│  │                                                                                │
│  │  ★ 专属通道编译层：                                                             │
│  │  ├── envelope_compile.py    ⭐ 猫通道编译（无 eyebrow 滞后）：                 │
│  │  │                             channels_from_envelope()  ← 通用 scale×envelope  │
│  │  │                             channels_from_packet()    ← 猫入口，自动注入耳位 │
│  │  │                             make_delivery_stub()      ← 猫02 stub           │
│  │  │                             └─ 调用 _shared/envelope_compile 的数学函数      │
│  │                                                                                │
│  │  ★ 品种层（Breed Layer）：                                                     │
│  │  │  📌 不同品种的猫，面部结构差异大（扁脸波斯 vs 尖脸暹罗）                  │
│  │  ├── breed_matrix.json   ⭐ 猫品种风格矩阵：base_offset + scale_factor        │
│  │  │                          布偶/暹罗/英短/田园，4品种风格偏移               │
│  │  └── breeds.py           猫品种配置加载器（读本地 breed_matrix.json）         │
│  │                                                                                │
│  │  ★ 其他专属文件：                                                               │
│  │                                                                                │
│  ├── presets.py            12个猫情绪预设（CAT_PRESETS）                           │
│  │                            警觉瞪视、狩猎锁定、委屈呜咽...                      │
│  ├── channel_adapter.py    ⭐ 猫通道适配器：                                      │
│  │                            ear_left  → 覆盖标准通道的 eyebrow                  │
│  │                            ear_right → 覆盖标准通道的 brow_raise               │
│  │                            （猫无独立眉毛肌，耳位取代眉毛的生态位）             │
│  ├── affine_renderer.py    CatEyeMesh + 耳位渲染（猫专属眼部网格）                │
│  ├── prior.py              猫扫视 + 三眼睑 + 耳耦合                              │
│  │                            📌 三眼睑（瞬膜）是猫特有的生理结构                 │
│  ├── detect.py             猫面部检测 + 品种推断（YOLO兜底）【🆕 新增】          │
│  │                            📌 从客户照片自动检测猫的面部关键点                │
│  ├── pulse_quality.py      猫质检规则                                             │
│  ├── pad_weights.py        ⭐ 猫13通道PAD权重表（区别于人类的12通道）            │
│  │                            ear_left / ear_right 加入 pupil_scale权重更高       │
│  │                            📌 猫瞳孔对情绪变化更敏感（狩猎→放大，生气→缩）    │
│  └── rhythm_data.py        节奏说明书猫文案【🆕 新增】                            │
│                               📌 猫物种的节奏描述文案                              │
│                                                                                    │
├════════════════════════════════════════════════════════════════════════════════════┤
│                                                                                    │
│  ▼ dog/   狗物种专属                                                              │
│  📌 狗特征：有眉毛肌（保留）+ 耳位折叠进 eyebrow + 品种风格                     │
│  ───────────────────────                                                           │
│  │  通道体系→ 保持标准12通道命名，但语义重映射：                                 │
│  │           eyebrow → 狗耳位（0=垂耳, 1=立耳）                                   │
│  │           brow_raise → 保留眉脊独立语义（狗有眉毛肌）                          │
│  │           📌 狗介于人和猫之间——有眉毛但不够灵活，耳朵很重要                   │
│  │                                                                                │
│  │  ★ 专属通道编译层：                                                             │
│  │  ├── envelope_compile.py    ⭐ 狗通道编译（无 eyebrow 滞后，耳位自动注入）：   │
│  │  │                             channels_from_envelope()  ← 通用 scale×envelope  │
│  │  │                             channels_from_packet()    ← 狗入口，自动注入耳位 │
│  │  │                             make_delivery_stub()      ← 狗02 stub           │
│  │  │                             └─ 调用 _shared/envelope_compile 的数学函数      │
│  │                                                                                │
│  │  ★ 品种层（Breed Layer）：                                                     │
│  │  ├── breed_matrix.json   ⭐ 狗品种风格矩阵：base_offset + scale_factor        │
│  │  │                          巨型贵宾/优雅型，品种风格偏移                     │
│  │  └── breeds.py           狗品种配置加载器（读本地 breed_matrix.json）         │
│  │                                                                                │
│  │  ★ 其他专属文件：                                                               │
│  │                                                                                │
│  ├── presets.py            10个狗情绪预设（DOG_PRESETS）                          │
│  │                            委屈·幼犬眼、警觉·竖耳、兴奋·期待...                │
│  ├── channel_adapter.py    ⭐ 狗通道适配器：                                      │
│  │                            left_angle  → 覆盖 eyebrow（耳位·垂耳/立耳）        │
│  │                            right_angle → 覆盖 brow_raise（保持眉脊语义）      │
│  │                            （与猫不同：猫右耳覆盖brow_raise用于第二耳道）      │
│  ├── affine_renderer.py    DogEyeMesh + 耳位渲染                                 │
│  ├── prior.py              狗扫视 + 耳耦合                                       │
│  ├── detect.py             狗面部检测 + 品种推断（YOLO兜底）【🆕 新增】          │
│  │                            📌 从客户照片自动检测狗的面部关键点                │
│  ├── pulse_quality.py      狗质检规则                                             │
│  ├── pad_weights.py        ⭐ 狗12通道PAD权重表（命名同人类，语义不同）          │
│  │                            eyebrow权重给耳位，brow_raise保留给眉脊             │
│  │                            📌 狗瞳孔权重微↑（兴奋时瞳孔放大）                  │
│  ├── rhythm_data.py        节奏说明书狗文案【🆕 新增】                            │
│  │                            📌 狗物种的节奏描述文案                              │
│  └── dog_pipeline.py       ⭐ 狗完整管线：SliderPacket→02烘焙（独立管线）        │
│                               📌 狗管线独立于 delivery_pipeline 的物种分发        │
│                                                                                    │
├════════════════════════════════════════════════════════════════════════════════════┤
│                                                                                    │
│  ▼ pomot/   Preset Prompt Template 合成引擎【🆕 新增】                          │
│  📌 将「预设情绪模板」与「客户自然语言」合成可控的眼眉滑杆包                    │
│  📌 这是「NL→SliderPacket→Prompt」的端到端两轮对话流程                          │
│  ─────────────────────────────────────────────                                      │
│                                                                                    │
│  ├── pipeline.py            ⭐ 管线入口：PomotPipeline 类                          │
│  │                            round1(): NL → 拆解 → 路由 → 合成 → 管线 → 拼装    │
│  │                            round2(): 客户反馈 → delta 微调                     │
│  │                            📌 两轮对话：第一轮生成，第二轮调整                 │
│  │                                                                                │
│  ├── nl_splitter.py         NL 拆解器：一句话 → 动作 + 情绪（NLSplitResult）      │
│  │                            📌 比如「委屈的跑回笼子再回头看了一眼」            │
│  │                               → 动作"跑回笼子回头" + 情绪"委屈"               │
│  ├── emotion_router.py      情绪路由：情绪词 → 预设名 + 物种/品种                │
│  │                            📌 从控制面/情绪包查找匹配的预设                │
│  ├── registry.py            预设注册表：按(species, breed, preset)加载预设模板    │
│  │                            📌 读取预设资产/目录下的 JSON 预设数据              │
│  ├── templates.py           数据类：NLSplitResult, EmotionRoute, PresetPromptTemplate│
│  ├── composer.py            ⭐ 第一轮合成：预设模板 + NL → SliderPacket           │
│  │                            📌 把「委屈」预设和「跑回笼子」结合成滑杆数据       │
│  ├── delta.py               第二轮微调：delta 叠加                                │
│  │                            📌 客户说「再委屈一点」→ 叠加 delta 增量           │
│  └── assembler.py           最终拼装：02_json→04_Prompt.txt→送扩散引擎 payload    │
│                               📌 组装成 Wan 扩散引擎能吃的完整 prompt             │
│                                                                                    │
└════════════════════════════════════════════════════════════════════════════════════┘
```

---

## 📌 三物种通道差异对比（核心！）

| 通道名 | human（人类） | cat（猫） | dog（狗） |
|--------|-------------|----------|----------|
| `eyebrow` | 眉压 | ❌ 不用（猫无眉毛肌）→ 被 `ear_left` 覆盖为**左耳位** | 被 `left_angle` 覆盖为**耳位**（0垂耳→1立耳） |
| `brow_raise` | 挑眉 | ❌ 不用 → 被 `ear_right` 覆盖为**右耳位/耳尖微颤** | **保留眉脊语义**（狗有眉毛肌），右耳角度仅影响幅度 |
| `ear_left` | ❌ 无 | ✅ **新增13通道**，左耳角度/偏移 | ❌ 无，信息折叠进 `eyebrow` |
| `ear_right` | ❌ 无 | ✅ **新增13通道**，右耳角度/偏移 | ❌ 无，信息折叠进 `brow_raise` |
| `pupil_scale` | 正常 | P权重↑（猫瞳孔更敏感） | P权重微↑ |
| `squint` | 正常 | P权重↑（猫眯眼=信任/满足） | 正常 |

> **📌 为什么通道不同？**  
> - 人类有独立眉毛肌 → `eyebrow` / `brow_raise` 语义完整  
> - 猫没有眉毛肌 → 耳朵代替眉毛表达情绪 → 拆出 `ear_left` / `ear_right` 两个独立通道  
> - 狗介于中间 → 有眉毛但不够灵活 → `eyebrow` 被耳位复用，`brow_raise` 保留给眉脊

---

## 🔗 数据流全景（完整版，含 pomot 两轮对话）

```
                    ┌─────────────────────────────────────────┐
                    │    客户自然语言（NL）输入                 │
                    │   "委屈的跑回笼子再回头看了一眼"          │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  pomot/pipeline.py  PomotPipeline      │
                    │                                         │
                    │  round1():                              │
                    │    1. nl_splitter    → 动作+情绪拆解    │
                    │    2. emotion_router → 情绪→预设名+物种 │
                    │    3. registry       → 按物种+预设加载  │
                    │    4. composer       → 预设+NL→Packet   │
                    │    5. run_pipeline   → 完整烘焙管线     │
                    │    6. assembler      → 拼装最终Prompt   │
                    │                                         │
                    │  round2(): 客户反馈 → delta 微调        │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  _shared/packet_finalize.py             │
                    │  → 禁区校验（G1~G8）                     │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  _shared/envelope_compile.py            │
                    │  → 纯数学：macro → 4段能量曲线 E(t)    │
                    │  （物种无关，共用同一能量骨架）           │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  按物种分发到各自的 envelope_compile    │
                    │  → E(t) + PAD → 12/13通道 × 150帧      │
                    │                                         │
                    │  human/  含 eyebrow 滞后 + pulse 耦合  │
                    │  cat/    通用 scale×envelope + 耳位注入 │
                    │  dog/    通用 scale×envelope + 耳位注入 │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  各物种 prior.py                        │
                    │  → 扫视(过冲) + 微漂微颤 + 物种特有逻辑 │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  各物种 pulse_quality.py                │
                    │  → Q01能量不足→抬升                     │
                    │  → Q02杂乱→平滑                         │
                    │  → Q03眉峰→延后（人类专属）              │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  02_烘焙_物种律.json (12通道逐帧数据)    │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  _shared/rhythm_compiler.py             │
                    │  + 各物种 rhythm_data.py (文案)         │
                    │  → 05_节拍表.txt（扩散引擎文本辅助）     │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  pomot/assembler.py                     │
                    │  → 02_json + 节拍表 → 04_Prompt.txt     │
                    │  → 送 Wan 扩散引擎的最终 payload         │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │  客户可选：species_detector.py           │
                    │  → 客户照片 → MediaPipe/OpenCV/YOLO     │
                    │  → 自动检测底膜参数 → 写入客户资产库     │
                    │  → 供 affine_renderer 渲染使用           │
                    └─────────────────────────────────────────┘
```

---

## 🧩 文件数量对比（完整版）

| 模块 | 文件数 | 说明 |
|------|--------|------|
| `_shared/`（公共） | **17文件** + 1素材 | (+2: species_template + species_detector) |
| `human/`（人类） | **7文件** | (+1: rhythm_data) |
| `cat/`（猫） | **10文件** | (+2: detect + rhythm_data) |
| `dog/`（狗） | **11文件** | (+2: detect + rhythm_data) |
| `pomot/`（合成引擎） | **8文件** | 🆕 全新模块 |
| **总计** | **53文件** | 全部在 gaze_engine/ 目录下 |

---

## 📂 pomot/ 模块详解（两轮对话流程）

```
┌─────────────────────────────────────────────────────────────────────┐
│                         pomot/ 两轮对话流程                         │
│              Preset Prompt Template 合成引擎                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  第一轮 round1():                                                   │
│  ─────────────────                                                   │
│  客户: "委屈的跑回笼子再回头看了一眼"                                │
│         │                                                           │
│         ▼                                                           │
│  ① nl_splitter.split()                                             │
│     → NLSplitResult(action="跑回笼子回头", emotion="委屈")         │
│         │                                                           │
│         ▼                                                           │
│  ② emotion_router.route(emotion="委屈", species_hint="dog")        │
│     → EmotionRoute(species="dog", preset_name="委屈·幼犬眼")       │
│         │                                                           │
│         ▼                                                           │
│  ③ registry.load(species="dog", preset="委屈·幼犬眼", breed=...)  │
│     → PresetPromptTemplate(macro=..., hold_seg=...)                │
│         │                                                           │
│         ▼                                                           │
│  ④ composer.compose(template, nl_action)                           │
│     → SliderPacket(含 macro + hold_seg + ear_params)               │
│         │                                                           │
│         ▼                                                           │
│  ⑤ 调用完整管线 run_delivery_from_packet()                         │
│     → 02_烘焙.json + 05_节拍表.txt                                  │
│         │                                                           │
│         ▼                                                           │
│  ⑥ assembler.assemble(02_json, beat_text, species)                │
│     → 04_Prompt.txt + 送扩散引擎 payload                            │
│                                                                     │
│  第二轮 round2():                                                   │
│  ─────────────────                                                   │
│  客户: "希望狗子再委屈一点"                                          │
│         │                                                           │
│         ▼                                                           │
│  delta.apply_delta(packet, "委屈", "再委屈一点")                   │
│  → 调整 push/power/speed 等 macro 参数                              │
│  → 重新走⑤⑥ → 新生成                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 新增/缺失文件快速索引

| 文件 | 模块 | 作用 | 之前状态 | 现在 |
|------|------|------|---------|------|
| [`species_template.py`](gaze_engine/_shared/species_template.py) | `_shared` | 物种底膜模板参数（几何参数数据类） | ❌ 缺失 | ✅ 已添加 |
| [`species_detector.py`](gaze_engine/_shared/species_detector.py) | `_shared` | 自动化检测（MediaPipe/OpenCV/YOLO） | ❌ 缺失 | ✅ 已添加 |
| [`cat/detect.py`](gaze_engine/cat/detect.py) | `cat` | 猫面部检测 + 品种推断 | ❌ 缺失 | ✅ 已添加 |
| [`dog/detect.py`](gaze_engine/dog/detect.py) | `dog` | 狗面部检测 + 品种推断 | ❌ 缺失 | ✅ 已添加 |
| [`human/rhythm_data.py`](gaze_engine/human/rhythm_data.py) | `human` | 节奏说明书人类文案 | ❌ 缺失 | ✅ 已添加 |
| [`cat/rhythm_data.py`](gaze_engine/cat/rhythm_data.py) | `cat` | 节奏说明书猫文案 | ❌ 缺失 | ✅ 已添加 |
| [`dog/rhythm_data.py`](gaze_engine/dog/rhythm_data.py) | `dog` | 节奏说明书狗文案 | ❌ 缺失 | ✅ 已添加 |
| [`pomot/pipeline.py`](gaze_engine/pomot/pipeline.py) | `pomot` | 两轮对话管线入口 | ❌ 缺失 | ✅ 已添加 |
| [`pomot/nl_splitter.py`](gaze_engine/pomot/nl_splitter.py) | `pomot` | NL→动作+情绪拆解 | ❌ 缺失 | ✅ 已添加 |
| [`pomot/emotion_router.py`](gaze_engine/pomot/emotion_router.py) | `pomot` | 情绪词→预设名路由 | ❌ 缺失 | ✅ 已添加 |
| [`pomot/registry.py`](gaze_engine/pomot/registry.py) | `pomot` | 预设注册表加载 | ❌ 缺失 | ✅ 已添加 |
| [`pomot/composer.py`](gaze_engine/pomot/composer.py) | `pomot` | 预设+NL→SliderPacket | ❌ 缺失 | ✅ 已添加 |
| [`pomot/delta.py`](gaze_engine/pomot/delta.py) | `pomot` | delta 微调叠加 | ❌ 缺失 | ✅ 已添加 |
| [`pomot/assembler.py`](gaze_engine/pomot/assembler.py) | `pomot` | 最终拼装→扩散引擎payload | ❌ 缺失 | ✅ 已添加 |
| [`pomot/templates.py`](gaze_engine/pomot/templates.py) | `pomot` | 数据类定义 | ❌ 缺失 | ✅ 已添加 |