from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates, update_memory_candidate_status
from xinyu_group_memory_pipeline import group_candidate_layer_allowed, group_full_memory_pipeline_enabled
from xinyu_memory_candidate_analysis import candidate_review_context


STATE_REL = Path("memory/context/memory_self_review_state.md")
TRACE_REL = Path("runtime/memory_self_review_trace.jsonl")

SELF_APPROVED_RECENT_CONTEXT = "self_approved_recent_context"
SELF_APPROVED_VOICE_REVIEW = "self_approved_voice_review"
OBSERVE_MORE_OWNER_PREFERENCE = "observe_more_owner_preference"
OBSERVE_MORE_RELATIONSHIP_SIGNAL = "observe_more_relationship_signal"
OBSERVE_MORE_UNKNOWN = "observe_more_unknown"
OWNER_REVIEW_REQUIRED = "owner_review_required"
BLOCKED_SCOPE_MISMATCH = "blocked_scope_mismatch"
BLOCKED_SENSITIVE = "blocked_sensitive"
MEMORY_REVIEW_CONTEXT_STATUSES = (
    "pending",
    OWNER_REVIEW_REQUIRED,
    SELF_APPROVED_RECENT_CONTEXT,
    SELF_APPROVED_VOICE_REVIEW,
    OBSERVE_MORE_OWNER_PREFERENCE,
    OBSERVE_MORE_RELATIONSHIP_SIGNAL,
    OBSERVE_MORE_UNKNOWN,
    "approved",
)

