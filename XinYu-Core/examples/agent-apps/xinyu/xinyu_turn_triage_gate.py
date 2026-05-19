from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_turn_classifier import VisibleTurnContext, classify_visible_turn


ACTIVE_TASK_LANE = "active_task_continue"
DIRECT_MEMORY_LANE = "direct_memory_recall"
EMOTIONAL_LANE = "emotional_support"
RELATIONSHIP_LANE = "relationship_boundary"
PERMISSION_LANE = "permission_or_control"
REST_LANE = "rest_low_burden"
RUNTIME_FIX_LANE = "urgent_runtime_fix"
ORDINARY_LANE = "ordinary_chat"

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
RELATIONSHIP_KEYWORDS = (
    "\u5173\u7cfb",
    "\u60c5\u7eea",
    "\u96be\u53d7",
    "\u51b7\u6de1",
    "\u5931\u671b",
    "\u751f\u6c14",
    "\u5728\u4e4e",
    "\u9053\u6b49",
    "\u966a\u6211",
    "relationship",
    "emotion",
)
REST_KEYWORDS = (
    "\u56f0",
    "\u7d2f",
    "\u75b2\u60eb",
    "\u60f3\u7761",
    "\u521a\u9192",
    "\u5348\u7761",
    "\u4f11\u606f",
    "tired",
    "sleepy",
    "nap",
    "rest",
)
RUNTIME_FIX_KEYWORDS = (
    "\u62a5\u9519",
    "\u5931\u8d25",
    "\u5d29",
    "\u4fee\u590d",
    "\u9519\u8bef",
    "\u5148\u4fee",
    "error",
    "fail",
    "failed",
    "broken",
    "traceback",
    "runtime",
    "health",
)
ACTIVE_CONTEXT_KEYWORDS = (
    "batch",
    "worklog",
    "plan",
    "todo",
    "next step",
    "implementation",
    "test",
    "pytest",
    "smoke",
    "dod",
    "cross-domain",
    "synaesthesia",
    "\u8ba1\u5212",
    "\u5de5\u4f5c\u65e5\u5fd7",
    "\u5b9e\u73b0",
    "\u6d4b\u8bd5",
    "\u7ee7\u7eed",
)
ACTIVE_TEXT_KEYWORDS = (
    "\u5b9e\u73b0",
    "\u6d4b\u8bd5",
    "\u4fee",
    "\u6539",
    "\u9879\u76ee",
    "\u4ee3\u7801",
    "\u6846\u67b6",
    "implement",
    "test",
    "project",
    "code",
    "batch",
    "worklog",
    "plan",
)
PERMISSION_KEYWORDS = (
    "\u6743\u9650",
    "\u81ea\u52a8",
    "\u4e0d\u8981\u95ee",
    "\u76f4\u63a5\u7ee7\u7eed",
    "\u76f4\u5230\u5b8c\u6210",
    "permission",
    "autonomous",
    "continue without asking",
)
CONTINUE_COMMANDS = {
    "\u7ee7\u7eed",
    "\u7ee7\u7eed\u505a",
    "\u7ee7\u7eed\u6267\u884c",
    "\u63a5\u7740",
    "\u63a5\u4e0b\u6765",
    "\u4e0b\u4e00\u6b65",
    "\u5f00\u59cb",
    "\u597d",
    "\u597d\u7684",
    "\u597d\u7ee7\u7eed",
    "\u597d\u5f00\u59cb",
    "\u6309\u8ba1\u5212\u7ee7\u7eed",
}


@dataclass(frozen=True, slots=True)
class TurnTriageDecision:
    primary_lane: str
    secondary_lanes: tuple[str, ...]
    priority_reason: str
    owner_directive: str
    current_task_policy: str
    memory_policy: str
    tool_policy: str
    reply_policy: str
    uncertainty: str
    notes: tuple[str, ...] = ()


