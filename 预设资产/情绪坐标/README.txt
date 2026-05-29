情绪坐标/ · PAD 预设资产
========================

与 情绪包/ 分工：
  情绪包/  → macro + hold_seg（E(t) 时间物理学）
  情绪坐标/ → PAD (P,A,D)（脸性格 · 12 通道 scale 性格）

目录
----
  human/   ← 16 种单情绪 + 1 大类「委屈」
  dog/     ← 10 种单情绪 + 1 大类「委屈」（定稿 v3.2）
  cat/     ← 12 种单情绪 + 1 大类「委屈」

每个 JSON = 一套 PAD
  · 单情绪：如 dog/警觉·竖耳.json
  · 大类：   如 dog/委屈.json — 三变体共用，不按变体拆 PAD

schema: emotion-pad-v1
  species, category, label, emotion_ids[], status, pad{P,A,D,position,channel_hint}

审定状态 status（三选一）
  修改中  — 正在调参/实验中，数值可能变
  脑补    — 初稿占位，未逐帧验收
  定稿    — 审定锁定，改需走合同

索引：{species}/_index.json

编辑顺序
--------
  1. 改 PAD → 本目录对应 json
  2. 同步 → gaze_engine/_shared/emotion_pad.py（编译查表）
  3. 同步 → 合同/03_情绪坐标/

委屈 特例
---------
  情绪包/委屈/变体*.json  不含 pad
  本目录 {species}/委屈.json  为该物种唯一 PAD 真源
