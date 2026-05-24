# 宠物版 jintao_node_eye 迁移方案

> 架构版本：v1.0
> 目标：将 Eye-Figma Engine 从「人类眼眉动画」扩展为「宠物（猫/狗）眼眉+耳部动画」
> 改动原则：**不破坏现有人类管线，通过 `species` 字段并行支持双物种**

---

## 一、核心设计思想

### 双物种共存架构

```
jintao_node_eye/
├── gaze_engine/
│   ├── channel_contract.py      ← 新增 species 路由，14 通道 (12+2)
│   ├── affine_renderer.py       ← 新增 CatEyeMesh / DogEyeMesh
│   ├── control_surface.py       ← 新增 PET_PRESETS 宠物预设
│   ├── envelope_compile.py      ← 新增 PET_PAD_WEIGHTS
│   ├── human_prior.py           ← 新增 pet_saccade_dynamics
│   ├── pulse_quality.py         ← 新增 pet_energy_channels
│   ├── slider_schema.py         ← SliderPacket 增加 species 字段
│   ├── persona_compiler.py      ← 不变（通道数兼容）
│   └── persona_matrix.json      ← 新增 breed_personas 品种人格
```

**入口路由**：所有模块通过 `channels.get("species", "human")` 或 `packet.species` 决定走人类还是宠物管线。

---

## 二、通道定义（channel_contract.py）

### 现状（人类 12 通道）

```python
CANONICAL_KEYS = [
    "pupil_x", "pupil_y", "blink", "eyebrow",
    "pupil_scale", "iris_scale", "cornea_bulge",
    "squint", "brow_raise", "lid_upper", "lid_lower", "eye_gloss",
]
```

### 目标（宠物 14 通道）

```python
CANONICAL_KEYS_HUMAN = [...]  # 原 12 通道保持不动

CANONICAL_KEYS_CAT = [
    "pupil_x", "pupil_y", "blink",          # 眼球运动 + 眨眼（眼睑水平开合）
    "ear_left", "ear_right",                 # 新增：左耳/右耳（猫核心情绪器官）
    "pupil_scale",                           # 瞳孔缩放（猫竖瞳缩成线，关键特征）
    "iris_scale", "cornea_bulge",
    "squint",                                # 眯眼（猫眯眼表达放松/满足）
    "brow_raise",                            # 猫无独立眉毛，映射为额肌/眼周皮肤
    "lid_upper", "lid_lower",
    "eye_gloss",                             # 眼湿润高光（猫眼泪汪汪也是表情）
]
# 注：CAT 共 14 通道，去掉了人类 "eyebrow"（猫无独立眉毛肌）
# 改为 "ear_left" + "ear_right" 双通道

CANONICAL_KEYS_DOG = [
    "pupil_x", "pupil_y", "blink",
    "ear_left", "ear_right",                 # 新增：狗耳更灵活，可 4 方向
    "pupil_scale",
    "iris_scale", "cornea_bulge",
    "squint",
    "brow_raise",                            # 狗有眉毛肌，保留
    "lid_upper", "lid_lower",
    "eye_gloss",
]
# 注：DOG 共 14 通道，保留了人类部分结构（狗的面部解剖更接近人类）
```

### 物种路由

```python
CANONICAL_KEYS_BY_SPECIES = {
    "human": CANONICAL_KEYS_HUMAN,
    "cat":   CANONICAL_KEYS_CAT,
    "dog":   CANONICAL_KEYS_DOG,
}

def get_canonical_keys(species: str = "human") -> list[str]:
    return CANONICAL_KEYS_BY_SPECIES.get(species, CANONICAL_KEYS_HUMAN)
```

---

## 三、底膜渲染（affine_renderer.py）

### 3.1 猫眼几何

猫眼与人类最大的区别：

```
人眼：      🔵  圆形眼眶，眼睑水平开合
猫眼：      🟢  杏仁状上挑眼眶，竖椭圆瞳孔，有内眦膜（第三眼睑）
```

