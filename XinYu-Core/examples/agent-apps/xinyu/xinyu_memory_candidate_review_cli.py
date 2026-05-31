from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates, update_memory_candidate_status
from xinyu_memory_candidate_analysis import candidate_review_context
from xinyu_memory_promotion import apply_stable_memory_promotion, build_stable_memory_promotion_dry_run


STATUSES = (
    "pending",
    "owner_review_required",
    "self_approved_recent_context",
    "self_approved_voice_review",
    "observe_more_owner_preference",
    "observe_more_relationship_signal",
    "observe_more_unknown",
    "blocked_scope_mismatch",
    "blocked_sensitive",
    "archived_observe_more",
    "archived_duplicate",
    "archived_rejected",
    "archived_blocked",
    "rejected",
    "approved",
    "applied_growth_log",
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _dict_field(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    return value if isinstance(value, dict) else {}


def _evidence_summary(row: dict[str, Any]) -> dict[str, Any]:
    evidence = _dict_field(row, "evidence")
    provenance = _dict_field(row, "provenance")
    return {
        "source_scope": evidence.get("source_scope") or provenance.get("dialogue_scope", ""),
        "source_turn_id": evidence.get("source_turn_id") or row.get("source_turn_id", ""),
        "source_message_count": evidence.get("source_message_count", len(row.get("source_message_ids", []) or [])),
        "confidence_score": evidence.get("confidence_score", row.get("confidence_score", 0)),
        "immune_status": evidence.get("immune_status", ""),
        "immune_danger_level": evidence.get("immune_danger_level", ""),
        "immune_action": evidence.get("immune_action", ""),
        "event_time": provenance.get("event_time") or row.get("created_at", ""),
        "stable_memory_write_allowed": provenance.get("stable_memory_write_allowed", False),
        "promotion_requires_review": provenance.get("promotion_requires_review", True),
    }


def _stable_memory_write_status(row: dict[str, Any]) -> str:
    provenance = _dict_field(row, "provenance")
    if provenance.get("stable_memory_write_allowed") is True:
        return "allowed_by_provenance"
    return "blocked_until_review"


def _all_candidates(root: Path, *, limit: int = 200) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status in STATUSES:
        for row in list_memory_candidates(root, status=status, limit=limit):
            candidate_id = _safe_str(row.get("candidate_id"))
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append(row)
    return rows


def get_candidate(root: Path, candidate_id: str) -> dict[str, Any] | None:
    clean_id = _safe_str(candidate_id).strip()
    for row in _all_candidates(root):
        if row.get("candidate_id") == clean_id:
            return row
    return None


def list_candidates(root: Path, *, status: str = "pending", limit: int = 20) -> dict[str, Any]:
    rows = list_memory_candidates(root, status=status, limit=limit)
    return {"ok": True, "status": status, "count": len(rows), "candidates": rows}


def show_candidate(root: Path, candidate_id: str) -> dict[str, Any]:
    row = get_candidate(root, candidate_id)
    if row is None:
        return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}
    return {"ok": True, "candidate": row}


def explain_candidate(root: Path, candidate_id: str) -> dict[str, Any]:
    row = get_candidate(root, candidate_id)
    if row is None:
        return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}
    review_context = candidate_review_context(row, _all_candidates(root))
    return {
        "ok": True,
        "candidate_id": row.get("candidate_id"),
        "source_turn_id": row.get("source_turn_id", ""),
        "source_message_ids": row.get("source_message_ids", []),
        "extraction_reason": row.get("reason", ""),
        "risk_flags": row.get("risk_flags", []),
        "evidence": _dict_field(row, "evidence"),
        "provenance": _dict_field(row, "provenance"),
        "evidence_summary": _evidence_summary(row),
        "memory_review": review_context,
        "target_gate": row.get("target_gate", ""),
        "target_memory_layer": row.get("target_memory_layer", ""),
        "status": row.get("status", ""),
        "stable_memory_write": _stable_memory_write_status(row),
    }


