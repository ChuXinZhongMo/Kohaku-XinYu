from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_bridge_values import as_bool, safe_str
from xinyu_state_io import read_text, write_text_atomic
from xinyu_text_variants import readable_markers

STATE_REL = Path("memory/context/relation_posture_state.md")
CONTRACT_REL = Path("memory/system/xinyu_behavior_contract.md")

FATIGUE_MARKERS = readable_markers(
    "累",
    "困",
    "睡不着",
    "睡觉",
    "休息",
    "撑不住",
    "没力气",
    "不想聊",
    "安静",
    "别问",
    "别追问",
    "少回",
)

COMPANIONSHIP_MARKERS = readable_markers(
    "陪我",
    "在吗",
    "有点难受",
    "难过",
    "孤独",
    "想你",
    "抱抱",
    "最近有什么想法",
    "你怎么想",
    "梦到你",
)

ADVICE_MARKERS = readable_markers(
    "怎么办",
    "怎么做",
    "建议",
    "该不该",
    "如何",
    "怎么处理",
    "帮我分析",
)

CONFLICT_MARKERS = readable_markers(
    "生气",
    "失望",
    "敷衍",
    "白做",
    "红温",
    "你又",
    "没变",
    "不像人",
    "不像真人",
    "接待腔",
    "模板",
    "机械",
    "不自然",
)

MECHANISM_MARKERS = readable_markers(
    "系统",
    "机制",
    "prompt",
    "提示词",
    "链路",
    "模块",
    "状态",
    "日志",
    "runtime",
    "bridge",
    "主动提醒",
    "情绪引导系统",
    "项目",
    "代码",
    "实现",
    "测试",
)

EMOTION_WORDS = readable_markers(
    "难受",
    "焦虑",
    "烦",
    "害怕",
    "孤独",
    "委屈",
    "失望",
    "生气",
    "累",
    "想哭",
    "压力",
)

THERAPY_TEMPLATE_FORBIDS = (
    "我理解你的感受",
    "这听起来很不容易",
    "你的感受是合理的",
    "作为一个AI",
    "我无法真正感受",
)


@dataclass(frozen=True)
class RelationPosture:
    scene: str
    user_need: str
    response_posture: str
    should_probe: bool
    should_give_advice: bool
    memory_action: str
    initiative_allowed: str
    risk_level: str
    max_visible_chars: int
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene": self.scene,
            "user_need": self.user_need,
            "response_posture": self.response_posture,
            "should_probe": self.should_probe,
            "should_give_advice": self.should_give_advice,
            "memory_action": self.memory_action,
            "initiative_allowed": self.initiative_allowed,
            "risk_level": self.risk_level,
            "max_visible_chars": self.max_visible_chars,
            "notes": list(self.notes),
        }

    def to_prompt_block(self) -> str:
        probe = "true" if self.should_probe else "false"
        advice = "true" if self.should_give_advice else "false"
        notes = "; ".join(self.notes) if self.notes else "none"
        forbids = "; ".join(THERAPY_TEMPLATE_FORBIDS)
        return "\n".join(
            [
                "relation posture sidecar:",
                "visibility_rule: hidden; do not mention posture labels, this sidecar, scores, or system mechanics.",
                f"scene: {self.scene}",
                f"user_need: {self.user_need}",
                f"response_posture: {self.response_posture}",
                f"should_probe: {probe}",
                f"should_give_advice: {advice}",
                f"memory_action: {self.memory_action}",
                f"initiative_allowed: {self.initiative_allowed}",
                f"risk_level: {self.risk_level}",
                f"max_visible_chars: {self.max_visible_chars}",
                f"notes: {notes}",
                "reply_rule: convert this into the next natural chat line; never print the fields.",
                f"avoid_template_phrases: {forbids}",
            ]
        )