#### 猫眼抛物线参数

```python
# 猫眼底图常量（1024x1024 坐标系）
CAT_LEFT_CX, CAT_LEFT_CY = 300, 310    # 猫眼位置偏上、偏外
CAT_RIGHT_CX, CAT_RIGHT_CY = 724, 310

CAT_EYE_W = 120                          # 猫眼较窄（杏仁状）
CAT_EYE_H = 90                           # 猫眼较高（上挑）

# 猫眼抛物线峰值（上眼睑更弯，眼角上挑）
CAT_UPPER_PEAK = 55                      # 人类 45 → 猫 55（更弯）
CAT_LOWER_BOT = 30                       # 人类 38 → 猫 30（下眼睑较平）

# 猫瞳孔（竖椭圆）
CAT_PUPIL_R_X = 8                        # 猫瞳孔水平半径（强光时可缩至 2px）
CAT_PUPIL_R_Y = 22                       # 猫瞳孔垂直半径（竖椭圆）
CAT_IRIS_R = 38                          # 猫虹膜半径（比人类略小，但占眼比例更大）
```

#### 猫眼三角形网格改动

```python
class CatEyeMesh(EyeMesh):
    """猫眼三角形控制网格"""
    
    def _build_source(self) -> dict[str, tuple[float, float]]:
        ew, eh = CAT_EYE_W, CAT_EYE_H
        return {
            "corner_inner": (-ew, -8),     # 内眼角比中心低（猫眼上挑）
            "corner_outer": (ew, -15),     # 外眼角更低（更上挑）
            # 上眼睑（更弯的抛物线，峰值更高）
            "upper_0": (-int(ew*0.85), -10),
            "upper_1": (-int(ew*0.5), -38),
            "upper_2": (0, -55),           # 峰值更高
            "upper_3": (int(ew*0.5), -45),
            "upper_4": (int(ew*0.85), -20),
            # 下眼睑（较平）
            "lower_0": (-int(ew*0.85), 8),
            "lower_1": (-int(ew*0.5), 22),
            "lower_2": (0, 30),
            "lower_3": (int(ew*0.5), 20),
            "lower_4": (int(ew*0.85), 5),
            # 虹膜（圆形，但瞳孔竖椭圆）
            "iris_top": (0, -CAT_IRIS_R),
            "iris_bottom": (0, CAT_IRIS_R),
            "iris_left": (-CAT_IRIS_R, 0),
            "iris_right": (CAT_IRIS_R, 0),
            # 瞳孔中心
            "pupil": (0, 0),
            # 猫无独立眉毛，改为"额头/耳根"控制点
            "brow_inner": (-120, -100),
            "brow_peak": (0, -130),
            "brow_outer": (120, -90),
        }
```

#### 猫瞳孔渲染（竖椭圆）

```python
# B 通道渲染时，猫瞳孔是竖椭圆而非圆形
if species == "cat":
    # 猫瞳孔：竖椭圆
    pupil_rx = max(2, int(CAT_PUPIL_R_X * (1.0 + p_scale * 0.3)))
    pupil_ry = max(2, int(CAT_PUPIL_R_Y * (1.0 + p_scale * 0.3)))
    if blink < 0.95:
        cv2.ellipse(canvas, dst_pts["pupil"], (pupil_rx, pupil_ry),
                    0, 0, 360, (255, 0, 0), 2, cv2.LINE_8)
```

### 3.2 狗眼几何

```
人眼 → 狗眼变化较小：
- 眼眶更圆，眼位更靠前
- 瞳孔圆形（与人类同）
- 眉脊更突出（尤其德国牧羊犬等）
```

```python
class DogEyeMesh(EyeMesh):
    """狗眼三角形控制网格"""
    
    def _build_source(self) -> dict[str, tuple[float, float]]:
        ew, eh = DOG_EYE_W, DOG_EYE_H
        # 狗眼眶更圆，抛物线更平缓
        # ... (复用人类 EyeMesh 主体，调整峰值即可)
```

