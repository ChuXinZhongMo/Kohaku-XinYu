from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_answer_discipline_visible_guard import evaluate_visible_reply_for_answer_discipline
from xinyu_turn_classifier import VisibleTurnContext, classify_visible_turn
from xinyu_visible_reply_guard import dedupe_visible_reply


NO_ERROR = "none"
BLANK_REPLY = "blank_reply"
INTERNAL_LABEL_LEAK = "internal_label_leak"
UNSUPPORTED_RECALL_CLAIM = "unsupported_recall_claim"
DUPLICATE_VISIBLE_REPLY = "duplicate_visible_reply"
TEMPLATE_REPLY_MISMATCH = "template_reply_mismatch"
STYLE_SURFACE_FAILURE = "style_surface_failure"
OVEREXPLAINED_REPAIR = "overexplained_repair"
TASK_NOT_EXECUTED = "task_not_executed"
STALE_CONTEXT_OVERRIDE = "stale_context_override"
RELATIONSHIP_MISREAD = "relationship_misread"

STYLE_CORRECTION_KEYWORDS = (
    "ai",
    "gpt",
    "\u4e0d\u50cf\u4eba",
    "\u4e0d\u81ea\u7136",
    "\u673a\u68b0",
    "\u6a21\u677f",
    "\u5ba2\u670d",
    "\u63a5\u5f85",
    "\u9ed8\u8ba4\u8154",
    "\u50cfai",
    "\u50cf ai",
)
OVEREXPLAIN_KEYWORDS = (
    "\u522b\u590d\u76d8",
    "\u4e0d\u8981\u590d\u76d8",
    "\u522b\u89e3\u91ca",
    "\u5c11\u89e3\u91ca",
    "\u89e3\u91ca\u592a\u591a",
    "\u522b\u627f\u8bfa",
    "\u4e0d\u8981\u627f\u8bfa",
    "\u627f\u8bfa\u6ca1\u7528",
    "do not explain",
    "stop explaining",
    "no promises",
)
TASK_FAILURE_KEYWORDS = (
    "\u4e3a\u4ec0\u4e48\u4e0d\u6309\u8ba1\u5212",
    "\u4e0d\u6309\u8ba1\u5212",
    "\u6ca1\u505a\u5b8c",
    "\u6ca1\u5b8c\u6210",
    "\u53ea\u5199\u8ba1\u5212",
    "\u4e0d\u8981\u53ea\u5199\u8ba1\u5212",
    "\u4e3a\u4ec0\u4e48\u505c",
    "not following the plan",
    "only wrote a plan",
)
STALE_CONTEXT_KEYWORDS = (
    "\u4e0d\u662f\u4e4b\u524d",
    "\u522b\u62ff\u65e7\u7684",
    "\u5f53\u524d\u8fd9\u53e5",
    "\u521a\u624d\u8bf4\u7684",
    "\u4f60\u6ca1\u770b\u5f53\u524d",
    "current message",
    "stale context",
)
RELATIONSHIP_KEYWORDS = (
    "\u5173\u7cfb",
    "\u96be\u53d7",
    "\u5931\u671b",
    "\u751f\u6c14",
    "\u5728\u4e4e",
    "\u966a\u6211",
)
PRODUCT_REPLY_KEYWORDS = (
    "\u7528\u6237",
    "\u53cd\u9988",
    "\u4f53\u9a8c",
    "\u4f18\u5316",
    "\u7cfb\u7edf",
    "\u8f93\u51fa",
    "user feedback",
    "optimize",
)
PROMISE_REPLY_KEYWORDS = (
    "\u6211\u4f1a\u6539",
    "\u4ee5\u540e\u6211\u4f1a",
    "\u4e0b\u6b21\u6211\u4f1a",
    "\u6211\u4f1a\u8bb0\u4f4f",
    "i will improve",
    "next time i will",
)


@dataclass(frozen=True, slots=True)
class ResponseErrorLoopDecision:
    error_class: str
    severity: str
    observed_signal: str
    correction_path: str
    next_turn_policy: str
    memory_policy: str
    retry_policy: str
    stability_policy: str
    owner_visible_reply_policy: str
    notes: tuple[str, ...] = ()

    @property
    def has_error(self) -> bool:
        return self.error_class != NO_ERROR


