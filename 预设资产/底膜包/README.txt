ecursor 预设资产 · ③ 底膜包
============================

定位
----
**不是「一个品种一套独立低膜」。**

狗/猫各 **1 套物种低膜**（本目录 species_default.json）；
每个品种 **1 份预存几何偏移**（{species}/breeds/{breed_id}.json）；
客户标定后写入 **客户资产库/物种底膜模板.json**。

合成：最终低膜 = 物种默认 × 品种偏移 × 客户配准

目录
----
底膜包/
├── human/species_default.json       ← 人类物种默认（全客户共用，无品种层）
├── cat/
│   ├── species_default.json         ← 猫物种默认
│   └── breeds/                      ← 9 品种几何偏移（CFA 眼耳型依据）
│       ├── _index.json
│       └── {breed_id}.json
├── dog/
│   ├── species_default.json         ← 狗物种默认
│   └── breeds/                      ← 10 品种几何偏移（AKC 眼耳型依据）
│       ├── _index.json
│       └── {breed_id}.json
└── README.txt                       ← 本文件

数据流
------
编辑 底膜包/{species}/breeds/*.json
  → python3 tools/03_工具脚本/sync_membrane_pack.py
  → gaze_engine/{species}/breed_style_catalog.json（template_scales / template_structure）
  → gaze_engine/{species}/breed_matrix.json + 预设资产/风格包/

品种偏移字段（ecursor_membrane_breed_v1）
----------------------------------------
  template_scales     相对物种默认的几何乘数（眼大小、眼型、耳形…）
  template_structure  狗专用：眉/耳控制点换形
  _reference          AKC / CFA 品种标准摘要（权威依据，非医学测量）
  membrane_notes      工程备注

客户标定结果不在此目录：
  → 客户资产库/客户_{id}/物种底膜模板.json

编辑指南
--------
改物种眼型默认：  编辑 species_default.json → 对齐 species_template.py
改品种耳形/眼型：  编辑 breeds/{breed_id}.json → 跑 sync_membrane_pack.py
客户配准：        仅门户 upload-photo / calibrate-template，禁止手改 JSON 做美颜

产品红线
--------
❌ 不提供「眼睛大一点」类自由滑杆（美图秀秀范畴）
✅ 仅允许参考照/锚点配准到真实解剖比例

合同
----
合同/06_工程底膜/底膜模板选择与标定专篇.md