### 3.3 耳位渲染（G 通道）

猫/狗耳是比眉毛重要 10 倍的情绪器官。耳位渲染方案：

```
G 通道（原人类仅画眉毛）→ 改为画「耳位指示线」
```

渲染规则：
```
左耳：从耳根 (lx, ly) 到耳尖 (lx+ear_left_x, ly+ear_left_y) 画线段
右耳：从耳根 (rx, ry) 到耳尖 (rx+ear_right_x, ry+ear_right_y) 画线段

ear_left, ear_right 每个是 2 维子参数：
  [0] = 耳位角度（-1=全趴→0=中立→1=全竖）
  [1] = 耳尖偏移（-1=向后→0=中立→1=向前）
```

**底图上预置猫/狗的耳根位置**，耳尖位置由 `ear_left[0]` 和 `ear_left[1]` 驱动。

同时保留眉线（画在 G 通道不影响耳位的区域）。

---

## 四、预设体系（control_surface.py）

### 猫版预设（12 个情绪）

| 预设 ID | 中文名 | 对应人类情绪 | 猫特有行为 |
|---------|--------|-------------|-----------|
| `cat_alarm_stare` | 警觉·盯 | 施压·凝视 | 竖耳、瞳孔收缩、眼不眨 |
| `cat_hunt_fixate` | 狩猎·锁定 | — | 身体伏低、瞳孔放大、眼不眨 |
| `cat_startle_fluff` | 惊吓·炸毛 | 惊惧·一怔 | 飞机耳、瞳孔炸开、快速眨眼 |
| `cat_curious_tilt` | 好奇·歪头 | — | 歪头+竖耳、一耳前一耳后 |
| `cat_cuddle_squint` | 撒娇·眯眼 | 魅惑·勾人 | 慢眨眼（猫信任信号）、半眯眼 |
| `cat_content_bliss` | 满足·飘然 | — | 眯眼成线、瞳孔缩小、慢眨 |
| `cat_annoyed_swish` | 不耐烦·甩尾 | 冷压·决心 | 耳朵背过去、半眯眼 |
| `cat_scared_flatten` | 恐惧·贴地 | 可怜·委屈 | 全飞机耳、瞳孔放大、快速眨眼 |
| `cat_sad_whimper` | 委屈·呜咽 | 要哭未哭 | 耳朵耷拉、眼湿润、慢眨眼 |
| `cat_angry_hiss` | 愤怒·哈气 | 怒视·压人 | 飞机耳+瞳孔缩成线、怒视 |
| `cat_sleepy_droop` | 困倦·迷离 | 空竭·死心 | 眼皮下垂、瞳孔放大、慢眨眼 |
| `cat_play_pounce` | 玩耍·扑击 | — | 瞳孔放大+耳朵前竖、快速扫视 |

### 狗版预设（10 个情绪）

| 预设 ID | 中文名 | 对应人类情绪 | 狗特有行为 |
|---------|--------|-------------|-----------|
| `dog_alert_bark` | 警觉·吠 | 施压·凝视 | 竖耳、瞳孔聚焦、眉压低 |
| `dog_happy_wag` | 开心·摇尾 | — | 放松眼、张嘴笑、眉毛上抬 |
| `dog_sad_puppy` | 委屈·幼犬眼 | 可怜·委屈 | 挑眉+眼往上翻、湿润 |
| `dog_scared_tuck` | 恐惧·夹尾 | 惊惧·一怔 | 耳朵后贴、瞳孔放大、快速眨眼 |
| `dog_angry_growl` | 愤怒·低吼 | 怒视·压人 | 竖耳前倾、瞳孔缩、眉压低 |
| `dog_curious_cock` | 好奇·歪头 | — | 单耳竖、歪头、瞳孔放大 |
| `dog_submissive_look` | 服从·回避 | 哀求·仰望 | 眼神回避、耳朵后贴、缓慢眨眼 |
| `dog_play_bow` | 邀玩·趴 | 打量·玩味 | 瞳孔放大、耳朵前竖、眉毛抬 |
| `dog_guilty_side` | 心虚·偷瞄 | — | 眼神侧移回避、耳朵耷拉 |
| `dog_content_sigh` | 满足·叹气 | — | 眼睛半闭、瞳孔缩小、耳朵放松 |