GROUP_SCOPE_MARKERS = (
    "group-scoped",
    "group_scope",
    "group_context",
    "owner_group",
    "qq:group",
    "message_type: group",
)
OWNER_RELATIONSHIP_LAYERS = (
    "memory/people/",
    "memory/relationships/",
)
SENSITIVE_SELF_LAYERS = (
    "memory/self/core.md",
    "memory/self/personality_profile.md",
    "memory/self/system_prompt_memory.md",
    "prompts/system.md",
)
POLICY_LAYERS = (
    "memory/context/owner_permission_grants.md",
    "memory/context/codex_delegation_policy.md",
    "config.yaml",
)
STABLE_CHANGE_MARKERS = (
    "stable identity",
    "permanent identity",
    "rewrite core",
    "rewrite personality",
    "change personality",
    "system prompt",
    "permission grant",
    "owner permission",
)
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bprivate[_ -]?key\b"),
    re.compile(r"(?i)\bcookie\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bsession[_ -]?(?:key|token|cookie)\b"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _one_line(value: Any, *, limit: int = 240, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _candidate_id(row: dict[str, Any]) -> str:
    return _one_line(row.get("candidate_id"), limit=100, default="unknown")


def _combined(row: dict[str, Any]) -> str:
    return "\n".join(
        [
            _safe_str(row.get("candidate_type")),
            _safe_str(row.get("target_gate")),
            _safe_str(row.get("target_memory_layer")),
            _safe_str(row.get("reason")),
            _safe_str(row.get("candidate_text")),
        ]
    )


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker and marker.lower() in lowered for marker in markers)


def _target_layer(row: dict[str, Any]) -> str:
    return _safe_str(row.get("target_memory_layer")).strip().replace("\\", "/").lower()


def _candidate_type(row: dict[str, Any]) -> str:
    return _safe_str(row.get("candidate_type")).strip().lower()


def _is_group_scoped(row: dict[str, Any]) -> bool:
    return _contains_any(_combined(row), GROUP_SCOPE_MARKERS)


def _is_owner_relationship_layer(layer: str) -> bool:
    return any(layer.startswith(prefix) for prefix in OWNER_RELATIONSHIP_LAYERS)


def _has_secret_or_private_credential(row: dict[str, Any]) -> bool:
    text = _combined(row)
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def _requires_owner_review(row: dict[str, Any]) -> bool:
    layer = _target_layer(row)
    combined = _combined(row)
    if layer in SENSITIVE_SELF_LAYERS or layer in POLICY_LAYERS:
        return True
    if _contains_any(combined, STABLE_CHANGE_MARKERS):
        return True
    return False


def review_memory_candidate(row: dict[str, Any], *, context_rows: list[dict[str, Any]] | None = None) -> dict[str, str]:
    ctype = _candidate_type(row)
    layer = _target_layer(row)
    memory_review = candidate_review_context(row, context_rows or [row])

    if _has_secret_or_private_credential(row):
        return _decision(
            row,
            status=BLOCKED_SENSITIVE,
            action="block_candidate",
            risk="sensitive",
            rationale="candidate contains credential-like or private security material",
            memory_review=memory_review,
        )

    if _is_group_scoped(row) and (ctype in {"owner_preference", "relationship_signal"} or _is_owner_relationship_layer(layer)):
        if not (
            group_full_memory_pipeline_enabled(None)
            and group_candidate_layer_allowed(None, target_layer=layer)
        ):
            return _decision(
                row,
                status=BLOCKED_SCOPE_MISMATCH,
                action="block_candidate",
                risk="scope_mismatch",
                rationale="group-scoped material cannot become owner or relationship memory",
                memory_review=memory_review,
            )

    if int(memory_review.get("conflict_count", 0) or 0) > 0:
        return _decision(
            row,
            status=OWNER_REVIEW_REQUIRED,
            action="hold_for_owner_conflict_resolution",
            risk="conflict",
            rationale="candidate conflicts with active memory candidate evidence",
            memory_review=memory_review,
        )

    if _requires_owner_review(row):
        return _decision(
            row,
            status=OWNER_REVIEW_REQUIRED,
            action="ask_owner_only_if_promotion_is_needed",
            risk="stable_identity_or_policy",
            rationale="candidate would alter stable self, prompt, permission, or policy memory",
            memory_review=memory_review,
        )

    if ctype in {"project_fact", "codex_result"} and layer == "memory/context/recent_context.md":
        return _decision(
            row,
            status=SELF_APPROVED_RECENT_CONTEXT,
            action="keep_as_recent_project_continuity",
            risk="low",
            rationale="project continuity can be carried as short-term context without stable profile write",
            memory_review=memory_review,
        )

    if ctype == "voice_correction":
        return _decision(
            row,
            status=SELF_APPROVED_VOICE_REVIEW,
            action="keep_as_voice_review_evidence",
            risk="medium",
            rationale="voice correction can be kept as review evidence but cannot rewrite stable voice profile here",
            memory_review=memory_review,
        )

    if ctype == "post_reply_growth_candidate":
        return _decision(
            row,
            status=OWNER_REVIEW_REQUIRED,
            action="ask_owner_to_confirm_growth_log_draft",
            risk="medium",
            rationale="post-reply growth candidates may become growth-log drafts only after owner review and never rewrite stable personality here",
            memory_review=memory_review,
        )

    if ctype == "owner_preference":
        if int(memory_review.get("evidence_count", 1) or 1) >= 2:
            return _decision(
                row,
                status=OWNER_REVIEW_REQUIRED,
                action="ask_owner_to_confirm_repeated_preference",
                risk="medium",
                rationale="repeated owner preference evidence is ready for owner review but not stable memory",
                memory_review=memory_review,
            )
        return _decision(
            row,
            status=OBSERVE_MORE_OWNER_PREFERENCE,
            action="observe_for_repetition",
            risk="medium",
            rationale="one owner preference signal is not enough to rewrite stable owner memory",
            memory_review=memory_review,
        )

    if ctype == "relationship_signal":
        if int(memory_review.get("evidence_count", 1) or 1) >= 2:
            return _decision(
                row,
                status=OWNER_REVIEW_REQUIRED,
                action="ask_owner_to_confirm_repeated_relationship_signal",
                risk="medium",
                rationale="repeated relationship evidence is ready for owner review but not stable memory",
                memory_review=memory_review,
            )
        return _decision(
            row,
            status=OBSERVE_MORE_RELATIONSHIP_SIGNAL,
            action="observe_for_emotional_repetition",
            risk="medium",
            rationale="relationship residue should not be frozen from one turn",
            memory_review=memory_review,
        )

    return _decision(
        row,
        status=OBSERVE_MORE_UNKNOWN,
        action="observe_without_promotion",
        risk="unknown",
        rationale="candidate type is not recognized by the self-review gate",
        memory_review=memory_review,
    )


def _decision(
    row: dict[str, Any],
    *,
    status: str,
    action: str,
    risk: str,
    rationale: str,
    memory_review: dict[str, Any] | None = None,
) -> dict[str, str]:
    review = memory_review if isinstance(memory_review, dict) else {}
    evidence_count = _one_line(review.get("evidence_count"), limit=20, default="1")
    conflict_count = _one_line(review.get("conflict_count"), limit=20, default="0")
    recommendation = _one_line(review.get("recommendation"), limit=80, default="single_candidate_review")
    notes = (
        f"{status}; action={action}; risk={risk}; rationale={rationale}; "
        f"memory_review={recommendation}; evidence_count={evidence_count}; conflict_count={conflict_count}; "
        "stable_memory_write=blocked; owner_bulk_review_required=false"
    )
    return {
        "candidate_id": _candidate_id(row),
        "candidate_type": _one_line(row.get("candidate_type"), limit=80),
        "target_memory_layer": _one_line(row.get("target_memory_layer"), limit=140),
        "confidence_score": _one_line(row.get("confidence_score"), limit=20, default="0"),
        "status": status,
        "action": action,
        "risk": risk,
        "rationale": rationale,
        "memory_review_recommendation": recommendation,
        "evidence_count": evidence_count,
        "conflict_count": conflict_count,
        "supporting_candidate_ids": _one_line(", ".join(review.get("supporting_candidate_ids", []) or []), limit=220),
        "conflicting_candidate_ids": _one_line(", ".join(review.get("conflicting_candidate_ids", []) or []), limit=220),
        "review_notes": notes,
    }


def run_memory_self_review(
    root: Path,
    *,
    checked_at: str | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    root = root.resolve()
    checked = checked_at or _now_iso()
    rows = list_memory_candidates(root, status="pending", limit=max(1, int(limit)))
    context_rows = _memory_review_context_rows(root, pending_rows=rows, limit=max(1, int(limit)))
    decisions: list[dict[str, str]] = []
    update_errors: list[str] = []

    for row in rows:
        decision = review_memory_candidate(row, context_rows=context_rows)
        if update_memory_candidate_status(
            root,
            candidate_id=decision["candidate_id"],
            status=decision["status"],
            review_notes=decision["review_notes"],
        ):
            decisions.append(decision)
        else:
            update_errors.append(decision["candidate_id"])

    result = _build_result(checked_at=checked, decisions=decisions, pending_seen=len(rows), update_errors=update_errors)
    _write(root / STATE_REL, _render_state(result))
    _append_trace(root, result)
    return result


def _build_result(
    *,
    checked_at: str,
    decisions: list[dict[str, str]],
    pending_seen: int,
    update_errors: list[str],
) -> dict[str, Any]:
    self_approved = sum(1 for item in decisions if item["status"].startswith("self_approved_"))
    observe_more = sum(1 for item in decisions if item["status"].startswith("observe_more_"))
    owner_review = sum(1 for item in decisions if item["status"] == OWNER_REVIEW_REQUIRED)
    blocked = sum(1 for item in decisions if item["status"].startswith("blocked_"))
    conflict_review = sum(1 for item in decisions if item.get("risk") == "conflict")
    latest = decisions[0] if decisions else {}
    notes = []
    if decisions:
        notes.append("memory_self_review_completed")
    else:
        notes.append("memory_self_review_no_pending")
    if update_errors:
        notes.append(f"update_errors:{len(update_errors)}")
    return {
        "checked_at": checked_at,
        "status": "reviewed" if decisions else "no_pending_candidates",
        "pending_seen": pending_seen,
        "reviewed_candidates": len(decisions),
        "self_approved": self_approved,
        "observe_more": observe_more,
        "owner_review_required": owner_review,
        "blocked": blocked,
        "conflict_review_required": conflict_review,
        "latest_candidate_id": latest.get("candidate_id", "none"),
        "latest_decision": latest.get("status", "none"),
        "latest_action": latest.get("action", "none"),
        "decisions": decisions,
        "update_errors": update_errors,
        "notes": notes,
    }


def _render_state(result: dict[str, Any]) -> str:
    decision_lines: list[str] = []
    decisions = result.get("decisions")
    if isinstance(decisions, list) and decisions:
        for index, item in enumerate(decisions[:12], 1):
            if not isinstance(item, dict):
                continue
            decision_lines.extend(
                [
                    f"### decision-{index}",
                    f"- candidate_id: {_one_line(item.get('candidate_id'), limit=100)}",
                    f"- candidate_type: {_one_line(item.get('candidate_type'), limit=80)}",
                    f"- decision: {_one_line(item.get('status'), limit=80)}",
                    f"- action: {_one_line(item.get('action'), limit=100)}",
                    f"- risk: {_one_line(item.get('risk'), limit=80)}",
                    f"- memory_review: {_one_line(item.get('memory_review_recommendation'), limit=80)}",
                    f"- evidence_count: {_one_line(item.get('evidence_count'), limit=20)}",
                    f"- conflict_count: {_one_line(item.get('conflict_count'), limit=20)}",
                    f"- supporting_candidate_ids: {_one_line(item.get('supporting_candidate_ids'), limit=220)}",
                    f"- conflicting_candidate_ids: {_one_line(item.get('conflicting_candidate_ids'), limit=220)}",
                    f"- target_memory_layer: {_one_line(item.get('target_memory_layer'), limit=140)}",
                    f"- rationale: {_one_line(item.get('rationale'), limit=220)}",
                    "",
                ]
            )
    else:
        decision_lines.extend(["### decision-none", "- candidate_id: none", "- decision: none", ""])

    notes = "\n".join(f"- {_one_line(note, limit=160)}" for note in result.get("notes", [])) or "- none"
    return f"""---
title: Memory Self Review State
memory_type: memory_self_review_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_memory_self_review
updated_at: {_one_line(result['checked_at'])}
status: active
tags: [memory, self-review, gate]
---

# Memory Self Review State

## Latest Review
- checked_at: {_one_line(result['checked_at'])}
- status: {_one_line(result['status'])}
- pending_seen: {_one_line(result['pending_seen'])}
- reviewed_candidates: {_one_line(result['reviewed_candidates'])}
- self_approved: {_one_line(result['self_approved'])}
- observe_more: {_one_line(result['observe_more'])}
- owner_review_required: {_one_line(result['owner_review_required'])}
- blocked: {_one_line(result['blocked'])}
- conflict_review_required: {_one_line(result['conflict_review_required'])}
- latest_candidate_id: {_one_line(result['latest_candidate_id'], limit=100)}
- latest_decision: {_one_line(result['latest_decision'], limit=80)}
- latest_action: {_one_line(result['latest_action'], limit=100)}

## Policy
- self_review_scope: pending_memory_candidates_only
- stable_memory_write: blocked
- owner_bulk_review_required: false
- owner_review_only_for: stable_identity_policy_sensitive_or_ambiguous_long_term_changes
- project_continuity_default: self_approved_recent_context
- voice_correction_default: self_approved_voice_review_without_profile_rewrite
- owner_preference_default: observe_more_until_repeated
- relationship_signal_default: observe_more_until_repeated
- repeated_owner_preference_or_relationship_signal: owner_review_required_without_stable_write
- conflicting_candidate_evidence: owner_review_required_conflict_resolution
- group_owner_relationship_memory: blocked_scope_mismatch
- credential_or_secret_material: blocked_sensitive

## Recent Decisions
{chr(10).join(decision_lines).rstrip()}

## Notes
{notes}
"""


def _append_trace(root: Path, result: dict[str, Any]) -> None:
    payload = {
        "checked_at": result["checked_at"],
        "status": result["status"],
        "pending_seen": result["pending_seen"],
        "reviewed_candidates": result["reviewed_candidates"],
        "self_approved": result["self_approved"],
        "observe_more": result["observe_more"],
        "owner_review_required": result["owner_review_required"],
        "blocked": result["blocked"],
        "conflict_review_required": result["conflict_review_required"],
        "latest_decision": result["latest_decision"],
        "notes": result["notes"][:8],
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _memory_review_context_rows(
    root: Path,
    *,
    pending_rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in pending_rows:
        candidate_id = _safe_str(row.get("candidate_id")).strip()
        if candidate_id and candidate_id not in seen:
            seen.add(candidate_id)
            rows.append(row)
    for status in MEMORY_REVIEW_CONTEXT_STATUSES:
        for row in list_memory_candidates(root, status=status, limit=max(1, int(limit))):
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append(row)
    return rows


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review XinYu pending memory candidates before any stable promotion.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_memory_self_review(args.root.resolve(), limit=max(1, args.limit))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(_render_state(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
