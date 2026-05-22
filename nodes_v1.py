"""
ecursor ComfyUI · 出厂链（单线）

Comfy 画布：1→2→4→5→6→7（03 包络在节点 2 内生成，不单独拖节点 3）
逻辑文件仍保留 03_能量包络.json 供工作台查看

改节点：搜「节点 1」「节点 2」… 或 JintaoEye_*
对照表：workflows/ComfyUI改代码手册.md

NODE_EDIT_MAP = {
    "1": ("JintaoEye_NaturalLanguageIn", "nl_to_packet.py", "llm_openai.py"),
    "2": ("JintaoEye_OpenWorkbench", "packet_finalize.py", "workbench_context.py"),
    "3": ("JintaoEye_EnergyEnvelope", "envelope_compile.py"),
    "4": ("JintaoEye_DenseFromEnvelope", "envelope_compile.py"),
    "5": ("JintaoEye_HumanPrior", "human_prior.py"),
    "6": ("JintaoEye_PulseQuality", "pulse_quality.py"),
    "7": ("JintaoEye_ControlVideo", "line_drawer.py"),
}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from gaze_engine.control_surface import PRESETS as ACTING_PULSE_PRESETS, packet_from_acting_preset
from gaze_engine.slider_schema import HoldSegment, MacroSliders
from gaze_engine.llm_openai import openai_configured
from gaze_engine.pipeline_io import (
    F_BAKED,
    F_CONSULT,
    F_DENSE_ENV,
    F_DENSE_PRIOR,
    F_DENSE_QUALITY,
    F_ENVELOPE,
    F_NL,
    F_PACKET,
    F_SYSTEM_PROMPT,
    F_PACKET_L1,
    cmd_dir,
    read_context,
    read_dense,
    read_packet,
    write_context,
    write_dense,
    write_envelope,
    write_packet,
)
from gaze_engine.llm_openai import chatgpt_node1, openai_configured, resolve_node1_system_prompt
from gaze_engine.node1_defaults import (
    load_previous_slider_packet,
    packet_to_context_snapshot,
    resolve_knowledge_base,
)
from gaze_engine.nl_intent import INTENT_APPLY, INTENT_CONSULT, CustomerNLResult
from gaze_engine.nl_router import resolve_packet_path_after_consult
from gaze_engine.nl_to_packet import packet_from_natural_language, pop_llm_meta
from gaze_engine.workbench_context import read_workbench_context, write_workbench_context
from gaze_engine.workbench_io import finalize_and_write_l1, write_slider_packet

def _p(path: str) -> Path:
    if path and path.strip():
        return Path(path.strip().strip('"')).resolve()
    return Path()

def _cat(tag: str) -> str:
    return f"ecursor/{tag}"

def _need_prev(path: str, label: str) -> str:
    if not path or not path.strip():
        raise ValueError(f"{label}：请先串联上一步（上步产物路径为空）")
    return path.strip()

_PRESET_KEEP = "（沿用上步）"

# 节点 1 · 最上=系统Prompt，中间=知识库，最下=客户自然语言（见工作流 Note）
_NODE1_PROMPT_PLACEHOLDER = "留空则用 prompts/node1_system_prompt.txt（通用厂内版）"
_NODE1_KB_PLACEHOLDER = "留空则用 prompts/node1_knowledge_base.txt（通用厂内版）"
_HOLD_SHAPE_ZH = ["平顶", "下泄", "慢拱", "脉冲", "发颤"]
_HOLD_SHAPE_EN = ("flat", "decay", "swell", "pulse", "tremble")

def _combo(options: list[str] | tuple[str, ...], display_name: str, **extra: object) -> tuple[str, dict]:
    """Comfy 新前端要求 COMBO 用 type=COMBO + options 列表（勿用裸 tuple 作首项）。"""
    return ("COMBO", {"options": list(options), "display_name": display_name, **extra})

def _str(display_name: str, **extra: object) -> tuple[str, dict]:
    return ("STRING", {"display_name": display_name, **extra})

def _int(display_name: str, default: int, **extra: object) -> tuple[str, dict]:
    return (
        "INT",
        {"default": default, "min": 0, "max": 100, "step": 1, "display_name": display_name, **extra},
    )

def _hold_shape_from_zh(label: str) -> str:
    label = (label or "平顶").strip()
    if label in _HOLD_SHAPE_EN:
        return label
    for zh, en in zip(_HOLD_SHAPE_ZH, _HOLD_SHAPE_EN, strict=True):
        if label == zh:
            return en
    return "flat"

def _preset_combo() -> list[str]:
    return [_PRESET_KEEP] + list(ACTING_PULSE_PRESETS.keys())

# ---------------------------------------------------------------------------
# 节点 1 · 自然语言 → 01_滑杆包.json
# ---------------------------------------------------------------------------
class JintaoEye_NaturalLanguageIn:
    """1 自然语言 | 改: llm_openai.py chatgpt_node1"""

    DESCRIPTION = (
        "三个框（从上到下）：①系统Prompt ②知识库 ③客户自然语言。"
        "画布左侧黄色说明框有详细注释。"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "system_prompt": _str(
                    "① 系统Prompt（规则·可留空）",
                    default=_NODE1_PROMPT_PLACEHOLDER,
                    multiline=True,
                    placeholder="① 系统Prompt：留空=内置默认",
                    tooltip="最上一框：写「咨询/生成」怎么分、输出 JSON 格式。留空=内置默认",
                ),
                "knowledge_base": _str(
                    "② 知识库（留空=通用内置）",
                    default=_NODE1_KB_PLACEHOLDER,
                    multiline=True,
                    placeholder="留空自动加载 prompts/node1_knowledge_base.txt",
                    tooltip="中间一框：留空=通用知识库文件；也可手填或接线",
                ),
                "customer_nl": _str(
                    "③ 客户自然语言（客户说什么）",
                    default="林青霞式施压瞬间凝视，更冷更钉",
                    multiline=True,
                    placeholder="③ 客户自然语言：客户本轮原话",
                    tooltip="最下一框：客户本轮原话，例如改戏、描述表演",
                ),
            },
            "optional": {
                "use_prior_slider": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "display_name": "带上轮滑杆",
                        "label_on": "是",
                        "label_off": "否",
                    },
                ),
                "use_chatgpt": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "display_name": "用语言模型",
                        "label_on": "开",
                        "label_off": "关",
                    },
                ),
                "chatgpt_model": _str("语言模型", default="gpt-4o-mini"),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("滑杆包路径", "模型回复")
    FUNCTION = "run"
    CATEGORY = "ecursor/1"

    def run(
        self,
        system_prompt,
        knowledge_base,
        customer_nl,
        use_prior_slider=True,
        use_chatgpt=True,
        chatgpt_model="gpt-4o-mini",
    ):
        if use_chatgpt and not openai_configured():
            raise RuntimeError(
                "已勾选用语言模型，但未设置 OPENAI_API_KEY。"
                "请在本目录 .env 填入密钥后重启 ComfyUI"
            )
        nl = (customer_nl or "").strip()
        if not nl:
            raise ValueError("请填写客户自然语言")
        kb = resolve_knowledge_base(knowledge_base)
        sp = (system_prompt or "").strip()
        out_dir = cmd_dir()
        (out_dir / F_NL).write_text(nl + "\n", encoding="utf-8")
        resolved_sp = resolve_node1_system_prompt(sp)
        (out_dir / F_SYSTEM_PROMPT).write_text(resolved_sp + "\n", encoding="utf-8")
        prev_pkt = load_previous_slider_packet(out_dir) if use_prior_slider else None

        if use_chatgpt and openai_configured():
            result = chatgpt_node1(
                nl,
                system_prompt=sp,
                knowledge_base=kb,
                model=chatgpt_model or "",
                previous_packet=prev_pkt,
            )
        else:
            pkt = packet_from_natural_language(nl, use_llm=False)
            result = CustomerNLResult(
                intent=INTENT_APPLY,
                reply=f"【已生成】预设「{pkt.emotion}」（关键词回退）",
                packet=pkt,
                meta={"intent_source": "keyword"},
            )

        reply = (result.reply or "").strip()
        (out_dir / F_CONSULT).write_text(reply + "\n", encoding="utf-8")

        if result.intent == INTENT_CONSULT:
            path = resolve_packet_path_after_consult(out_dir)
            ctx_kw: dict = dict(natural_language=nl, knowledge_base=kb, merge=True)
            if prev_pkt is not None:
                ctx_kw["last_slider_packet"] = packet_to_context_snapshot(prev_pkt)
            write_workbench_context(**ctx_kw)
            return (path, reply)

        pkt = result.packet
        if pkt is None:
            raise RuntimeError("apply 意图但未得到滑杆包，请检查系统 Prompt 的 JSON 契约")
        meta = result.meta if isinstance(result.meta, dict) else {}
        note_out = str(
            meta.get("energy_map_note") or meta.get("diffusion_prompt") or ""
        ).strip()
        path = write_packet(pkt, out_dir / F_PACKET)
        write_slider_packet(pkt)
        write_workbench_context(
            natural_language=nl,
            knowledge_base=kb,
            energy_map_note=note_out,
            last_slider_packet=packet_to_context_snapshot(pkt),
            merge=True,
        )
        return (path, reply)

# ---------------------------------------------------------------------------
# 节点 2 · 操作台（L1 定稿 + 保存 + 内嵌包络，供下轮节点 1 修改）
# ---------------------------------------------------------------------------
class JintaoEye_OpenWorkbench:
    """2 操作台 | L1 定稿、写 02/03、上下文；全量由节点 4 展开"""

    @classmethod
    def INPUT_TYPES(cls):
        presets = _preset_combo()
        return {
            "required": {
                "prev_packet_path": _str("上步产物路径", default=""),
                "director_nl": _str("导演自然语言", default="", multiline=True),
                "knowledge_base": _str("知识库摘录", default="", multiline=True),
                "energy_map_note": _str(
                    "能量图说明(来自节点1)",
                    default="",
                    multiline=True,
                    tooltip="留空则自动读 01_操作台上下文.json 里节点1写的 energy_map_note",
                ),
                "emotion_preset": _combo(
                    presets, "情绪预设", default=_PRESET_KEEP
                ),
                "use_manual_sliders": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "display_name": "用手动滑杆",
                        "label_on": "用下方滑杆覆盖",
                        "label_off": "沿用节点1滑杆",
                    },
                ),
                "macro_push": _int("往哪使劲", 85),
                "macro_power": _int("力度", 90),
                "macro_speed": _int("快慢", 88),
                "macro_steady": _int("盯得稳", 94),
                "macro_grip": _int("定得住", 90),
                "macro_outro": _int("收场", 32),
                "hold_shape": _combo(_HOLD_SHAPE_ZH, "盯住形状", default="平顶"),
                "pulse_rate": _int("脉冲密度", 0),
                "pulse_depth": _int("脉冲深度", 0),
                "swell": _int("段内起伏", 0),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("L1滑杆路径",)
    FUNCTION = "run"
    CATEGORY = "ecursor/2"

    def run(
        self,
        prev_packet_path,
        director_nl,
        knowledge_base,
        energy_map_note,
        emotion_preset,
        use_manual_sliders,
        macro_push,
        macro_power,
        macro_speed,
        macro_steady,
        macro_grip,
        macro_outro,
        hold_shape,
        pulse_rate,
        pulse_depth,
        swell,
    ):
        prev = _need_prev(prev_packet_path, "2 操作台")
        path = _p(prev)
        if not path.is_file():
            raise FileNotFoundError(f"2：找不到滑杆包 {path}（请先跑节点1）")
        pkt, _ = read_packet(str(path))

        if emotion_preset and emotion_preset != _PRESET_KEEP:
            if emotion_preset not in ACTING_PULSE_PRESETS:
                raise ValueError(f"2：未知情绪预设 {emotion_preset!r}")
            if pkt.emotion != emotion_preset:
                pkt = packet_from_acting_preset(emotion_preset)

        if use_manual_sliders:
            pkt.macro = MacroSliders(
                push=macro_push,
                power=macro_power,
                speed=macro_speed,
                steady=macro_steady,
                grip=macro_grip,
                outro=macro_outro,
            )
            pkt.hold_seg = HoldSegment(
                shape=_hold_shape_from_zh(hold_shape),  # type: ignore[arg-type]
                pulse_rate=pulse_rate,
                pulse_depth=pulse_depth,
                swell=swell,
            )
        pkt = pkt.clamped()

        nl = (director_nl or "").strip()
        kb = (knowledge_base or "").strip()
        note = (energy_map_note or "").strip()
        ctx = read_workbench_context()
        if not nl:
            nl = str(ctx.get("natural_language") or "").strip()
        if not kb:
            kb = str(ctx.get("knowledge_base") or "").strip()
        if not note:
            note = str(
                ctx.get("energy_map_note") or ctx.get("prompt") or ""
            ).strip()
        if not kb:
            kb = resolve_knowledge_base("")

        write_slider_packet(pkt)
        write_workbench_context(
            natural_language=nl,
            energy_map_note=note,
            knowledge_base=kb,
        )
        if nl:
            (cmd_dir() / F_NL).write_text(nl + "\n", encoding="utf-8")

        l1 = finalize_and_write_l1(pkt)
        pkt_l1, _ = read_packet(str(l1))
        write_envelope(pkt_l1)
        return (str(l1.resolve()),)

# ---------------------------------------------------------------------------
# 节点 3 · 能量包络（可选/调试；出厂链已并入节点 2，画布可不拖）
# ---------------------------------------------------------------------------
class JintaoEye_EnergyEnvelope:
    """3 能量包络(可选) | 正常跑节点 2 即会写 03_能量包络.json"""

    DEPRECATED = True

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"上步产物路径": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("产物路径",)
    FUNCTION = "run"
    CATEGORY = "ecursor/3"

    def run(self, 上步产物路径):
        prev = _need_prev(上步产物路径, "3 包络")
        pkt, _ = read_packet(prev)
        return (write_envelope(pkt),)

# ---------------------------------------------------------------------------
# 节点 4 · 全量 12×150
# ---------------------------------------------------------------------------
class JintaoEye_DenseFromEnvelope:
    """4 全量展开 | 改: envelope_compile.py channels_from_packet"""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"上步产物路径": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("产物路径",)
    FUNCTION = "run"
    CATEGORY = "ecursor/4"

    def run(self, 上步产物路径):
        from gaze_engine.envelope_compile import channels_from_packet, make_delivery_stub

        _need_prev(上步产物路径, "4 全量")
        l1 = cmd_dir() / F_PACKET_L1
        env_p = cmd_dir() / F_ENVELOPE
        if not l1.is_file():
            raise FileNotFoundError(f"4：缺少 {F_PACKET_L1}，请先跑 2 操作台")
        pkt, _ = read_packet(str(l1))
        if not env_p.is_file():
            write_envelope(pkt)
        channels = channels_from_packet(pkt)
        stub = make_delivery_stub(pkt, channels, label=pkt.emotion or "")
        stub["energy_envelope"] = json.loads(env_p.read_text(encoding="utf-8"))
        write_context(stub)
        return (write_dense(channels, packet=pkt, stub=stub),)

# ---------------------------------------------------------------------------
# 节点 5 · 真人律 → 05_全量_真人律.json
# ---------------------------------------------------------------------------
class JintaoEye_HumanPrior:
    """5 真人律 | 改: human_prior.py"""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"上步产物路径": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("产物路径",)
    FUNCTION = "run"
    CATEGORY = "ecursor/5"

    def run(self, 上步产物路径):
        from gaze_engine.human_prior import apply_human_prior

        dense_p = _need_prev(上步产物路径, "5 真人律")
        channels, pkt, ctx = read_dense(dense_p)
        if not ctx:
            ctx = read_context()
        dense_out, _ = apply_human_prior(channels, pkt, ctx)
        return (write_dense(dense_out, packet=pkt, stub=ctx, path=cmd_dir() / F_DENSE_PRIOR),)

# ---------------------------------------------------------------------------
# 节点 6 · 平庸纠正 → 06_全量_平庸纠正.json
# ---------------------------------------------------------------------------
class JintaoEye_PulseQuality:
    """6 平庸纠正 | 改: pulse_quality.py"""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"上步产物路径": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("产物路径",)
    FUNCTION = "run"
    CATEGORY = "ecursor/6"

    def run(self, 上步产物路径):
        from gaze_engine.pulse_quality import fix_pulse_quality

        prev = _need_prev(上步产物路径, "6 平庸")
        channels, pkt, ctx = read_dense(prev)
        if not ctx:
            ctx = read_context()
        dense_out, _ = fix_pulse_quality(channels, pkt, ctx)
        return (write_dense(dense_out, packet=pkt, stub=ctx, path=cmd_dir() / F_DENSE_QUALITY),)


# ---------------------------------------------------------------------------
# 节点 7 · 2D 霓虹控制视频（纯 OpenCV 渲染，送 Wan22FunControl）
# ---------------------------------------------------------------------------
class JintaoEye_ControlVideo:
    """7 控制视频 | 改: line_drawer.py"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "上步产物路径": ("STRING", {"default": ""}),
                "render_video": ("BOOLEAN", {"default": True, "label_on": "是", "label_off": "否"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("产物路径",)
    FUNCTION = "run"
    CATEGORY = "ecursor/7"

    def run(self, 上步产物路径, render_video=True):
        from gaze_engine.line_drawer import generate_control_video
        from gaze_engine.pipeline_io import read_dense
        from asset_lib import cmd_dir

        dense_p = _need_prev(上步产物路径, "7 控制视频")
        channels, pkt, _ = read_dense(dense_p)
        out = cmd_dir() / "control_video.mp4"

        if render_video:
            generate_control_video(
                {"channels": channels, "frame_count": 150, "fps": 30},
                str(out),
            )

        return (str(out.resolve()),)


NODE_CLASS_MAPPINGS = {
    "JintaoEye_NaturalLanguageIn": JintaoEye_NaturalLanguageIn,
    "JintaoEye_OpenWorkbench": JintaoEye_OpenWorkbench,
    "JintaoEye_EnergyEnvelope": JintaoEye_EnergyEnvelope,
    "JintaoEye_DenseFromEnvelope": JintaoEye_DenseFromEnvelope,
    "JintaoEye_HumanPrior": JintaoEye_HumanPrior,
    "JintaoEye_PulseQuality": JintaoEye_PulseQuality,
    "JintaoEye_ControlVideo": JintaoEye_ControlVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JintaoEye_NaturalLanguageIn": "1 自然语言",
    "JintaoEye_OpenWorkbench": "2 操作台",
    "JintaoEye_EnergyEnvelope": "3 能量包络",
    "JintaoEye_DenseFromEnvelope": "4 全量展开",
    "JintaoEye_HumanPrior": "5 真人律",
    "JintaoEye_PulseQuality": "6 平庸纠正",
    "JintaoEye_ControlVideo": "7 2D控制视频",
}
