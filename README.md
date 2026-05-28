# jintao_node_eye — 数字人表情资产中台

> **Eye-Figma Engine**：12 参数驱动的表情几何中间件。  
> 上接客户审美，下接扩散引擎。  
> 编译链：S0 → E(t) → PAD → pulse → style → 底膜 → 扩散（宏观见合同总览）。

---

## 架构

唯一宏观文档：[`合同/00_管线导读/00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md)

## 启动

```bash
./一键打开创作门户.sh
# → http://127.0.0.1:8765/portal
```

## 项目入口

| 用途 | 文件 |
|------|------|
| **宏观架构（唯一）** | [`合同/00_管线导读/00_从门户到扩散_管线总览.md`](合同/00_管线导读/00_从门户到扩散_管线总览.md) |
| HTTP 服务 | [`tools/01_工作台服务/serve_workbench.py`](tools/01_工作台服务/serve_workbench.py) |
| 客户创作门户 | [`tools/01_工作台服务/客户门户.html`](tools/01_工作台服务/客户门户.html) |
| 核心引擎 | [`gaze_engine/`](gaze_engine/) |
| 代码依赖图谱 | [`AI_INDEX.md`](AI_INDEX.md) |
| 合同索引 | [`合同/README.md`](合同/README.md) |
