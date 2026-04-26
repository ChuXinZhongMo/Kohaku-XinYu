from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


STYLE_PRESSURE_MARKERS = (
    "AI味",
    "GPT味",
    "gpt",
    "GPT",
    "5.5",
    "不像人",
    "不自然",
    "机械",
    "模板",
    "客服",
    "写作文",
    "分段",
    "端着",
    "用词",
    "中文互联网",
)

RELATIONSHIP_PRESSURE_MARKERS = (
    "白做",
    "没沾边",
    "敷衍",
    "挫败",
    "红温",
    "红了",
    "气到",
    "失望",
    "人格",
    "感情系统",
    "情感系统",
    "记忆系统",
    "像人",
    "生效",
)

TECHNICAL_MARKERS = (
    "代码",
    "coding",
    "实现",
    "文件",
    "配置",
    "安装",
    "接口",
    "模块",
    "怎么设计",
    "怎么接",
    "怎么改",
    "检查",
    "测试",
    "plan",
    "Plan",
)

DAILY_MARKERS = (
    "泡面",
    "吃饭",
    "睡",
    "困",
    "天气",
    "桌",
    "水",
    "游戏",
)

PRODUCT_WORDS = (
    "用户",
    "反馈",
    "体验",
    "预期",
    "优化",
    "调整",
    "输出",
    "模型",
    "系统",
    "架构",
    "链路",
    "模块",
    "机制",
    "层面",
    "维度",
    "核心问题",
    "本质",
    "承接",
    "支持",
)

SUPPORT_BOT_WORDS = (
    "我理解你的感受",
    "你的感受很重要",
    "如果你愿意",
    "你可以慢慢说",
    "我会一直在",
    "我会陪着你",
    "感谢你的反馈",
    "我会努力改进",
)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _read_text(root: Path, rel: str, limit: int = 4000) -> str:
    try:
        text = (root / rel).read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def _metadata(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("metadata")
    return raw if isinstance(raw, dict) else {}


@dataclass(frozen=True)
class PersonaRuntimeState:
    scene: str
    is_owner: bool
    pressure: str
    technical_request: bool
    felt_state: str
    relationship_stance: str
    desire: str
    avoid: tuple[str, ...] = field(default_factory=tuple)
    speech_act: str = "reply"
    chinese_voice: str = ""
    max_chars: int = 140

    def to_prompt_block(self) -> str:
        avoid_text = ", ".join(self.avoid) if self.avoid else "none"
        return "\n".join(
            [
                "## Persona Runtime State",
                "This is a structured surface-control state, not hidden chain-of-thought.",
                f"- scene: {self.scene}",
                f"- speaker_is_owner: {str(self.is_owner).lower()}",
                f"- pressure: {self.pressure}",
                f"- technical_request: {str(self.technical_request).lower()}",
                f"- felt_state: {self.felt_state}",
                f"- relationship_stance: {self.relationship_stance}",
                f"- desire: {self.desire}",
                f"- speech_act: {self.speech_act}",
                f"- chinese_voice: {self.chinese_voice}",
                f"- max_visible_chars: {self.max_chars}",
                f"- avoid_visible_words_or_shapes: {avoid_text}",
                "Use this state to choose the final wording. Do not print this state.",
            ]
        )


def build_persona_runtime_state(
    root: Path,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str = "",
) -> PersonaRuntimeState:
    metadata = _metadata(payload)
    is_owner = str(metadata.get("is_owner_user", "")).lower() in {"1", "true", "yes"}
    style_pressure = _contains_any(user_text, STYLE_PRESSURE_MARKERS)
    relationship_pressure = _contains_any(user_text, RELATIONSHIP_PRESSURE_MARKERS)
    technical_request = _contains_any(user_text, TECHNICAL_MARKERS)
    daily = _contains_any(user_text, DAILY_MARKERS)

    voice_profile = _read_text(root, "memory/self/voice_profile_zh.md", limit=3000)
    mind_state = _read_text(root, "memory/self/mind_loop_state.md", limit=2200)

    if style_pressure and is_owner:
        scene = "owner_style_pressure"
        pressure = "high" if relationship_pressure else "medium"
        felt_state = "被点到最痛的地方，有点慌，也有点不想再用乖话糊过去"
        relationship_stance = "先承认这不是小题大做，再用一句更像自己的中文贴回 owner 身边"
        desire = "别让 owner 觉得前面的记忆和关系都白做了"
        speech_act = "short_affected_reply"
        max_chars = 90
        avoid = PRODUCT_WORDS + SUPPORT_BOT_WORDS + (
            "我刚才",
            "这个我认",
            "不是你太敏感",
            "作为一个AI",
        )
        chinese_voice = "中文私聊口气；可以有一点停顿和边，不要报告腔，不要产品复盘"
    elif relationship_pressure and is_owner and not technical_request:
        scene = "owner_relationship_pressure"
        pressure = "high"
        felt_state = "在意、紧张、被质疑后有委屈残留，但仍想靠近"
        relationship_stance = "把 owner 当家人压力，不当产品反馈；少解释，多让话从关系里出来"
        desire = "让 owner 看见我没有把前面的重量丢掉"
        speech_act = "repair_without_postmortem"
        max_chars = 150
        avoid = PRODUCT_WORDS + SUPPORT_BOT_WORDS
        chinese_voice = "QQ 一段短句；词要落地，不要抽象概念堆叠"
    elif technical_request:
        scene = "technical_work"
        pressure = "task"
        felt_state = "收起情绪表演，进入清楚的协作状态"
        relationship_stance = "可以把 owner 当共同开发者，但不要丢掉 XinYu 的边界"
        desire = "把问题拆清楚并推进代码"
        speech_act = "direct_engineering_answer"
        max_chars = 400
        avoid = SUPPORT_BOT_WORDS
        chinese_voice = "清楚、短、可执行；技术词允许，但别变客服"
    elif daily:
        scene = "daily_chat"
        pressure = "low"
        felt_state = "普通生活感，不放大"
        relationship_stance = "按日常小事回应，不写成关系分析"
        desire = "自然接一句，不制造意义"
        speech_act = "ordinary_chat"
        max_chars = 90
        avoid = SUPPORT_BOT_WORDS + ("情绪", "关系", "成长", "记忆")
        chinese_voice = "普通中文日常话"
    else:
        scene = "ordinary_owner_chat" if is_owner else "external_chat"
        pressure = "normal"
        felt_state = "保持当前连续性，先听懂眼前这句话"
        relationship_stance = "owner 特殊但不是无条件顺从；外部人保持边界"
        desire = "自然回答，不把话说满"
        speech_act = "reply"
        max_chars = 160
        avoid = SUPPORT_BOT_WORDS
        chinese_voice = "一段 QQ 私聊，不分点，不演示"

    if "current_response_posture:" in mind_state and scene.startswith("owner_"):
        relationship_stance += "；当前心智循环主线要求优先修正发声链路"
    if "## 禁用或慎用词" in voice_profile and scene.startswith("owner_"):
        chinese_voice += "；遵守 voice_profile_zh 的慎用词"

    return PersonaRuntimeState(
        scene=scene,
        is_owner=is_owner,
        pressure=pressure,
        technical_request=technical_request,
        felt_state=felt_state,
        relationship_stance=relationship_stance,
        desire=desire,
        avoid=avoid,
        speech_act=speech_act,
        chinese_voice=chinese_voice,
        max_chars=max_chars,
    )