### 预设参数值示例（猫版）

```python
PET_PRESETS: dict[str, dict[str, Any]] = {
    "cat_alarm_stare": {
        "note": "竖耳、瞳孔收缩、眼不眨",
        "macro": {"push": 82, "power": 88, "speed": 90, "steady": 94, "grip": 90, "outro": 28},
        "hold_seg": {"shape": "flat", "pulse_rate": 0, "pulse_depth": 0, "swell": 0},
        "ear": {"left": [0.9, 0.1], "right": [0.9, 0.1]},  # 双耳全竖稍向前
    },
    "cat_cuddle_squint": {
        "note": "慢眨眼、半眯眼、耳朵放松",
        "macro": {"push": 62, "power": 32, "speed": 20, "steady": 72, "grip": 82, "outro": 72},
        "hold_seg": {"shape": "pulse", "pulse_rate": 32, "pulse_depth": 18, "swell": 18},
        "ear": {"left": [0.3, 0.0], "right": [0.3, 0.0]},  # 耳朵半竖
    },
    "cat_startle_fluff": {
        "note": "飞机耳、瞳孔炸开、快速眨眼",
        "macro": {"push": 38, "power": 68, "speed": 96, "steady": 48, "grip": 32, "outro": 14},
        "hold_seg": {"shape": "tremble", "pulse_rate": 28, "pulse_depth": 36, "swell": 0},
        "ear": {"left": [-0.9, -0.5], "right": [-0.9, -0.5]},  # 飞机耳（全趴+向后）
    },
}
```

---

## 五、人格/品种包体系（persona_matrix.json）

### 品种人格矩阵

| 品种 | 品种人格 ID | 特征 | base_offset 偏置特征 |
|------|-----------|------|---------------------|
| 布偶猫 | `ragdoll_cat` | 温顺、放松、反应迟钝 | ear 偏低、blink 偏高 |
| 暹罗猫 | `siamese_cat` | 高冷、警觉、反应快 | ear 偏高、pupil_scale 活跃 |
| 田园猫 | `stray_cat` | 机敏、野性、反应猛烈 | pupil_x/y 活跃、blink 偏低 |
| 英短 | `british_cat` | 憨厚、淡定、慢 | 所有参数偏低、outro 偏大 |
| 金毛 | `golden_dog` | 外向、兴奋、表情丰富 | brow_raise 高、ear 活跃 |
| 德牧 | `shepherd_dog` | 机警、专注、克制 | ear 竖立、pupil_scale 稳定 |
| 柯基 | `corgi_dog` | 活泼、好奇、表情夸张 | ear 活跃、blink 偏低 |
| 柴犬 | `shiba_dog` | 倔强、表情包、喜怒鲜明 | 两极分化大、transition 快 |

### 品种人格数据结构（在 persona_matrix.json 中）

