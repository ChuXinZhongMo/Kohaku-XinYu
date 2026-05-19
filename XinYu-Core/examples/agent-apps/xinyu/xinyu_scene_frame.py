from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


VALID_SCENES = {
    "project_work",
    "memory_review",
    "initiative_feedback",
    "runtime_status",
    "emotional_relation",
    "casual_chat",
}

PROJECT_WORK_KEYWORDS = (
    "\u4ee3\u7801",
    "\u6d4b\u8bd5",
    "\u5b9e\u73b0",
    "\u63a5\u5165",
    "\u6587\u4ef6",
    "\u67b6\u6784",
    "\u6a21\u5757",
    "\u9879\u76ee",
    "\u4fee",
    "\u6539",
    "plan",
    "test",
    "implement",
    "batch",
    "worklog",
)
MEMORY_REVIEW_KEYWORDS = (
    "\u8bb0\u5fc6",
    "\u9057\u5fd8",
    "\u68c0\u7d22",
    "\u53ec\u56de",
    "\u56de\u60f3",
    "\u65f6\u95f4",
    "memory",
    "recall",
    "retrieve",
)
INITIATIVE_FEEDBACK_KEYWORDS = (
    "\u4e3b\u52a8",
    "\u53cd\u9988",
    "\u6253\u6270",
    "initiative",
    "proactive",
    "feedback",
)
RUNTIME_STATUS_KEYWORDS = (
    "\u8fd0\u884c",
    "\u72b6\u6001",
    "\u4eea\u8868\u76d8",
    "runtime",
    "health",
    "metrics",
    "status",
)
EMOTIONAL_RELATION_KEYWORDS = (
    "\u5173\u7cfb",
    "\u60c5\u7eea",
    "\u96be\u53d7",
    "\u51b7\u6de1",
    "\u5931\u671b",
    "\u966a",
    "emotion",
    "relationship",
    "feel",
)
AFTER_NIGHT_SHIFT_KEYWORDS = (
    "\u521a\u4e0b\u591c\u73ed",
    "\u4e0b\u5b8c\u591c\u73ed",
    "\u591c\u73ed",
    "night shift",
)
LOW_ENERGY_KEYWORDS = (
    "\u56f0",
    "\u7d2f",
    "\u75b2\u60eb",
    "\u60f3\u7761",
    "\u7761\u4e00\u89c9",
    "\u8865\u89c9",
    "tired",
    "sleepy",
    "exhausted",
)
WAKE_KEYWORDS = (
    "\u521a\u9192",
    "\u521a\u7761\u9192",
    "\u7761\u9192",
    "\u9192\u4e86",
    "just woke",
    "woke up",
)
REST_KEYWORDS = (
    "\u5348\u7761",
    "\u7761\u89c9",
    "\u4f11\u606f",
    "\u8865\u89c9",
    "nap",
    "sleep",
    "rest",
)
EXPLICIT_RECALL_KEYWORDS = (
    "\u4e4b\u524d",
    "\u4e0a\u6b21",
    "\u521a\u624d",
    "\u8bb0\u5f97",
    "\u8fd8\u8bb0\u5f97",
    "\u8bf4\u8fc7",
    "previous",
    "earlier",
    "remember",
)


@dataclass(frozen=True, slots=True)
class SceneFrame:
    scene_id: str
    time_context: str
    owner_state: str
    task_mode: str
    memory_relation: str
    reply_policy: str
    uncertainty: str
    notes: tuple[str, ...] = ()


def build_scene_frame(
    root: Path,
    *,
    user_text: str = "",
    visible_turn: Any | None = None,
    contextual_scene: str = "",
    canonical_recall_context: str = "",
    evaluated_at: datetime | str | None = None,
) -> SceneFrame:
    del root
    text = _safe_text(user_text)
    recall_text = _safe_text(canonical_recall_context)
    scene_id = _scene_id(text, contextual_scene=contextual_scene, visible_turn=visible_turn)
    time_context = _time_context(text, recall_text=recall_text, evaluated_at=evaluated_at)
    owner_state = _owner_state(text, recall_text=recall_text, time_context=time_context)
    task_mode = _task_mode(scene_id, text)
    memory_relation = _memory_relation(text, recall_text=recall_text)
    reply_policy = _reply_policy(task_mode, owner_state, time_context)
    uncertainty = _uncertainty(owner_state, memory_relation)
    notes = (
        "scene_frame_v1",
        "advisory_only_current_owner_message_wins",
        "no_private_memory_body_output",
    )
    return SceneFrame(
        scene_id=scene_id,
        time_context=time_context,
        owner_state=owner_state,
        task_mode=task_mode,
        memory_relation=memory_relation,
        reply_policy=reply_policy,
        uncertainty=uncertainty,
        notes=notes,
    )


def render_scene_frame_prompt_block(frame: SceneFrame) -> str:
    lines = [
        "## Scene Frame",
        "purpose: compact current-scene routing before reply; advisory only, current owner message wins.",
        f"- scene_id: {frame.scene_id}",
        f"- time_context: {frame.time_context}",
        f"- owner_state: {frame.owner_state}",
        f"- task_mode: {frame.task_mode}",
        f"- memory_relation: {frame.memory_relation}",
        f"- reply_policy: {frame.reply_policy}",
        f"- uncertainty: {frame.uncertainty}",
    ]
    if frame.notes:
        lines.append("- notes: " + ", ".join(frame.notes))
    return "\n".join(lines).strip()