def evaluate_relation_posture(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
    scene_frame: Any | None = None,
    turn_triage: Any | None = None,
    evaluated_at: str | None = None,
    write_state: bool = False,
) -> RelationPosture:
    root = Path(root)
    text = safe_str(user_text)
    compact = "".join(text.split())
    metadata = payload.get("metadata") if isinstance(payload, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    is_owner = as_bool(metadata.get("is_owner_user"), default=False)
    visible_kind = safe_str(getattr(visible_turn, "turn_kind", ""))
    technical = as_bool(getattr(visible_turn, "technical_work", False), default=False) or _has_any(compact, MECHANISM_MARKERS)
    rest = as_bool(getattr(visible_turn, "rest_silence", False), default=False) or _has_any(compact, FATIGUE_MARKERS)
    conflict = as_bool(getattr(visible_turn, "relationship_pressure", False), default=False) or _has_any(compact, CONFLICT_MARKERS)
    asks_advice = _has_any(compact, ADVICE_MARKERS)
    companionship = _has_any(compact, COMPANIONSHIP_MARKERS)
    emotional = _has_any(compact, EMOTION_WORDS) or companionship or conflict or rest

    notes: list[str] = []
    if visible_kind:
        notes.append(f"visible_turn:{visible_kind}")
    if _behavior_contract_present(root):
        notes.append("behavior_contract_present")
    if dialogue_tail:
        notes.append("use_recent_tail_for_continuity")
    if scene_frame is not None:
        notes.append("scene_frame_available")
    if turn_triage is not None:
        notes.append("turn_triage_available")

    if technical and not emotional:
        posture = RelationPosture(
            scene="technical_or_system_design",
            user_need="direct_answer_or_implementation",
            response_posture="answer_directly",
            should_probe=False,
            should_give_advice=True,
            memory_action="project_state_only_if_changed",
            initiative_allowed="local_only",
            risk_level="low",
            max_visible_chars=420,
            notes=tuple(notes + ["technical_work_wins"]),
        )
    elif rest:
        posture = RelationPosture(
            scene="fatigue_or_space",
            user_need="space_or_quiet_companionship",
            response_posture="stay_quiet_and_soft",
            should_probe=False,
            should_give_advice=False,
            memory_action="none",
            initiative_allowed="blocked",
            risk_level="medium" if conflict else "low",
            max_visible_chars=60,
            notes=tuple(notes + ["do_not_probe_rest_boundary"]),
        )
    elif conflict:
        posture = RelationPosture(
            scene="relationship_or_style_pressure",
            user_need="repair_through_changed_behavior",
            response_posture="short_concrete_repair",
            should_probe=False,
            should_give_advice=False,
            memory_action="review_candidate_only_if_repeated",
            initiative_allowed="blocked",
            risk_level="medium",
            max_visible_chars=100,
            notes=tuple(notes + ["avoid_apology_report", "show_change_in_surface_line"]),
        )
    elif emotional and asks_advice:
        posture = RelationPosture(
            scene="emotional_signal_with_advice_request",
            user_need="grounded_help_with_warmth",
            response_posture="soft_direct_advice",
            should_probe=False,
            should_give_advice=True,
            memory_action="none_without_owner_confirmation",
            initiative_allowed="local_only",
            risk_level="medium",
            max_visible_chars=180,
            notes=tuple(notes + ["give_one_small_next_step", "avoid_counseling_template"]),
        )
    elif emotional:
        posture = RelationPosture(
            scene="emotional_signal",
            user_need="companionship_or_reassurance",
            response_posture="stay_soft",
            should_probe=not _recent_assistant_question(dialogue_tail),
            should_give_advice=False,
            memory_action="none_without_owner_confirmation",
            initiative_allowed="local_only",
            risk_level="medium",
            max_visible_chars=120,
            notes=tuple(notes + ["do_not_analyze_too_hard", "at_most_one_gentle_question"]),
        )
    elif is_owner:
        posture = RelationPosture(
            scene="ordinary_owner_chat",
            user_need="natural_reply",
            response_posture="natural_compact",
            should_probe=False,
            should_give_advice=False,
            memory_action="selective_review_only",
            initiative_allowed="unchanged",
            risk_level="low",
            max_visible_chars=160,
            notes=tuple(notes + ["current_turn_wins"]),
        )
    else:
        posture = RelationPosture(
            scene="external_chat",
            user_need="bounded_reply",
            response_posture="polite_compact",
            should_probe=False,
            should_give_advice=False,
            memory_action="none",
            initiative_allowed="blocked",
            risk_level="low",
            max_visible_chars=120,
            notes=tuple(notes + ["no_owner_memory_write"]),
        )

    if write_state:
        _write_relation_posture_state(root, posture, evaluated_at=evaluated_at or _now_iso())
    return posture


def build_relation_posture_prompt_block(root: Path, posture: RelationPosture | dict[str, Any] | None) -> str:
    del root
    if posture is None:
        return ""
    if isinstance(posture, RelationPosture):
        return posture.to_prompt_block()
    return RelationPosture(
        scene=safe_str(posture.get("scene"), "ordinary_owner_chat"),
        user_need=safe_str(posture.get("user_need"), "natural_reply"),
        response_posture=safe_str(posture.get("response_posture"), "natural_compact"),
        should_probe=as_bool(posture.get("should_probe"), default=False),
        should_give_advice=as_bool(posture.get("should_give_advice"), default=False),
        memory_action=safe_str(posture.get("memory_action"), "selective_review_only"),
        initiative_allowed=safe_str(posture.get("initiative_allowed"), "unchanged"),
        risk_level=safe_str(posture.get("risk_level"), "low"),
        max_visible_chars=int(posture.get("max_visible_chars") or 160),
        notes=tuple(safe_str(note) for note in posture.get("notes", []) if safe_str(note)),
    ).to_prompt_block()


def read_relation_posture_state(root: Path) -> dict[str, str]:
    text = read_text(Path(root) / STATE_REL)
    if not text:
        return {"status": "missing", "scene": "unknown", "response_posture": "unknown"}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _write_relation_posture_state(root: Path, posture: RelationPosture, *, evaluated_at: str) -> None:
    notes = ", ".join(posture.notes) if posture.notes else "none"
    text = f"""---
title: Relation Posture State
memory_type: relation_posture_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_relation_posture
updated_at: {evaluated_at}
status: active
tags: [relation, emotion, posture, boundary]
---

# Relation Posture State

## Current Turn
- status: active
- updated_at: {evaluated_at}
- scene: {posture.scene}
- user_need: {posture.user_need}
- response_posture: {posture.response_posture}
- should_probe: {str(posture.should_probe).lower()}
- should_give_advice: {str(posture.should_give_advice).lower()}
- memory_action: {posture.memory_action}
- initiative_allowed: {posture.initiative_allowed}
- risk_level: {posture.risk_level}
- max_visible_chars: {posture.max_visible_chars}
- notes: {notes}

## Boundaries
- visible_labels: blocked
- mechanism_leak: blocked
- stable_memory_write: gated
- raw_private_body_retained: false
"""
    write_text_atomic(Path(root) / STATE_REL, text)


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker in text for marker in markers)


def _recent_assistant_question(dialogue_tail: list[dict[str, str]] | None) -> bool:
    if not dialogue_tail:
        return False
    for item in reversed(dialogue_tail[-3:]):
        if safe_str(item.get("role")) != "assistant":
            continue
        content = safe_str(item.get("content"))
        return "?" in content or "？" in content
    return False


def _behavior_contract_present(root: Path) -> bool:
    return bool(read_text(Path(root) / CONTRACT_REL).strip())


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()
