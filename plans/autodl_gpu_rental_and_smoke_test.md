# AutoDL GPU 租赁 & 生产线冒烟实验计划

> **问题定位**：上次 GPU 租下来后，通过 `scp` 传文件（模型权重 + 代码）速度极慢，浪费了大量计费时间。  
> **核心策略**：**模型在云端直接下载（不走本地→云端传输）**，代码通过 AutoDL 网页文件管理器上传或 `git clone`。

---

## 一、AutoDL 选型策略

### 1.1 GPU 选型

| 因素 | 推荐 | 理由 |
|------|------|------|
| **机型** | A5000 / A6000 / 4090 / A100 | Wan 2.1 i2v-14b 需要 ≥ 24GB 显存 |
| **镜像** | PyTorch 2.x + CUDA 12.x | 预装 ComfyUI + torch，省去环境配置 |
| **计费方式** | 按量计费（开机才扣钱） | 开发调试阶段不关机不扣费 |
| **地区** | 北京B区 / 华东 | 离你最近的节点，延迟最低 |

### 1.2 存储方案（关键）

AutoDL 有三种存储，**必须理解差异才能解决慢的问题**：

| 存储路径 | 类型 | 读写速度 | 持久性 | 用途 |
|---------|------|---------|--------|------|
| `/root/autodl-tmp/` | **本地 SSD** | ⚡最快 | ❌ 实例关机后清空 | 放模型权重（临时） |
| `/root/autodl-fs/` | **文件存储**（NAS） | 🐢 较慢 | ✅ 持久保留 | 放代码、客户资产 |
| 系统盘 `/root/` | 系统盘 | ⚡快 | ❌ 空间小(~20GB) | 只放系统文件 |

**关键结论**：
- **模型文件（VAE/CLIP/UNET ~21GB）** → 放 `/root/autodl-tmp/comfyui/`，在实例上用 `curl` 直接从 hf-mirror 下载
- **代码（jintao_node_eye ~2MB）** → 用 `git clone` + AutoDL 网页文件管理器上传
- **不要**用 `scp` 从本地上传大文件，这是上次慢的根源

---

## 二、文件传输加速方案（核心）

### 方案 A：模型 — 云端直接下载 ✅（推荐）

| 文件 | 大小 | 下载方式 | 源 | 预计耗时 |
|------|------|---------|-----|---------|
| VAE (`wan_2.1_vae.safetensors`) | 243MB | `curl -L` | hf-mirror | ~1-2 min |
| CLIP (`umt5_xxl_fp8_e4m3fn_scaled.safetensors`) | 1.9GB | `curl -L` | hf-mirror | ~5-10 min |
| UNET (`wan2.1-i2v-14b-480p-Q3_K_S.gguf`) | 16GB | `curl -L` + `nohup` 后台 | hf-mirror | ~30-60 min |

**已有脚本**: [`tools/03_工具脚本/ssh_download_models.py`](tools/03_工具脚本/ssh_download_models.py)  
→ 一键 SSH 到 AutoDL 实例，自动创建目录、下载、建立软链

### 方案 B：代码 — 网页文件管理器 + git（推荐）

| 方法 | 操作 | 适用场景 |
|------|------|---------|
| **AutoDL 网页文件管理** | 登录 AutoDL 控制台 → 文件管理 → 上传整个文件夹 | 首次部署（~2MB，几秒完成） |
| **`git clone`** | `cd /root/autodl-fs/ && git clone <你的仓库>` | 你有 GitHub/GitLab 仓库 |
| **`rsync -avz --partial`** | 本地执行 `rsync -avz --partial -e "ssh -p 44948" ./ root@connect.bjb1.seetacloud.com:/root/autodl-fs/jintao_node_eye/` | 后续增量更新（只传改动的文件） |

**rsync 的优势**：支持断点续传、压缩传输、只传差异文件，比 `scp` 快 3-5 倍。

### 方案 C：客户资产 — 网页上传

客户照片（几 MB）直接在 AutoDL 网页文件管理器上传到 `/root/autodl-fs/客户资产库/`，不走 scp。

---

## 三、生产线冒烟实验步骤

### 3.1 什么是"冒烟实验"？

验证完整链路：**情绪预设 → 包络编译 → 工程底膜 → 扩散引擎 → 视频输出**  
确认：① 代码能跑 ② 数据流正确 ③ ComfyUI + Wan 能出图

### 3.2 实验流程

```
第1层：纯代码逻辑（本机能跑）         ← CPU only
  └─ delivery_pipeline.py 烘焙 → 02_烘焙_真人律.json

第2层：工程底膜渲染（需 GPU）          ← GPU
  └─ affine_renderer.py → 工程底膜素材 (12×150 帧)

第3层：Wan 扩散引擎（需 GPU + 模型）  ← GPU + 21GB 模型
  └─ ComfyUI + Wan2.1 → 最终视频
```

### 3.3 具体步骤

#### Step 1：租用实例

