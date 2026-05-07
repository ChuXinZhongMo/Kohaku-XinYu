from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from source_request_planner_engine import split_requests
from source_search_provider_engine import SUPPORTED_PROVIDERS, provider_name
from source_search_resolver_engine import split_existing_results


READY_PERMISSIONS = {"prepare_only", "integrate_ready"}
ACTIVE_MODES = {"enabled", "dry_run"}
QUALITY_FOLLOWUP_KINDS = {"source_diversity", "quality_followup", "corroboration_followup"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def activation_mode(root: Path | None = None) -> str:
    raw = os.environ.get("XINYU_AUTONOMOUS_SEARCH")
    if raw is not None and raw.strip():
        return raw.strip().lower()
    if root is not None:
        try:
            capability = read_text(root / "memory/context/capability_zones_state.md")
            grants = read_text(root / "memory/context/owner_permission_grants.md")
        except OSError:
            capability = ""
            grants = ""
        if (
            "autonomous_search_provider: enabled_duckduckgo_html_bounded_ai_domain" in capability
            and "grant_autonomous_source_collect: approved_bounded_candidate_material_only" in grants
        ):
            return "enabled"
    return "disabled"


def max_queries_per_pass() -> int:
    raw = os.environ.get("XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES", "1").strip()
    try:
        return max(0, min(int(raw), 3))
    except ValueError:
        return 1


def owner_high_autonomy_granted(root: Path) -> bool:
    try:
        grants = read_text(root / "memory/context/owner_permission_grants.md")
    except OSError:
        return False
    return (
        "grant_high_autonomy_learning_search: "
        "approved_budgeted_ai_domain_and_quality_followup_search_through_gates"
    ) in grants or "grant_autonomous_source_collect: approved_bounded_candidate_material_only" in grants


def render_state(
    evaluated_at: str,
    mode: str,
    activation: str,
    provider: str,
    permission: str,
    reason: str,
    pending_url_requests: int,
    candidate_results: int,
    integration_permission: str,
    quality_grade: str,
    quality_warnings: str,
    owner_high_autonomy_search: bool,
    quality_followup_pending: bool,
    allowed_queries: int,
) -> str:
    return f"""---
title: Autonomous Search Activation State
memory_type: autonomous_search_activation_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 84
impact_score: 83
confidence_score: 100
status: active
tags: [knowledge, search, activation]
---

# Autonomous Search Activation State

## Last Evaluation
- evaluated_at: {evaluated_at}
- mode: {mode}
- activation_mode: {activation}
- provider: {provider}
- activation_permission: {permission}
- activation_reason: {reason}
- allowed_queries: {allowed_queries}
- pending_url_requests: {pending_url_requests}
- candidate_results: {candidate_results}
- integration_permission: {integration_permission}
- learning_quality_grade: {quality_grade}
- learning_quality_warnings: {quality_warnings}
- owner_high_autonomy_search: {"yes" if owner_high_autonomy_search else "no"}
- quality_followup_pending: {"yes" if quality_followup_pending else "no"}

## Boundaries
- This gate only decides whether a provider search may run in this maintenance pass.
- It never fetches pages, accepts URLs, or learns claims.
- Provider output must still pass search result gate, outward source fetch, source comparison, learner integration, and learning quality checks.
- It does not rewrite self, owner, relationship, emotion, dream, or archive memory.
"""


def run_autonomous_search_activation(
    root: Path,
    evaluated_at: str | None = None,
    mode: str = "runtime_autonomous_search_activation",
) -> dict[str, object]:
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()
    activation = activation_mode(root)
    provider = provider_name(root)
    requests = split_requests(read_text(root / "memory/knowledge/source_requests.md"))
    pending = [item for item in requests if item.get("status") == "pending_url"]
    pending_request_ids = {item.get("request_id") for item in pending}
    results = split_existing_results(read_text(root / "memory/knowledge/source_search_results.md"))
    candidates = [
        item
        for item in results
        if item.get("status") == "candidate" and item.get("request_id") in pending_request_ids
    ]
    integration_text = read_text(root / "memory/knowledge/source_integration_gate_state.md")
    integration_permission = extract_value(integration_text, "integration_permission", "hold")
    quality_text = read_text(root / "memory/knowledge/learning_quality_state.md")
    quality_grade = extract_value(quality_text, "quality_grade", "unknown")
    quality_warnings = extract_value(quality_text, "warning_count", "0")
    learned_entries = extract_value(quality_text, "learned_entries", "0")
    high_autonomy = owner_high_autonomy_granted(root)
    quality_needs_review = quality_grade == "review_needed" or quality_warnings not in {"0", "unknown"}
    quality_followup_pending = any(item.get("followup_kind") in QUALITY_FOLLOWUP_KINDS for item in pending)

    permission = "blocked"
    reason = "not_evaluated"
    allowed_queries = 0
    if activation not in ACTIVE_MODES:
        permission = "disabled"
        reason = "activation_disabled"
    elif provider not in SUPPORTED_PROVIDERS:
        reason = "provider_disabled_or_unsupported"
    elif integration_permission not in READY_PERMISSIONS:
        reason = "integration_gate_not_open"
    elif not pending:
        reason = "no_pending_url_requests"
    elif candidates:
        reason = "candidate_results_already_waiting"
    elif quality_needs_review and not high_autonomy and not quality_followup_pending:
        reason = "learning_quality_needs_review"
    elif quality_grade == "unknown" and learned_entries not in {"0", "unknown"}:
        reason = "learning_quality_unknown_after_learning"
    elif activation == "dry_run":
        permission = "observe_only"
        reason = "dry_run"
    else:
        permission = "provider_allowed"
        if quality_needs_review and high_autonomy:
            reason = "owner_high_autonomy_quality_followup_allowed"
        elif quality_needs_review and quality_followup_pending:
            reason = "learning_quality_followup_search_allowed"
        else:
            reason = "all_gates_open"
        allowed_queries = min(len(pending), max_queries_per_pass())

    write_text(
        root / "memory/knowledge/autonomous_search_activation_state.md",
        render_state(
            evaluated_at,
            mode,
            activation,
            provider,
            permission,
            reason,
            len(pending),
            len(candidates),
            integration_permission,
            quality_grade,
            quality_warnings,
            high_autonomy,
            quality_followup_pending,
            allowed_queries,
        ),
    )
    return {
        "evaluated_at": evaluated_at,
        "activation_mode": activation,
        "provider": provider,
        "activation_permission": permission,
        "activation_reason": reason,
        "allowed_queries": allowed_queries,
        "pending_url_requests": len(pending),
        "candidate_results": len(candidates),
        "integration_permission": integration_permission,
        "learning_quality_grade": quality_grade,
        "learning_quality_warnings": quality_warnings,
        "quality_followup_pending": quality_followup_pending,
    }