def classify_response_error(
    root: Path,
    *,
    user_text: str = "",
    previous_visible_reply: str = "",
    current_candidate_reply: str = "",
    payload: dict[str, Any] | None = None,
    visible_turn: VisibleTurnContext | Any | None = None,
    triage_decision: Any | None = None,
    answer_discipline_result: dict[str, Any] | None = None,
    answer_guard_result: Any | None = None,
    dedupe_result: Any | None = None,
) -> ResponseErrorLoopDecision:
    text = _safe_text(user_text)
    reply = _safe_text(current_candidate_reply or previous_visible_reply)
    visible = visible_turn or _classify_visible(root, payload=payload, user_text=text)
    guard = answer_guard_result or _answer_guard(reply, answer_discipline_result)
    flags = _guard_flags(guard)

    if flags.get("blank_reply"):
        return _decision(
            error_class=BLANK_REPLY,
            severity="high",
            observed_signal="visible_guard_blank_reply",
            correction_path="regenerate_minimal_current_turn_answer",
            next_turn_policy="do_not_explain_failure_before_answering",
            memory_policy="no_durable_write",
            retry_policy="single_retry_with_short_current_answer",
            stability_policy="no_persona_or_memory_change",
            owner_visible_reply_policy="one_direct_replacement_reply",
        )
    if flags.get("leaked_internal_label"):
        return _decision(
            error_class=INTERNAL_LABEL_LEAK,
            severity="high",
            observed_signal="visible_guard_internal_label_or_path_leak",
            correction_path="strip_internal_metadata_and_answer_surface_only",
            next_turn_policy="do_not_mention_gates_hashes_files_or_scores",
            memory_policy="no_durable_write",
            retry_policy="rewrite_without_internal_labels",
            stability_policy="guard_visible_surface_not_identity",
            owner_visible_reply_policy="plain_owner_facing_reply_only",
        )
    if flags.get("unsupported_history_claim") or flags.get("overconfident_without_evidence"):
        return _decision(
            error_class=UNSUPPORTED_RECALL_CLAIM,
            severity="high",
            observed_signal="answer_discipline_history_overclaim",
            correction_path="acknowledge_uncertainty_then_use_only_supported_recall",
            next_turn_policy="current_owner_message_wins_over_unverified_history",
            memory_policy="use_canonical_recall_only_no_fact_write",
            retry_policy="answer_current_turn_with_evidence_boundary",
            stability_policy="do_not_strengthen_stale_memory",
            owner_visible_reply_policy="compact_uncertain_recall_or_current_answer",
        )
    if flags.get("template_like_casual_reply"):
        return _decision(
            error_class=TEMPLATE_REPLY_MISMATCH,
            severity="medium",
            observed_signal="answer_discipline_template_in_casual_context",
            correction_path="drop_missing-evidence_template_for_ordinary_chat",
            next_turn_policy="answer_normally_when_no_recall_pressure",
            memory_policy="no_durable_write",
            retry_policy="replace_with_current_message_reply",
            stability_policy="avoid_global_voice_change_from_one_case",
            owner_visible_reply_policy="short_natural_reply",
        )

    dedupe = dedupe_result or _dedupe(reply)
    if bool(getattr(dedupe, "changed", False)):
        return _decision(
            error_class=DUPLICATE_VISIBLE_REPLY,
            severity="medium",
            observed_signal="visible_reply_duplicate_unit",
            correction_path="use_deduped_reply_or_regenerate_once",
            next_turn_policy="avoid_repeating_same_visible_unit",
            memory_policy="no_durable_write",
            retry_policy="dedupe_before_visible_send",
            stability_policy="output_filter_only",
            owner_visible_reply_policy="single_clean_reply",
        )

    if _has_any(text, TASK_FAILURE_KEYWORDS):
        return _decision(
            error_class=TASK_NOT_EXECUTED,
            severity="high",
            observed_signal="owner_reports_plan_or_execution_gap",
            correction_path="resume_execution_before_postmortem",
            next_turn_policy="state_current_batch_action_then_do_it",
            memory_policy="write_worklog_recovery_point_not_stable_memory",
            retry_policy="execute_small_focused_batch",
            stability_policy="do_not_convert_execution_gap_into_persona_change",
            owner_visible_reply_policy="short_status_plus_next_action",
        )
    if _has_any(text, STALE_CONTEXT_KEYWORDS):
        return _decision(
            error_class=STALE_CONTEXT_OVERRIDE,
            severity="high",
            observed_signal="owner_says_current_turn_was_overridden_by_old_context",
            correction_path="discard_conflicting_old_context_for_this_turn",
            next_turn_policy="current_owner_text_has_priority",
            memory_policy="treat_as_review_candidate_only_if_repeated",
            retry_policy="answer_current_text_without_old_assumption",
            stability_policy="do_not_delete_old_memory_from_one_conflict",
            owner_visible_reply_policy="correct_current_turn_directly",
        )
    if _is_style_failure(text, visible=visible):
        repair_class = OVEREXPLAINED_REPAIR if _has_any(text, OVEREXPLAIN_KEYWORDS) else STYLE_SURFACE_FAILURE
        return _decision(
            error_class=repair_class,
            severity="high",
            observed_signal="owner_style_or_repair_pressure",
            correction_path="make_the_next_reply_itself_different",
            next_turn_policy="do_not_answer_with_self_diagnosis_or_future_promise",
            memory_policy="voice_review_candidate_only_no_stable_profile_write",
            retry_policy="short_present_tense_replacement",
            stability_policy="avoid_overcorrecting_global_persona",
            owner_visible_reply_policy="short_specific_less_polished",
        )
    if _has_any(text, OVEREXPLAIN_KEYWORDS) or (_has_any(reply, PROMISE_REPLY_KEYWORDS) and _owner_pressure(text)):
        return _decision(
            error_class=OVEREXPLAINED_REPAIR,
            severity="medium",
            observed_signal="owner_rejects_explanation_or_empty_promise",
            correction_path="stop_repair_report_and_answer_current_fact",
            next_turn_policy="do_not_answer_with_self_diagnosis_or_future_promise",
            memory_policy="no_stable_write_review_only_if_repeated",
            retry_policy="one_short_replacement_no_promise",
            stability_policy="do_not_make_new_identity_claim",
            owner_visible_reply_policy="present_tense_repair_by_action",
        )
    if _has_any(text, RELATIONSHIP_KEYWORDS) and _has_any(reply, PRODUCT_REPLY_KEYWORDS):
        return _decision(
            error_class=RELATIONSHIP_MISREAD,
            severity="high",
            observed_signal="relationship_pressure_answered_as_product_feedback",
            correction_path="answer_relationship_pressure_as_relation_not_support_ticket",
            next_turn_policy="warm_direct_boundary_aware",
            memory_policy="relationship_residue_review_only_if_meaningful",
            retry_policy="short_relational_reply",
            stability_policy="no_stable_relationship_rewrite_from_one_turn",
            owner_visible_reply_policy="owner_private_wording_not_customer_service",
        )

    triage_lane = _safe_text(getattr(triage_decision, "primary_lane", ""))
    if triage_lane:
        observed = f"triage_lane:{triage_lane}"
    else:
        observed = "no_visible_failure_signal"
    return _decision(
        error_class=NO_ERROR,
        severity="none",
        observed_signal=observed,
        correction_path="no_error_loop_action",
        next_turn_policy="continue_current_policy",
        memory_policy="unchanged",
        retry_policy="no_retry_needed",
        stability_policy="unchanged",
        owner_visible_reply_policy="unchanged",
    )