```
1. 打开 https://www.autodl.com/create
2. 选择 GPU: A5000 (24GB) 够用，便宜
   可选：4090 D (24GB) / A6000 (48GB) 
3. 镜像选择: "PyTorch 2.4.0 + CUDA 12.4 + ComfyUI"
4. 创建实例
5. 开机（计费开始）
```

#### Step 2：下载模型（在云端直接下载，不走本地传输）

```bash
# SSH 登录实例
ssh -p 44948 root@connect.bjb1.seetacloud.com

# 或直接执行已有脚本（从本地执行）
python3 tools/03_工具脚本/ssh_download_models.py
```

脚本会自动：
- 创建 `/root/autodl-tmp/comfyui/vae/`, `text_encoders/`, `unet/` ...
- 从 hf-mirror 下载 VAE (243MB) + CLIP (1.9GB) 
- 后台下载 UNET (16GB，需 30-60 min)
- 建立软链 `ln -s /root/autodl-tmp/comfyui/XXX /root/ComfyUI/models/XXX`

**⚠️ 注意**：UNET 下载需要约 30-60 分钟，这段时间 GPU 是空闲的。  
→ 先下载模型，模型下载完后再正式干活，避免 GPU 开着等模型。

#### Step 3：上传代码

```bash
# 方式 1: rsync（推荐，自动压缩 + 增量传输）
rsync -avz --partial -e "ssh -p 44948" \
  /home/jintao/ai_video/ComfyUI/custom_nodes/jintao_node_eye/ \
  root@connect.bjb1.seetacloud.com:/root/autodl-fs/jintao_node_eye/

# 方式 2: AutoDL 网页文件管理器
# 浏览器打开 AutoDL 控制台 → 实例列表 → 文件管理 → 上传文件夹
```

代码很小（~2MB），无论哪种方式都是几秒完成。

#### Step 4：环境配置

```bash
# SSH 到实例
ssh -p 44948 root@connect.bjb1.seetacloud.com

# 确认 Python 和依赖
cd /root/autodl-fs/jintao_node_eye
pip install paramiko pillow numpy  # 项目依赖

# 验证 ComfyUI
cd /root/ComfyUI
python3 main.py --listen 0.0.0.0 --port 8188 &
# 确认能启动
```

#### Step 5：运行第1层冒烟测试 — 管道烘焙（CPU only）

```bash
cd /root/autodl-fs/jintao_node_eye

# 方案 A: 使用预设脚本
./scripts/s01_env.sh
./scripts/s01_从能量生成02.sh "施压·凝视"

# 方案 B: 直接 Python
python3 -c "
from gaze_engine.delivery_pipeline import run_delivery_from_packet
from gaze_engine._shared.slider_schema import SliderPacket

packet = SliderPacket(emotion='施压·凝视')
baked, dense, prior_rep, pq_rep = run_delivery_from_packet(packet)
print('✓ 烘焙完成，帧数:', len(dense.get('eye_open_l', [])))
print('  prior:', prior_rep)
print('  pulse_quality:', pq_rep)
"
```

**预期输出**：`02_烘焙_真人律.json` 文件生成，包含 12×150 帧数据。

#### Step 6：运行第2层冒烟测试 — 工程底膜渲染（CPU + GPU）

```bash
# 用 gaze_engine 渲染工程底膜
python3 -c "
from pathlib import Path
from gaze_engine.human.affine_renderer import render_frame
import json

# 读取烘焙结果
baked = json.loads(Path('客户资产库/客户_C001/项目_P001/输出/02_烘焙_真人律.json').read_text())

# 渲染第一帧
frame = render_frame(baked, frame_index=0)
print('✓ 工程底膜渲染成功，尺寸:', frame.shape)
"
```

#### Step 7：运行第3层冒烟测试 — ComfyUI + Wan 扩散引擎

这一步需要确保模型已下载完成。

```bash
# 检查模型
ls -lh /root/autodl-tmp/comfyui/unet/wan2.1-i2v-14b-480p-Q3_K_S.gguf

# 如果还没下载完，查看进度
tail -f /tmp/dl_unet.log

# 确认 ComfyUI 运行中
# 用工作台 → "生成节拍表" → 扩散引擎

# 或者构造 ComfyUI API 请求直接测试
python3 -c "
import requests
# ComfyUI API 提交工作流
# ...
"
```

### 3.4 冒烟实验验收标准

| 层级 | 验收项 | 通过标准 |
|------|--------|---------|
| L1 | delivery_pipeline 烘焙 | 输出合法的 `02_烘焙_真人律.json` |
| L2 | affine_renderer 渲染 | 输出帧图像（工程底膜） |
| L3 | ComfyUI + Wan | 输出视频文件（.mp4） |

---

## 四、时间线预估

```
T+0min   租用 GPU 实例（立即开始计费）
T+0min   SSH 登录
T+0~2min 执行 ssh_download_models.py（VAE + CLIP + UNET 后台）
         同时 rsync 上传代码（几秒）
T+2~5min 环境配置 + 第1层冒烟（管道烘焙，CPU only）
T+60min  模型下载完成后
T+60min  第2/3层冒烟（工程底膜 + 扩散引擎）
T+90min  🎉 完成！关机（停止计费）
```

