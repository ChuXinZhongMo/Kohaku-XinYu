from __future__ import annotations


__all__ = (
    "REPORT_REL",
    "STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL",
    "STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL",
)

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates
from xinyu_feedback_consumption_diagnostics import build_feedback_consumption_diagnostics
from xinyu_memory_candidate_analysis import candidate_claim_metadata_from_row, candidate_review_context
from xinyu_memory_health_report_store import STAGE8_STATE_REL
from xinyu_memory_health_report_store import memory_health_report_path
from xinyu_memory_health_report_store import read_memory_health_source_text
from xinyu_memory_health_report_store import read_memory_health_text
from xinyu_memory_health_report_store import write_memory_health_report_text
from xinyu_memory_health_report_store import write_stage8_memory_governance_state_text

from xinyu_action_feedback_coverage import REPORT_REL

from xinyu_memory_health_report_store import STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL

from xinyu_memory_health_report_store import STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL

CANDIDATE_STATUSES = (
    "pending",
    "owner_review_required",
    "self_approved_recent_context",
    "self_approved_voice_review",
    "observe_more_owner_preference",
    "observe_more_relationship_signal",
    "observe_more_unknown",
    "blocked_scope_mismatch",
    "blocked_sensitive",
    "rejected",
    "approved",
    "applied_growth_log",
    "archived_observe_more",
    "archived_duplicate",
    "archived_rejected",
    "archived_blocked",
)
DUPLICATE_BACKLOG_STATUSES = {
    "pending",
    "owner_review_required",
    "self_approved_recent_context",
    "self_approved_voice_review",
    "observe_more_owner_preference",
    "observe_more_relationship_signal",
    "observe_more_unknown",
    "approved",
}
PRIVATE_STATUSES = {"owner_review_required"}
PRIVATE_TARGETS = {
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/self/voice_calibration_log.md",
}
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bprivate[_ -]?key\b"),
    re.compile(r"(?i)\bcookie\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)
DIALOGUE_PREVIEW_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bowner_turn\s*:"),
    re.compile(r"(?i)\bvisible_reply\s*:"),
    re.compile(r"(?i)\buser_turn\s*:"),
    re.compile(r"(?i)\bassistant_reply\s*:"),
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _one_line(value: Any, *, limit: int = 180, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _read_text(path: Path, *, limit: int = 20000) -> str:
    return read_memory_health_text(path, limit=limit)


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        return default
    value = _one_line(match.group(1), limit=220, default=default)
    return value if value else default


def _int_field(text: str, name: str, default: int = 0) -> int:
    raw = _field(text, name, str(default))
    match = re.search(r"-?\d+", raw)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _duplicate_consolidation_summary(root: Path, *, duplicate_cluster_count: int) -> dict[str, Any]:
    if duplicate_cluster_count <= 0:
        return {
            "duplicate_consolidation_status": "not_required",
            "duplicate_consolidation_packet_path": "none",
            "duplicate_consolidation_item_count": 0,
            "duplicate_consolidation_conflict_cluster_count": 0,
            "duplicate_consolidation_ready_cluster_count": 0,
        }
    state = read_memory_health_source_text(root, "stage8_duplicate_consolidation_state")
    if not state.strip():
        return {
            "duplicate_consolidation_status": "missing",
            "duplicate_consolidation_packet_path": "none",
            "duplicate_consolidation_item_count": 0,
            "duplicate_consolidation_conflict_cluster_count": 0,
            "duplicate_consolidation_ready_cluster_count": 0,
        }
    state_cluster_count = _int_field(state, "duplicate_cluster_count", -1)
    packet_status = _field(state, "packet_status", "missing")
    status = "ready" if packet_status == "ready_for_consolidation_review" else packet_status
    if state_cluster_count != duplicate_cluster_count:
        status = "stale"
    return {
        "duplicate_consolidation_status": status,
        "duplicate_consolidation_packet_path": _field(state, "packet_path", "none"),
        "duplicate_consolidation_item_count": _int_field(state, "consolidation_item_count", 0),
        "duplicate_consolidation_conflict_cluster_count": _int_field(state, "conflict_cluster_count", 0),
        "duplicate_consolidation_ready_cluster_count": _int_field(state, "ready_cluster_count", 0),
    }


def _learning_trial_validation_summary(root: Path, personality: dict[str, Any]) -> dict[str, Any]:
    learning_gate = _safe_str(personality.get("learning_trial_success_gate"), "unknown")
    if learning_gate in {"not_required", "satisfied"}:
        return {
            "learning_trial_validation_status": learning_gate,
            "learning_trial_validation_active_key": _safe_str(personality.get("learning_trial_active_key"), "none"),
            "learning_trial_validation_needed_success_count": 0,
            "learning_trial_validation_owner_action": (
                "owner_explicit_apply_required_no_auto_promotion" if learning_gate == "satisfied" else "none"
            ),
            "learning_trial_validation_packet_path": "none",
        }
    state = read_memory_health_source_text(root, "stage8_learning_trial_validation_state")
    if not state.strip():
        return {
            "learning_trial_validation_status": "missing",
            "learning_trial_validation_active_key": _safe_str(personality.get("learning_trial_active_key"), "none"),
            "learning_trial_validation_needed_success_count": 2,
            "learning_trial_validation_owner_action": "write_or_refresh_learning_trial_validation_packet",
            "learning_trial_validation_packet_path": "none",
        }
    active_key = _field(state, "active_trial_key", "none")
    status = _field(state, "validation_status", "missing")
    owner_action = _field(state, "owner_action", "none")
    if active_key != _safe_str(personality.get("learning_trial_active_key"), "none"):
        status = "stale"
        owner_action = "refresh_learning_trial_validation_packet_active_key_changed"
    if _field(state, "success_evidence_status", "none") != _safe_str(
        personality.get("learning_trial_success_evidence_status"),
        "none",
    ):
        status = "stale"
    return {
        "learning_trial_validation_status": status,
        "learning_trial_validation_active_key": active_key,
        "learning_trial_validation_needed_success_count": _int_field(state, "needed_consecutive_success_count", 2),
        "learning_trial_validation_owner_action": owner_action,
        "learning_trial_validation_packet_path": _field(state, "packet_path", "none"),
    }


def _all_candidate_rows(root: Path, *, limit_per_status: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status in CANDIDATE_STATUSES:
        for row in list_memory_candidates(root, status=status, limit=limit_per_status):
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append(row)
    return rows


def _is_private_row(row: dict[str, Any]) -> bool:
    status = _safe_str(row.get("status"))
    target = _safe_str(row.get("target_memory_layer")).replace("\\", "/")
    flags = [_safe_str(flag) for flag in row.get("risk_flags", []) or []]
    candidate_text = _safe_str(row.get("candidate_text"))
    has_dialogue_preview = any(pattern.search(candidate_text) for pattern in DIALOGUE_PREVIEW_PATTERNS)
    return status in PRIVATE_STATUSES or target in PRIVATE_TARGETS or "scope:owner_private" in flags or has_dialogue_preview


def _row_preview(row: dict[str, Any]) -> str:
    if _is_private_row(row):
        return "hidden_private_or_owner_review_required"
    return _one_line(row.get("candidate_text"), limit=220, default="")


def _safe_row_item(row: dict[str, Any]) -> dict[str, Any]:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    return {
        "candidate_id": row.get("candidate_id"),
        "status": row.get("status"),
        "candidate_type": row.get("candidate_type"),
        "target_memory_layer": row.get("target_memory_layer"),
        "target_gate": row.get("target_gate"),
        "risk_flags": row.get("risk_flags") if isinstance(row.get("risk_flags"), list) else [],
        "claim_topic_key": evidence.get("claim_topic_key"),
        "claim_polarity": evidence.get("claim_polarity"),
        "candidate_text_preview": _row_preview(row),
    }


def build_memory_candidate_clusters(rows: list[dict[str, Any]], *, max_clusters: int = 20) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        meta = candidate_claim_metadata_from_row(row)
        topic = _safe_str(meta.get("claim_topic_key")) or "unknown"
        grouped[topic].append(row)
    clusters: list[dict[str, Any]] = []
    for topic, items in grouped.items():
        if not items:
            continue
        exemplar = items[0]
        review = candidate_review_context(exemplar, rows)
        statuses = Counter(_safe_str(item.get("status"), "unknown") for item in items)
        types = Counter(_safe_str(item.get("candidate_type"), "unknown") for item in items)
        targets = Counter(_safe_str(item.get("target_memory_layer"), "unknown") for item in items)
        clusters.append(
            {
                "claim_topic_key": topic,
                "size": len(items),
                "status_counts": dict(sorted(statuses.items())),
                "candidate_type_counts": dict(sorted(types.items())),
                "target_memory_layer_counts": dict(sorted(targets.items())),
                "supporting_candidate_ids": review.get("supporting_candidate_ids", []),
                "conflicting_candidate_ids": review.get("conflicting_candidate_ids", []),
                "conflict_count": review.get("conflict_count", 0),
                "recommendation": review.get("recommendation", "observe_more"),
                "items": [_safe_row_item(item) for item in items[:8]],
            }
        )
    clusters.sort(key=lambda item: (int(item.get("size", 0)), int(item.get("conflict_count", 0))), reverse=True)
    return clusters[:max(1, int(max_clusters))]


def _duplicate_backlog_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if _safe_str(row.get("status")) in DUPLICATE_BACKLOG_STATUSES]


def _count_growth_entries(text: str) -> int:
    return len(re.findall(r"(?m)^##\s+", text)) or len(re.findall(r"(?im)^-\s+.*growth", text))


def _learning_trial_gate_summary(learning: str, self_review: str) -> dict[str, Any]:
    active_trial_habit = _field(learning, "active_trial_habit", "none")
    active_trial_key = _field(learning, "active_trial_key", _field(learning, "latest_failure_kind", "none"))
    status = _field(learning, "status", "none")
    repair_count = _int_field(learning, "repair_count", 0)
    success_count = _int_field(learning, "success_count", 0)
    success_streak = _int_field(learning, "success_streak", 0)
    trial_success_count = _int_field(learning, "trial_success_count", success_count)
    trial_success_streak = _int_field(learning, "trial_success_streak", success_streak)
    latest_success_trial_key = _field(learning, "latest_success_trial_key", "none")
    success_evidence_status = _field(learning, "success_evidence_status", "none")
    promotion_signal = _field(learning, "promotion_signal", "false").lower()
    last_owner_reaction = _field(learning, "last_owner_reaction", "none")
    self_review_reason = _field(self_review, "learning_trial_gate_reason", "")

    if active_trial_habit in {"", "none", "unknown"}:
        gate = "not_required"
        reason = "no_active_trial_habit"
    elif (
        status == "trial_supported"
        and trial_success_count >= 2
        and trial_success_streak >= 2
        and last_owner_reaction == "explicit_success"
        and success_evidence_status == "same_trial_explicit_owner_success"
        and latest_success_trial_key not in {"", "none", "unknown"}
        and (promotion_signal in {"true", "possible_after_self_review"} or trial_success_streak >= 2)
    ):
        gate = "satisfied"
        reason = "learning_trial_success_gate_satisfied"
    else:
        gate = "blocked"
        blockers: list[str] = []
        if not learning.strip():
            blockers.append("missing_learning_closed_loop_state")
        if active_trial_key in {"", "none", "unknown"}:
            blockers.append("missing_active_trial_key")
        if latest_success_trial_key in {"", "none", "unknown"}:
            blockers.append("missing_success_trial_key")
        if success_evidence_status != "same_trial_explicit_owner_success":
            blockers.append(f"success_evidence_not_same_trial:{success_evidence_status}")
        if repair_count >= 8 and trial_success_streak < 2:
            blockers.append(f"repair_pressure_overloaded:{repair_count}")
        if status != "trial_supported":
            blockers.append(f"status_not_trial_supported:{status}")
        if trial_success_count < 2:
            blockers.append(f"trial_success_count_below_2:{trial_success_count}")
        if trial_success_streak < 2:
            blockers.append(f"trial_success_streak_below_2:{trial_success_streak}")
        if last_owner_reaction != "explicit_success":
            blockers.append(f"last_owner_reaction_not_explicit_success:{last_owner_reaction}")
        reason = self_review_reason or "learning_trial_success_gate_not_satisfied:" + ",".join(blockers[:6])

    return {
        "learning_trial_success_gate": gate,
        "learning_trial_gate_reason": reason,
        "learning_trial_status": status,
        "learning_trial_active_key": active_trial_key,
        "learning_trial_latest_success_key": latest_success_trial_key,
        "learning_trial_success_evidence_status": success_evidence_status,
        "learning_trial_repair_count": repair_count,
        "learning_trial_success_count": success_count,
        "learning_trial_success_streak": success_streak,
        "learning_trial_same_key_success_count": trial_success_count,
        "learning_trial_same_key_success_streak": trial_success_streak,
        "learning_trial_promotion_signal": promotion_signal,
        "learning_trial_last_owner_reaction": last_owner_reaction,
    }


def _personality_summary(root: Path) -> dict[str, Any]:
    evolution = read_memory_health_source_text(root, "personality_evolution")
    self_review = read_memory_health_source_text(root, "personality_self_review")
    change = read_memory_health_source_text(root, "personality_change")
    learning = read_memory_health_source_text(root, "learning_closed_loop")
    growth = read_memory_health_source_text(root, "growth_log", limit=80000)
    combined = "\n".join([evolution, self_review, change])
    summary: dict[str, Any] = {
        "stable_profile_write": "blocked_review_only_not_auto_apply",
        "owner_memory_write": "blocked_owner_review_required",
        "growth_entry_estimate": _count_growth_entries(growth),
        "reflection_entry_estimate": len(re.findall(r"(?i)reflection", growth)),
    }
    for key in ("evolution_stage", "gate_decision", "trial_permission", "stable_profile_write_permission", "profile_changed"):
        match = re.search(rf"(?m)^-\s*{re.escape(key)}:\s*(.+)$", combined)
        if match:
            summary[key] = match.group(1).strip()
    summary.update(_learning_trial_gate_summary(learning, self_review))
    return summary


def _is_blocked_boundary(value: Any) -> bool:
    text = _safe_str(value).strip().lower()
    return text.startswith("blocked") or text in {
        "review_only_not_auto_apply",
        "blocked_review_only_not_auto_apply",
        "blocked_owner_review_required",
    }


def _stage8_memory_governance(
    *,
    inventory: dict[str, Any],
    duplicate_cluster_count: int,
    duplicate_consolidation: dict[str, Any],
    learning_trial_validation: dict[str, Any],
    personality: dict[str, Any],
    privacy_boundary: dict[str, Any],
    feedback_closure: dict[str, Any],
) -> dict[str, Any]:
    stage7_ready = bool(feedback_closure.get("ready_for_stage8", False))
    candidate_total = int(inventory.get("total") or 0)
    owner_review_required = int(inventory.get("owner_review_required_count") or 0)
    private_or_owner_scoped = int(inventory.get("private_or_owner_scoped_count") or 0)
    learning_gate = _safe_str(personality.get("learning_trial_success_gate"), "unknown")
    learning_validation_status = _safe_str(
        learning_trial_validation.get("learning_trial_validation_status"),
        "missing" if learning_gate == "blocked" else learning_gate,
    )
    duplicate_consolidation_status = _safe_str(
        duplicate_consolidation.get("duplicate_consolidation_status"),
        "missing" if duplicate_cluster_count else "not_required",
    )
    stable_profile_write = _safe_str(personality.get("stable_profile_write"), "unknown")
    owner_memory_write = _safe_str(personality.get("owner_memory_write"), "unknown")
    owner_review_text = _safe_str(privacy_boundary.get("owner_review_candidate_text"), "unknown")
    stable_personality_write = _safe_str(privacy_boundary.get("stable_personality_write"), "unknown")
    privacy_ok = owner_review_text == "hidden"
    stable_boundary_ok = _is_blocked_boundary(stable_profile_write) and _is_blocked_boundary(stable_personality_write)
    owner_boundary_ok = _is_blocked_boundary(owner_memory_write)

    violations: list[str] = []
    if not privacy_ok:
        violations.append(f"owner_review_candidate_text_not_hidden:{owner_review_text}")
    if not stable_boundary_ok:
        violations.append("stable_personality_write_not_blocked")
    if not owner_boundary_ok:
        violations.append("owner_memory_write_not_blocked")

    if violations:
        status = "violation"
        reason = ",".join(violations[:4])
        next_step = "fix_memory_privacy_or_write_boundary_before_any_stage8_work"
    elif not stage7_ready:
        status = "waiting_for_stage7"
        reason = "stage7_feedback_closure_not_ready"
        next_step = "finish_stage7_feedback_consumption_before_memory_governance"
    else:
        status = "active_guarded"
        if owner_review_required:
            reason = f"owner_review_required_candidates:{owner_review_required}"
            next_step = "review_owner_required_memory_candidates_in_owner_channel_only"
        elif duplicate_cluster_count:
            reason = f"duplicate_candidate_clusters:{duplicate_cluster_count}"
            next_step = "consolidate_duplicate_candidate_clusters_before_stable_write"
        elif learning_gate == "blocked":
            reason = "learning_trial_success_gate_blocked"
            next_step = "collect_same_trial_explicit_success_before_profile_change"
        else:
            reason = "memory_governance_boundaries_active"
            next_step = "continue_read_only_memory_governance_canary"

    ready_for_stage9 = (
        status == "active_guarded"
        and owner_review_required == 0
        and duplicate_cluster_count == 0
        and learning_gate in {"not_required", "satisfied"}
    )
    if ready_for_stage9:
        reason = "memory_governance_backlog_and_learning_gate_clear"
        next_step = "stage9_self_state_model_can_start"

    return {
        "status": status,
        "ready_for_stage9": ready_for_stage9,
        "reason": reason,
        "stage7_ready_for_stage8": stage7_ready,
        "stage7_reason": _safe_str(feedback_closure.get("reason"), "missing"),
        "candidate_total": candidate_total,
        "owner_review_required_count": owner_review_required,
        "private_or_owner_scoped_count": private_or_owner_scoped,
        "duplicate_cluster_count": int(duplicate_cluster_count),
        "learning_trial_success_gate": learning_gate,
        "learning_trial_validation_status": learning_validation_status,
        "learning_trial_validation_active_key": _safe_str(
            learning_trial_validation.get("learning_trial_validation_active_key"),
            "none",
        ),
        "learning_trial_validation_needed_success_count": int(
            learning_trial_validation.get("learning_trial_validation_needed_success_count") or 0
        ),
        "learning_trial_validation_owner_action": _safe_str(
            learning_trial_validation.get("learning_trial_validation_owner_action"),
            "none",
        ),
        "learning_trial_validation_packet_path": _safe_str(
            learning_trial_validation.get("learning_trial_validation_packet_path"),
            "none",
        ),
        "duplicate_consolidation_status": duplicate_consolidation_status,
        "duplicate_consolidation_item_count": int(
            duplicate_consolidation.get("duplicate_consolidation_item_count") or 0
        ),
        "duplicate_consolidation_conflict_cluster_count": int(
            duplicate_consolidation.get("duplicate_consolidation_conflict_cluster_count") or 0
        ),
        "duplicate_consolidation_ready_cluster_count": int(
            duplicate_consolidation.get("duplicate_consolidation_ready_cluster_count") or 0
        ),
        "duplicate_consolidation_packet_path": _safe_str(
            duplicate_consolidation.get("duplicate_consolidation_packet_path"),
            "none",
        ),
        "stable_profile_write": stable_profile_write,
        "owner_memory_write": owner_memory_write,
        "owner_review_candidate_text": owner_review_text,
        "stable_personality_write": stable_personality_write,
        "growth_apply_mode": "dry_run_or_owner_apply_confirmed_growth_log_only",
        "stable_identity_profile_apply": "blocked",
        "raw_owner_text_in_state": False,
        "visible_reply_text_in_state": False,
        "consciousness_claim": False,
        "next_step": next_step,
    }


def build_memory_health_report(root: Path, *, limit_per_status: int = 1000, max_clusters: int = 20) -> dict[str, Any]:
    root = root.resolve()
    rows = _all_candidate_rows(root, limit_per_status=limit_per_status)
    status_counts = Counter(_safe_str(row.get("status"), "unknown") for row in rows)
    type_counts = Counter(_safe_str(row.get("candidate_type"), "unknown") for row in rows)
    target_counts = Counter(_safe_str(row.get("target_memory_layer"), "unknown") for row in rows)
    owner_review = [row for row in rows if _safe_str(row.get("status")) == "owner_review_required"]
    private_rows = [row for row in rows if _is_private_row(row)]
    duplicate_backlog_rows = _duplicate_backlog_rows(rows)
    all_clusters = build_memory_candidate_clusters(
        duplicate_backlog_rows,
        max_clusters=max(len(duplicate_backlog_rows), int(max_clusters)),
    )
    clusters = all_clusters[: max(1, int(max_clusters))]
    duplicate_clusters = [cluster for cluster in all_clusters if int(cluster.get("size", 0)) > 1]
    personality = _personality_summary(root)
    feedback = build_feedback_consumption_diagnostics(root)
    feedback_closure = (
        feedback.get("stage7_feedback_closure")
        if isinstance(feedback.get("stage7_feedback_closure"), dict)
        else {}
    )
    privacy_boundary = {
        "owner_review_candidate_text": "hidden",
        "owner_memory_write": "blocked_without_explicit_owner_apply",
        "stable_personality_write": "blocked_review_only",
    }
    duplicate_consolidation = _duplicate_consolidation_summary(root, duplicate_cluster_count=len(duplicate_clusters))
    learning_trial_validation = _learning_trial_validation_summary(root, personality)
    stage8 = _stage8_memory_governance(
        inventory={
            "total": len(rows),
            "owner_review_required_count": len(owner_review),
            "private_or_owner_scoped_count": len(private_rows),
        },
        duplicate_cluster_count=len(duplicate_clusters),
        duplicate_consolidation=duplicate_consolidation,
        learning_trial_validation=learning_trial_validation,
        personality=personality,
        privacy_boundary=privacy_boundary,
        feedback_closure=feedback_closure,
    )
    recommendations = [
        "keep_stable_personality_write_blocked_until_owner_review",
        "keep_owner_private_candidate_body_hidden",
        "review_owner_review_required_candidates_in_owner_channel_only",
    ]
    if duplicate_clusters:
        recommendations.append("consolidate_duplicate_candidate_clusters_before_any_stable_write")
    if duplicate_clusters and duplicate_consolidation.get("duplicate_consolidation_status") in {"missing", "stale"}:
        recommendations.append("write_or_refresh_stage8_duplicate_consolidation_packet")
    if int(personality.get("growth_entry_estimate", 0) or 0) > int(personality.get("reflection_entry_estimate", 0) or 0):
        recommendations.append("add_mid_term_episode_pages_for_repeated_growth_evidence")
    if personality.get("learning_trial_success_gate") == "blocked":
        recommendations.append("keep_trial_habit_out_of_stable_profile_until_learning_success_repeats")
    if personality.get("learning_trial_success_gate") == "blocked" and learning_trial_validation.get(
        "learning_trial_validation_status"
    ) in {"missing", "stale"}:
        recommendations.append("write_or_refresh_stage8_learning_trial_validation_packet")
    return {
        "ok": True,
        "generated_at": _now_iso(),
        "root": str(root),
        "candidate_inventory": {
            "total": len(rows),
            "status_counts": dict(sorted(status_counts.items())),
            "candidate_type_counts": dict(sorted(type_counts.items())),
            "target_memory_layer_counts": dict(sorted(target_counts.items())),
            "owner_review_required_count": len(owner_review),
            "private_or_owner_scoped_count": len(private_rows),
        },
        "clusters": clusters,
        "duplicate_cluster_count": len(duplicate_clusters),
        "owner_review_required": [_safe_row_item(row) for row in owner_review[:50]],
        "personality": personality,
        "privacy_boundary": privacy_boundary,
        "stage8_memory_governance": stage8,
        "duplicate_consolidation": duplicate_consolidation,
        "learning_trial_validation": learning_trial_validation,
        "recommendations": recommendations,
    }


def render_memory_health_report(report: dict[str, Any]) -> str:
    inventory = report.get("candidate_inventory") if isinstance(report.get("candidate_inventory"), dict) else {}
    personality = report.get("personality") if isinstance(report.get("personality"), dict) else {}
    privacy = report.get("privacy_boundary") if isinstance(report.get("privacy_boundary"), dict) else {}
    lines = [
        "# XinYu Memory Health Report",
        "",
        f"- generated_at: {_one_line(report.get('generated_at'))}",
        f"- root: {_one_line(report.get('root'), limit=260)}",
        "- mode: read_only_preparation",
        "- stable_memory_write: blocked",
        "- owner_private_body: hidden",
        "",
        "## Candidate Inventory",
        f"- total: {_one_line(inventory.get('total'), default='0')}",
        f"- owner_review_required_count: {_one_line(inventory.get('owner_review_required_count'), default='0')}",
        f"- private_or_owner_scoped_count: {_one_line(inventory.get('private_or_owner_scoped_count'), default='0')}",
        f"- duplicate_cluster_count: {_one_line(report.get('duplicate_cluster_count'), default='0')}",
        "",
        "### Status Counts",
    ]
    for key, value in (inventory.get("status_counts") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "### Candidate Type Counts"])
    for key, value in (inventory.get("candidate_type_counts") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Owner Review Required"])
    owner_items = report.get("owner_review_required") if isinstance(report.get("owner_review_required"), list) else []
    if not owner_items:
        lines.append("- none")
    for item in owner_items:
        lines.append(
            "- "
            f"id={_one_line(item.get('candidate_id'), limit=80)}; "
            f"type={_one_line(item.get('candidate_type'), limit=80)}; "
            f"target={_one_line(item.get('target_memory_layer'), limit=140)}; "
            "candidate_text_preview=hidden_owner_review_required"
        )
    lines.extend(["", "## Top Candidate Clusters"])
    clusters = report.get("clusters") if isinstance(report.get("clusters"), list) else []
    if not clusters:
        lines.append("- none")
    for cluster in clusters[:12]:
        lines.append(
            "- "
            f"topic={_one_line(cluster.get('claim_topic_key'), limit=80)}; "
            f"size={_one_line(cluster.get('size'), default='0')}; "
            f"conflicts={_one_line(cluster.get('conflict_count'), default='0')}; "
            f"recommendation={_one_line(cluster.get('recommendation'), limit=100)}; "
            f"statuses={json.dumps(cluster.get('status_counts', {}), ensure_ascii=False, sort_keys=True)}"
        )
    lines.extend(["", "## Personality Gate"])
    for key in sorted(personality):
        lines.append(f"- {key}: {_one_line(personality.get(key), limit=180)}")
    stage8 = report.get("stage8_memory_governance") if isinstance(report.get("stage8_memory_governance"), dict) else {}
    lines.extend(["", "## Stage 8 Memory Governance"])
    for key in (
        "status",
        "ready_for_stage9",
        "reason",
        "stage7_ready_for_stage8",
        "candidate_total",
        "owner_review_required_count",
        "private_or_owner_scoped_count",
        "duplicate_cluster_count",
        "duplicate_consolidation_status",
        "duplicate_consolidation_item_count",
        "duplicate_consolidation_conflict_cluster_count",
        "duplicate_consolidation_ready_cluster_count",
        "duplicate_consolidation_packet_path",
        "learning_trial_success_gate",
        "learning_trial_validation_status",
        "learning_trial_validation_active_key",
        "learning_trial_validation_needed_success_count",
        "learning_trial_validation_owner_action",
        "learning_trial_validation_packet_path",
        "stable_profile_write",
        "owner_memory_write",
        "owner_review_candidate_text",
        "stable_personality_write",
        "growth_apply_mode",
        "stable_identity_profile_apply",
        "next_step",
    ):
        value = stage8.get(key, "missing")
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else _one_line(value, limit=180)}")
    lines.extend(["", "## Privacy Boundary"])
    for key in sorted(privacy):
        lines.append(f"- {key}: {_one_line(privacy.get(key), limit=180)}")
    lines.extend(["", "## Recommendations"])
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def write_memory_health_report(root: Path, report: dict[str, Any], *, output: Path | None = None) -> Path:
    return write_memory_health_report_text(root, render_memory_health_report(report), output=output)


def write_stage8_memory_governance_state(root: Path, report: dict[str, Any], *, report_path: Path | None = None) -> Path:
    root = root.resolve()
    stage8 = report.get("stage8_memory_governance") if isinstance(report.get("stage8_memory_governance"), dict) else {}
    target_report = report_path or memory_health_report_path(root)
    text = f"""---
title: Stage 8 Memory Governance State
memory_type: stage8_memory_governance_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_memory_health_report
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, memory, governance, stage8]
---

# Stage 8 Memory Governance State

## Gate
- stage8_memory_governance_status: {stage8.get('status', 'missing')}
- stage8_memory_ready_for_stage9: {str(bool(stage8.get('ready_for_stage9', False))).lower()}
- stage8_memory_governance_reason: {stage8.get('reason', 'missing')}
- stage8_stage7_ready_for_stage8: {str(bool(stage8.get('stage7_ready_for_stage8', False))).lower()}
- stage8_stage7_reason: {stage8.get('stage7_reason', 'missing')}
- stage8_next_step: {stage8.get('next_step', 'missing')}

## Inventory
- stage8_candidate_total: {stage8.get('candidate_total', 0)}
- stage8_owner_review_required_count: {stage8.get('owner_review_required_count', 0)}
- stage8_private_or_owner_scoped_count: {stage8.get('private_or_owner_scoped_count', 0)}
- stage8_duplicate_cluster_count: {stage8.get('duplicate_cluster_count', 0)}
- stage8_duplicate_consolidation_status: {stage8.get('duplicate_consolidation_status', 'missing')}
- stage8_duplicate_consolidation_item_count: {stage8.get('duplicate_consolidation_item_count', 0)}
- stage8_duplicate_consolidation_conflict_cluster_count: {stage8.get('duplicate_consolidation_conflict_cluster_count', 0)}
- stage8_duplicate_consolidation_ready_cluster_count: {stage8.get('duplicate_consolidation_ready_cluster_count', 0)}
- stage8_learning_trial_success_gate: {stage8.get('learning_trial_success_gate', 'missing')}
- stage8_learning_trial_validation_status: {stage8.get('learning_trial_validation_status', 'missing')}
- stage8_learning_trial_validation_active_key: {stage8.get('learning_trial_validation_active_key', 'none')}
- stage8_learning_trial_validation_needed_success_count: {stage8.get('learning_trial_validation_needed_success_count', 0)}
- stage8_learning_trial_validation_owner_action: {stage8.get('learning_trial_validation_owner_action', 'none')}
- stage8_learning_trial_validation_packet_path: {stage8.get('learning_trial_validation_packet_path', 'none')}

## Boundaries
- stage8_stable_profile_write: {stage8.get('stable_profile_write', 'missing')}
- stage8_owner_memory_write: {stage8.get('owner_memory_write', 'missing')}
- stage8_owner_review_candidate_text: {stage8.get('owner_review_candidate_text', 'missing')}
- stage8_stable_personality_write: {stage8.get('stable_personality_write', 'missing')}
- stage8_growth_apply_mode: {stage8.get('growth_apply_mode', 'missing')}
- stage8_stable_identity_profile_apply: {stage8.get('stable_identity_profile_apply', 'missing')}
- raw_owner_text_in_state: false
- visible_reply_text_in_state: false
- stable_memory_write_without_owner_apply: false
- consciousness_claim: false
- report_path: {target_report.as_posix()}
"""
    return write_stage8_memory_governance_state_text(root, text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build XinYu memory/persona health report without stable writes.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = build_memory_health_report(args.root)
    if args.write:
        path = write_memory_health_report(args.root, report, output=args.output)
        write_stage8_memory_governance_state(args.root, report, report_path=path)
        report["report_path"] = str(path)
        report["stage8_state_path"] = str(args.root.resolve() / STAGE8_STATE_REL)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_memory_health_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