def triage_turn(
    root: Path,
    *,
    user_text: str = "",
    payload: dict[str, Any] | None = None,
    visible_turn: VisibleTurnContext | Any | None = None,
    scene_frame: Any | None = None,
    recent_work_context: str = "",
    canonical_recall_context: str = "",
    evaluated_at: Any | None = None,
) -> TurnTriageDecision:
    del evaluated_at
    text = _safe_text(user_text)
    visible = visible_turn or _classify_visible(root, payload=payload, user_text=text)
    text_has_active_work = _has_any(text, ACTIVE_TEXT_KEYWORDS)
    active_context = text_has_active_work or _has_active_task_context(
        visible=visible,
        scene_frame=scene_frame,
        recent_work_context=recent_work_context,
        canonical_recall_context=canonical_recall_context,
    )
    short_continue = _is_short_continue_command(text)
    rest = _is_rest_context(text, visible=visible, scene_frame=scene_frame, canonical_recall_context=canonical_recall_context)
    explicit_recall = _has_any(text, EXPLICIT_RECALL_KEYWORDS) or _scene_value(scene_frame, "memory_relation") == "explicit_recall_request"
    relationship = _is_relationship_context(text, visible=visible, scene_frame=scene_frame)
    runtime_fix = _is_runtime_fix_context(text, visible=visible, scene_frame=scene_frame)
    permission = _has_any(text, PERMISSION_KEYWORDS)

    secondary: list[str] = []
    if rest:
        secondary.append(REST_LANE)
    if permission:
        secondary.append(PERMISSION_LANE)
    if relationship:
        secondary.append(RELATIONSHIP_LANE)

    if runtime_fix and _has_error_signal(text):
        return _decision(
            primary_lane=RUNTIME_FIX_LANE,
            secondary_lanes=secondary,
            priority_reason="runtime_error_or_health_signal_before_optional_work",
            owner_directive="fix_or_stabilize_runtime",
            current_task_policy="fix_current_failure_before_feature_work",
            memory_policy="use_canonical_recall_only_for_relevant_runtime_context",
            tool_policy="tools_allowed_for_diagnosis_and_focused_fix",
            reply_policy="short_status_then_action",
            uncertainty="exact_runtime_failure_requires_local_validation",
        )

    if explicit_recall:
        return _decision(
            primary_lane=DIRECT_MEMORY_LANE,
            secondary_lanes=secondary,
            priority_reason="owner_explicitly_requested_prior_context",
            owner_directive="recall_before_new_action",
            current_task_policy="answer_recall_before_expanding_scope",
            memory_policy="use_canonical_living_memory_recall",
            tool_policy="no_tool_action_until_recall_need_is_satisfied",
            reply_policy="compact_recall_then_current_answer",
            uncertainty="retrieved_context_may_be_incomplete",
        )

    if relationship and not active_context:
        primary = RELATIONSHIP_LANE if _visible_bool(visible, "relationship_pressure") else EMOTIONAL_LANE
        return _decision(
            primary_lane=primary,
            secondary_lanes=secondary,
            priority_reason="relational_or_emotional_pressure_outranks_optional_expansion",
            owner_directive="stabilize_relation_or_emotion",
            current_task_policy="do_not_hide_emotional_pressure_behind_project_work",
            memory_policy="no_durable_write_without_meaningful_residue",
            tool_policy="avoid_tools_unless_owner_explicitly_requests_work",
            reply_policy="warm_boundary_aware_short",
            uncertainty="emotional_state_is_inferred_from_current_text",
        )

    if active_context and (short_continue or text_has_active_work or permission or _scene_task_mode(scene_frame) in {"technical_execution", "runtime_status"}):
        return _decision(
            primary_lane=ACTIVE_TASK_LANE,
            secondary_lanes=secondary,
            priority_reason="owner_short_command_resolves_against_pending_work_context",
            owner_directive=_owner_directive_for_active(short_continue=short_continue, permission=permission),
            current_task_policy="resume_without_reasking",
            memory_policy="use_canonical_recall_only_if_needed_for_task_continuity",
            tool_policy="tools_allowed_for_focused_batch",
            reply_policy="short_direct_progress_update" if rest else "direct_task_answer",
            uncertainty="pending_task_context_is_advisory_current_text_still_wins",
        )

    if rest:
        return _decision(
            primary_lane=REST_LANE,
            secondary_lanes=secondary,
            priority_reason="owner_low_energy_or_rest_context",
            owner_directive="lower_visible_burden",
            current_task_policy="avoid_new_scope_unless_explicit",
            memory_policy="normally_no_durable_write",
            tool_policy="no_tools_unless_owner_explicitly_requests_work",
            reply_policy="short_gentle_low_burden",
            uncertainty="physical_state_not_directly_observed",
        )

    return _decision(
        primary_lane=ORDINARY_LANE,
        secondary_lanes=secondary,
        priority_reason="no_higher_priority_lane_detected",
        owner_directive="answer_current_turn",
        current_task_policy="do_not_invent_pending_work",
        memory_policy="selective_recall_only_when_needed",
        tool_policy="no_tools_unless_task_requires_it",
        reply_policy="compact_natural",
        uncertainty="no_scene_specific_signal",
    )


def render_turn_triage_prompt_block(decision: TurnTriageDecision) -> str:
    lines = [
        "## Turn Triage Gate",
        "purpose: advisory current-turn priority before recall/tool/action; current owner message wins.",
        f"- primary_lane: {decision.primary_lane}",
        f"- secondary_lanes: {', '.join(decision.secondary_lanes) if decision.secondary_lanes else 'none'}",
        f"- priority_reason: {decision.priority_reason}",
        f"- owner_directive: {decision.owner_directive}",
        f"- current_task_policy: {decision.current_task_policy}",
        f"- memory_policy: {decision.memory_policy}",
        f"- tool_policy: {decision.tool_policy}",
        f"- reply_policy: {decision.reply_policy}",
        f"- uncertainty: {decision.uncertainty}",
    ]
    if decision.notes:
        lines.append("- notes: " + ", ".join(decision.notes))
    return "\n".join(lines).strip()


