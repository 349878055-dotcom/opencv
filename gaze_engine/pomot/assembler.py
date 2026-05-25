"""最终拼装器：02_烘焙.json + 客户叙事 + 元信息 → 04_Prompt.txt → 送扩散引擎 payload

最终送扩散引擎的是两样东西：
  ① OpenCV 线条图 MP4（视觉控制信号）
  ② 04_给视频生成的Prompt.txt（语义控制信号）
  不含任何 JSON 文件。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DiffusionPromptAssembler:
    """扩散引擎提示词拼装器"""

    # ── 负向 Prompt 固定模板 ──
    _NEGATIVE_PROMPT = (
        "色调艳丽，过曝，模糊，字幕，整体发灰，低质量，丑陋，畸形，"
        "脸变形，换脸，多余人物，眉眼与画面不同步，"
        "乱动脱节，情绪浓度不足，涣散无神，夸张鬼脸，杂乱背景"
    )

    def __init__(self, rhythm_compiler_module: str = "gaze_engine._shared.rhythm_compiler") -> None:
        self._rhythm_module = rhythm_compiler_module

    def assemble(
        self,
        baked_json: dict,
        customer_action: str = "",
        *,
        species: str = "human",
        breed: str = "",
        emotion: str = "",
        mood_tags: list[str] | None = None,
        scene_desc: str = "",
        use_llm_scene: bool = False,
        llm_model: str = "",
    ) -> dict[str, Any]:
        """
        拼装送扩散引擎的最终 payload。

        Args:
            baked_json: 02_烘焙_真人律.json 的完整内容（dict）
            customer_action: 客户叙事动作文本
            species: 物种 human|dog|cat
            breed: 品种名
            emotion: 情绪名
            mood_tags: 情绪标签列表
            scene_desc: 场景描述（可选，留空则 LLM 填充或省略）
            use_llm_scene: 是否用 LLM 生成场景描述
            llm_model: LLM 模型名

        Returns:
            {
                "prompt_04": str,       # 04_给视频生成的Prompt.txt 文本
                "payload": {            # 送扩散引擎的 payload
                    "video": str,       # OpenCV 线条图 MP4 路径（由调用者补充）
                    "prompt": str       # prompt_04 内容
                }
            }
        """
        # ── 1. 生成 05_扩散节拍表.txt 文本 ──
        beat_text = self._build_beat_text(baked_json, species=species)

        # ── 2. 拼装正向段 ──
        positive_text = self._build_positive_prompt(
            species=species,
            breed=breed,
            emotion=emotion,
            mood_tags=mood_tags,
            scene_desc=scene_desc,
            use_llm_scene=use_llm_scene,
            customer_action=customer_action,
            llm_model=llm_model,
        )

        # ── 3. 拼装五段 ──
        emotion_name = emotion or baked_json.get("mood", "未知")
        lines = [
            "# 给视频生成引擎的说明",
            f"# 情绪: {emotion_name}",
            f"# 物种: {species}",
            f"# 品种: {breed or '-'}",
            f"# 来源: 04_Prompt.txt · 从 02_烘焙.json 自动拼装",
            "",
            "## 正向 Prompt",
            positive_text,
            "",
            "## 扩散节拍表",
            beat_text,
            "",
            "## 叙事",
            customer_action or "（无客户叙事）",
            "",
            "## 负向 Prompt",
            self._NEGATIVE_PROMPT,
            "",
        ]
        prompt_04 = "\n".join(lines)

        # ── 4. 返回最终 payload（video 路径由调用者补充） ──
        return {
            "prompt_04": prompt_04,
            "payload": {
                "video": "",  # 由调用者填写 OpenCV 线条图 MP4 路径
                "prompt": prompt_04,
            },
        }

    def _build_beat_text(self, baked_json: dict, species: str = "human") -> str:
        """调用 rhythm_compiler 生成 05_扩散节拍表.txt 文本"""
        try:
            import importlib

            mod = importlib.import_module(self._rhythm_module)
            return mod.build_metronome_text(baked_json, species=species)
        except Exception:
            return "# 扩散节拍表（生成失败）\n"

    def _build_positive_prompt(
        self,
        species: str,
        breed: str,
        emotion: str,
        mood_tags: list[str] | None,
        scene_desc: str,
        use_llm_scene: bool,
        customer_action: str,
        llm_model: str,
    ) -> str:
        """拼装正向 Prompt 段"""
        mood_tags = mood_tags or ([emotion] if emotion else [])

        # 物种自适应的开头
        if species == "human":
            species_line = breed or "人物"
        elif species == "dog":
            species_line = f"{breed or '狗狗'}犬，真实毛发" if breed else "狗狗，真实毛发"
        elif species == "cat":
            species_line = f"{breed or '猫咪'}猫，真实毛发" if breed else "猫咪，真实毛发"
        else:
            species_line = breed or "人物"

        # LLM 场景描述（可选）
        if not scene_desc and use_llm_scene:
            scene_desc = self._llm_scene_desc(species, breed, emotion, customer_action, llm_model)

        emo_tag_str = "、".join(mood_tags) if mood_tags else emotion

        subject_map = {"dog": "狗狗", "cat": "猫咪", "human": "单人"}
        subject_type = subject_map.get(species, "单人")

        parts = [
            species_line,
            scene_desc or "",
            f"情绪浓度100，{emo_tag_str}",
            "眉毛与耳朵的运动严格跟随控制序列的节奏与幅度",
            "整体节奏紧跟眉眼控制序列的节奏与幅度",
            "眉眼以外可自然发挥，情绪起伏每一拍与眉眼对齐",
            f"{subject_type}，高清",
        ]
        return "，".join(p for p in parts if p)

    def _llm_scene_desc(
        self, species: str, breed: str, emotion: str, action: str, model: str
    ) -> str:
        """用 LLM 生成场景描述（可选增强）"""
        try:
            from gaze_engine._shared.llm_openai import openai_configured

            if not openai_configured():
                return ""
            from openai import OpenAI
            import os

            prompt = (
                f"请为以下场景生成一句画面质感描述（15字以内，不要引号）：\n"
                f"物种: {species}, 品种: {breed or '-'}, 情绪: {emotion}\n"
                f"叙事: {action}"
            )
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            resp = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return (resp.choices[0].message.content or "").strip().strip('"').strip("'")
        except Exception:
            return ""

    def assemble_to_file(
        self,
        baked_json: dict,
        output_path: str | Path,
        customer_action: str = "",
        *,
        species: str = "human",
        breed: str = "",
        emotion: str = "",
        mood_tags: list[str] | None = None,
    ) -> Path:
        """拼装并写入文件"""
        result = self.assemble(
            baked_json,
            customer_action=customer_action,
            species=species,
            breed=breed,
            emotion=emotion,
            mood_tags=mood_tags,
        )
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result["prompt_04"], encoding="utf-8")
        return path