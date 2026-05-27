"""预设注册表：按 (species, breed, preset) 加载预设模板"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaze_engine.pomot.templates import PresetPromptTemplate

# ── 物种 → 预设代码路径映射 ──
_SPECIES_PRESET_MODULE: dict[str, str] = {
    "human": "gaze_engine.human.control_surface",
    "dog": "gaze_engine.dog.presets",
    "cat": "gaze_engine.cat.presets",
}

_SPECIES_BREED_MODULE: dict[str, str] = {
    "dog": "gaze_engine.dog.breeds",
    "cat": "gaze_engine.cat.breeds",
}


class PomotRegistry:
    """预设注册表"""

    def __init__(self) -> None:
        self._cache: dict[str, PresetPromptTemplate] = {}

    def load(
        self,
        species: str = "human",
        preset_name: str = "",
        breed: str = "",
    ) -> PresetPromptTemplate:
        """
        加载预设模板。

        Args:
            species: 物种 human|dog|cat
            preset_name: 预设名，如 '可怜·委屈'
            breed: 品种名（宠物用）

        Returns:
            PresetPromptTemplate
        """
        cache_key = f"{species}:{preset_name}:{breed}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        template = PresetPromptTemplate(
            species=species,
            breed=breed,
        )

        # 1. 从物种预设代码加载基础 slider_packet
        pkt = self._load_preset_packet(species, preset_name)
        if pkt:
            template.slider_packet = pkt
            template.emotion_id = preset_name

        # 2. 从品种配置加载品种微调
        breed_adjust = self._load_breed_adjust(species, breed)
        if breed_adjust:
            template.slider_packet["_breed_adjust"] = breed_adjust

        # 3. 缓存
        self._cache[cache_key] = template
        return template

    def _load_preset_packet(self, species: str, preset_name: str) -> dict | None:
        """从物种预设代码加载 slider_packet"""
        try:
            if species == "human":
                from gaze_engine.human.control_surface import PRESETS
                from gaze_engine.human.control_surface import packet_from_acting_preset

                if preset_name in PRESETS:
                    pkt = packet_from_acting_preset(preset_name)
                    return pkt.to_dict()
            elif species == "dog":
                from gaze_engine.dog.presets import dog_packet_from_file

                try:
                    pkt = dog_packet_from_file(preset_name)
                    return pkt.to_dict()
                except KeyError:
                    pass
            elif species == "cat":
                from gaze_engine.cat.presets import CAT_PRESETS

                if preset_name in CAT_PRESETS:
                    raw = CAT_PRESETS[preset_name]
                    return raw if isinstance(raw, dict) else raw.to_dict()  # type: ignore[union-attr]
        except Exception:
            pass
        return None

    def _load_breed_adjust(self, species: str, breed: str) -> dict | None:
        """从品种配置加载微调参数"""
        if not breed:
            return None
        try:
            if species == "dog":
                from gaze_engine.dog.breeds import BREEDS

                return BREEDS.get(breed)
            elif species == "cat":
                from gaze_engine.cat.breeds import BREEDS

                return BREEDS.get(breed)
        except Exception:
            pass
        return None


    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()