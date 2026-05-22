# jintao_node_eye（ecursor S01）

## 资产库

```
资产库/人格包/S01_林青霞_东方不败/施压瞬间凝视/
  指令/_archive/                  ← 历史母版（只读参考）
  指令/05_扩散节拍表.txt
```

**主链（Python）**：滑杆 → **能量包络 E(t)** → 全量 12×150 → human_prior → pulse_quality → 烘焙 02  
实现：`gaze_engine/envelope_compile.py` · 主合同：`contracts/全量帧指令集规范.md`（继承原关键帧规范）。

## 常用命令

```bash
# 从 16 预设生成烘焙 02
./scripts/s01_从能量生成02.sh 施压·凝视

export ECURSOR_SPARSE_JSON="资产库/.../指令/02_烘焙_真人律.json"

./scripts/s01_导出扩散节拍表.sh

./scripts/s01_主验收示意图.sh
./scripts/s01_五样本烘焙02.sh

cd tools && python3 build_workbench_pipeline_cache.py   # 刷新工作台缓存
```

**Comfy 工作流**：`workflows/ecursor_S01.json`（节点 **1→7** 顺序编号）  
**改节点**：对我说「改 3 包络」等 → `workflows/ComfyUI改代码手册.md` + `nodes_v1.py` 搜 `节点 3`
