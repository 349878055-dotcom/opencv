"""预设注册表：按 (preset) 加载人类预设模板"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaze_engine.delivery.pomot.templates import PresetPromptTemplate

# ── 人类预设代码路径（仅人类）──
_SPECIES_PRESET_MODULE: dict[str, str] = {
    "human": "gaze_engine.control_surface",
}


class PomotRegistry:
    """预设注册表（仅人类）"""

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
            species: 物种（仅支持 human）
            preset_name: 预设名，如 '施压·凝视'
            breed: 保留参数，不再使用

        Returns:
            PresetPromptTemplate
        """
        cache_key = f"{species}:{preset_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        template = PresetPromptTemplate(
            species=species,
            breed="",
        )

        # 从人类预设代码加载基础 slider_packet
        pkt = self._load_preset_packet(preset_name)
        if pkt:
            template.slider_packet = pkt
            template.emotion_id = preset_name

        # 缓存
        self._cache[cache_key] = template
        return template

    def _load_preset_packet(self, preset_name: str) -> dict | None:
        """从预设资产 JSON 加载 slider_packet"""
        try:
            from asset_lib import is_valid_preset
            from gaze_engine.input.control_surface import packet_from_acting_preset

            if is_valid_preset("human", preset_name):
                pkt = packet_from_acting_preset(preset_name)
                return pkt.to_dict()
        except Exception:
            pass
        return None


    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()