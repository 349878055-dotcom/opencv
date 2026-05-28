"""Pomot 管线入口：将 Pomot 各模块串联为完整的端到端流程"""
from __future__ import annotations

from typing import Any

from gaze_engine._shared.slider_schema import SliderPacket
from gaze_engine.delivery_pipeline import run_species_delivery, write_delivery_json
from gaze_engine.pomot.nl_splitter import NLSplitter
from gaze_engine.pomot.emotion_router import EmotionRouter
from gaze_engine.pomot.registry import PomotRegistry
from gaze_engine.pomot.composer import PomotComposer
from gaze_engine.pomot.delta import PacketDeltaApplier
from gaze_engine.pomot.assembler import DiffusionPromptAssembler


class PomotPipeline:
    """
    Pomot 管线：完整的两轮对话流程。

    用法:
        pipeline = PomotPipeline()

        # 第一轮
        result_v1 = pipeline.round1("委屈的跑回了笼子再回头看了一眼")

        # 第二轮
        result_v2 = pipeline.round2("希望狗子再委屈一点", result_v1["packet"])
    """

    def __init__(self) -> None:
        self.splitter = NLSplitter()
        self.router = EmotionRouter()
        self.registry = PomotRegistry()
        self.composer = PomotComposer(self.registry)
        self.delta_applier = PacketDeltaApplier()
        self.assembler = DiffusionPromptAssembler()

    def round1(
        self,
        customer_nl: str,
        *,
        photo_hint: str = "",
        run_pipeline: bool = True,
        species_override: str = "",
        emotion_override: str = "",
        breed_override: str = "",
        output_dir: str = "",
    ) -> dict[str, Any]:
        """
        第一轮：NL → 拆解 → 路由 → 合成 → 管线 → 拼装

        Args:
            customer_nl: 客户自然语言
            photo_hint: 参考照片路径（可选）
            run_pipeline: 是否执行完整管线（生成 02_烘焙.json）
            species_override: 强制指定物种
            emotion_override: 强制指定情绪
            breed_override: 强制指定品种
            output_dir: 输出目录（可选）

        Returns:
            {
                "split": NLSplitResult,
                "route": EmotionRoute,
                "packet": SliderPacket,
                "baked_json": dict | None,   # 02_烘焙.json 内容
                "beat_text": str,             # 05_节拍表.txt 文本
                "prompt_04": str,             # 04_Prompt.txt 文本
                "payload": {                  # 送扩散引擎
                    "video": "",
                    "prompt": str
                }
            }
        """
        # 1. NL 拆解
        split = self.splitter.split(customer_nl, photo_hint=photo_hint)

        # 允许外部覆盖
        if species_override:
            split.species_hint = species_override
        if breed_override:
            split.breed_hint = breed_override

        # 2. 情绪路由（门户按钮 → preset_override 直连情绪包，不走 NL 词表）
        route = self.router.route(
            split.emotion,
            split.species_hint,
            split.breed_hint,
            preset_override=emotion_override,
        )

        # 3. 第一轮合成
        packet = self.composer.compose(split, route)

        result: dict[str, Any] = {
            "split": split,
            "route": route,
            "packet": packet,
            "baked_json": None,
            "beat_text": "",
            "prompt_04": "",
            "payload": {"video": "", "prompt": ""},
        }

        # 4. 管线执行
        if run_pipeline:
            baked_json = self._run_delivery(
                packet, output_dir,
                species=route.species,
                breed=route.breed or "",
                style_id=route.breed or packet.style or "",
                narrative_action=split.action or "",
            )
            result["baked_json"] = baked_json

            # 5. 最终拼装
            assembly = self.assembler.assemble(
                baked_json,
                customer_action=split.action,
                species=route.species,
                breed=route.breed,
                emotion=route.preset_name,
                mood_tags=[],
            )
            result["beat_text"] = assembly["payload"]["prompt"].split("## 扩散节拍表")[1].split("## 叙事")[0].strip() if "## 扩散节拍表" in (assembly.get("prompt_04") or "") else ""
            result["prompt_04"] = assembly["prompt_04"]
            result["payload"] = assembly["payload"]

        return result

    def round2(
        self,
        customer_nl: str,
        previous_packet: SliderPacket,
        previous_baked: dict | None = None,
        *,
        run_pipeline: bool = True,
        output_dir: str = "",
    ) -> dict[str, Any]:
        """
        第二轮：微调 → delta 叠加 → 管线 → 重新拼装

        Args:
            customer_nl: 客户微调文本
            previous_packet: 上一轮的 SliderPacket
            previous_baked: 上一轮的 baked_json（可选，用于保留元信息）
            run_pipeline: 是否重新执行管线
            output_dir: 输出目录

        Returns:
            同 round1
        """
        # 1. NL 拆解（仅提取微调意图）
        split = self.splitter.split(customer_nl)

        # 2. Delta 叠加
        packet = self.delta_applier.apply(previous_packet, customer_nl)

        result: dict[str, Any] = {
            "split": split,
            "route": None,
            "packet": packet,
            "baked_json": None,
            "beat_text": "",
            "prompt_04": "",
            "payload": {"video": "", "prompt": ""},
            "delta_summary": self.delta_applier.extract_delta_summary(customer_nl),
        }

        # 3. 管线执行
        if run_pipeline:
            species = "human"
            breed = ""
            emotion = packet.emotion
            if previous_baked:
                species = previous_baked.get("species", "human")
                breed = previous_baked.get("breed", "")

            baked_json = self._run_delivery(
                packet, output_dir,
                species=species,
                breed=breed,
                style_id=breed or packet.style or "",
                narrative_action=split.action or (previous_baked or {}).get("narrative_action", ""),
            )
            result["baked_json"] = baked_json

            # 4. 最终拼装
            assembly = self.assembler.assemble(
                baked_json,
                customer_action=split.action or "",
                species=species,
                breed=breed,
                emotion=emotion,
            )
            result["prompt_04"] = assembly["prompt_04"]
            result["payload"] = assembly["payload"]

        return result

    def _run_delivery(
        self,
        packet: SliderPacket,
        output_dir: str = "",
        species: str = "human",
        breed: str = "",
        style_id: str = "",
        narrative_action: str = "",
    ) -> dict:
        """执行管线，返回 02_烘焙.json 内容"""
        sid = style_id or breed or ""
        baked, _, _, _ = run_species_delivery(
            packet,
            species,
            narrative_action=narrative_action,
            breed_id=breed or "",
            style_id=sid,
        )

        baked["species"] = species
        baked["gaze_emotion_id"] = packet.emotion
        baked["mood"] = packet.emotion
        if breed:
            baked["breed"] = breed
        if narrative_action:
            baked["narrative_action"] = narrative_action

        # 写入文件（如果指定了输出目录）
        if output_dir:
            from pathlib import Path
            from asset_lib import write_baked_json

            out = Path(output_dir)
            write_baked_json(out, baked, species=species)

        return baked