# ecursor_style_v1 — 人类/品种风格包 JSON 格式

> **状态：已定稿 v1** · 与 [`风格化偏向专篇_情绪与人格耦合.md`](风格化偏向专篇_情绪与人格耦合.md) §4.4 一致。

---

## 1. 用途

- 1 人格 / 1 品种 = **1 个** `style.json`，全局作用于该 id 的**全部情绪**。
- 运行时：`styled[ch,t] = clamp01(base_offset[ch] + scale_factor[ch] × pulse[ch,t])`
- 加载：`gaze_engine/_shared/style_compose.load_style_json(species, id)`

---

## 2. 文件路径

```text
预设资产/风格包/{species}/{id}/style.json
```

| species | 示例 id |
|---------|---------|
| `human` | `天选者_大祭司`、`魅惑者_温碧霞` … 共 9 个 |
| `cat` | `british_cat`、`ragdoll_cat`、`siamese_cat` … 共 9 个 |
| `dog` | `poodle_giant`、`golden_retriever`、`husky` … 共 10 个 |

---

## 3. 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `schema` | string | ✅ | 固定 `"ecursor_style_v1"` |
| `id` | string | ✅ | 与目录名一致 |
| `label` | string | ✅ | 展示名 |
| `species` | string | ✅ | `human` / `dog` / `cat` |
| `notes` | string | 推荐 | 气质一句话 |
| `base_offset` | object | ✅ | 12 通道静态偏置，各值 ∈ [0,1] |
| `scale_factor` | object | ✅ | 12 通道动态增益，各值 ∈ [0,1] |

**不含**（v1 不做）：矩阵 M、AU 表、逐情绪 override。

---

## 4. 十二通道键名

```text
pupil_x, pupil_y, blink, eyebrow, pupil_scale, iris_scale,
cornea_bulge, squint, brow_raise, lid_upper, lid_lower, eye_gloss
```

与 [`gaze_engine/human/envelope_compile.py`](../../gaze_engine/human/envelope_compile.py) 中 `HUMAN_CHANNELS` 一致。

---

## 5. 示例（节选）

```json
{
  "schema": "ecursor_style_v1",
  "id": "天选者_大祭司",
  "label": "天选者/大祭司",
  "species": "human",
  "notes": "冷峻克制，天生压迫感",
  "base_offset": { "pupil_x": 0.48, "...": "..." },
  "scale_factor": { "eyebrow": 0.90, "...": "..." }
}
```

---

## 6. 真源与同步

| 资产 | 路径 |
|------|------|
| **编辑真源（human 九人格）** | [`gaze_engine/human/persona_style_catalog.json`](../../gaze_engine/human/persona_style_catalog.json) |
| **编辑真源（猫 9 品种）** | [`gaze_engine/cat/breed_style_catalog.json`](../../gaze_engine/cat/breed_style_catalog.json) |
| **编辑真源（狗 10 品种）** | [`gaze_engine/dog/breed_style_catalog.json`](../../gaze_engine/dog/breed_style_catalog.json) |
| 同步脚本 | human: [`sync_human_style_pack.py`](../../tools/03_工具脚本/sync_human_style_pack.py) · cat/dog: [`sync_species_style_pack.py`](../../tools/03_工具脚本/sync_species_style_pack.py) |
| 运行时矩阵（fallback） | [`gaze_engine/human/persona_matrix.json`](../../gaze_engine/human/persona_matrix.json) |
| 人格合同 | [`合同/05_风格化/人/`](人/) 各 `{id}.md` §4 |

```bash
python tools/03_工具脚本/sync_human_style_pack.py
```

---

## 7. 与 persona_matrix 的关系

- `apply_persona_style()` **优先**读 `style.json`；缺失时回退 `persona_matrix.json`。
- 改 human 人格数值：**只改 catalog → 跑 sync**，保证三处一致。
