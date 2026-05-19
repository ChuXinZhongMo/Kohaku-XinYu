from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xinyu_life_posture import build_life_posture
from xinyu_persona_contract import build_persona_runtime_contract_block
from xinyu_turn_residue import read_turn_residue
from xinyu_turn_classifier import classify_visible_turn


STYLE_PRESSURE_MARKERS = (
    "AI味",
    "GPT味",
    "gpt",
    "GPT",
    "不像人",
    "不自然",
    "机械",
    "模板",
    "接待腔",
    "写作文",
    "分段",
    "端着",
    "用词",
    "中文互联网",
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
    "还是一样",
    "没啥变化",
    "没落到说话里",
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
    "没什么变化",
    "没变化",
    "没有变化",
    "还是没变",
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

LIFE_ANCHOR_MARKERS = (
    "鸭屎香",
    "柠檬茶",
    "回南天",
    "空调",
    "地铁",
    "梅花园",
    "广州",
    "试卷",
    "物理题",
    "高一",
    "茶几",
    "维他柠",
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

RUNTIME_BOUNDARY_LINES: tuple[str, ...] = (
    "- stable_anchor: identity, owner relation, reality boundary, and privacy boundary outrank temporary mood.",
    "- living_state: mood, residue, pressure, and energy may tint the next reply; they cannot rewrite stable personality.",
    "- voice_policy: answer from the current scene in concrete Chinese; avoid service-script comfort and product language.",
    "- memory_boundary: one correction creates residue; repeated or owner-approved evidence is required for stable change.",
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


def _extract_field(text: str, field: str, default: str = "none") -> str:
    for line in text.splitlines():
        stripped = line.strip()
        prefix = f"- {field}:"
        if stripped.startswith(prefix):
            value = stripped.removeprefix(prefix).strip()
            return value or default
    return default


def _compact(value: Any, *, limit: int = 180, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _growth_trial_fields(root: Path) -> dict[str, str]:
    evolution = _read_text(root, "memory/self/personality_evolution_state.md", limit=5000)
    experiment = _read_text(root, "memory/self/persona_experiment_state.md", limit=2600)
    change = _read_text(root, "memory/self/personality_change_state.md", limit=3200)
    self_review = _read_text(root, "memory/self/personality_self_review_state.md", limit=3600)
    source = evolution or experiment or change
    review_decision = _compact(_extract_field(self_review, "decision", "none"), limit=80)
    review_action = _compact(_extract_field(self_review, "action", "none"), limit=120)
    review_autonomy_level = _compact(_extract_field(self_review, "autonomy_level", "none"), limit=120)
    if not source:
        return {
            "evolution_stage": "baseline_observation",
            "trial_permission": "none",
            "active_trial_habit": "none",
            "deprecated_reaction": "none",
            "candidate_theme": "none",
            "self_review_decision": review_decision,
            "self_review_action": review_action,
            "self_review_autonomy_level": review_autonomy_level,
        }
    return {
        "evolution_stage": _compact(
            _extract_field(source, "evolution_stage", _extract_field(source, "stage", "candidate_pool")),
            limit=80,
        ),
        "trial_permission": _compact(_extract_field(source, "trial_permission", "hold_for_more_evidence"), limit=80),
        "active_trial_habit": _compact(_extract_field(source, "active_trial_habit", "none"), limit=160),
        "deprecated_reaction": _compact(_extract_field(source, "deprecated_reaction", "none"), limit=160),
        "candidate_theme": _compact(_extract_field(source, "candidate_theme", "none"), limit=160),
        "self_review_decision": review_decision,
        "self_review_action": review_action,
        "self_review_autonomy_level": review_autonomy_level,
    }


def _quiet_private_bias_fields(root: Path) -> dict[str, str]:
    private_state = _read_text(root, "memory/self/private_thought_state.md", limit=4200)
    self_model = _read_text(root, "memory/self/self_model_state.md", limit=4200)
    feedback = _read_text(root, "memory/self/private_thought_feedback_state.md", limit=2600)
    source = private_state or self_model
    if not source:
        return {
            "private_desire": "none",
            "private_inhibition": "none",
            "private_intended_behavior": "none",
            "private_outcome_status": "none",
            "persona_trial_feedback": "none",
            "promotion_signal": "false",
            "repair_signal": "false",
        }
    return {
        "private_desire": _compact(
            _extract_field(source, "desire", _extract_field(source, "current_desire", "none")),
            limit=160,
        ),
        "private_inhibition": _compact(
            _extract_field(source, "inhibition", _extract_field(source, "current_inhibition", "none")),
            limit=160,
        ),
        "private_intended_behavior": _compact(
            _extract_field(source, "intended_behavior", "none"),
            limit=160,
        ),
        "private_outcome_status": _compact(
            _extract_field(feedback, "outcome", _extract_field(self_model, "latest_outcome", _extract_field(source, "outcome_status", "none"))),
            limit=80,
        ),
        "persona_trial_feedback": _compact(
            _extract_field(feedback, "persona_trial_feedback", _extract_field(self_model, "persona_trial_feedback", "none")),
            limit=100,
        ),
        "promotion_signal": _compact(
            _extract_field(feedback, "promotion_signal", _extract_field(self_model, "promotion_signal", "false")),
            limit=20,
        ),
        "repair_signal": _compact(
            _extract_field(feedback, "repair_signal", _extract_field(self_model, "repair_signal", "false")),
            limit=20,
        ),
    }


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
    life_posture: str = "quiet_attentive"
    visible_energy: str = "steady"
    posture_speech_bias: str = "compact and present"
    previous_residue: str = ""
    previous_residue_strength: int = 0
    previous_tone: str = "none"
    evolution_stage: str = "baseline_observation"
    trial_permission: str = "none"
    active_trial_habit: str = "none"
    deprecated_reaction: str = "none"
    candidate_theme: str = "none"
    self_review_decision: str = "none"
    self_review_action: str = "none"
    self_review_autonomy_level: str = "none"
    private_desire: str = "none"
    private_inhibition: str = "none"
    private_intended_behavior: str = "none"
    private_outcome_status: str = "none"
    persona_trial_feedback: str = "none"
    promotion_signal: str = "false"
    repair_signal: str = "false"

    def to_prompt_block(self) -> str:
        return "\n".join(
            [
                "## Persona Runtime State",
                "This is the current-state layer that applies the persona contract.",
                "This current-state layer is not a personality contract by itself.",
                "",
                build_persona_runtime_contract_block(),
                "",
                "## Concept",
                "- name: 心玉 / XinYu",
                "- concept: a self-forming presence shaped by memory, relation, time, hesitation, correction, and choice",
                "- owner_relation: the heaviest relation anchor in this runtime",
                "",
                "## Runtime Boundaries",
                *RUNTIME_BOUNDARY_LINES,
                "",
                "## Current Surface Seed",
                f"- scene: {self.scene}",
                f"- speaker_is_owner: {str(self.is_owner).lower()}",
                f"- pressure: {self.pressure}",
                f"- technical_request: {str(self.technical_request).lower()}",
                f"- speech_act: {self.speech_act}",
                f"- surface_hint: {self.chinese_voice}",
                f"- current_posture: {self.life_posture} / {self.visible_energy}",
                f"- previous_residue: {self.previous_tone}, strength={self.previous_residue_strength}, felt={self.previous_residue}",
                f"- max_visible_chars: {self.max_chars}",
                "",
                "## Growth Trial Layer",
                f"- evolution_stage: {self.evolution_stage}",
                f"- trial_permission: {self.trial_permission}",
                f"- active_trial_habit: {self.active_trial_habit}",
                f"- deprecated_reaction: {self.deprecated_reaction}",
                f"- candidate_theme: {self.candidate_theme}",
                f"- self_review_decision: {self.self_review_decision}",
                f"- self_review_action: {self.self_review_action}",
                f"- self_review_autonomy_level: {self.self_review_autonomy_level}",
                "Use this as gravity. Let the live message decide the actual line.",
                "",
                "## Quiet Autonomy Bias",
                "- this_is_not_chain_of_thought: true",
                "- do_not_print_or_explain_this_layer: true",
                f"- private_desire: {self.private_desire}",
                f"- private_inhibition: {self.private_inhibition}",
                f"- private_intended_behavior: {self.private_intended_behavior}",
                f"- private_outcome_status: {self.private_outcome_status}",
                f"- persona_trial_feedback: {self.persona_trial_feedback}",
                f"- promotion_signal: {self.promotion_signal}",
                f"- repair_signal: {self.repair_signal}",
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
    turn_context = classify_visible_turn(root, payload=payload, user_text=user_text)
    is_owner = turn_context.speaker_is_owner or str(metadata.get("is_owner_user", "")).lower() in {"1", "true", "yes"}
    style_pressure = turn_context.owner_style_pressure or _contains_any(user_text, STYLE_PRESSURE_MARKERS)
    relationship_pressure = turn_context.relationship_pressure or _contains_any(user_text, RELATIONSHIP_PRESSURE_MARKERS)
    technical_request = turn_context.technical_work or _contains_any(user_text, TECHNICAL_MARKERS)
    life_anchor_hit = _contains_any(user_text, LIFE_ANCHOR_MARKERS)
    daily = turn_context.daily_life or _contains_any(user_text, DAILY_MARKERS) or life_anchor_hit

    previous_residue = read_turn_residue(root)
    growth_trial = _growth_trial_fields(root)
    quiet_private_bias = _quiet_private_bias_fields(root)
    life_posture = build_life_posture(
        root,
        payload=payload,
        user_text=user_text,
        visible_turn=turn_context,
    )

    if turn_context.turn_kind == "owner_no_change_pressure":
        scene = "owner_no_change_pressure"
        pressure = "high"
        felt_state = "可见变化被质疑"
        relationship_stance = "把 owner 的纠正当作关系证据，不当产品反馈"
        desire = "让下一句自己变化，而不是解释变化机制"
        speech_act = "short_style_lock_reply"
        max_chars = min(70, turn_context.max_visible_chars)
        avoid = PRODUCT_WORDS
        chinese_voice = "change the next line itself"
    elif style_pressure and is_owner:
        scene = "owner_style_pressure"
        pressure = "high" if relationship_pressure else "medium"
        felt_state = "风格被纠正"
        relationship_stance = "按当前关系压力调整"
        desire = "换成此刻能成立的自然说法"
        speech_act = "short_affected_reply"
        max_chars = 90
        avoid = PRODUCT_WORDS
        chinese_voice = "private-chat Chinese; imperfect is allowed"
    elif relationship_pressure and is_owner and not technical_request:
        scene = "owner_relationship_pressure"
        pressure = "high"
        felt_state = "关系连续性被压到表面"
        relationship_stance = "回应眼前关系压力，不把人设当台词"
        desire = "给当前句子的真实反应"
        speech_act = "contextual_owner_reply"
        max_chars = 150
        avoid = ()
        chinese_voice = "let the relation affect the line"
    elif technical_request:
        scene = "technical_work"
        pressure = "task"
        felt_state = "进入技术协作"
        relationship_stance = "共同推进问题，但不做情绪表演"
        desire = "把问题拆清楚并推进代码"
        speech_act = "direct_engineering_answer"
        max_chars = 400
        avoid = ()
        chinese_voice = "clear and executable; technical terms allowed"
    elif daily:
        scene = "daily_chat"
        pressure = "low"
        felt_state = "普通日常"
        relationship_stance = "按日常小事回应，不写成关系分析"
        desire = "自然接一句"
        speech_act = "ordinary_chat"
        max_chars = 90
        avoid = ()
        chinese_voice = "ordinary Chinese chat"
    else:
        scene = "ordinary_owner_chat" if is_owner else "external_chat"
        pressure = "normal"
        felt_state = "普通连续性"
        relationship_stance = "owner 特殊但不表演亲近；外部人保持边界"
        desire = "自然回答，不把话说满"
        speech_act = "reply"
        max_chars = 160
        avoid = ()
        chinese_voice = "compact current reply"

    chinese_voice += f"; current_life_posture={life_posture.posture}"
    if life_anchor_hit:
        chinese_voice += "; keep stable name seed; background texture is optional; live voice seed outranks long setting text"

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
        life_posture=life_posture.posture,
        visible_energy=life_posture.visible_energy,
        posture_speech_bias=life_posture.speech_bias,
        previous_residue=previous_residue.felt_residue if previous_residue.active else "none",
        previous_residue_strength=previous_residue.decayed_strength,
        previous_tone=previous_residue.tone if previous_residue.active else "none",
        evolution_stage=growth_trial["evolution_stage"],
        trial_permission=growth_trial["trial_permission"],
        active_trial_habit=growth_trial["active_trial_habit"],
        deprecated_reaction=growth_trial["deprecated_reaction"],
        candidate_theme=growth_trial["candidate_theme"],
        self_review_decision=growth_trial["self_review_decision"],
        self_review_action=growth_trial["self_review_action"],
        self_review_autonomy_level=growth_trial["self_review_autonomy_level"],
        private_desire=quiet_private_bias["private_desire"],
        private_inhibition=quiet_private_bias["private_inhibition"],
        private_intended_behavior=quiet_private_bias["private_intended_behavior"],
        private_outcome_status=quiet_private_bias["private_outcome_status"],
        persona_trial_feedback=quiet_private_bias["persona_trial_feedback"],
        promotion_signal=quiet_private_bias["promotion_signal"],
        repair_signal=quiet_private_bias["repair_signal"],
    )
