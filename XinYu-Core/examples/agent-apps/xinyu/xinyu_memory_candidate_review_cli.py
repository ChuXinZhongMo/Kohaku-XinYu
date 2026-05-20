from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates, update_memory_candidate_status


STATUSES = ("pending", "owner_review_required", "self_approved_recent_context", "self_approved_voice_review", "rejected", "approved")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


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
    return {
        "ok": True,
        "candidate_id": row.get("candidate_id"),
        "source_turn_id": row.get("source_turn_id", ""),
        "source_message_ids": row.get("source_message_ids", []),
        "extraction_reason": row.get("reason", ""),
        "risk_flags": row.get("risk_flags", []),
        "target_gate": row.get("target_gate", ""),
        "target_memory_layer": row.get("target_memory_layer", ""),
        "status": row.get("status", ""),
        "stable_memory_write": "blocked_until_review",
    }


def decide_candidate(root: Path, candidate_id: str, *, decision: str, review_notes: str = "") -> dict[str, Any]:
    status = "approved" if decision == "approve" else "rejected"
    row = get_candidate(root, candidate_id)
    if row is None:
        return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}
    if decision == "approve":
        approval_error = _approval_error(row, review_notes=review_notes)
        if approval_error:
            return {"ok": False, "error": approval_error, "candidate_id": candidate_id, "status": row.get("status", "")}
    if not update_memory_candidate_status(root, candidate_id=candidate_id, status=status, review_notes=review_notes):
        return {"ok": False, "error": "candidate_update_failed", "candidate_id": candidate_id}
    return {"ok": True, "candidate_id": candidate_id, "status": status, "review_notes": review_notes}


def _approval_error(row: dict[str, Any], *, review_notes: str) -> str:
    risk_text = " ".join(_safe_str(flag).lower() for flag in row.get("risk_flags", []))
    risk_text += " " + _safe_str(row.get("review_notes")).lower()
    risk_text += " " + _safe_str(row.get("reason")).lower()
    if any(marker in risk_text for marker in ("runtime_trace", "timeout", "temporary_operational")):
        return "runtime_or_timeout_candidate_cannot_be_approved_directly"
    high_risk_types = {"relationship_signal", "owner_preference", "personality_change", "voice_correction"}
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
    for name in ("show", "explain", "approve", "reject"):
        item = sub.add_parser(name)
        item.add_argument("candidate_id")
        if name in {"approve", "reject"}:
            item.add_argument("--notes", default="")
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
    else:
        result = decide_candidate(root, args.candidate_id, decision="reject", review_notes=args.notes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
