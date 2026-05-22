# Comfy 节点编号 1～7（和我沟通就用这个）

```text
Comfy 画布：1 → 2 → 4 → 5 → 6 → 7
（03 能量包络在节点 2 内写出，不必单独拖「3 能量包络」）
```

| 编号 | 画布名 | 类名 | 主要改哪个 .py |
|------|--------|------|----------------|
| **1** | 1 自然语言 | `JintaoEye_NaturalLanguageIn` | `nl_to_packet.py` `llm_openai.py` |
| **2** | 2 操作台 | `JintaoEye_OpenWorkbench` | `packet_finalize.py` `workbench_context.py` |
| **3** | （内嵌） | 节点 2 写出 `03_能量包络.json` | `envelope_compile.py` |
| **4** | 4 全量展开 | `JintaoEye_DenseFromEnvelope` | `envelope_compile.py` |
| **5** | 5 真人律 | `JintaoEye_HumanPrior` | `human_prior.py` |
| **6** | 6 平庸纠正 | `JintaoEye_PulseQuality` | `pulse_quality.py` |

**nodes_v1.py** 里搜：`# 节点 1`、`# 节点 2` …

---

## 节点 1 · 系统 Prompt + 知识库 + 客户话

**不用自己拼**：①② 留空或占位 → 自动读 `prompts/node1_system_prompt.txt`、`prompts/node1_knowledge_base.txt`。  
**修改轮**：勾选「带上轮滑杆」，会读上一轮 `01_滑杆包.json` 给 LLM。

| 输入 | 说明 |
|------|------|
| **系统Prompt** | 留空 → `prompts/node1_system_prompt.txt` |
| **知识库** | 留空 → `prompts/node1_knowledge_base.txt` |
| **客户自然语言** | 客户本轮说的话 |
| **带上轮滑杆** | 默认开；读历史包，支持「再冷一点」 |
| **用语言模型 / 语言模型** | 默认开 gpt-4o-mini |

| 输出 | 说明 |
|------|------|
| **滑杆包路径** | apply 时写 `01_滑杆包.json`；consult 时沿用旧包 |
| **模型回复** | 咨询或生成确认 → `01_咨询回复.txt` |

落盘：`01_系统Prompt.txt`、`01_操作台上下文.json`（含 `energy_map_note`、`last_slider_packet`）→ **节点 2 自动吃**

---

## 节点 2 · 定稿保存（不再打开网页）

**角色**：接节点 1 滑杆 → L1 禁区 → 写 `02_滑杆_L1纠正.json` + `03_能量包络.json` + 上下文（下轮节点 1 改包用）。**不**在本节点展开全量；全量在节点 4。

## 节点 2 控件（Comfy）

| 框名 | 干什么 |
|------|--------|
| **上步产物路径** | 接节点 1 的「滑杆包路径」 |
| **导演自然语言 / 知识库 / 能量图说明(来自节点1)** | 留空自动读节点 1 写入的上下文 |
| **情绪预设 / 用手动滑杆 / 六根滑杆…** | 见 `contracts/滑杆规范.md` |

---

## 写出文件（资产库/…/指令/）

| 编号 | 文件 |
|------|------|
| 1 | `01_滑杆包.json` `01_自然语言.txt` `01_操作台上下文.json` |
| 2 | `02_滑杆_L1纠正.json` |
| 3 | `03_能量包络.json` |
| 4 | `04_全量_包络展开.json` |
| 5 | `05_全量_真人律.json` |
| 6 | `06_全量_平庸纠正.json` |
| 7 | `02_烘焙_真人律.json` + 灰模 |

---

## 你怎么和我说

- 「改 **1**」= `nl_to_packet.py` `llm_openai.py`
- 「**1→2**」= 滑杆包路径串联

工作流：`workflows/ecursor_S01.json` · Reload Custom Nodes 后加载 **revision 15**。