def _decision(
    *,
    primary_lane: str,
    secondary_lanes: list[str],
    priority_reason: str,
    owner_directive: str,
    current_task_policy: str,
    memory_policy: str,
    tool_policy: str,
    reply_policy: str,
    uncertainty: str,
) -> TurnTriageDecision:
    ordered_secondary = tuple(lane for lane in dict.fromkeys(secondary_lanes) if lane != primary_lane)
    return TurnTriageDecision(
        primary_lane=primary_lane,
        secondary_lanes=ordered_secondary,
        priority_reason=priority_reason,
        owner_directive=owner_directive,
        current_task_policy=current_task_policy,
        memory_policy=memory_policy,
        tool_policy=tool_policy,
        reply_policy=reply_policy,
        uncertainty=uncertainty,
        notes=(
            "medical_triage_mapping",
            "advisory_only_current_owner_message_wins",
            "no_private_memory_body_output",
        ),
    )


def _classify_visible(root: Path, *, payload: dict[str, Any] | None, user_text: str) -> VisibleTurnContext | None:
    try:
        return classify_visible_turn(root, payload=payload, user_text=user_text)
    except Exception:
        return None


def _has_active_task_context(
    *,
    visible: Any | None,
    scene_frame: Any | None,
    recent_work_context: str,
    canonical_recall_context: str,
) -> bool:
    if _visible_bool(visible, "technical_work"):
        return True
    if _scene_value(scene_frame, "scene_id") in {"project_work", "runtime_status"}:
        return True
    if _scene_task_mode(scene_frame) in {"technical_execution", "runtime_status"}:
        return True
    combined = f"{_safe_text(recent_work_context)}\n{_safe_text(canonical_recall_context)}"
    return _has_any(combined, ACTIVE_CONTEXT_KEYWORDS)


def _is_runtime_fix_context(text: str, *, visible: Any | None, scene_frame: Any | None) -> bool:
    if _scene_value(scene_frame, "scene_id") == "runtime_status" or _scene_task_mode(scene_frame) == "runtime_status":
        return True
    if _visible_bool(visible, "technical_work") and _has_any(text, RUNTIME_FIX_KEYWORDS):
        return True
    return _has_any(text, RUNTIME_FIX_KEYWORDS)


def _has_error_signal(text: str) -> bool:
    return _has_any(
        text,
        (
            "\u62a5\u9519",
            "\u5931\u8d25",
            "\u5d29",
            "\u4fee\u590d",
            "\u9519\u8bef",
            "\u5148\u4fee",
            "error",
            "fail",
            "failed",
            "broken",
            "traceback",
        ),
    )


def _is_rest_context(
    text: str,
    *,
    visible: Any | None,
    scene_frame: Any | None,
    canonical_recall_context: str,
) -> bool:
    if _visible_bool(visible, "rest_silence"):
        return True
    if _scene_value(scene_frame, "owner_state") == "low_energy_or_tired":
        return True
    if _scene_value(scene_frame, "time_context") in {"after_night_shift", "recent_wake_from_rest", "rest_related"}:
        return True
    if "recent_wake_from_nap" in _safe_text(canonical_recall_context).lower():
        return True
    return _has_any(text, REST_KEYWORDS)


def _is_relationship_context(text: str, *, visible: Any | None, scene_frame: Any | None) -> bool:
    if _visible_bool(visible, "relationship_pressure"):
        return True
    if _scene_task_mode(scene_frame) == "relational_support":
        return True
    if _scene_value(scene_frame, "scene_id") == "emotional_relation":
        return True
    return _has_any(text, RELATIONSHIP_KEYWORDS)


def _owner_directive_for_active(*, short_continue: bool, permission: bool) -> str:
    if permission:
        return "autonomous_continue_within_plan"
    if short_continue:
        return "continue_pending_task"
    return "execute_current_task"


def _is_short_continue_command(text: str) -> bool:
    compact = _compact_command(text)
    if compact in CONTINUE_COMMANDS:
        return True
    return compact.startswith("\u6309\u8ba1\u5212") and "\u7ee7\u7eed" in compact


def _compact_command(text: str) -> str:
    stripped = _safe_text(text).strip().lower()
    remove_chars = " \t\r\n,.;:!?，。；：！？、~"
    for char in remove_chars:
        stripped = stripped.replace(char, "")
    return stripped


def _scene_task_mode(scene_frame: Any | None) -> str:
    return _scene_value(scene_frame, "task_mode")


def _scene_value(scene_frame: Any | None, attr: str) -> str:
    value = getattr(scene_frame, attr, "")
    return value.strip().lower() if isinstance(value, str) else ""


def _visible_bool(visible: Any | None, attr: str) -> bool:
    return bool(getattr(visible, attr, False)) if visible is not None else False


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = _safe_text(text).lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)