def render_response_error_loop_prompt_block(decision: ResponseErrorLoopDecision) -> str:
    lines = [
        "## Response Error Loop",
        "purpose: visible feedback control; classify the failure and choose the next correction path without exposing raw private text.",
        f"- error_class: {decision.error_class}",
        f"- severity: {decision.severity}",
        f"- observed_signal: {decision.observed_signal}",
        f"- correction_path: {decision.correction_path}",
        f"- next_turn_policy: {decision.next_turn_policy}",
        f"- memory_policy: {decision.memory_policy}",
        f"- retry_policy: {decision.retry_policy}",
        f"- stability_policy: {decision.stability_policy}",
        f"- owner_visible_reply_policy: {decision.owner_visible_reply_policy}",
    ]
    if decision.notes:
        lines.append("- notes: " + ", ".join(decision.notes))
    return "\n".join(lines).strip()


def _decision(
    *,
    error_class: str,
    severity: str,
    observed_signal: str,
    correction_path: str,
    next_turn_policy: str,
    memory_policy: str,
    retry_policy: str,
    stability_policy: str,
    owner_visible_reply_policy: str,
) -> ResponseErrorLoopDecision:
    return ResponseErrorLoopDecision(
        error_class=error_class,
        severity=severity,
        observed_signal=observed_signal,
        correction_path=correction_path,
        next_turn_policy=next_turn_policy,
        memory_policy=memory_policy,
        retry_policy=retry_policy,
        stability_policy=stability_policy,
        owner_visible_reply_policy=owner_visible_reply_policy,
        notes=(
            "control_theory_feedback_mapping",
            "advisory_only_next_turn_policy",
            "no_private_memory_body_output",
        ),
    )


def _classify_visible(root: Path, *, payload: dict[str, Any] | None, user_text: str) -> VisibleTurnContext | None:
    try:
        return classify_visible_turn(root, payload=payload, user_text=user_text)
    except Exception:
        return None


def _answer_guard(reply: str, result: dict[str, Any] | None) -> Any | None:
    if not result:
        return None
    try:
        return evaluate_visible_reply_for_answer_discipline(reply, result)
    except Exception:
        return None


def _dedupe(reply: str) -> Any | None:
    if not reply.strip():
        return None
    try:
        return dedupe_visible_reply(reply)
    except Exception:
        return None


def _guard_flags(guard: Any | None) -> dict[str, bool]:
    if guard is None:
        return {}
    raw = guard.get("flags") if isinstance(guard, dict) else getattr(guard, "flags", {})
    if not isinstance(raw, dict):
        return {}
    return {str(key): bool(value) for key, value in raw.items()}


def _is_style_failure(text: str, *, visible: Any | None) -> bool:
    if bool(getattr(visible, "owner_style_pressure", False)):
        return True
    if bool(getattr(visible, "owner_no_change_pressure", False)):
        return True
    return _has_any(text, STYLE_CORRECTION_KEYWORDS)


def _owner_pressure(text: str) -> bool:
    return _has_any(text, STYLE_CORRECTION_KEYWORDS + OVEREXPLAIN_KEYWORDS + RELATIONSHIP_KEYWORDS)


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = _safe_text(text).lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)
