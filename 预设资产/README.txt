ecursor 预设资产库
==================

两大分类 + 底膜包
-----------------

① 情绪包/           ← 基本情绪滑杆 + PAD 气质（macro + hold_seg + pad）
│
├── human/           ← 16种（施压·凝视、可怜·委屈、魅惑·勾人…）
├── cat/             ← 12种（警觉瞪视、狩猎锁定、愤怒嘶哈…含 ear + pad）
└── dog/             ← 10种（警觉·竖耳、委屈·幼犬眼…含 ear + pad）


② 风格包/           ← 风格偏移（base_offset + scale_factor）
│                  公式：final = clamp(base + pulse * scale)
│                  作用于该风格的所有情绪
│
├── human/           ← 9 个人格风格
│   ├── 天选者_大祭司/   冷峻克制
│   ├── 魅惑者_部落巫医/ 妖冶诱惑
│   ├── 魅惑者_温碧霞/   眼波流转
│   ├── 狠厉者_铁血将军/ 铁血无情
│   ├── 怯弱者_逃兵/     畏缩怯懦
│   ├── 悲悯者_圣徒/     悲天悯人
│   ├── 呆滞者_傀儡/     空洞失神
│   ├── 癫狂者_疯僧/     疯癫狂乱
│   └── 天真者_幼童/     天真无邪
│
├── cat/             ← 4 个猫品种
│   ├── ragdoll_cat/   布偶猫/温顺型
│   ├── siamese_cat/   暹罗猫/高冷型
│   ├── stray_cat/     田园猫/机敏型
│   └── british_cat/   英短/憨厚型
│
└── dog/             ← 狗品种
    └── poodle_giant/  巨型贵宾/优雅型


③ 底膜包/           ← 几何骨架预设（SpeciesTemplate 物种默认）
│
├── human/species_default.json
├── cat/species_default.json
└── dog/species_default.json
    （品种几何：gaze_engine/{cat,dog}/breed_matrix.json · template_scales / template_structure）


编辑指南
--------
改预设数值：   情绪包/human/可怜·委屈.json → 改 macro/hold_seg/pad
改风格偏移：   风格包/human/天选者_大祭司/style.json → 改 base_offset/scale_factor
改物种底膜：   底膜包/{species}/species_default.json → 对齐 species_template.py
加新风格：     建 风格包/{species}/{风格名}/style.json
客户配准结果： 存到 客户资产库/客户_{id}/物种底膜模板.json（门户标定，禁止美颜手改）
❌ 不提供「眼睛大一点」类客户滑杆 — 合同/06_工程底膜/底膜模板选择与标定专篇.md
