from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import (
    list_memory_candidates,
    update_memory_candidate_metadata,
    update_memory_candidate_status,
)
from xinyu_memory_candidate_analysis import candidate_claim_metadata_from_row, candidate_review_context
from xinyu_memory_candidate_maintenance_store import STATE_REL
from xinyu_memory_candidate_maintenance_store import TRACE_REL
from xinyu_memory_candidate_maintenance_store import append_memory_candidate_maintenance_trace
from xinyu_memory_candidate_maintenance_store import write_memory_candidate_maintenance_state


MAINTENANCE_STATUSES = (
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
)
OBSERVE_MORE_STATUSES = {
    "observe_more_owner_preference",
    "observe_more_relationship_signal",
    "observe_more_unknown",
}
BLOCKED_STATUSES = {"blocked_scope_mismatch", "blocked_sensitive"}
ARCHIVE_STATUS_BY_SOURCE = {
    "rejected": "archived_rejected",
    "blocked_scope_mismatch": "archived_blocked",
    "blocked_sensitive": "archived_blocked",
}
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


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _all_candidate_rows(root: Path, *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status in MAINTENANCE_STATUSES:
        for row in list_memory_candidates(root, status=status, limit=max(1, int(limit))):
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append(row)
    return rows


def backfill_memory_candidate_metadata(root: Path, *, limit: int = 500) -> dict[str, Any]:
    root = root.resolve()
    rows = _all_candidate_rows(root, limit=limit)
    updated: list[str] = []
    skipped: list[str] = []
    for row in rows:
        candidate_id = _safe_str(row.get("candidate_id")).strip()
        evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        claim = candidate_claim_metadata_from_row(row)
        new_evidence = {
            "evidence_kind": evidence.get("evidence_kind") or "dialogue_turn",
            "source_scope": evidence.get("source_scope") or _scope_from_row(row),
            "source_turn_id": evidence.get("source_turn_id") or row.get("source_turn_id", ""),
            "source_message_ids": evidence.get("source_message_ids") or row.get("source_message_ids", []),
            "source_message_count": evidence.get("source_message_count") or len(row.get("source_message_ids", []) or []),
            "confidence_score": evidence.get("confidence_score", row.get("confidence_score", 0)),
            "reason": evidence.get("reason") or row.get("reason", ""),
            "target_gate": evidence.get("target_gate") or row.get("target_gate", ""),
            "target_memory_layer": evidence.get("target_memory_layer") or row.get("target_memory_layer", ""),
            "created_at": evidence.get("created_at") or row.get("created_at", ""),
            **evidence,
            **{key: value for key, value in claim.items() if not evidence.get(key)},
        }
        new_provenance = {
            "event_time": provenance.get("event_time") or row.get("created_at", ""),
            "stable_memory_write_allowed": provenance.get("stable_memory_write_allowed", False),
            "promotion_requires_review": provenance.get("promotion_requires_review", True),
            "schema": provenance.get("schema") or "memory_candidate_backfill_v1",
            **provenance,
        }
        if new_evidence == evidence and new_provenance == provenance:
            skipped.append(candidate_id)
            continue
        if update_memory_candidate_metadata(root, candidate_id=candidate_id, evidence=new_evidence, provenance=new_provenance):
            updated.append(candidate_id)
        else:
            skipped.append(candidate_id)
    return {
        "backfilled": len(updated),
        "scanned": len(rows),
        "updated_candidate_ids": updated[:50],
        "skipped": len(skipped),
    }


def cleanup_memory_candidates(
    root: Path,
    *,
    checked_at: str | None = None,
    observe_more_days: int = 30,
    rejected_days: int = 14,
    blocked_days: int = 30,
    limit: int = 500,
) -> dict[str, Any]:
    root = root.resolve()
    checked = _parse_iso(checked_at) or datetime.now().astimezone()
    rows = _all_candidate_rows(root, limit=limit)
    archived: list[dict[str, str]] = []
    for row in rows:
        status = _safe_str(row.get("status"))
        created = _parse_iso(row.get("created_at")) or checked
        age = checked - created
        target_status = ""
        reason = ""
        if status in OBSERVE_MORE_STATUSES and age >= timedelta(days=max(1, observe_more_days)):
            review = candidate_review_context(row, rows)
            if int(review.get("evidence_count", 1) or 1) <= 1 and int(review.get("conflict_count", 0) or 0) == 0:
                target_status = "archived_observe_more"
                reason = "stale_observe_more_without_repeated_evidence"
        elif status == "rejected" and age >= timedelta(days=max(1, rejected_days)):
            target_status = "archived_rejected"
            reason = "stale_rejected_candidate"
        elif status in BLOCKED_STATUSES and age >= timedelta(days=max(1, blocked_days)):
            target_status = ARCHIVE_STATUS_BY_SOURCE.get(status, "archived_blocked")
            reason = "stale_blocked_candidate"
        if not target_status:
            continue
        candidate_id = _safe_str(row.get("candidate_id"))
        notes = _append_review_note(row, f"{reason}; archived_at={checked.isoformat(timespec='seconds')}")
        if update_memory_candidate_status(root, candidate_id=candidate_id, status=target_status, review_notes=notes):
            archived.append({"candidate_id": candidate_id, "from": status, "to": target_status, "reason": reason})
    return {
        "checked_at": checked.isoformat(timespec="seconds"),
        "scanned": len(rows),
        "archived": len(archived),
        "archived_items": archived[:50],
    }


def run_memory_candidate_maintenance(
    root: Path,
    *,
    checked_at: str | None = None,
    limit: int = 500,
    write_state: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    checked = checked_at or _now_iso()
    backfill = backfill_memory_candidate_metadata(root, limit=limit)
    cleanup = cleanup_memory_candidates(root, checked_at=checked, limit=limit)
    result = {
        "checked_at": checked,
        "backfill": backfill,
        "cleanup": cleanup,
        "notes": ["memory_candidate_maintenance_completed"],
    }
    if write_state:
        _write_state(root, result)
        _append_trace(root, result)
    return result


def _scope_from_row(row: dict[str, Any]) -> str:
    flags = row.get("risk_flags") if isinstance(row.get("risk_flags"), list) else []
    for flag in flags:
        text = _safe_str(flag)
        if text.startswith("scope:"):
            return text.split(":", 1)[1].strip()
    return "unknown"


def _append_review_note(row: dict[str, Any], note: str) -> str:
    current = _safe_str(row.get("review_notes")).strip()
    if not current:
        return note
    return f"{current}; {note}"


def _write_state(root: Path, result: dict[str, Any]) -> None:
    cleanup = result.get("cleanup") if isinstance(result.get("cleanup"), dict) else {}
    backfill = result.get("backfill") if isinstance(result.get("backfill"), dict) else {}
    text = f"""---
title: Memory Candidate Maintenance State
memory_type: memory_candidate_maintenance_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_memory_candidate_maintenance
updated_at: {_safe_str(result.get('checked_at'))}
status: active
tags: [memory, candidates, maintenance]
---

# Memory Candidate Maintenance State

## Latest
- checked_at: {_safe_str(result.get('checked_at'))}
- scanned: {_safe_str(cleanup.get('scanned'), '0')}
- backfilled: {_safe_str(backfill.get('backfilled'), '0')}
- archived: {_safe_str(cleanup.get('archived'), '0')}
- stable_memory_write: blocked

## Policy
- backfill: metadata_only_no_candidate_text_rewrite
- observe_more_cleanup: archive_stale_singletons
- rejected_cleanup: archive_after_review_window
- blocked_cleanup: archive_after_review_window
- approved_candidates: never_archived_by_maintenance
"""
    write_memory_candidate_maintenance_state(root, text)


def _append_trace(root: Path, result: dict[str, Any]) -> None:
    payload = {
        "checked_at": result.get("checked_at"),
        "backfilled": result.get("backfill", {}).get("backfilled"),
        "archived": result.get("cleanup", {}).get("archived"),
        "notes": result.get("notes", [])[:8],
    }
    append_memory_candidate_maintenance_trace(root, payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill and clean up XinYu memory candidates.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_memory_candidate_maintenance(args.root.resolve(), limit=max(1, args.limit))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
