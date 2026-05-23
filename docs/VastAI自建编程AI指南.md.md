# Vast.ai 自建编程 AI 助手完整指南

> 目标：租用 GPU 显卡 → 安装 DeepSeek 等模型 → 配置 Cursor/VSCode 使用自定义后端 → **告别按 Token 付费**

---

## 一、准备工作

### 1.1 确认 Vast.ai 账户余额

登录 [vast.ai](https://vast.ai) → 右上角钱包 → 确认有 **$50**

### 1.2 本地需要安装的工具

在你自己的电脑上安装 SSH 客户端（Linux/Mac 自带，Windows 用 PowerShell 或 Git Bash）

---

## 二、Vast.ai 租用 GPU

### 2.1 搜索合适的实例

1. 登录 Vast.ai → 左侧 **"Rent"** 标签
2. 设置搜索条件（图例参考）：

```
GPU RAM: ≥ 22000 MB    ← 必须，模型需要显存
Price:    ≤ 0.40 $/hr  ← 控制预算
CUDA:     ≥ 12.0       ← 新模型需要
Disk:     ≥ 20 GB      ← 模型文件大约 10-15GB
```

3. 推荐 GPU 型号（按性价比排序）：

| GPU | 显存 | 典型价格 | $50 可用时长 | 能跑的模型 |
|-----|------|----------|-------------|-----------|
| RTX 3090 | 24GB | $0.20-0.30/hr | **~200 小时** | 7B~16B 模型 |
| RTX 4090 | 24GB | $0.30-0.45/hr | **~140 小时** | 7B~16B 模型 |
| RTX 3090 Ti | 24GB | $0.30-0.40/hr | **~150 小时** | 同上 |
| 2× RTX 3090 | 48GB | $0.50-0.70/hr | **~80 小时** | 33B~70B 模型 |

> **推荐：单张 RTX 3090（$0.25/hr）**，跑 16B 模型绰绰有余

### 2.2 筛选技巧

- **Sort by:** → `Price $/hr`（按价格从低到高）
- **只看 "Verified"** 标记的提供商（更稳定）
- **IDLE 时间** 选短一点的（按小时计费，不用时关掉）
- **Location** 选靠近你的地区（延迟低）

### 2.3 租用步骤

1. 找到心仪的实例 → 点击 **"Rent"**
2. 选择模板：
   - **Template:** 搜索 `ollama` 或 `pytorch` 或 `ubuntu`
   - 推荐选 **"ollama/ollama"** 模板（预装 Ollama，最简单）
   - 如果没有，选 **"pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"**
3. 在 **"On-Start Script"** 框里粘贴下面这段启动脚本：

```bash
#!/bin/bash
# 自动安装 Ollama + 下载模型 + 启动 OpenAI 兼容 API

# 1. 安装 Ollama（如果模板没预装）
which ollama || (curl -fsSL https://ollama.com/install.sh | sh)

# 2. 下载 DeepSeek-Coder 模型（编程专用，6.7B，24GB VRAM 能跑）
ollama pull deepseek-coder-v2:16b-lite-instruct-q4_K_M

# 或者（选其中一个，别都下）：
# ollama pull qwen2.5-coder:14b-instruct-q4_K_M  # 另一种选择

# 3. 配置 Ollama 允许外部访问
cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
systemctl daemon-reload
systemctl restart ollama

# 4. 打印完成信息
echo "=========================================="
echo "Ollama 已启动！"
echo "API 地址: http://<你的实例IP>:11434"
echo "测试: curl http://localhost:11434/api/tags"
echo "=========================================="
```

4. 点击 **"Rent"** 完成租用

---

## 三、连接与验证

### 3.1 获取连接信息

租用成功后，Vast.ai 会显示：
- **IP 地址**（如 `185.XXX.XXX.XXX`）
- **端口号**（如 `21345`）
- **SSH 命令**（如 `ssh -p 21345 root@185.XXX.XXX.XXX`）

### 3.2 登录到实例

在你本地电脑打开终端，执行 Vast.ai 提供的 SSH 命令：

```bash
ssh -p <端口号> root@<IP地址>
```

首次连接会提示确认指纹，输入 `yes`

### 3.3 验证模型在运行

登录后，执行：

```bash
# 检查 Ollama 是否运行
ollama list

# 测试模型是否能正常响应
curl http://localhost:11434/api/generate -d '{
  "model": "deepseek-coder-v2:16b-lite-instruct-q4_K_M",
  "prompt": "用 Python 写一个快速排序",
  "stream": false
}'
```

如果返回了 JSON 格式的代码，说明成功了！

### 3.4 获取公网 API 地址

在 Vast.ai 实例详情页，找到：
- **"Port Mappings"** 或 **"Open Ports"**
- 确保 `11434` 端口是 **公开（Public）** 状态

如果要暴露 API 地址，你的地址格式是：

```
http://<Vast实例IP>:<映射端口>/v1
```

> 例如：`http://185.123.45.67:21346`

测试方法（在你的本地电脑执行）：

```bash
curl http://<Vast实例IP>:<映射端口>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-coder-v2:16b-lite-instruct-q4_K_M",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

---

## 四、配置 Cursor 使用自建模型

### 4.1 Cursor 设置

Cursor 支持自定义 API endpoint：

1. 打开 Cursor → `Settings`（`Cmd+,` / `Ctrl+,`）
2. 左侧 → **Models** 或 **AI** 标签
3. 找到 **"Custom API Endpoint"** 或类似选项
4. 填入：

```
API Endpoint: http://<你的Vast实例IP>:<端口>/v1
API Key:     随便填一个（比如 "not-needed"）
Model:       deepseek-coder-v2:16b-lite-instruct-q4_K_M
```

5. 保存，然后在对话中选择这个自定义模型

### 4.2 安装 Continue.dev 插件（备选方案）

如果 Cursor 不支持自定义端点，用 VSCode + Continue 插件：

1. 安装 VSCode
2. 安装 **Continue** 插件（`continue.continue`）
3. 配置 `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "My DeepSeek",
      "provider": "openai",
      "model": "deepseek-coder-v2:16b-lite-instruct-q4_K_M",
      "apiBase": "http://<你的Vast实例IP>:<端口>/v1",
      "apiKey": "not-needed"
    }
  ],
  "tabAutocompleteModel": {
    "title": "My DeepSeek Auto",
    "provider": "openai",
    "model": "deepseek-coder-v2:16b-lite-instruct-q4_K_M",
    "apiBase": "http://<你的Vast实例IP>:<端口>/v1",
    "apiKey": "not-needed"
  }
}
```

---

## 五、推荐模型选择

| 模型 | 参数量 | 最低显存 | 质量 | 推荐度 |
|------|--------|---------|------|--------|
| `deepseek-coder-v2:16b-lite-instruct-q4_K_M` | 16B | 12GB | ★★★★★ 编程最强 | ⭐⭐⭐⭐⭐ |
| `qwen2.5-coder:14b-instruct-q4_K_M` | 14B | 10GB | ★★★★☆ 优秀 | ⭐⭐⭐⭐ |
| `qwen2.5-coder:7b-instruct-q4_K_M` | 7B | 6GB | ★★★☆☆ 够用 | ⭐⭐⭐ |
| `codellama:7b-instruct-q4_K_M` | 7B | 6GB | ★★★☆☆ | ⭐⭐⭐ |
| `deepseek-coder-v2:16b-lite-instruct-fp16` | 16B | 24GB | ★★★★★ 满精度 | ⭐⭐⭐⭐（显存刚够） |

> **安装命令:** `ollama pull <模型名>`

建议装两个模型一个主力一个备胎：

```bash
# 主力（编程专用）
ollama pull deepseek-coder-v2:16b-lite-instruct-q4_K_M

