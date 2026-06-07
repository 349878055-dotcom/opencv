# gaze_engine 模块分类地图

> **物理目录结构**：每个管线阶段一个独立子目录，文件按职责归类。
>
> 与合同管线编号一致：`01`→`08`，见 [`合同/00_管线导读/00_从门户到扩散_管线总览.md`](../合同/00_管线导读/00_从门户到扩散_管线总览.md)。

---

## 目录结构总览

```
gaze_engine/
├── 00_MODULE_MAP.md         ← 本文件
├── __init__.py              ← 包初始化
│
├── input/                   ← 01_输入与收口（s01）
│   ├── control_surface.py       🏆 16预设唯一真源
│   ├── slider_schema.py         SliderPacket 数据类
│   ├── slider_bounds.py         L1 禁区
│   ├── packet_finalize.py       收口校验
│   ├── channel_contract.py      🧹 校验函数
│   └── node1_defaults.py        默认值加载
│
├── envelope/                ← 02_情绪与能量 → E(t)（s02）
│   ├── envelope_compile.py      ⭐ E(t) 主钟 + 人类通道编译
│   └── emotion_pad.py           38 情绪 PAD 真源表
│
├── pad/                     ← 03_情绪坐标 → pad_scale[12]（s03）
│   └── pad_weights.py           人类 PAD 权重表
│
├── channel/                 ← 04_通道编译 → pulse[12×150]（s04）
│   ├── micro_jitter.py          微颤动引擎
│   └── oculomotor_prior.py      眼动先验（扫视动力学 + 通道耦合）
│
├── style/                   ← 05_风格化 → styled[12×150]（s05）
│   ├── style_compose.py         pulse→styled
│   ├── persona_compiler.py      九大人格 apply_persona_style
│   ├── persona_matrix.json      九大人格矩阵
│   └── persona_style_catalog.json 九大人格风格真源
│
├── prior_qc/                ← 06_先验与质检 → final[12×150]（s06）
│   ├── human_prior.py           真人化先验
│   ├── pulse_quality_core.py    平庸三检核心
│   └── pulse_quality.py         平庸三检（人类包装）
│
├── render/                  ← 07_工程底膜 → MP4（s07）
│   ├── affine_renderer.py       🏆 主渲染器（OpenCV 线条图）
│   ├── affine_gloss.py          眼湿润高光
│   ├── species_template.py      人类底膜模板 17参数
│   ├── species_detector.py      MediaPipe 人脸 468 点检测
│   ├── spatial_calibration.py   空间标定（仿射矩阵）
│   ├── geometry_adapter.py      几何适配补丁
│   ├── base_mesh_gen.py         基础网格
│   └── assets/                  工程底膜素材（eyelid_raw.png）
│
├── delivery/                ← 08_输出与扩散 → Wan（s08）
│   ├── delivery_pipeline.py     🏆 主交付链（01→06 端到端编排）
│   ├── project_archive.py       项目归档 + 扩散包
│   ├── rhythm_compiler.py       节奏说明书编译器
│   ├── rhythm_data.py           节奏说明书人类文案
│   ├── pipeline_io.py           JSON 读写
│   ├── workbench_io.py          操作台读写
│   ├── workbench_context.py     上下文管理
│   ├── audio_compiler.py        ⚠️ 禁用中
│   └── pomot/                   🏆 预设 Prompt 模板合成引擎
│       ├── pipeline.py              管线入口（round1 / round2）
│       ├── nl_splitter.py           NL 拆解器
│       ├── emotion_router.py        情绪路由
│       ├── registry.py              预设注册表
│       ├── templates.py             数据类
│       ├── composer.py              第一轮合成
│       ├── delta.py                 第二轮微调
│       └── assembler.py             最终拼装 → 送扩散引擎
│
├── nl/                      ← NL 自然语言
│   ├── nl_intent.py              意图分类
│   ├── nl_router.py              NL 路由
│   └── nl_to_packet.py           关键词→预设
│
├── _shared/                 ← 🏗 基础设施
│   ├── customer_db.py             客户资产库 CRUD + 认证
│   └── llm_openai.py              LLM 集成
│
└── test_persona_integrity.py  ← 🧪 人格完整性自检
```

---

## 模块依赖关系

```
01_input ──→ 02_envelope ──→ 03_pad ──→ 04_channel
                                            │
                                            ▼
                                        05_style
                                            │
                                            ▼
                                        06_prior_qc
                                            │
                                            ▼
                                        07_render
                                            │
                                            ▼
                                        08_delivery ──→ Wan

🏗 _shared      NL
(customer_db,   (nl_intent,
 llm_openai)     nl_router, nl_to_packet)
```

---

## 快速查找：文件 → 目录

| 文件 | 目录 |
|------|------|
| `control_surface.py` | `01_input/` |
| `slider_schema.py` | `01_input/` |
| `slider_bounds.py` | `01_input/` |
| `packet_finalize.py` | `01_input/` |
| `channel_contract.py` | `01_input/` |
| `node1_defaults.py` | `01_input/` |
| `envelope_compile.py` | `02_envelope/` |
| `emotion_pad.py` | `02_envelope/` |
| `pad_weights.py` | `03_pad/` |
| `micro_jitter.py` | `04_channel/` |
| `oculomotor_prior.py` | `04_channel/` |
| `style_compose.py` | `05_style/` |
| `persona_compiler.py` | `05_style/` |
| `persona_matrix.json` | `05_style/` |
| `persona_style_catalog.json` | `05_style/` |
| `human_prior.py` | `06_prior_qc/` |
| `pulse_quality_core.py` | `06_prior_qc/` |
| `pulse_quality.py` | `06_prior_qc/` |
| `affine_renderer.py` | `07_render/` |
| `affine_gloss.py` | `07_render/` |
| `species_template.py` | `07_render/` |
| `species_detector.py` | `07_render/` |
| `spatial_calibration.py` | `07_render/` |
| `geometry_adapter.py` | `07_render/` |
| `base_mesh_gen.py` | `07_render/` |
| `assets/` | `07_render/` |
| `delivery_pipeline.py` | `08_delivery/` |
| `project_archive.py` | `08_delivery/` |
| `rhythm_compiler.py` | `08_delivery/` |
| `rhythm_data.py` | `08_delivery/` |
| `pipeline_io.py` | `08_delivery/` |
| `workbench_io.py` | `08_delivery/` |
| `workbench_context.py` | `08_delivery/` |
| `audio_compiler.py` | `08_delivery/` |
| `pomot/*` | `08_delivery/pomot/` |
| `nl_intent.py` | `nl/` |
| `nl_router.py` | `nl/` |
| `nl_to_packet.py` | `nl/` |
| `customer_db.py` | `_shared/` |
| `llm_openai.py` | `_shared/` |

---

> **维护说明**：新增文件时请放入对应目录，并更新本映射表。
