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

# ── 负向 Prompt 基础模板（三物种共用 N1～N3）──
_NEGATIVE_BASE = (
    "色调艳丽，过曝，模糊，字幕，整体发灰，低质量，丑陋，畸形，"
    "脸变形，换脸，多余人物，眉眼与画面不同步，"
    "乱动脱节，情绪浓度不足，涣散无神，夸张鬼脸，杂乱背景"
)

_RHYTHM_LINES: dict[str, tuple[str, ...]] = {
    "dog": (
        "眼部与控制线的运动严格跟随控制序列的节奏与幅度",
        "整体节奏紧跟眼神控制序列的节奏与幅度",
        "眼以外可自然发挥，耳形/耳动由参考图与正向 Prompt 决定",
    ),
    "cat": (
        "眼部与控制线的运动严格跟随控制序列的节奏与幅度",
        "整体节奏紧跟眼神控制序列的节奏与幅度",
        "眼以外可自然发挥，耳形/耳动由参考图与正向 Prompt 决定",
    ),
    "human": (
        "眉毛与眼部的运动严格跟随控制序列的节奏与幅度",
        "整体节奏紧跟眉眼控制序列的节奏与幅度",
        "眉眼以外可自然发挥，情绪起伏每一拍与控制序列对齐",
    ),
}


