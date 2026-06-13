from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_proactivity_scorer import (
    ProactiveDecision,
    candidate_signature,
    collect_proactive_candidates,
    decide_proactive_candidate,
    score_proactive_candidate,
)
from xinyu_proactive_contract import (
    desktop_focus_label,
    proactive_source_is_urgent,
    should_surface_desktop_item,
)


EVENTS_REL = Path("runtime/initiative_lifecycle_events.jsonl")
METRICS_REL = Path("runtime/initiative_metrics.json")
STATE_REL = Path("memory/context/initiative_lifecycle_state.md")
FEEDBACK_STATE_REL = Path("memory/context/initiative_feedback_state.md")
CONTEXTUAL_SELF_STATE_REL = Path("memory/context/contextual_self_loop_state.md")
CONTEXTUAL_RECALL_STATE_REL = Path("memory/context/contextual_recall_state.md")
RECENT_SCAN_LINES = 300
DEFAULT_EXPIRES_SECONDS = 12 * 60 * 60
METRICS_WINDOW_HOURS = 24
GENTLE_CONTEXT_BYPASS_MIN_SCORE = 52
SUBSTANTIVE_CONTEXT_BYPASS_MIN_SCORE = 75
SUBSTANTIVE_CONTEXT_BYPASS_SOURCE_TYPES = {
    "runtime_error",
    "task_done",
    "task_failed",
}
QQ_ONLY_OUTWARD_BLOCKS = {
    "qq_send_disabled_for_dream_v0",
    "qq_send_disabled_for_owner_long_idle_v0",
}
FINAL_FEEDBACK_STATUSES = {
    "dismiss",
    "dismissed",
    "read_locally",
    "reply",
    "replied",
    "approve_qq",
    "approved_qq",
    "sent",
    "failed",
    "expired",
}


def run_initiative_orchestrator(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    delivery_level: str = "desktop_inbox",
    dry_run: bool = False,
    max_candidates: int = 8,
) -> dict[str, Any]:
    root = root.resolve()
    checked_at = _timestamp_or_now_iso(checked_at)
    trigger = _one_line(trigger or "manual", limit=80)
    requested_delivery = _one_line(delivery_level or "desktop_inbox", limit=80)
    feedback = _load_feedback_index(root)
    context_gate = _load_context_gate(root, observed_at=checked_at)
    previous_signatures = _load_recent_signatures(root / EVENTS_REL)
    candidates = collect_proactive_candidates(root, checked_at=checked_at)
    if not candidates:
        event = _base_event(
            checked_at=checked_at,
            trigger=trigger,
            stage="decision",
            status="no_candidates",
        )
        event["candidate_count"] = 0
        event["decision_count"] = 0
        event["gate"] = {
            "decision": "hold_private",
            "blocked_by": [],
            "positive_reasons": [],
            "negative_reasons": ["no_candidates"],
        }
        event["delivery"] = {"level": "none", "desktop_candidate_id": "", "claimable": False}
        event["context_gate"] = context_gate
        _append_event(root, event)
        _write_state(
            root,
            checked_at=checked_at,
            trigger=trigger,
            candidate_count=0,
            decision_count=0,
            selected=None,
            gate_decision="hold_private",
            blocked_by=[],
            held_by=["no_candidates"],
            delivery_level="none",
            feedback_pending_count=_pending_feedback_count(root, observed_at=checked_at),
            context_gate=context_gate,
            notes=["no_candidates"],
        )
        _write_metrics(root, observed_at=checked_at)
        return {
            "accepted": True,
            "status": "no_candidates",
            "checked_at": checked_at,
            "candidate_count": 0,
            "decision_count": 0,
            "delivery_level": "none",
            "desktop_item": {},
            "notes": ["no_candidates"],
        }

    decisions: list[ProactiveDecision] = []
    for candidate in candidates[: max(1, int(max_candidates))]:
        score = score_proactive_candidate(
            candidate,
            checked_at=checked_at,
            previous_signatures=previous_signatures,
        )
        score = _apply_feedback_bias(candidate, score, feedback=feedback)
        decisions.append(decide_proactive_candidate(candidate, score, checked_at=checked_at))
    decisions.sort(key=_decision_sort_key, reverse=True)
    selected = decisions[0]
    gate = _gate_decision(selected, feedback=feedback, requested_delivery=requested_delivery)
    gate = _apply_context_gate(selected, gate, context_gate=context_gate)
    desktop_item = (
        _desktop_item_from_decision(selected, gate=gate, checked_at=checked_at)
        if gate["decision"] == "desktop_inbox" and not dry_run
        else {}
    )
    lifecycle_event = _event_from_decision(
        selected,
        checked_at=checked_at,
        trigger=trigger,
        candidate_count=len(candidates),
        decision_count=len(decisions),
        gate=gate,
        context_gate=context_gate,
        desktop_item=desktop_item,
        dry_run=dry_run,
    )
    _append_event(root, lifecycle_event)
    _write_state(
        root,
        checked_at=checked_at,
        trigger=trigger,
        candidate_count=len(candidates),
        decision_count=len(decisions),
        selected=selected,
        gate_decision=gate["decision"],
        blocked_by=list(gate["blocked_by"]),
        held_by=list(gate["held_by"]),
        delivery_level=_safe_str(lifecycle_event.get("delivery", {}).get("level"), "none"),
        feedback_pending_count=_pending_feedback_count(root, observed_at=checked_at),
        context_gate=context_gate,
        notes=["dry_run"] if dry_run else [],
    )
    result = {
        "accepted": True,
        "status": gate["decision"],
        "checked_at": checked_at,
        "candidate_count": len(candidates),
        "decision_count": len(decisions),
        "candidate_id": selected.candidate_id,
        "source_type": selected.source_type,
        "intent_type": selected.intent_type,
        "total_score": selected.total_score,
        "recommendation": selected.recommendation,
        "preferred_channel": selected.preferred_channel,
        "delivery_level": _safe_str(lifecycle_event.get("delivery", {}).get("level"), "none"),
        "desktop_item": desktop_item,
        "hard_blocks": list(selected.hard_blocks),
        "reasons_positive": list(selected.reasons_positive),
        "reasons_negative": list(gate["negative_reasons"]),
        "context_gate": context_gate,
        "notes": list(gate["notes"]) + (["dry_run"] if dry_run else []),
    }
    _write_metrics(root, observed_at=checked_at)
    return result