def decide_candidate(root: Path, candidate_id: str, *, decision: str, review_notes: str = "") -> dict[str, Any]:
    status = "approved" if decision == "approve" else "rejected"
    row = get_candidate(root, candidate_id)
    if row is None:
        return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}
    if decision == "approve":
        review_context = candidate_review_context(row, _all_candidates(root))
        approval_error = _approval_error(row, review_notes=review_notes, review_context=review_context)
        if approval_error:
            return {"ok": False, "error": approval_error, "candidate_id": candidate_id, "status": row.get("status", "")}
    if not update_memory_candidate_status(root, candidate_id=candidate_id, status=status, review_notes=review_notes):
        return {"ok": False, "error": "candidate_update_failed", "candidate_id": candidate_id}
    result = {"ok": True, "candidate_id": candidate_id, "status": status, "review_notes": review_notes}
    if decision == "approve":
        preview = build_stable_memory_promotion_dry_run(root, candidate_id, write_preview=True)
        result.update(
            {
                "stable_memory_write": "dry_run_only",
                "apply_allowed": False,
                "promotion_preview_path": preview.get("preview_path", ""),
                "promotion_preview_before_hash": preview.get("before_hash", ""),
                "promotion_preview_blockers": preview.get("blockers", []),
                "notes": ["approval_recorded", "promotion_preview_written", "stable_memory_not_modified"],
            }
        )
    return result


def dry_run_candidate_promotion(
    root: Path,
    candidate_id: str,
    *,
    allow_unapproved: bool = False,
    write_preview: bool = False,
) -> dict[str, Any]:
    return build_stable_memory_promotion_dry_run(
        root,
        candidate_id,
        allow_unapproved=allow_unapproved,
        write_preview=write_preview,
    )


def apply_candidate_promotion(
    root: Path,
    candidate_id: str,
    *,
    review_notes: str = "",
    expected_before_hash: str = "",
) -> dict[str, Any]:
    return apply_stable_memory_promotion(
        root,
        candidate_id,
        review_notes=review_notes,
        expected_before_hash=expected_before_hash,
    )


def _approval_error(row: dict[str, Any], *, review_notes: str, review_context: dict[str, Any] | None = None) -> str:
    risk_text = " ".join(_safe_str(flag).lower() for flag in row.get("risk_flags", []))
    risk_text += " " + _safe_str(row.get("review_notes")).lower()
    risk_text += " " + _safe_str(row.get("reason")).lower()
    if any(marker in risk_text for marker in ("runtime_trace", "timeout", "temporary_operational")):
        return "runtime_or_timeout_candidate_cannot_be_approved_directly"
    context = review_context if isinstance(review_context, dict) else {}
    if context.get("conflict_count", 0) and "owner_resolved_conflict" not in review_notes:
        return "candidate_conflict_requires_owner_resolution"
    high_risk_types = {
        "relationship_signal",
        "owner_preference",
        "personality_change",
        "voice_correction",
        "post_reply_growth_candidate",
    }
    candidate_type = _safe_str(row.get("candidate_type")).strip()
    if candidate_type in high_risk_types and "owner_approved_high_risk" not in review_notes:
        return "high_risk_candidate_requires_explicit_owner_approval"
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review XinYu memory candidates.")
    parser.add_argument("--root", type=Path, default=Path("."))
    sub = parser.add_subparsers(dest="command", required=True)
    list_parser = sub.add_parser("list")
    list_parser.add_argument("--status", default="pending")
    list_parser.add_argument("--limit", type=int, default=20)
    for name in ("show", "explain", "approve", "reject", "dry-run", "apply"):
        item = sub.add_parser(name)
        item.add_argument("candidate_id")
        if name in {"approve", "reject", "apply"}:
            item.add_argument("--notes", default="")
        if name == "dry-run":
            item.add_argument("--allow-unapproved", action="store_true")
            item.add_argument("--write-preview", action="store_true")
        if name == "apply":
            item.add_argument("--expected-before-hash", default="")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "list":
        result = list_candidates(root, status=args.status, limit=args.limit)
    elif args.command == "show":
        result = show_candidate(root, args.candidate_id)
    elif args.command == "explain":
        result = explain_candidate(root, args.candidate_id)
    elif args.command == "approve":
        result = decide_candidate(root, args.candidate_id, decision="approve", review_notes=args.notes)
    elif args.command == "dry-run":
        result = dry_run_candidate_promotion(
            root,
            args.candidate_id,
            allow_unapproved=args.allow_unapproved,
            write_preview=args.write_preview,
        )
    elif args.command == "apply":
        result = apply_candidate_promotion(
            root,
            args.candidate_id,
            review_notes=args.notes,
            expected_before_hash=args.expected_before_hash,
        )
    else:
        result = decide_candidate(root, args.candidate_id, decision="reject", review_notes=args.notes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