class DiffusionPromptAssembler:
    """扩散引擎提示词拼装器"""

    def __init__(self, rhythm_compiler_module: str = "gaze_engine.rhythm_compiler") -> None:
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
        beat_text = self._build_beat_text(baked_json, species=species)

        emotion_name = (
            baked_json.get("gaze_emotion_id")
            or baked_json.get("mood")
            or emotion
            or "未知"
        )
        if not breed:
            breed = str(baked_json.get("breed") or baked_json.get("persona") or "")

        breed_display = self._resolve_breed_display(species, breed)
        revision = baked_json.get("revision") or baked_json.get("_compile_mode") or ""

        positive_text = self._build_positive_prompt(
            species=species,
            breed=breed,
            breed_display=breed_display,
            emotion=emotion_name,
            mood_tags=mood_tags,
            scene_desc=scene_desc,
            use_llm_scene=use_llm_scene,
            customer_action=customer_action,
            llm_model=llm_model,
            baked_json=baked_json,
        )
        negative_text = self._build_negative_prompt(species)

        lines = [
            "# 给视频生成引擎的说明",
            f"# 情绪: {emotion_name}",
            f"# 物种: {species}",
            f"# 品种: {breed_display or breed or '-'}",
            f"# revision: {revision or '-'}",
            "# 来源: 04_Prompt.txt · 从 02_烘焙.json 自动拼装",
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
            negative_text,
            "",
        ]
        prompt_04 = "\n".join(lines)

        return {
            "prompt_04": prompt_04,
            "payload": {
                "video": "",
                "prompt": prompt_04,
            },
        }

    @staticmethod
    def resolve_breed_display(species: str, breed_id: str) -> str:
        """风格/人格 id → 中文展示名（供门户与 04 头使用，仅人类）。"""
        if not breed_id or breed_id in ("default",):
            return ""
        try:
            if species == "human":
                _root = Path(__file__).resolve().parents[3]
                matrix = _root / "gaze_engine" / "style" / "persona_matrix.json"
                if matrix.is_file():
                    personas = json.loads(matrix.read_text(encoding="utf-8")).get("personas") or {}
                    if breed_id in personas:
                        return str(personas[breed_id].get("label") or breed_id)
                style = _root / "预设资产" / "风格包" / breed_id / "style.json"
                if style.is_file():
                    return str(json.loads(style.read_text(encoding="utf-8")).get("label") or breed_id)
        except Exception:
            pass

        return breed_id
    def _resolve_breed_display(self, species: str, breed_id: str) -> str:
        return self.resolve_breed_display(species, breed_id)

    def _build_beat_text(self, baked_json: dict, species: str = "human") -> str:
        try:
            import importlib

            mod = importlib.import_module(self._rhythm_module)
            source = baked_json.get("revision") or baked_json.get("_compile_mode") or ""
            return mod.build_metronome_text(
                baked_json, species=species, source_path=source
            )
        except Exception:
            return "# 扩散节拍表（生成失败）\n"

    def _build_positive_prompt(
        self,
        *,
        species: str,
        breed: str,
        breed_display: str,
        emotion: str,
        mood_tags: list[str] | None,
        scene_desc: str,
        use_llm_scene: bool,
        customer_action: str,
        llm_model: str,
        baked_json: dict | None = None,
    ) -> str:
        mood_tags = mood_tags or ([emotion] if emotion else [])
        emo_tag_str = "、".join(mood_tags) if mood_tags else emotion
        display = breed_display or breed

        if species == "human":
            species_line = f"{display}（气质参考，不换客户脸）" if display else "人物"
        elif species == "dog":
            species_line = f"{display or '狗'}，真实毛发"
        elif species == "cat":
            species_line = f"{display or '猫'}，真实毛发"
        else:
            species_line = display or "人物"

        if not scene_desc and use_llm_scene:
            scene_desc = self._llm_scene_desc(species, breed, emotion, customer_action, llm_model)

        visual = self._species_visual_prompt(
            species, emotion, f"情绪浓度100，{emo_tag_str}"
        )
        if species in ("dog", "cat") and baked_json:
            from gaze_engine.ear_prompt import (
                ear_params_from_baked,
                merge_ear_into_visual,
            )

            visual = merge_ear_into_visual(
                visual, ear_params_from_baked(baked_json), species=species
            )
        rhythm_lines = _RHYTHM_LINES.get(species, _RHYTHM_LINES["human"])
        subject_type = {"dog": "狗狗", "cat": "猫咪", "human": "单人"}.get(species, "单人")

        parts = [species_line]
        if scene_desc:
            parts.append(scene_desc)
        parts.append(visual)
        parts.extend(rhythm_lines)
        parts.append(f"{subject_type}，高清真实质感")
        return "，".join(p for p in parts if p)

    @staticmethod
    def _species_visual_prompt(species: str, emotion: str, fallback: str) -> str:
        mod_path = f"gaze_engine.{species}.rhythm_data"
        try:
            import importlib

            mod = importlib.import_module(mod_path)
            prompts = getattr(mod, "EMOTION_VISUAL_PROMPTS", {}) or {}
            if emotion in prompts:
                return str(prompts[emotion])
            for key, text in prompts.items():
                if key.split("·")[0] in (emotion or ""):
                    return str(text)
        except ImportError:
            pass
        return fallback

    @staticmethod
    def _build_negative_prompt(species: str) -> str:
        extra = ""
        mod_path = f"gaze_engine.{species}.rhythm_data"
        try:
            import importlib

            mod = importlib.import_module(mod_path)
            extra = str(getattr(mod, "NEGATIVE_EXTRA", "") or "")
        except ImportError:
            pass
        if extra:
            return f"{_NEGATIVE_BASE}，{extra}"
        return _NEGATIVE_BASE

    def _llm_scene_desc(
        self, species: str, breed: str, emotion: str, action: str, model: str
    ) -> str:
        try:
            from gaze_engine._shared.llm_openai import openai_configured

            if not openai_configured():
                return ""
            from openai import OpenAI
            import os

            display = self._resolve_breed_display(species, breed) or breed or "-"
            prompt = (
                f"请为以下场景生成一句画面质感描述（15字以内，不要引号）：\n"
                f"物种: {species}, 品种: {display}, 情绪: {emotion}\n"
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

    @staticmethod
    def split_for_wan(prompt_04: str) -> dict[str, str]:
        """将 04_Prompt.txt 拆为 Comfy/Wan 的 positive / negative CLIP 输入。"""
        text = prompt_04 or ""
        neg_marker = "## 负向 Prompt"
        narrative_marker = "## 叙事"
        beat_marker = "## 扩散节拍表"
        pos_marker = "## 正向 Prompt"

        negative = ""
        if neg_marker in text:
            negative = text.split(neg_marker, 1)[1].strip()

        positive_parts: list[str] = []
        if pos_marker in text:
            after_pos = text.split(pos_marker, 1)[1]
            if beat_marker in after_pos:
                positive_parts.append(after_pos.split(beat_marker, 1)[0].strip())
            else:
                positive_parts.append(after_pos.split(narrative_marker, 1)[0].strip())
        if beat_marker in text:
            beat_block = text.split(beat_marker, 1)[1]
            if narrative_marker in beat_block:
                positive_parts.append(beat_block.split(narrative_marker, 1)[0].strip())
            elif neg_marker in beat_block:
                positive_parts.append(beat_block.split(neg_marker, 1)[0].strip())
            else:
                positive_parts.append(beat_block.strip())
        if narrative_marker in text:
            narrative = text.split(narrative_marker, 1)[1]
            if neg_marker in narrative:
                narrative = narrative.split(neg_marker, 1)[0]
            positive_parts.append(narrative.strip())

        return {
            "positive": "\n\n".join(p for p in positive_parts if p),
            "negative": negative,
        }