```json
{
  "_schema_version": "2.0",
  "_description": "九大人格矩阵 + 宠物品种人格矩阵",
  "personas": { ... },  // 原人类人格不动

  "breed_personas": {
    "ragdoll_cat": {
      "species": "cat",
      "label": "布偶猫 / 温顺型",
      "base_offset": {
        "pupil_x": 0.45, "pupil_y": 0.45, "blink": 0.60, "ear_left": 0.35,
        "ear_right": 0.35, "pupil_scale": 0.45, "iris_scale": 0.50,
        "cornea_bulge": 0.45, "squint": 0.50, "brow_raise": 0.40,
        "lid_upper": 0.50, "lid_lower": 0.50, "eye_gloss": 0.60
      },
      "scale_factor": {
        "pupil_x": 0.30, "pupil_y": 0.25, "blink": 0.60, "ear_left": 0.50,
        "ear_right": 0.50, "pupil_scale": 0.40, "iris_scale": 0.30,
        "cornea_bulge": 0.25, "squint": 0.40, "brow_raise": 0.30,
        "lid_upper": 0.35, "lid_lower": 0.35, "eye_gloss": 0.40
      }
    },
    "siamese_cat": {
      "species": "cat",
      "label": "暹罗猫 / 高冷型",
      "base_offset": {
        "pupil_x": 0.48, "pupil_y": 0.48, "blink": 0.45, "ear_left": 0.65,
        "ear_right": 0.65, "pupil_scale": 0.55, "iris_scale": 0.50,
        ...
      }
    }
  }
}
```

---

## 六、SliderPacket 数据类改动（slider_schema.py）

```python
@dataclass
class SliderPacket:
    emotion: str = "s01_pressure"
    style: str = "default"
    species: str = "human"        # ← 新增：human / cat / dog
    macro: MacroSliders = field(default_factory=MacroSliders)
    hold_seg: HoldSegment = field(default_factory=HoldSegment)
    ear: EarParams = field(default_factory=EarParams)  # ← 新增
    schema: str = SCHEMA_ID

@dataclass
class EarParams:
    """猫/狗耳位参数"""
    left_angle: float = 0.0      # -1.0 (全趴) ~ 0.0 (中立) ~ 1.0 (全竖)
    left_tip: float = 0.0        # -1.0 (向后) ~ 0.0 (中立) ~ 1.0 (向前)
    right_angle: float = 0.0
    right_tip: float = 0.0
```

---

## 七、能量包络改动（envelope_compile.py）

### PAD 权重表（猫版）

```python
PET_PAD_WEIGHTS_CAT: Dict[str, tuple[float, float, float]] = {
    "pupil_x":      (0.0,  0.50,  0.40),
    "pupil_y":      (0.0,  0.50,  0.40),
    "blink":        (0.0,  0.30,  0.10),
    "ear_left":     (0.05, 0.35,  0.25),   # 猫耳与情绪密切相关
    "ear_right":    (0.05, 0.35,  0.25),
    "pupil_scale":  (0.20, 0.40,  0.30),   # 猫瞳孔缩放权重更高（情绪指标）
    "iris_scale":   (0.10, 0.20,  0.10),
    "cornea_bulge": (0.0,  0.40,  0.30),
    "squint":       (0.15, 0.35,  0.20),   # 猫眯眼权重更高
    "brow_raise":   (0.10, 0.20, -0.20),
    "lid_upper":    (0.0,  0.50,  0.40),
    "lid_lower":    (0.0,  0.30,  0.20),
    "eye_gloss":    (0.30, 0.10,  0.0),
}
```

**核心差异**：
- `pupil_scale` 的 P 权重从 0.10 → 0.20（猫瞳孔反应更敏感）
- `squint` 的 P 权重从 0.10 → 0.15（猫眯眼是重要的情感表达）
- 新增 `ear_left` / `ear_right` 的 PAD 权重

---

## 八、真人化先验改动（human_prior.py）

### 可复用的部分
- **二阶欠阻尼扫视**（pupil_x/y 的过冲）→ 猫狗同样适用，但参数不同
- **微颤/微漂**（micro_jitter）→ 猫的微颤频率更高（22Hz vs 人类 14Hz）
- **能量耦合** → 移除/替换 `_couple_eyebrow_lag` 为 `_couple_ear_lag`

### 需要改动的部分

```python
def _apply_pet_saccade_dynamics(
    channels: dict[str, list[float]],
    species: str,
    ...
) -> None:
    """猫/狗扫视动力学（参数不同）"""
    if species == "cat":
        zeta = 0.45      # 猫眼扫射阻尼更小 → 过冲更大（猫反应更"弹"）
        omega = 18.0     # 猫眼扫射频率更高（更快）
    elif species == "dog":
        zeta = 0.60      # 狗眼扫射较沉稳
        omega = 14.0     # 狗眼扫射频率中等
```

