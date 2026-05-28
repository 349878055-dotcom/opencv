# AutoDL 扩散 GPU · 运维备忘

> **AI Agent 读这个**：实例路径、启停命令真源 → [`已部署实例.json`](已部署实例.json)  
> **扩散包送 Wan** → [`扩散输出流程专篇.md`](../../合同/08_输出与扩散/扩散输出流程专篇.md) §四～§六

---

## 每次要用 GPU（3 步）

1. [AutoDL 控制台](https://www.autodl.com/console/instance/list) → **开机**
2. SSH 登录（端口以控制台为准），执行：

```bash
bash /root/autodl-tmp/scripts/start_comfy.sh
```

3. 控制台 → **自定义服务** → 端口 **8188** → 浏览器打开 ComfyUI

---

## 收工

- **关机**：必须在 **AutoDL 网页** 点「关机」（SSH 里 `poweroff` 停不了 GPU 计费）
- **不要** 点「释放实例」

---

## 密码

勿提交到 Git。本地可建 `tools/autodl/.env.local`（已 gitignore）：

```bash
AUTODL_SSH="ssh -p PORT root@connect.bjb1.seetacloud.com"
AUTODL_PASSWORD="..."
```