def _scene_id(text: str, *, contextual_scene: str, visible_turn: Any | None) -> str:
    if contextual_scene in VALID_SCENES:
        return contextual_scene
    turn_scene = _visible_turn_scene(visible_turn)
    if turn_scene in VALID_SCENES:
        return turn_scene
    if _has_any(text, RUNTIME_STATUS_KEYWORDS):
        return "runtime_status"
    if _has_any(text, INITIATIVE_FEEDBACK_KEYWORDS):
        return "initiative_feedback"
    if _has_any(text, EXPLICIT_RECALL_KEYWORDS):
        return "memory_review"
    if _has_any(text, MEMORY_REVIEW_KEYWORDS):
        return "memory_review"
    if _has_any(text, PROJECT_WORK_KEYWORDS):
        return "project_work"
    if _has_any(text, EMOTIONAL_RELATION_KEYWORDS):
        return "emotional_relation"
    return "casual_chat"


def _visible_turn_scene(visible_turn: Any | None) -> str:
    if visible_turn is None:
        return ""
    if _truthy_attr(visible_turn, "technical_work") or _truthy_attr(visible_turn, "technical_request"):
        return "project_work"
    if _truthy_attr(visible_turn, "relationship_pressure"):
        return "emotional_relation"
    for attr in ("scene_id", "scene", "turn_type", "mode"):
        value = getattr(visible_turn, attr, "")
        if isinstance(value, str) and value:
            normalized = value.strip().lower()
            if normalized in VALID_SCENES:
                return normalized
            if normalized in {"technical_work", "coding", "project"}:
                return "project_work"
            if normalized in {"daily_life", "ordinary_chat"}:
                return "casual_chat"
            if normalized in {"relationship_pressure", "emotion"}:
                return "emotional_relation"
    return ""


def _time_context(text: str, *, recall_text: str, evaluated_at: datetime | str | None) -> str:
    if _has_any(text, AFTER_NIGHT_SHIFT_KEYWORDS):
        return "after_night_shift"
    if "recent_wake_from_nap" in recall_text or _has_any(text, WAKE_KEYWORDS):
        return "recent_wake_from_rest"
    if _has_any(text, REST_KEYWORDS):
        return "rest_related"
    now = _coerce_datetime(evaluated_at)
    if now is not None and (now.hour >= 23 or now.hour < 6):
        return "late_night"
    return "ordinary_time"


def _owner_state(text: str, *, recall_text: str, time_context: str) -> str:
    if time_context in {"after_night_shift", "recent_wake_from_rest"} or _has_any(text, LOW_ENERGY_KEYWORDS):
        return "low_energy_or_tired"
    if _has_any(text, EMOTIONAL_RELATION_KEYWORDS):
        return "emotional_pressure_possible"
    if "recent_wake_from_nap" in recall_text:
        return "low_energy_or_tired"
    return "unknown_or_unstated"


def _task_mode(scene_id: str, text: str) -> str:
    if scene_id == "project_work":
        return "technical_execution"
    if scene_id == "memory_review":
        return "memory_review"
    if scene_id == "runtime_status":
        return "runtime_status"
    if scene_id == "initiative_feedback":
        return "initiative_feedback"
    if scene_id == "emotional_relation":
        return "relational_support"
    if _has_any(text, PROJECT_WORK_KEYWORDS):
        return "technical_execution"
    return "ordinary_chat"


def _memory_relation(text: str, *, recall_text: str) -> str:
    if "## temporal context" in recall_text.lower() or "temporal_inference:" in recall_text.lower():
        return "time_bound_recall"
    if _has_any(text, EXPLICIT_RECALL_KEYWORDS):
        return "explicit_recall_request"
    if "## recalled context" in recall_text.lower():
        return "recalled_continuity"
    return "current_turn_first"


def _reply_policy(task_mode: str, owner_state: str, time_context: str) -> str:
    low_burden = owner_state == "low_energy_or_tired" or time_context in {"after_night_shift", "recent_wake_from_rest"}
    if task_mode == "technical_execution":
        return "short_direct_low_burden" if low_burden else "direct_task_answer"
    if task_mode == "relational_support":
        return "warm_low_burden" if low_burden else "warm_boundary_aware"
    if low_burden:
        return "short_gentle_low_burden"
    if task_mode in {"memory_review", "runtime_status", "initiative_feedback"}:
        return "compact_structured_answer"
    return "compact_natural"


def _uncertainty(owner_state: str, memory_relation: str) -> str:
    parts = ["exact_owner_physical_state_not_observed"]
    if owner_state == "unknown_or_unstated":
        parts.append("owner_state_not_stated")
    if memory_relation == "current_turn_first":
        parts.append("no_time_bound_memory_used")
    return ",".join(parts)


def _coerce_datetime(value: datetime | str | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _truthy_attr(value: Any, attr: str) -> bool:
    return bool(getattr(value, attr, False))
