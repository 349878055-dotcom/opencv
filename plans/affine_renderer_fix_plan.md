# affine_renderer.py 根因分析 & "标准函数"方案

## 一、问题定位

### 根本原因：变形因子是线性的，与底图抛物线不匹配

[`deform()`](gaze_engine/affine_renderer.py:183) 中的变形因子：
```python
factor = 1.0 - abs(x - self.cx) / EYE_W * 0.4  # ← 线性衰减
```

[`_eye_ring()`](gaze_engine/base_mesh_gen.py:48) 中底图的抛物线公式：
```python
y_offset = UPPER_PEAK * (1 - (2*t - 1)**2)  # ← 二次(抛物线)衰减
```

**这两个衰减曲线不同。** 线性衰减的控制点变形后不在抛物线上。当 `_smooth_ring` 用 7 个非抛物线点拟合抛物线时，必然产生误差 → 眼角跑偏、曲线不平滑。

### 历史上每次尝试的失败原因

| 方案 | 问题 |
|------|------|
| 原始 5 点 `polylines` | 5 点连直线，弧度全靠 5 个折点 → 方块眼 |
| 18 三角形 Mesh Warp | 三角形边界 C0 连续但 C1 不连续 → 毛刺 |
| 7 点抛物线拟合 | 7 点不在抛物线上（因为变形因子是线性的）→ 拟合误差 → 眼角色差 |

**三个方案都错在同一个根因：`deform()` 产生的是线性衰减的变形，但底图是抛物线。**

## 二、"标准函数" 方案

正确的做法是：**渲染不经过 `deform()`，直接用底图的抛物线公式 + 变形参数。**

```
底图公式: y_offset = UPPER_PEAK * (1 - (2t-1)²)
变形后:   y_offset = (UPPER_PEAK - blink*40 - lid_upper*15) * (1 - (2t-1)²)
```

这样：
- 变形后的曲线**仍然是完美抛物线**（公式不变，只改 peak 值）
- 眼角**精确闭合**（t=0 和 t=1 时 y_offset=0）
- 曲线**与底图完全一致**（同一公式）
- 无拟合、无三角形、无毛刺

## 三、具体修改

### 3.1 新增 `_parametric_eyelid()` 方法

不用 `deform()` 返回的控制点，直接根据 channels 参数生成平滑眼睑曲线：

```python
def _parametric_eyelid(self, mesh, channels, steps=40) -> np.ndarray:
    """标准函数：用底图抛物线公式 + 变形参数，生成82点平滑眼睑环"""
    cx, cy = mesh.cx, mesh.cy
    ew = EYE_W  # 150
    
    blink = channels.get("blink", 0.0)
    lid_upper = channels.get("lid_upper", 0.0)
    squint = channels.get("squint", 0.0)
    lid_lower = channels.get("lid_lower", 0.0)
    
    # 变形后的抛物线峰值（正值=眼睁，负值=眼闭）
    upper_peak = max(-2, UPPER_PEAK - blink * BLINK_DROP - lid_upper * LID_UPPER_DROP)
    lower_bot = max(-2, LOWER_BOT - squint * SQUINT_LIFT - lid_lower * LID_LOWER_LIFT)
    
    pts = []
    # 上眼睑：从左到右
    for i in range(steps + 1):
        t = i / steps
        x = int(cx - ew + 2 * ew * t)
        y_offset = upper_peak * (1 - (2*t - 1)**2)
        y = int(cy - y_offset)
        pts.append((x, y))
    # 下眼睑：从右到左
    for i in range(steps + 1):
        t = i / steps
        x = int(cx + ew - 2 * ew * t)
        y_offset = lower_bot * (1 - (2*t - 1)**2)
        y = int(cy + y_offset)
        pts.append((x, y))
    
    return np.array(pts, dtype=np.int32)
```

### 3.2 修改 `render_frame()`

- 眼睑 → 用 `_parametric_eyelid()`，不走 `deform()`
- 眉毛 → 继续用 `deform()` 的 3 点（眉毛没有抛物线拟合问题）
- 虹膜 + 瞳孔 → 不变

### 3.3 新增或调整常量

`UPPER_PEAK` 和 `LOWER_BOT` 目前只在 `_build_source()` 中硬编码。需要提升为模块常量：

```python
# ── 底图抛物线常量（匹配 base_mesh_gen._eye_ring）──
UPPER_PEAK = 45      # 上眼睑抛物线峰值
LOWER_BOT = 38       # 下眼睑抛物线谷值 (45 * 0.85)
```

## 四、增量发现：LINE_AA → LINE_8（2026-05-24 验证并应用）

### 问题
[`affine_renderer.py`](gaze_engine/affine_renderer.py) 全部 4 处绘图使用 `cv2.LINE_AA`。
结合 [`micro_jitter.py`](gaze_engine/micro_jitter.py) 对 pupil_x/y 施加的 14Hz 微颤动，
相邻帧间 LINE_AA 产生的半透明边缘像素值跳变 → 扩散引擎看到"闪烁边缘"→ 成品纹理毛刺。

### 修改
| 位置 | 从 | 到 |
|------|-----|-----|
| [眼睑 polylines](gaze_engine/affine_renderer.py:322) | `cv2.LINE_AA` | `cv2.LINE_8` |
| [眉毛 polylines](gaze_engine/affine_renderer.py:331) | `cv2.LINE_AA` | `cv2.LINE_8` |
| [虹膜 circle](gaze_engine/affine_renderer.py:346) | `cv2.LINE_AA` | `cv2.LINE_8` |
| [瞳孔 circle](gaze_engine/affine_renderer.py:351) | `cv2.LINE_AA` | `cv2.LINE_8` |

### 原理
硬边缘（LINE_8）→ 像素值只有 0 或 255 → 相邻帧无中间值跳变 → 稳定骨架。
微颤动依然存在于 pupil_x/y 指令集中，扩散引擎能感知到"瞳孔在动"，但边缘不再闪烁。

### 后续如果觉得"不够活"
不要改回 LINE_AA。应该调 micro_jitter.py 的频率/幅度参数：
- 降低频率（14Hz → 3-5Hz）产生更优雅的扫视摆动
- 增加幅度补偿，让瞳孔移动更具物理惯性感

## 五、验证计划

| 检查项 | 方法 | 预期 |
|--------|------|------|
| 眼角闭合 | 计算首尾距离 | 0px（天然闭合） |
| 曲线平滑度 | 相邻点间距标准差 | < 1.0 |
| 虹膜圆度 | cv2.contourArea + perimeter | > 0.89 |
| channels=0 vs 底图 | 视觉对比 | 肉眼不可区分 |
| blink=1.0 | 眼睑完全闭合 | 上下眼睑在中心相遇 |