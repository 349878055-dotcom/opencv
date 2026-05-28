# AutoDL 扩散引擎部署专篇 — 从门户导出到 GPU 成片

> **管线位置**：本地门户 `export` → **本环节（AutoDL + ComfyUI + Wan Fun Control）** → 成片 MP4 回传  
> **状态：2026-05-28** · 对齐当前代码与 Wan 2.2 Fun Control 节点  
> **合同规范**：本文遵循 [`合同规范.md`](../合同规范.md) 五段格式

**一句话**：本地只跑眼眉编译与底膜渲染；GPU 推理放 [AutoDL](https://www.autodl.com/console/instance/list)。首次把 ComfyUI + 模型装进**数据盘**，之后「开机 → 启动 Comfy → 上传扩散包 → 跑工作流 → 关机」即可。

---

## ⚡ 极速路径（避免上次数小时白跑）

### 全权委托模式（你不会 SSH 也行）

**你只需要做 3 件事**，其余（装 Comfy、下模型、启服务、工作流、试跑）**全部发 SSH 给我搞定**：

| # | 你在 AutoDL 网页上 | 说明 |
|---|-------------------|------|
| 1 | [实例列表](https://www.autodl.com/console/instance/list) → **创建实例** | 镜像选 **ComfyUI 社区镜像**；GPU **4090 24G**；数据盘 **100G** |
| 2 | 等状态 **运行中** → 复制 **SSH 登录指令** + **root 密码** | 控制台实例卡片里都有 |
| 3 | **发给我**（聊天里粘贴即可） | 见下方模板 |

```text
【AutoDL 全权委托】
SSH: ssh -p XXXXX root@connect.xxxx.seetacloud.com
密码: xxxxx
镜像名: （控制台显示的完整名字）
```

发完你就可以不管了。我会：SSH 进去 → 跑 bootstrap → 启 Comfy 8188 → 导入 Fun Control 工作流 → 试跑；需要扩散包时会让你本地点一下「导出」，或你告诉我项目路径我指导你点哪。

### 阶段一：今天只装机、不跑测试包（推荐）

测试包还要调参时，**今天不必 export**。「弄好」= 环境就绪，可随时接包：

| 验收项 | 今天做到 | 不测包 |
|--------|----------|--------|
| ComfyUI 8188 能打开 | ✅ | — |
| Wan 2.2 六个模型文件齐全 | ✅ | — |
| VideoHelperSuite 已装 | ✅ | — |
| Fun Control 150 帧工作流已导入 | ✅ | — |
| 用占位图自检节点不报错 | ✅（可选） | 不跑完整 5 秒成片 |
| 关机保留数据盘 | ✅ | — |

**你发 SSH → 我装完告诉你「阶段一 OK」→ 你关机**。  
等测试包调满意了，再 **阶段二**：export → scp 上传 → 跑第一支成片（通常 15 分钟）。

> **安全提示**：密码用完后可在 AutoDL 控制台改密；不要用主账号长期明文密码。

---

上次慢/失败的常见原因：**裸 PyTorch 镜像从零装**、**HuggingFace 直连**、**用了 I2V 工作流没有 control_video**。

| 步骤 | 做什么 | 预计时间 |
|------|--------|----------|
| ① 选镜像 | AutoDL **社区镜像**里搜 **ComfyUI**（已带 Python/torch） | 2 min |
| ② 选 GPU | **RTX 4090 24G**，数据盘 **100G** | 2 min |
| ③ SSH 一键装机 | 跑 [`scripts/autodl_bootstrap_wan22.sh`](../../scripts/autodl_bootstrap_wan22.sh)（hf-mirror 国内加速） | 20–40 min（仅首次下模型） |
| ④ 启 Comfy | `bash /root/autodl-tmp/scripts/start_comfy.sh` + 控制台映射 **8188** | 2 min |
| ⑤ 发我 SSH | 我远程导入 **Fun Control 150 帧**工作流 + 试跑 | 15–30 min |

**不要选**：纯 Ubuntu、纯 PyTorch 无 Comfy、Wan 2.1 GGUF 镜像（和本项目 2.2 Fun Control 不一致）。

**SSH 发我格式**（复制控制台整行即可）：

```text
ssh -p <端口> root@<主机>
GPU: RTX 4090
数据盘: /root/autodl-tmp
镜像名: （控制台显示的社区镜像名）
Comfy 是否已预装: 是/否
本地是否已有扩散包: 是/否
```

**引用本合同的兄弟文件**：

| 文件 | 关系 |
|------|------|
| [`00_从门户到扩散_管线总览.md`](../00_管线导读/00_从门户到扩散_管线总览.md) | 上游：S0–S8 全链 |
| [`扩散引擎包组装专篇.md`](扩散引擎包组装专篇.md) | 上游：`export` 产出 `扩散引擎包/` |
| [`扩散引擎提示词拼装规范.md`](扩散引擎提示词拼装规范.md) | 并列：Wan CLIP 拆分 §4.8 |
| [`12通道到底膜MP4专篇.md`](../06_工程底膜/12通道到底膜MP4专篇.md) | 并列：03 MP4 规格（150 帧 RGB） |

**代码真源**：

| 职责 | 文件 |
|------|------|
| 扩散包落盘 | `gaze_engine/_shared/project_archive.py:build_diffusion_bundle()` |
| 门户 export | `tools/01_工作台服务/serve_workbench.py:portal_export()` |
| Wan 接线 | `gaze_engine/pomot/assembler.py:split_for_wan()` |

---

## 一、概述（What）

### 1.1 本文件管什么

| 环节 | 范围 |
|------|------|
| ✅ AutoDL 实例怎么选、数据盘要不要开 | 算力 + 持久化存储 |
| ✅ 首次装机清单 | ComfyUI、Wan 2.2 模型、插件、工作流 |
| ✅ 日常开关机 SOP | 省钱、不丢模型 |
| ✅ 扩散包怎么上传、怎么喂 Wan | `control_video` + `wan±` + `start_image` |
| ✅ 你需要给我（AI/协作者）什么信息 | SSH、路径、样例包 |
| ✅ 验收 | 成片与底膜节拍对齐 |

### 1.2 全链路一张图

```text
┌─ 本地（CPU 即可，门户 8765）────────────────────────────────────┐
│  客户门户 → Pomot → 保存 → export                                  │
│  产出：客户资产库/…/输出/扩散引擎包/                                │
│    · 03_工程底模.mp4                                               │
│    · wan_positive.txt / wan_negative.txt                           │
│    · start_image.jpg                                               │
│    · manifest.json（ready_for_diffusion: true）                    │
└───────────────────────────────┬───────────────────────────────────┘
                                │ scp / AutoDL 网盘 / rsync
                                ▼
┌─ AutoDL（GPU 计费）───────────────────────────────────────────────┐
│  ComfyUI + Wan22FunControlToVideo                                │
│    control_video ← 03_工程底模.mp4                                 │
│    start_image   ← start_image.jpg                               │
│    positive      ← wan_positive.txt                                │
│    negative      ← wan_negative.txt                                │
│    length = 150  fps = 30                                          │
└───────────────────────────────┬───────────────────────────────────┘
                                │ 下载成片
                                ▼
                         本地验收 / 交付客户
```

### 1.3 边界（非管辖）

| ❌ 不管 | 见 |
|---------|-----|
| 02 怎么编译、底膜怎么画 | `06_工程底膜/` |
| 04 五段怎么拼 | [`扩散引擎提示词拼装规范.md`](扩散引擎提示词拼装规范.md) |
| 门户 UI 交互 | [`UI设计原则.md`](UI设计原则.md) |
| AutoDL 账号充值、发票 | AutoDL 官方文档 |

### 1.4 角色分工

| 角色 | 跑在哪 | 做什么 |
|------|--------|--------|
| **眼眉引擎** | 本地 | Pomot、02 烘焙、03 MP4、扩散包 |
| **扩散引擎** | AutoDL GPU | Wan 图生视频 + Fun Control |
| **你** | 两边 | 门户定稿 export；AutoDL 开关机与上传包 |
| **AI 协作者** | 远程 | 帮你写启动脚本、Comfy 工作流、排查 OOM |

---

## 二、理论依据（Theory）

### 2.1 为什么要拆本地 + 云端

| 约束 | 含义 |
|------|------|
| 眼眉管线 | OpenCV 渲染 + 大量 Python 合同逻辑，**CPU 足够**，改参频繁 |
| Wan 2.2 14B | 单卡 **≥24GB VRAM**（fp8 + 4step LoRA 约 83% 4090 占用） |
| 计费 | AutoDL **按 GPU 开机时长**计费；本地门户可 24h 不关 |
| 数据同源 | MP4 与 Prompt 必须 **同 revision**（见 [`扩散引擎包组装专篇.md`](扩散引擎包组装专篇.md) §3.2） |

### 2.2 Wan 节点选型（必须用 Fun Control）

本项目底膜是 **RGB 三色控制视频**，不是普通 I2V：

| 节点 | 是否适用 | 原因 |
|------|----------|------|
| `WanImageToVideo` | ❌ | 无 `control_video` 输入，无法控制眉眼节奏 |
| `WanFunControlToVideo` | ✅ Wan 2.1 | 有 `control_video` |
| **`Wan22FunControlToVideo`** | ✅ **推荐** | Wan 2.2 + `control_video`，与本地已有 2.2 模型一致 |

ComfyUI 内置节点定义：`comfy_extras/nodes_wan.py` → `Wan22FunControlToVideo`。

### 2.3 帧数对齐

| 来源 | 值 |
|------|-----|
| 眼眉引擎 03 MP4 | **150 帧 @ 30fps = 5 秒** |
| Wan 工作流 `length` | 必须设 **150**（步长 4 的整数倍，150 合法） |
| 输出 `CreateVideo` fps | **30**（与底膜一致，便于对拍） |

---

## 三、为什么这样做（Why）

### 3.1 关键决策

| 决策 | 备选 | 选择 | 理由 |
|------|------|------|------|
| 存储 | 只用系统盘 | **开数据盘 + 模型放数据盘** | 系统盘 ~30GB，Wan 模型一套 ~40GB+ |
| 实例生命周期 | 释放重建 | **关机保留实例** | 释放 = 全丢；关机只停 GPU 费 |
| 包传输 | 整库同步 | **只 scp `扩散引擎包/`** | 每次项目几 MB～几十 MB |
| 工作流 | 官方 I2V 模板 | **自建 Fun Control 流** | 官方 blueprint 无 control_video |
| 门户位置 | 放 AutoDL | **放本地** | 改合同/预设不需要 GPU |

### 3.2 AutoDL 三种「停」的区别（必懂）

| 操作 | GPU 费 | 数据盘 | 系统盘环境 | 何时用 |
|------|--------|--------|------------|--------|
| **关机** | 停 | 保留 | 一般保留 | 今天不用 GPU 了 |
| **重启** | 计费继续 | 保留 | 保留 | Comfy 卡死 |
| **释放实例** | 停 | **清空** | **清空** | 彻底不用这台了 |

> **结论**：模型、ComfyUI、工作流一律放 **数据盘**；长期素材可再挂 **AutoDL 网盘**（跨实例共享，略慢）。

---

## 四、怎么实现（How）

### 4.0 你需要给我（AI）什么 — 清单

开始远程协助前，请准备：

| # | 信息 | 示例 | 用途 |
|---|------|------|------|
| 1 | AutoDL **SSH 登录命令** | `ssh -p 12345 root@connect.westb.seetacloud.com` | 远程装环境 |
| 2 | **数据盘挂载路径** | 通常是 `/root/autodl-tmp` 或控制台显示的 `数据盘` 路径 | 模型落盘 |
| 3 | GPU 型号 | RTX 4090 24G | 确认能跑 fp8 14B |
| 4 | 是否已有 ComfyUI | 无 / 有，路径 | 决定全新装还是补模型 |
| 5 | **一份真实扩散包** | 门户 export 后的 `扩散引擎包/` 整目录 | 联调 Wan 接线 |
| 6 | `manifest.json` | `ready_for_diffusion: true` | 确认本地 export 成功 |
| 7 | 期望分辨率 | 如 640×640 或 832×480 | 工作流 width/height |
| 8 | （可选）HuggingFace / 镜像 Token | 内网下载模型 | 加速首次拉模型 |

**不需要给我**：AutoDL 登录密码长期明文（可临时开、用完改）；客户隐私原图若敏感可只给脱敏测试包。

---

### 4.1 AutoDL 控制台：实例与存储怎么组

#### Step 1 · 注册与充值

1. 打开 [AutoDL 控制台 · 实例列表](https://www.autodl.com/console/instance/list)
2. 充值（按量计费，4090 约 ¥2–3/小时量级，以页面为准）

#### Step 2 · 创建实例

| 配置项 | 推荐 |
|--------|------|
| 地区 | 离你近 + 有 4090/3090 24G |
| 镜像 | **PyTorch 2.x + CUDA 12.x** 或 **ComfyUI 官方/community 镜像**（若有） |
| GPU | **RTX 4090 24GB**（Wan 2.2 fp8 14B 官方测 ~84% VRAM） |
| 系统盘 | 默认即可 |
| **数据盘** | **≥50GB，建议 100GB** |

> **是否单独组「空间存储」？**  
> - **要开数据盘**（跟实例一起买）— 放 ComfyUI + 模型，关机不丢。  
> - **网盘**（可选）— 放备份工作流、成片归档；不是必须第一步。  
> - **不需要**单独再买对象存储；初期 `scp` 扩散包足够。

#### Step 3 · 记录连接信息

控制台实例卡片 → **SSH 指令**、**Jupyter**、**自定义服务**（后面 ComfyUI 8188 端口映射用）。

---

### 4.2 目录规划（数据盘，一次定终身）

```text
/root/autodl-tmp/                    ← 数据盘根（示例，以控制台为准）
├── ComfyUI/                         ← git clone 或镜像自带
│   ├── models/
│   │   ├── diffusion_models/        ← Wan 2.2 UNet ×2
│   │   ├── loras/                   ← lightx2v 4step ×2
│   │   ├── text_encoders/           ← umt5_xxl_fp8
│   │   └── vae/                     ← wan_2.1_vae
│   ├── custom_nodes/
│   │   └── comfyui-videohelpersuite/  ← 读 MP4 帧
│   └── user/
│       ├── default/workflows/
│       │   └── eye_wan22_fun_control_150.json   ← 眼眉专用工作流（待建）
│       └── input/
│           └── diffusion_bundle/    ← 每次上传扩散包放这里
└── scripts/
    ├── start_comfy.sh
    └── pull_wan22_models.sh
```

**软链技巧**（若 Comfy 在系统盘、模型在数据盘）：

```bash
ln -s /root/autodl-tmp/models /root/ComfyUI/models
```

---

### 4.3 首次装载清单（只做一次）

#### A. ComfyUI

```bash
cd /root/autodl-tmp
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

若镜像已带 ComfyUI，跳过 clone，**确认版本 ≥ 0.3.45**（含 Wan 2.2 节点）。

#### B. 必要插件

```bash
cd custom_nodes
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
# ComfyUI-Manager 建议一并安装，便于补依赖
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
```

#### C. Wan 2.2 模型（与本地 blueprint 一致）

| 文件 | 目录 |
|------|------|
| `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | `models/diffusion_models/` |
| `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | `models/diffusion_models/` |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` | `models/loras/` |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` | `models/loras/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `models/text_encoders/` |
| `wan_2.1_vae.safetensors` | `models/vae/` |

下载源：[Comfy-Org Wan 2.2 Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged)（AutoDL 实例内可用 `huggingface-cli` 或 `wget`）。

#### D. 眼眉专用工作流（待你 export 后我帮你定稿）

在标准 Wan 2.2 I2V 基础上改动：

```text
Load Image          → start_image
VHS_LoadVideo       → control_video（03_工程底模.mp4，frame_load_cap=150，force_rate=30）
Load Text（或 Primitive）→ wan_positive / wan_negative
Wan22FunControlToVideo
  · length = 150
  · width / height = 与项目约定一致（如 640×640）
KSamplerAdvanced ×2（high/low noise 分段，同官方 2.2 模板）
CreateVideo fps = 30
Save Video
```

> **P0**：工作流必须走 `Wan22FunControlToVideo`，不是 `WanImageToVideo`。

#### E. 启动脚本 `scripts/start_comfy.sh`

```bash
#!/bin/bash
set -e
cd /root/autodl-tmp/ComfyUI
# 监听 0.0.0.0 以便 AutoDL 自定义服务映射
python main.py --listen 0.0.0.0 --port 8188
```

控制台 → **自定义服务** → 添加 `8188` → 获得外网 URL（形如 `https://xxxxx.autodl.pro`）。

---

### 4.4 日常 SOP：随时关机、随时启动

#### 开机（要用 GPU 时）

```text
① AutoDL 控制台 → 实例 → 「开机」
② 等状态 Running
③ SSH 登录（或 Jupyter 终端）
④ bash /root/autodl-tmp/scripts/start_comfy.sh &
⑤ 控制台确认 8188 自定义服务 → 浏览器打开 ComfyUI
```

#### 关机（今天收工）

```text
① Comfy 队列跑完后 Ctrl+C 停 main.py
② 控制台 → 「关机」
③ 确认 GPU 已停止计费（实例列表显示「已关机」）
```

#### **不要**做的

- ❌ 把大模型放系统盘后不备份就「释放实例」
- ❌ 在 GPU 关机状态下指望还能推理（除非另开 CPU 实例，本项目不需要）
- ❌ 用旧扩散包配新 02（revision 不一致）

#### 可选：无 GPU 时本地门户

```bash
cd /path/to/jintao_node_eye
./一键打开创作门户.sh
# Pomot → 保存 → export → 得到扩散引擎包
```

---

### 4.5 单次项目：从 export 到成片

#### Step 1 · 本地 export

门户路径：`客户资产库/客户_{cid}/项目_{pid}/输出/扩散引擎包/`

验收：

```bash
cat 客户资产库/.../扩散引擎包/manifest.json | python3 -m json.tool
# ready_for_diffusion 必须为 true
```

#### Step 2 · 上传到 AutoDL

本地执行（把端口/主机换成你的）：

```bash
BUNDLE="客户资产库/客户_C001/项目_P001/输出/扩散引擎包"
scp -P <SSH端口> -r "$BUNDLE"/* root@<主机>:/root/autodl-tmp/ComfyUI/input/diffusion_bundle/
```

或在 AutoDL **文件存储 / Jupyter 上传**（小文件可用，大 MP4 建议 scp）。

#### Step 3 · ComfyUI 里接线

| Wan 输入 | 文件 |
|----------|------|
| `control_video` | `input/diffusion_bundle/03_工程底模.mp4` |
| `start_image` | `input/diffusion_bundle/start_image.jpg` |
| positive 文本 | 粘贴 `wan_positive.txt` 全文 |
| negative 文本 | 粘贴 `wan_negative.txt` 全文 |
| `length` | **150** |

#### Step 4 · 下载成片

输出一般在 `ComfyUI/output/`，用 scp 拉回本地对照底膜预览。

---

### 4.6 与代码/manifest 的字段对照

`build_diffusion_bundle()` 写入的 manifest（摘录）：

```json
{
  "schema": "diffusion_bundle_v1",
  "frame_count": 150,
  "fps": 30,
  "ready_for_diffusion": true,
  "usage": "整包 scp 到 AutoDL；start_image + 03 MP4 + wan_positive/negative 进 Wan Fun Control"
}
```

本地 export API：`POST /api/portal/export`（见 [`扩散引擎包组装专篇.md`](扩散引擎包组装专篇.md) §4.4）。

---

### 4.7 故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| OOM | 分辨率过高 / 未用 fp8 | 降 width×height；确认 fp8 模型 |
| 画面不动 / 节奏错 | 用了 I2V 而非 Fun Control | 换 `Wan22FunControlToVideo` |
| 眨眼帧对不上 | length≠150 或 fps≠30 | 改工作流参数 |
| 身份不像 | 未接 start_image | 检查 `start_image.jpg` |
| 情绪方向错 | wan± 传反或未传 positive | 对照 `04_Prompt.txt` |
| Comfy 打不开 | 服务未起 / 端口未映射 | 重启 `start_comfy.sh` + 自定义服务 |

---

## 五、检查点（Checkpoints）

| 编号 | 检查项 | 方法 | 合格标准 | 优先级 |
|------|--------|------|----------|--------|
| D01 | 数据盘已挂载 | `df -h` | 模型目录在数据盘 | **P0** |
| D02 | Wan 模型齐全 | `ls models/diffusion_models` | 2 个 2.2 UNet + vae + clip | **P0** |
| D03 | Fun Control 工作流 | 打开 workflow JSON | 含 `Wan22FunControlToVideo` | **P0** |
| D04 | 本地扩散包就绪 | `manifest.ready_for_diffusion` | `true` | **P0** |
| D05 | 上传完整 | 远程 `ls input/diffusion_bundle` | 03 + wan± + start_image | **P0** |
| D06 | 帧数 | 工作流 length + VHS cap | **150** | **P0** |
| D07 | 成片可生成 | Comfy Queue 无报错 | 输出 MP4 | **P0** |
| D08 | 节奏对齐 | 30fps 慢放对比 | 扫视/眨眼与底膜同期 | **P0** |
| D09 | 关机不断粮 | 关机再开机 | 模型仍在，Comfy 可启 | **P1** |

**快速验收（本地侧）**：

```bash
python3 scripts/verify_diffusion_prompt_contract.py
./一键打开创作门户.sh
# Pomot → 保存 → export → 检查 输出/扩散引擎包/manifest.json
```

---

## 六、下一步（与你协作）

你完成 **§4.1 创建实例 + 开数据盘** 后，把 **§4.0 清单 1–6** 发我，我可以：

1. 写好 `pull_wan22_models.sh` + `start_comfy.sh` 贴进数据盘  
2. 基于你的 `扩散引擎包/` 生成 **`eye_wan22_fun_control_150.json`** 工作流  
3. 远程跑通第一支成片，把参数写回本文 §4.3 D

---

## 七、修改记录

| 日期 | 修改内容 | 原因 |
|------|---------|------|
| 2026-05-28 | 初版：AutoDL 实例/存储/首次装载/开关机 SOP/扩散包上传/Wan Fun Control | 接扩散引擎落地操作空白 |