### 猫独有：第三眼睑（内眦膜）

猫在眨眼时会短暂闭合内眦膜（第三眼睑），渲染时需要在 R 通道额外画一条弧线。

```python
# 在 affine_renderer 的渲染函数中
if species == "cat" and blink > 0.3:
    # 画内眦膜弧线（从内眼角到瞳孔边缘）
    cv2.ellipse(canvas, (inner_corner_x, inner_corner_y),
                (12, 8), -15, 0, 160, (255, 0, 0), 3, cv2.LINE_8)
```

---

## 九、改动范围总结与实施路线图

### 改动范围矩阵

| 模块 | 文件 | 改动量 | 改动类型 |
|------|------|--------|---------|
| 通道定义 | `channel_contract.py` | **中** (~50 行) | 新增 `get_canonical_keys()` 物种路由 + CANONICAL_KEYS_CAT/DOG |
| 数据类 | `slider_schema.py` | **小** (~20 行) | SliderPacket 加 `species`、`EarParams` 数据类 |
| 预设系统 | `control_surface.py` | **中** (~200 行) | 新增 22 个 PET_PRESETS + export 路由 |
| 底膜渲染 | `affine_renderer.py` | **大** (~300 行) | CatEyeMesh + DogEyeMesh + 猫瞳孔椭圆 + 耳位渲染 |
| 能量包络 | `envelope_compile.py` | **小** (~30 行) | PET_PAD_WEIGHTS + species 路由 |
| 真人化 | `human_prior.py` | **中** (~80 行) | pet 版本扫射参数 + 第三眼睑 |
| 平庸质检 | `pulse_quality.py` | **小** (~20 行) | pet 版本 ENERGY_CHANNELS |
| 人格系统 | `persona_matrix.json` | **中** (~80 行) | 新增 breed_personas 字典 |
| 人格编译 | `persona_compiler.py` | **小** (~10 行) | 支持可选的通道数（12 vs 14） |
| 工作台 UI | `能量工作台.html` | **中** (~100 行) | 新增物种选择器、耳位滑杆 |
| NL 路由 | `nl_to_packet.py` | **小** (~20 行) | 识别 cat/dog 关键词 |

### 总计

| 指标 | 数值 |
|------|------|
| 新增 Python 代码 | ~700 行 |
| 新增 JSON 数据 | ~80 行 |
| 新增 HTML/JS | ~100 行 |
| 修改行数（存量） | ~200 行 |
| 零改动的模块 | `delivery_pipeline.py`, `pipeline_io.py`, `node1_defaults.py`, `llm_openai.py` |

### 实施路线图（4 阶段）

```
阶段 1 — 基础设施（1 天）
  ├── channel_contract.py: 增加物种路由 + 猫/狗 CANONICAL_KEYS
  ├── slider_schema.py: 增加 species + EarParams
  └── control_surface.py: 先加猫/狗 species 路由和预设 ID

阶段 2 — 核心渲染（2 天）
  ├── affine_renderer.py: CatEyeMesh 三角形网格 + 猫瞳孔椭圆渲染
  ├── affine_renderer.py: 耳位线渲染（G 通道）
  ├── affine_renderer.py: 第三眼睑（内眦膜）
  └── 跑 `--test` 验证猫眼底模输出

阶段 3 — 物理管线（1 天）
  ├── envelope_compile.py: PET_PAD_WEIGHTS + species 路由
  ├── human_prior.py: 猫/狗扫射参数 + 耳位耦合
  └── pulse_quality.py: pet ENERGY_CHANNELS

阶段 4 — 人格 + 工作台（1 天）
  ├── persona_matrix.json: 8 个品种人格
  ├── 能量工作台.html: 物种选择器 + 耳位滑杆
  └── 端到端测试：NL → 猫眼参数 → 底膜 → 输出
```

