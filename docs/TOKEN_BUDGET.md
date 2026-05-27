# TOKEN_BUDGET · Token 预算追踪与优化指南

> 目标：量化 Token 消耗，持续优化，让每一分钱都花在刀刃上。

---

## 一、当前优化措施 & 预估省 Token 量

| 优化措施 | 改动文件 | 省 Token 量（预估） | 原理 |
|---------|---------|-------------------|------|
| **AI_INDEX.md**（代码图谱） | [`AI_INDEX.md`](AI_INDEX.md) | 首次进入节省 3000-8000 | Agent 不再遍历目录，一次读完即理解全项目 |
| **内置 Prompt 压缩** | [`gaze_engine/_shared/llm_openai.py`](gaze_engine/_shared/llm_openai.py) | 回退路径节省 **55%** (380→170 tokens) | `_router_system_prompt()` 精简 |
| **模型分档** | [`gaze_engine/_shared/llm_openai.py`](gaze_engine/_shared/llm_openai.py) | consult 场景节省 **60-90%** | consult 走 CHEAP_MODEL |
| **知识库按需截短** | [`gaze_engine/_shared/llm_openai.py`](gaze_engine/_shared/llm_openai.py) | 轻量模型场景节省 50% | 知识库从 8000→4000/2000 chars |
| **廉价 apply prompt** | [`gaze_engine/_shared/llm_openai.py`](gaze_engine/_shared/llm_openai.py) | 简单场景节省 **70%** | `_cheap_apply_system_prompt()` ~50 tokens |
| **Agent 行为约束** | [`.cursorrules`](.cursorrules) | 单次任务节省 2000-5000 | 禁止 ls/grep/find 等浪费动作 |

**总计预估：单次任务 Token 消耗降低 60-80%**。

---

## 二、量化观测方法

### 2.1 记录优化前的基线

```bash
# 找一个典型任务（如"生成施压凝视，更冷更钉"）
# 记录：
# - 交互轮数
# - 总 Token 消耗（从 LLM API 账单 / Cursor 用量面板看）
# - 完成时间
```

### 2.2 优化后对比

```bash
# 同样任务，对比：
# - 交互轮数（预期减少 30-50%）
# - 单次调用 Token（预期减少 40-60%）
# - 总完成时间（可能更快或持平）
```

### 2.3 持续监控指标

| 指标 | 如何获取 | 目标值 |
|------|---------|-------|
| 单次 LLM 调用 prompt tokens | OpenAI API 返回 `usage.prompt_tokens` | < 500 |
| 单次 LLM 调用 completion tokens | OpenAI API 返回 `usage.completion_tokens` | < 200 |
| 首次项目理解 Token | Agent 读取 AI_INDEX.md 的 Token 开销 | < 2000 |
| Agent 每轮交互的 Tool 调用次数 | Cursor/VSCode 活动记录 | < 5 |

---

## 三、省 Token 工作流最佳实践

### 日常开发流程

```
① 有需求 → 先查 AI_INDEX.md（2 秒定位目标文件）
② 只读目标函数 / 类（不要读整个文件）
③ 修改代码（最小改动，输出 diff）
④ 只跑相关测试（不跑全量）
⑤ 提交
```

### 跟 AI Agent 交互时的精准指令模板

| 场景 | 推荐指令 | 不建议 |
|------|---------|--------|
| 改代码 | "改 [`gaze_engine/_shared/envelope_compile.py`](gaze_engine/_shared/envelope_compile.py) 的 `build_energy_envelope()`，把...改成..." | "帮我优化一下这个项目" |
| 查问题 | "在 [`human/human_prior.py`](gaze_engine/human/human_prior.py:275) 的 `apply_human_prior()` 里，过冲系数为什么是 0.3？" | "为什么生成的动画看起来不自然？" |
| 加功能 | "在 [`human/control_surface.py`](gaze_engine/human/control_surface.py:18) 的 PRESETS 里加一个预设...；同步更新 [`_shared/slider_bounds.py`](gaze_engine/_shared/slider_bounds.py)" | "帮我加一个新情绪" |

---

## 四、Token 消耗追踪表

复制这个表格到每次任务开始时，手动记录：

| 日期 | 任务 | 交互轮数 | LLM 调用次数 | 总 Prompt Tokens | 总 Completion Tokens | 成本($) |
|------|------|---------|-------------|-----------------|---------------------|---------|
|      |      |         |             |                 |                     |         |
|      |      |         |             |                 |                     |         |

---

## 五、进一步优化方向（当当前措施不够时）

1. **本地缓存 LLM 响应**：相同输入不重复调用（适合高频预设修改）
2. **离线意图分类**：用 `nl_intent.py` 的关键词规则代替 LLM consult
3. **缩短对话历史**：每次只保留最近 1-2 轮上下文
4. **使用更便宜的模型**：如 Gemini 1.5 Flash-8B / Claude 3 Haiku
5. **Pre-compile 预设**：16 预设的 macro JSON 预编译，LLM 只选 preset 名不再传全量

---

## 六、各模型 Token 价格参考（2026年）

| 模型 | 输入($/1M tokens) | 输出($/1M tokens) | 适合场景 |
|------|------------------|------------------|---------|
| GPT-4o-mini | $0.15 | $0.60 | 默认主模型（性价比之选） |
| Gemini 1.5 Flash | $0.075 | $0.30 | 比 GPT-4o-mini 再省 50% |
| Claude 3 Haiku | $0.25 | $1.25 | 质量更高但稍贵 |
| GPT-4o | $2.50 | $10.00 | 仅复杂推理场景使用 |

**建议**：日常工作用 `gpt-4o-mini`，简单 consult 切到 `gemini-1.5-flash` 或 `gpt-4o-mini`。