def record_initiative_feedback(
    root: Path,
    *,
    candidate_id: str,
    action: str,
    feedback_at: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    candidate_id = _one_line(candidate_id, limit=160)
    action = _normalize_feedback_action(action)
    feedback_at = _timestamp_or_now_iso(feedback_at)
    if not candidate_id:
        return {"accepted": False, "recorded": False, "notes": ["missing_candidate_id"]}
    if action not in FINAL_FEEDBACK_STATUSES:
        return {"accepted": False, "recorded": False, "candidate_id": candidate_id, "notes": ["invalid_action"]}
    latest = _latest_event_for_candidate(root, candidate_id)
    event = _base_event(checked_at=feedback_at, trigger="desktop_ack", stage="feedback", status=action)
    event.update(
        {
            "candidate_id": candidate_id,
            "source_type": _safe_str(latest.get("source_type"), "unknown"),
            "intent_type": _safe_str(latest.get("intent_type"), "unknown"),
            "candidate_signature": _safe_str(latest.get("candidate_signature"), ""),
            "feedback": {
                "status": action,
                "feedback_event_id": event["event_id"],
                "details": _clean_json_value(details or {}),
            },
        }
    )
    _append_event(root, event)
    _write_feedback_state(root, feedback_at=feedback_at, candidate_id=candidate_id, action=action, latest=latest)
    _write_metrics(root, observed_at=feedback_at)
    return {
        "accepted": True,
        "recorded": True,
        "candidate_id": candidate_id,
        "action": action,
        "feedback_event_id": event["event_id"],
        "notes": ["initiative_feedback_recorded"],
    }


def _gate_decision(
    decision: ProactiveDecision,
    *,
    feedback: dict[str, dict[str, Any]],
    requested_delivery: str,
) -> dict[str, Any]:
    signature = decision.candidate_signature or candidate_signature(decision.candidate)
    blocked_by = [block for block in decision.hard_blocks if block not in QQ_ONLY_OUTWARD_BLOCKS]
    held_by: list[str] = []
    notes: list[str] = [block for block in decision.hard_blocks if block in QQ_ONLY_OUTWARD_BLOCKS]
    visible = f"{decision.candidate.owner_visible_text} {decision.content_preview}".lower()
    if "[redacted-" in visible:
        blocked_by.append("owner_visible_text_redacted_sensitive")
    previous = feedback.get(signature) or feedback.get(decision.candidate_id) or {}
    previous_status = _safe_str(previous.get("status")).lower()
    if previous_status in {"dismiss", "dismissed", "owner_negative", "failed"}:
        held_by.append(f"recent_feedback_{previous_status}")
    if not should_surface_desktop_item(
        source_type=decision.source_type,
        intent_type=decision.intent_type,
        source_ref=decision.candidate.source_ref,
    ):
        held_by.append("desktop_visibility_internal_only")
    if decision.recommendation == "drop":
        blocked_by.append("scorer_drop")
    if decision.recommendation == "hold" or decision.preferred_channel == "silent":
        held_by.append("scorer_hold")
    hold_blocks = [block for block in blocked_by if block.endswith("_hold")]
    if hold_blocks:
        held_by.extend(hold_blocks)
        blocked_by = [block for block in blocked_by if not block.endswith("_hold")]
    if blocked_by:
        gate_decision = "blocked"
    elif held_by:
        gate_decision = "hold_private"
    elif requested_delivery in {"desktop_inbox", "show_desktop", "state_only"} and decision.preferred_channel in {"inbox", "qq"}:
        gate_decision = "desktop_inbox"
    else:
        gate_decision = "hold_private"
        held_by.append("delivery_not_enabled")
    if gate_decision == "desktop_inbox":
        notes.append("desktop_inbox_local_only")
    return {
        "decision": gate_decision,
        "blocked_by": tuple(dict.fromkeys(blocked_by)),
        "held_by": tuple(dict.fromkeys(held_by)),
        "positive_reasons": tuple(decision.reasons_positive),
        "negative_reasons": tuple(dict.fromkeys((*decision.reasons_negative, *blocked_by, *held_by))),
        "notes": tuple(notes),
    }


def _apply_context_gate(
    decision: ProactiveDecision,
    gate: dict[str, Any],
    *,
    context_gate: dict[str, Any],
) -> dict[str, Any]:
    if gate.get("decision") != "desktop_inbox" or not context_gate.get("observed"):
        return gate
    posture = _safe_str(context_gate.get("initiative_posture")).lower()
    scene = _safe_str(context_gate.get("current_scene")).lower()
    recall_support = bool(context_gate.get("recall_support"))
    score = _safe_int(decision.total_score)
    urgent_source = proactive_source_is_urgent(decision.source_type)
    held_reason = ""
    gentle_presence = decision.source_type == "owner_long_idle" and score >= GENTLE_CONTEXT_BYPASS_MIN_SCORE
    substantive_progress = (
        decision.source_type in SUBSTANTIVE_CONTEXT_BYPASS_SOURCE_TYPES
        and score >= SUBSTANTIVE_CONTEXT_BYPASS_MIN_SCORE
    )
    if posture in {"quiet_by_default", "quiet_presence"}:
        if not urgent_source and not gentle_presence and not substantive_progress:
            held_reason = f"context_gate_{posture}"
    elif posture == "hold_unless_owner_asks":
        if not urgent_source:
            held_reason = "context_gate_hold_unless_owner_asks"
    elif posture == "diagnostic_only":
        if not urgent_source:
            held_reason = "context_gate_diagnostic_only"
    elif posture == "feedback_shaped":
        if not recall_support and not urgent_source:
            held_reason = "context_gate_recall_support_missing"
    if scene == "memory_review" and not urgent_source:
        held_reason = held_reason or "context_gate_memory_review_restraint"
    if not held_reason:
        notes = tuple(dict.fromkeys((*gate.get("notes", ()), "context_gate_passed")))
        return {**gate, "notes": notes}
    held_by = tuple(dict.fromkeys((*gate.get("held_by", ()), held_reason)))
    negative = tuple(dict.fromkeys((*gate.get("negative_reasons", ()), held_reason)))
    notes = tuple(dict.fromkeys((*gate.get("notes", ()), "context_gate_held_private")))
    return {
        **gate,
        "decision": "hold_private",
        "held_by": held_by,
        "negative_reasons": negative,
        "notes": notes,
    }


def _desktop_item_from_decision(
    decision: ProactiveDecision,
    *,
    gate: dict[str, Any],
    checked_at: str,
) -> dict[str, Any]:
    preview = _desktop_candidate_preview(decision)
    return {
        "candidateId": decision.candidate_id,
        "requestId": decision.decision_id,
        "status": "candidate_only",
        "deliveryLevel": "state_only",
        "requiresOwnerAck": True,
        "claimable": False,
        "createdAt": checked_at,
        "expiresAt": _expiry(decision.candidate.expires_at, checked_at),
        "kind": decision.intent_type,
        "source": "initiative_orchestrator",
        "focusKind": decision.source_type,
        "focusLabel": _desktop_focus_label(decision),
        "priority": str(decision.total_score),
        "requestFamily": "initiative_lifecycle",
        "threadId": decision.candidate_signature,
        "requestedAction": "owner_review",
        "evidenceHash": decision.candidate_signature,
        "dedupeHash": decision.candidate_signature,
        "candidatePreview": preview,
        "whyNowPreview": _clip(_why_now(decision, gate), 220),
        "answerState": "pending",
        "claimId": "",
        "ackStatus": "",
        "adapterMessageId": "",
        "adapterError": "",
        "initiativeLifecycle": True,
        "initiativeDecisionId": decision.decision_id,
        "initiativeSignature": decision.candidate_signature,
        "notes": ["initiative_orchestrator", "local_only", "qq_claim_disabled"],
    }


def _desktop_focus_label(decision: ProactiveDecision) -> str:
    return desktop_focus_label(decision.source_type, decision.intent_type)


def _event_from_decision(
    decision: ProactiveDecision,
    *,
    checked_at: str,
    trigger: str,
    candidate_count: int,
    decision_count: int,
    gate: dict[str, Any],
    context_gate: dict[str, Any],
    desktop_item: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    score = decision.score
    penalties = (
        score.interruption_cost
        + score.repetition_penalty
        + score.uncertainty_penalty
        + score.flavor_penalty
        + score.stale_penalty
    )
    delivery = {
        "level": "dry_run"
        if dry_run
        else ("desktop_inbox" if desktop_item else ("none" if gate["decision"] == "blocked" else "private_bias")),
        "desktop_candidate_id": _safe_str(desktop_item.get("candidateId")),
        "claimable": False,
    }
    event = _base_event(checked_at=checked_at, trigger=trigger, stage="decision", status=gate["decision"])
    event.update(
        {
            "candidate_count": candidate_count,
            "decision_count": decision_count,
            "candidate_id": decision.candidate_id,
            "source_type": decision.source_type,
            "intent_type": decision.intent_type,
            "candidate_signature": decision.candidate_signature,
            "content_preview": _clip(decision.content_preview, 180),
            "score": {
                "total_score": score.total_score,
                "utility_score": score.utility_score,
                "urgency_score": score.urgency_score,
                "owner_relevance": score.owner_relevance,
                "novelty_score": score.novelty_score,
                "inner_pressure": score.inner_pressure,
                "penalties": penalties,
            },
            "gate": {
                "decision": gate["decision"],
                "blocked_by": list(gate["blocked_by"]),
                "held_by": list(gate["held_by"]),
                "positive_reasons": list(gate["positive_reasons"]),
                "negative_reasons": list(gate["negative_reasons"]),
                "notes": list(gate.get("notes", ())),
            },
            "context_gate": context_gate,
            "delivery": delivery,
            "feedback": _feedback_from_delivery(delivery),
            "candidate": asdict(decision.candidate),
        }
    )
    return _clean_json_value(event)


def _feedback_from_delivery(delivery: dict[str, Any]) -> dict[str, Any]:
    level = _safe_str(delivery.get("level"), "none")
    requires_owner_feedback = level == "desktop_inbox"
    status = {
        "desktop_inbox": "pending",
        "private_bias": "private_only",
        "dry_run": "not_requested",
        "none": "not_delivered",
    }.get(level, "not_requested")
    return {
        "status": status,
        "feedback_event_id": "",
        "requires_owner_feedback": requires_owner_feedback,
        "reason": level,
    }


def _write_state(
    root: Path,
    *,
    checked_at: str,
    trigger: str,
    candidate_count: int,
    decision_count: int,
    selected: ProactiveDecision | None,
    gate_decision: str,
    blocked_by: list[str],
    held_by: list[str],
    delivery_level: str,
    feedback_pending_count: int,
    context_gate: dict[str, Any],
    notes: list[str],
) -> None:
    selected_id = selected.candidate_id if selected else "none"
    selected_source = selected.source_type if selected else "none"
    selected_intent = selected.intent_type if selected else "none"
    selected_score = selected.total_score if selected else 0
    lines = [
        "---",
        "title: Initiative Lifecycle State",
        "memory_type: initiative_lifecycle_state",
        "time_scope: short_term",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_initiative_orchestrator",
        f"updated_at: {_timestamp_or_now_iso(checked_at)}",
        "status: active",
        "tags: [initiative, lifecycle, proactive, feedback]",
        "---",
        "",
        "# Initiative Lifecycle State",
        "",
        f"- checked_at: {_timestamp_or_now_iso(checked_at)}",
        f"- last_trigger: {trigger}",
        f"- candidate_count: {candidate_count}",
        f"- decision_count: {decision_count}",
        f"- selected_candidate_id: {selected_id}",
        f"- selected_source: {selected_source}",
        f"- selected_intent: {selected_intent}",
        f"- selected_decision: {gate_decision}",
        f"- selected_score: {selected_score}",
        f"- blocked_count: {len(blocked_by)}",
        f"- held_count: {len(held_by)}",
        f"- delivery_level: {delivery_level}",
        f"- pending_feedback_count: {feedback_pending_count}",
        f"- context_gate_observed: {str(bool(context_gate.get('observed'))).lower()}",
        f"- context_scene: {_safe_str(context_gate.get('current_scene'), 'unknown')}",
        f"- context_initiative_posture: {_safe_str(context_gate.get('initiative_posture'), 'unknown')}",
        f"- context_recall_support: {str(bool(context_gate.get('recall_support'))).lower()}",
        f"- context_gate_age_seconds: {_safe_str(context_gate.get('age_seconds'), 'unknown')}",
        f"- context_gate_stale: {str(bool(context_gate.get('stale'))).lower()}",
        f"- interruption_posture: {'restrained' if gate_decision != 'desktop_inbox' else 'owner_visible_local'}",
        f"- next_step: {_state_next_step(gate_decision)}",
        "",
        "## Boundaries",
        "- no_direct_qq_send: true",
        "- claimable: false",
        "- stable_memory_write: blocked",
        "- source_text_policy: previews_only",
        "",
        "## Notes",
    ]
    lines.extend(f"- {note}" for note in (notes or ["none"]))
    _write_text_atomic(root / STATE_REL, "\n".join(lines).rstrip() + "\n")


def _write_feedback_state(
    root: Path,
    *,
    feedback_at: str,
    candidate_id: str,
    action: str,
    latest: dict[str, Any],
) -> None:
    signature = _safe_str(latest.get("candidate_signature"), "unknown")
    lines = [
        "---",
        "title: Initiative Feedback State",
        "memory_type: initiative_feedback_state",
        "time_scope: short_term",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_initiative_orchestrator",
        f"updated_at: {_timestamp_or_now_iso(feedback_at)}",
        "status: active",
        "tags: [initiative, feedback, proactive]",
        "---",
        "",
        "# Initiative Feedback State",
        "",
        f"- last_feedback_at: {_timestamp_or_now_iso(feedback_at)}",
        f"- candidate_id: {candidate_id}",
        f"- candidate_signature: {signature}",
        f"- action: {action}",
        f"- source_type: {_safe_str(latest.get('source_type'), 'unknown')}",
        f"- intent_type: {_safe_str(latest.get('intent_type'), 'unknown')}",
        f"- future_effect: {_feedback_effect(action)}",
        "",
        "## Boundaries",
        "- stable_memory_write: blocked",
        "- personality_promotion: blocked",
        "- scoring_bias_only: true",
        "",
    ]
    _write_text_atomic(root / FEEDBACK_STATE_REL, "\n".join(lines))


def _load_context_gate(root: Path, *, observed_at: str) -> dict[str, Any]:
    self_path = root / CONTEXTUAL_SELF_STATE_REL
    recall_path = root / CONTEXTUAL_RECALL_STATE_REL
    self_fields = _load_markdown_fields(self_path)
    recall_fields = _load_markdown_fields(recall_path)
    observed = bool(self_fields)
    evaluated_at = _safe_str(self_fields.get("evaluated_at") or self_fields.get("updated_at"))
    age_seconds = _age_seconds(evaluated_at, observed_at=observed_at)
    recall_count = _safe_int(recall_fields.get("admitted_recall_count"))
    suppressed_count = _safe_int(recall_fields.get("suppressed_recall_count"))
    source_count = _safe_int(recall_fields.get("source_count"))
    posture = _safe_str(self_fields.get("initiative_posture"), "unknown")
    scene = _safe_str(self_fields.get("current_scene"), "unknown")
    next_action = _safe_str(self_fields.get("next_action_bias"), "unknown")
    return {
        "observed": observed,
        "evaluated_at": evaluated_at,
        "age_seconds": age_seconds if age_seconds is not None else "unknown",
        "stale": bool(age_seconds is not None and age_seconds > 6 * 60 * 60),
        "current_scene": scene,
        "initiative_posture": posture,
        "next_action_bias": next_action,
        "forgetting_posture": _safe_str(self_fields.get("forgetting_posture"), "unknown"),
        "recall_support": recall_count > 0,
        "admitted_recall_count": recall_count,
        "suppressed_recall_count": suppressed_count,
        "recall_source_count": source_count,
        "reason": _context_gate_reason(
            observed=observed,
            scene=scene,
            posture=posture,
            next_action=next_action,
            recall_count=recall_count,
            age_seconds=age_seconds,
        ),
    }


def _context_gate_reason(
    *,
    observed: bool,
    scene: str,
    posture: str,
    next_action: str,
    recall_count: int,
    age_seconds: int | None,
) -> str:
    if not observed:
        return "context_gate_unobserved_legacy_behavior"
    freshness = "fresh" if age_seconds is not None and age_seconds <= 6 * 60 * 60 else "stale_or_unknown_age"
    if recall_count > 0:
        return f"scene={scene};posture={posture};recall_supported;next={next_action};{freshness}"
    return f"scene={scene};posture={posture};recall_absent;next={next_action};{freshness}"


def _age_seconds(value: str, *, observed_at: str) -> int | None:
    start = _parse_iso(value)
    end = _parse_iso(observed_at)
    if start is None or end is None:
        return None
    try:
        return max(0, int((end - start).total_seconds()))
    except TypeError:
        return max(0, int((end.replace(tzinfo=None) - start.replace(tzinfo=None)).total_seconds()))


def _load_markdown_fields(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = _safe_str(key).strip()
        if not key:
            continue
        fields[key] = _one_line(value.strip(), limit=180)
    return fields


def _load_feedback_index(root: Path) -> dict[str, dict[str, Any]]:
    feedback: dict[str, dict[str, Any]] = {}
    for event in _read_events(root / EVENTS_REL):
        if event.get("stage") != "feedback":
            continue
        status = _safe_str(event.get("status"))
        candidate_id = _safe_str(event.get("candidate_id"))
        signature = _safe_str(event.get("candidate_signature"))
        source_type = _safe_str(event.get("source_type"))
        intent_type = _safe_str(event.get("intent_type"))
        if candidate_id:
            feedback[candidate_id] = {"status": status, "event": event}
        if signature:
            feedback[signature] = {"status": status, "event": event}
        source_key = _source_feedback_key(source_type, intent_type)
        if source_key:
            feedback[source_key] = {"status": status, "event": event}
    return feedback


def _apply_feedback_bias(candidate: Any, score: Any, *, feedback: dict[str, dict[str, Any]]) -> Any:
    signature = candidate_signature(candidate)
    exact = feedback.get(signature) or feedback.get(_safe_str(candidate.candidate_id))
    source = feedback.get(_source_feedback_key(candidate.source_type, candidate.intent_type))
    signal = exact or source or {}
    status = _safe_str(signal.get("status")).lower()
    if not status:
        return score

    total_delta = 0
    confidence_delta = 0
    interruption_delta = 0
    repetition_delta = 0
    positive = list(score.reasons_positive)
    negative = list(score.reasons_negative)
    if status in {"reply", "replied", "sent", "approve_qq", "approved_qq"}:
        total_delta = 10
        confidence_delta = 4
        positive.append("feedback_bias_replied")
    elif status == "read_locally":
        total_delta = 4
        confidence_delta = 2
        positive.append("feedback_bias_read_locally")
    elif status in {"dismiss", "dismissed"}:
        total_delta = -14
        repetition_delta = 8
        negative.append("feedback_bias_dismissed")
    elif status == "failed":
        total_delta = -18
        interruption_delta = 8
        negative.append("feedback_bias_failed_delivery")
    else:
        return score

    return replace(
        score,
        total_score=_clamp_int(_safe_int(score.total_score) + total_delta),
        confidence=_clamp_int(_safe_int(score.confidence) + confidence_delta),
        interruption_cost=_clamp_int(_safe_int(score.interruption_cost) + interruption_delta),
        repetition_penalty=_clamp_int(_safe_int(score.repetition_penalty) + repetition_delta),
        reasons_positive=tuple(dict.fromkeys(positive)),
        reasons_negative=tuple(dict.fromkeys(negative)),
    )


def _write_metrics(root: Path, *, observed_at: str) -> None:
    events = _events_in_window(_read_events(root / EVENTS_REL), observed_at=observed_at, hours=METRICS_WINDOW_HOURS)
    decisions = [event for event in events if event.get("stage") == "decision"]
    feedback_events = [event for event in events if event.get("stage") == "feedback"]
    metrics = {
        "updated_at": observed_at,
        "window_hours": METRICS_WINDOW_HOURS,
        "event_count_24h": len(events),
        "decision_event_count_24h": len(decisions),
        "candidate_seen_count_24h": sum(_safe_int(event.get("candidate_count")) for event in decisions),
        "selected_count_24h": sum(1 for event in decisions if _safe_str(event.get("candidate_id"))),
        "desktop_shown_count_24h": sum(
            1 for event in decisions if _safe_str(event.get("delivery", {}).get("level")) == "desktop_inbox"
        ),
        "held_private_count_24h": sum(1 for event in decisions if _safe_str(event.get("status")) == "hold_private"),
        "blocked_count_24h": sum(1 for event in decisions if _safe_str(event.get("status")) == "blocked"),
        "feedback_count_24h": len(feedback_events),
        "dismiss_count_24h": sum(
            1 for event in feedback_events if _safe_str(event.get("status")).lower() in {"dismiss", "dismissed"}
        ),
        "reply_count_24h": sum(
            1 for event in feedback_events if _safe_str(event.get("status")).lower() in {"reply", "replied", "sent"}
        ),
        "approved_qq_count_24h": sum(
            1 for event in feedback_events if _safe_str(event.get("status")).lower() in {"approve_qq", "approved_qq"}
        ),
        "failed_count_24h": sum(1 for event in feedback_events if _safe_str(event.get("status")).lower() == "failed"),
        "pending_feedback_count": _pending_feedback_count(root, observed_at=observed_at),
        "status_counts_24h": _count_by(events, "status"),
        "feedback_counts_24h": _count_by(feedback_events, "status"),
        "source_counts_24h": _count_by(events, "source_type"),
    }
    path = root / METRICS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(_clean_json_value(metrics), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _events_in_window(events: list[dict[str, Any]], *, observed_at: str, hours: int) -> list[dict[str, Any]]:
    anchor = _parse_iso(observed_at)
    if anchor is None:
        return list(events[-RECENT_SCAN_LINES:])
    max_age = max(1, int(hours)) * 3600
    windowed: list[dict[str, Any]] = []
    for event in events:
        ts = _parse_iso(_safe_str(event.get("ts")))
        if ts is None:
            continue
        try:
            age_seconds = (anchor - ts).total_seconds()
        except TypeError:
            age_seconds = (anchor.replace(tzinfo=None) - ts.replace(tzinfo=None)).total_seconds()
        if 0 <= age_seconds <= max_age:
            windowed.append(event)
    return windowed


def _count_by(events: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        value = _safe_str(event.get(key), "unknown") or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_int(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def _source_feedback_key(source_type: Any, intent_type: Any) -> str:
    source = _one_line(source_type, limit=80).lower()
    intent = _one_line(intent_type, limit=80).lower()
    if not source or source == "unknown" or not intent or intent == "unknown":
        return ""
    return f"source:{source}:{intent}"


def _latest_event_for_candidate(root: Path, candidate_id: str) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    for event in _read_events(root / EVENTS_REL):
        if _safe_str(event.get("candidate_id")) == candidate_id:
            latest = event
    return latest


def _pending_feedback_count(root: Path, *, observed_at: str | None = None) -> int:
    pending: set[str] = set()
    final: set[str] = set()
    for event in _read_events(root / EVENTS_REL):
        candidate_id = _safe_str(event.get("candidate_id"))
        if not candidate_id:
            continue
        if (
            event.get("stage") == "decision"
            and _safe_str(event.get("delivery", {}).get("level")) == "desktop_inbox"
            and _safe_str(event.get("feedback", {}).get("status"), "pending") == "pending"
            and not _decision_feedback_expired(event, observed_at=observed_at)
        ):
            pending.add(candidate_id)
        elif event.get("stage") == "feedback":
            final.add(candidate_id)
    return len(pending - final)


def _decision_feedback_expired(event: dict[str, Any], *, observed_at: str | None) -> bool:
    if not observed_at:
        return False
    observed = _parse_iso(observed_at)
    if observed is None:
        return False
    expires = _parse_iso(_event_expires_at(event))
    if expires is None:
        return False
    try:
        return observed >= expires
    except TypeError:
        return observed.replace(tzinfo=None) >= expires.replace(tzinfo=None)


def _event_expires_at(event: dict[str, Any]) -> str:
    candidate = event.get("candidate")
    if isinstance(candidate, dict):
        expires = _safe_str(candidate.get("expires_at") or candidate.get("expiresAt"))
        if expires:
            return expires
    return _safe_str(event.get("expires_at") or event.get("expiresAt"))


def _load_recent_signatures(path: Path) -> set[str]:
    signatures: set[str] = set()
    for event in _read_events(path)[-RECENT_SCAN_LINES:]:
        signature = _safe_str(event.get("candidate_signature"))
        if signature and event.get("stage") == "decision":
            signatures.add(signature)
    return signatures


def _read_events(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    return events


def _append_event(root: Path, event: dict[str, Any]) -> None:
    path = root / EVENTS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_clean_json_value(event), ensure_ascii=False, sort_keys=True) + "\n")


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _base_event(*, checked_at: str, trigger: str, stage: str, status: str) -> dict[str, Any]:
    return {
        "event_id": "init-" + _timestamp_id(checked_at) + "-" + _short_hash(f"{stage}|{status}|{trigger}|{checked_at}"),
        "ts": checked_at,
        "stage": stage,
        "status": status,
        "trigger": trigger,
    }


def _decision_sort_key(decision: ProactiveDecision) -> tuple[int, int]:
    preferred_rank = {"qq": 4, "inbox": 3, "silent": 1}.get(decision.preferred_channel, 0)
    recommendation_rank = {"send_now": 4, "inbox": 3, "hold": 2, "drop": 1}.get(decision.recommendation, 0)
    return preferred_rank, recommendation_rank, decision.total_score


def _desktop_candidate_preview(decision: ProactiveDecision) -> str:
    source = decision.source_type
    owner_text = _safe_str(decision.candidate.owner_visible_text)
    detail = _safe_str(decision.content_preview)
    if source == "runtime_error":
        if "adapter_error=dry_run_not_enqueued" in detail.lower():
            return "A local proactive draft was kept on the desktop instead of being sent to QQ."
        return owner_text or "A runtime subsystem needs a quick local check."
    if source == "task_done":
        return owner_text or "A delegated task has a result ready to review."
    if source == "task_failed":
        return owner_text or "A delegated task needs attention."
    if source == "style_repair":
        return "A reply-style repair is ready for local review."
    if source == "dream_residue":
        return "A dream residue is available for local review."
    if source == "reflection_question":
        return owner_text or "A reflection topic is waiting for local review."
    if source == "owner_long_idle":
        return "XinYu has been quiet for a long time and is only leaving a local note."
    return owner_text or _clip(detail, 160)


def _why_now(decision: ProactiveDecision, gate: dict[str, Any]) -> str:
    positive = ",".join(decision.reasons_positive[:2]) or "initiative_pressure"
    negative = ",".join(gate.get("held_by") or gate.get("blocked_by") or ()) or "local_review"
    return f"{decision.source_type}/{positive}; gate={gate['decision']}; restraint={negative}"


def _state_next_step(gate_decision: str) -> str:
    if gate_decision == "desktop_inbox":
        return "wait for owner ack before changing future initiative bias"
    if gate_decision == "blocked":
        return "keep private and do not surface"
    return "hold as private bias until a grounded turn or later review"


def _feedback_effect(action: str) -> str:
    if action in {"dismiss", "dismissed"}:
        return "lower similar future initiative priority"
    if action in {"reply", "replied"}:
        return "increase confidence for similar grounded owner-visible initiatives"
    if action in {"approve_qq", "approved_qq"}:
        return "record owner approval signal without bypassing qq gates"
    if action == "failed":
        return "raise delivery caution for similar future initiatives"
    return "record feedback without stable memory promotion"


def _normalize_feedback_action(action: str) -> str:
    value = _one_line(action, limit=40).lower()
    return {
        "read": "read_locally",
        "read_local": "read_locally",
        "reply": "replied",
        "approve": "approved_qq",
        "approve_qq": "approved_qq",
        "dismiss": "dismissed",
    }.get(value, value)


def _expiry(value: str, checked_at: str) -> str:
    value = _safe_str(value)
    if value:
        return value
    parsed = _parse_iso(checked_at)
    if parsed is None:
        parsed = datetime.now().astimezone()
    return (parsed + timedelta(seconds=DEFAULT_EXPIRES_SECONDS)).isoformat()


def _parse_iso(value: str) -> datetime | None:
    text = _safe_str(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(_safe_str(value))
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat()


def _timestamp_id(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())[:14] or str(int(datetime.now().timestamp()))


def _short_hash(value: Any, *, length: int = 10) -> str:
    import hashlib

    return hashlib.sha256(_safe_str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _clip(value: Any, limit: int = 160) -> str:
    text = " ".join(_safe_str(value).split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _one_line(value: Any, *, limit: int = 160) -> str:
    return _clip(value, limit=limit)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_clean_json_value(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _safe_str(value)