**注意**：模型下载期间 GPU 在空转计费（~5元/小时），但这是必须的成本。  
如果想省钱：可以在下载模型时选便宜的小机型（如 4090 稍便宜），下载完再切到目标机型。

---

## 五、省时省钱的几个关键技巧

| 技巧 | 说明 |
|------|------|
| **实例关机重开不丢 /autodl-tmp** | AutoDL 支持"关机保留 /autodl-tmp"，下次开机会自动挂载 |
| **模型只下载一次** | 配置好 `/root/autodl-tmp/comfyui/` 后，以后每次租用只执行软链 |
| **代码用 git 管理** | 在 GitHub/Gitee 建私有仓库，每次 `git pull` 即可更新 |
| **AutoDL 自定义镜像** | 配置好一次环境后保存为自定义镜像，下次直接加载 |

---

## 六、推荐的命令速查表

```bash
# ===== SSH 登录 =====
ssh -p 44948 root@connect.bjb1.seetacloud.com

# ===== 代码上传（本地执行） =====
rsync -avz --partial -e "ssh -p 44948" \
  /home/jintao/ai_video/ComfyUI/custom_nodes/jintao_node_eye/ \
  root@connect.bjb1.seetacloud.com:/root/autodl-fs/jintao_node_eye/

# ===== 模型下载（云端执行） =====
cd /root/autodl-tmp/comfyui
mkdir -p vae text_encoders unet

# VAE (243MB)
curl -L -o vae/wan_2.1_vae.safetensors \
  "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"

# CLIP (1.9GB)
curl -L -o text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"

# UNET (16GB, 后台)
nohup curl -L -o unet/wan2.1-i2v-14b-480p-Q3_K_S.gguf \
  "https://hf-mirror.com/city96/wan2.1-i2v-14b-Q3_K_S-GGUF/resolve/main/wan2.1-i2v-14b-Q3_K_S.gguf" \
  > /tmp/dl_unet.log 2>&1 &

# 建立软链
ln -sf /root/autodl-tmp/comfyui/vae /root/ComfyUI/models/vae
ln -sf /root/autodl-tmp/comfyui/text_encoders /root/ComfyUI/models/text_encoders
ln -sf /root/autodl-tmp/comfyui/unet /root/ComfyUI/models/unet

# ===== 冒烟测试 =====
cd /root/autodl-fs/jintao_node_eye
python3 -c "
from gaze_engine.delivery_pipeline import run_delivery_from_packet
from gaze_engine._shared.slider_schema import SliderPacket
from pathlib import Path
import json

packet = SliderPacket(emotion='施压·凝视')
baked, dense, prior_rep, pq_rep = run_delivery_from_packet(packet)
out_path = Path('/root/autodl-fs/jintao_node_eye/02_smoke_test.json')
out_path.write_text(json.dumps(baked, ensure_ascii=False, indent=2))
print(f'✓ 冒烟测试通过，输出: {out_path}')
print(f'  prior: {prior_rep}')
print(f'  pulse_quality: {pq_rep}')
"
```

---

## 七、现有脚本清单

| 脚本 | 用途 | 状态 |
|------|------|------|
| [`tools/03_工具脚本/ssh_autodl.py`](tools/03_工具脚本/ssh_autodl.py) | SSH 连接 + 基础状态检查 | ✅ 可用 |
| [`tools/03_工具脚本/ssh_check_dirs.py`](tools/03_工具脚本/ssh_check_dirs.py) | 检查远端目录结构 | ✅ 可用 |
| [`tools/03_工具脚本/ssh_check_models.py`](tools/03_工具脚本/ssh_check_models.py) | 检查远端模型是否存在 | ✅ 可用 |
| [`tools/03_工具脚本/ssh_check_storage.py`](tools/03_工具脚本/ssh_check_storage.py) | 检查远端存储挂载 | ✅ 可用 |
| [`tools/03_工具脚本/ssh_download_models.py`](tools/03_工具脚本/ssh_download_models.py) | 一键下载 VAE + CLIP + UNET | ✅ 可用（含后台下载） |

---

## 八、操作清单（Checklist）

- [ ] **选型**：在 AutoDL 创建页面选择合适的 GPU + 镜像
- [ ] **开机**：启动实例，记录 SSH 连接信息
- [ ] **下载模型**：用 `ssh_download_models.py` 或手动执行 `curl` 下载 VAE + CLIP + UNET
- [ ] **上传代码**：用 rsync 或 AutoDL 网页文件管理器上传 jintao_node_eye
- [ ] **建立软链**：将 `/root/autodl-tmp/comfyui/` → 软链到 `/root/ComfyUI/models/`
- [ ] **L1 冒烟**：运行 delivery_pipeline 烘焙，验证 02.json 输出
- [ ] **L2 冒烟**：运行 affine_renderer 渲染工程底膜
- [ ] **L3 冒烟**：启动 ComfyUI，构造完整工作流，出视频
- [ ] **关机**：停止实例（计费停止）

---

*计划版本: 1.0 · 2026-05-26*