---

## 十、兼容性保障

### 向后兼容原则

1. **所有新增字段都有默认值**：`species="human"`, `ear=EarParams()`
2. **现有 12 通道数据完全不变**：只是加了一个路由层
3. **现有 16 个人类预设不动**：在 `control_surface.py` 中 $_PRESETS 和 PET_PRESETS 并存
4. **原 AffineRenderer 类不动**：新增 `CatAffineRenderer` 和 `DogAffineRenderer`
5. **`delivery_pipeline.py` 改动最小**：只需在 `run_delivery()` 开头加 `species` 参数传递

### 数据流对比

```
人类管线（原封不动）：
  SliderPacket(species="human") → envelope_compile → human_prior → affine_renderer → 02_烘焙.json

猫管线（新增）：
  SliderPacket(species="cat", ear=EarParams(...)) → pet_envelope_compile → pet_human_prior → cat_affine_renderer → 02_烘焙.json
  
狗管线（新增）：
  SliderPacket(species="dog", ear=EarParams(...)) → pet_envelope_compile → pet_human_prior → dog_affine_renderer → 02_烘焙.json
```

### RGB 三色分离协议（保持不变）

```
输出始终是：R=眼眶, G=耳位+眉, B=瞳孔+虹膜
690×361 尺寸不变，Wan 扩散引擎不需要改任何东西
```

```
┌──────────────────────────────────────────────────────────────┐
│                    Wan 扩散引擎                               │
│  接收 RGB 控制图 (690×361) → 生成猫视频                       │
│  完全不知道"这是猫还是人"，只看 RGB 通道位置                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 十一、MVP 建议（第一版做哪些）

```
第 1 版只做猫 —— 理由：
1. 猫眼型（竖瞳）视觉差异化最大，一眼就能认出不同于人类
2. 猫耳情绪表达更鲜明（飞机耳 vs 竖耳）
3. 市场上"AI 猫视频"话题热度 > "AI 狗视频"
4. 狗的解剖更接近人类，差异化不够惊艳

第 1 版只做 6 个情绪 —— 按优先级排序：
1. cat_cuddle_squint（撒娇·眯眼）—— 最能引发"好可爱"反应
2. cat_alarm_stare（警觉·盯）—— 展示精准控制力
3. cat_startle_fluff（惊吓·炸毛）—— 戏剧效果最强
4. cat_curious_tilt（好奇·歪头）—— 猫的标志性动作
5. cat_sleepy_droop（困倦·迷离）—— 展示慢速控制
6. cat_hunt_fixate（狩猎·锁定）—— 展示静态控制的精度
```

---

## 十二、NPC 中的对话决策流程图

```mermaid
flowchart TD
    A[用户输入 NL] --> B{nl_intent 识别物种}
    B -->|含 cat/猫/喵/猫咪| C1[species=cat]
    B -->|含 dog/狗/汪/狗狗| C2[species=dog]
    B -->|默认| C0[species=human]
    
    C1 --> D1[选择猫情绪预设]
    C2 --> D2[选择狗情绪预设]
    C0 --> D0[选择人类情绪预设]
    
    D1 --> E1[猫能量包络 E猫t]
    D2 --> E2[狗能量包络 E狗t]
    D0 --> E0[人类能量包络 E人t]
    
    E1 --> F1[猫扫视动力学 + 微颤22Hz]
    E2 --> F2[狗扫视动力学 + 微颤16Hz]
    E0 --> F0[人类扫视动力学 + 微颤14Hz]
    
    F1 --> G1[猫眼质检 + 猫眼底膜渲染]
    F2 --> G2[狗眼质检 + 狗眼底膜渲染]
    F0 --> G0[人类质检 + 人类底膜渲染]
    
    G1 --> H[输出 RGB 控制图 + JSON → Wan]
    G2 --> H
    G0 --> H