# 备胎（小模型，快速响应简单问题）
ollama pull deepseek-coder-v2:16b-lite-instruct-q4_K_M
```

---

## 六、使用与关闭

### 6.1 日常使用

每次要写代码时：
1. 登录 Vast.ai → 点击你的实例 → **"Start"**
2. 等 1-2 分钟让服务起来
3. 在 Cursor 中开始写代码

### 6.2 用完关掉（省钱关键！）

**用完一定要关！** 否则会持续扣费。

- **停止实例：** 点 **"Stop"** — 只停计算，保留磁盘（不扣 GPU 费）
- **销毁实例：** 点 **"Destroy"** — 全部删除（下次要重新装模型）

> 建议：每次用完点 **Stop**，下次 **Start** 即可继续用，模型还在

### 6.3 费用监控

Vast.ai 右上角钱包 → **"Billing"** 查看消耗

```bash
# 估计用量
# RTX 3090 @ $0.25/hr → 每天用8小时 = $2/天 → $50 可以用 25天
# 比 API 按量付费便宜 5-10 倍
```

---

## 七、高级：用 vLLM 替代 Ollama（更快）

Ollama 简单但不是最快的。想要更好的性能，用 **vLLM**（支持 PagedAttention，显存利用率更高）：

### 在实例上安装 vLLM

```bash
# 登录到 Vast 实例后执行

# 1. 安装依赖
pip install vllm

# 2. 启动 vLLM 服务器
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/deepseek-coder-v2-lite-instruct \
    --dtype auto \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.9 \
    --host 0.0.0.0 \
    --port 8000
```

然后 API 地址就是 `http://<IP>:8000/v1`

---

## 八、常见问题

### Q: 模型响应太慢？
- 换小模型（如 `qwen2.5-coder:7b`）
- 检查是否用了量化版（带 `q4_K_M` 的更快）
- 换更高端的 GPU（如 RTX 4090）

### Q: 显存不够？
- 用量化模型（`q4_K_M` 后缀的）
- 检查其他进程是否占用了显存：`nvidia-smi`

### Q: 连接不上？
- 确认实例是 Running 状态
- 确认端口映射正确
- 在 Vast 控制台检查防火墙设置

### Q: 想用 DeepSeek-R1 做推理？
R1 蒸馏版可以在 24GB 上运行：

```bash
ollama pull deepseek-r1:14b
ollama pull deepseek-r1:7b  # 更小更快
```

### Q: 如何让模型也支持我的项目上下文？
在 Cursor 的 `.cursorrules` 文件里写好项目说明，和现在一样用。

---

**总结：** RTX 3090（$0.25/hr）+ DeepSeek-Coder-V2-Lite（16B）= $50 用 **200 小时**，搞定编程 AI 助手