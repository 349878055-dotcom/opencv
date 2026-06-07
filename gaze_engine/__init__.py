"""gaze_engine — 凝视引擎核心包。

目录结构按管线模块分组（见 00_MODULE_MAP.md）：

input/      输入与收口（SliderPacket、L1、预设真源）   ← s01
envelope/   情绪与能量（E(t) 主钟）                    ← s02
pad/        情绪坐标（PAD 权重）                       ← s03
channel/    通道编译（微颤、眼动先验）                  ← s04
style/      风格化（人格 style）                       ← s05
prior_qc/   先验与质检                                 ← s06
render/     工程底膜（OpenCV 渲染）                    ← s07
delivery/   输出与扩散（含 pomot/）                    ← s08
nl/         自然语言处理
_shared/    基础设施（客户 DB、LLM）
"""
