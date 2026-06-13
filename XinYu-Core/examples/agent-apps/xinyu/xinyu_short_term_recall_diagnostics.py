from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_short_term_recall_diagnostics_store import REPORT_REL
from xinyu_short_term_recall_diagnostics_store import SHORT_TRACE_REL
from xinyu_short_term_recall_diagnostics_store import STATE_REL
from xinyu_short_term_recall_diagnostics_store import TRACE_REL
from xinyu_short_term_recall_diagnostics_store import WORKING_MEMORY_DIR_REL
from xinyu_short_term_recall_diagnostics_store import append_short_term_recall_trace_event
from xinyu_short_term_recall_diagnostics_store import read_short_term_recall_prompt_report
from xinyu_short_term_recall_diagnostics_store import read_short_term_recall_trace_tail
from xinyu_short_term_recall_diagnostics_store import short_term_recall_storage_stats
from xinyu_short_term_recall_diagnostics_store import write_short_term_recall_report_text
from xinyu_short_term_recall_diagnostics_store import write_short_term_recall_state_text

SHORT_TERM_SIDECAR = "short_term_continuity"
SIDECAR_CLIP_WARN_CHARS = 1550


def build_short_term_recall_diagnostics(
    root: Path,
    *,
    trace_limit: int = 200,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = generated_at or _now_iso()
    trace_rows = read_short_term_recall_trace_tail(root, max_lines=max(1, int(trace_limit)))
    direct_events = [_safe_event(row) for row in trace_rows if row.get("direct_reference") is True]
    latest = direct_events[-1] if direct_events else {}
    prompt_report = read_short_term_recall_prompt_report(root)
    prompt = _prompt_sidecar_status(prompt_report, latest)
    storage = short_term_recall_storage_stats(root)
    archive = _archive_fallback_status(latest, storage)
    budget = _budget_status(prompt)
    primary_failure = _primary_failure_class(latest, prompt, archive, budget, storage)

    if not latest:
        status = "no_samples"
    elif primary_failure == "none":
        status = "pass"
    else:
        status = "needs_check"

    report = {
        "ok": status in {"pass", "no_samples"},
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "trace_limit": max(1, int(trace_limit)),
        "direct_reference_count": len(direct_events),
        "primary_failure_class": primary_failure,
        "latest_direct_reference": {
            "checked_at": latest.get("checked_at", "none"),
            "turn_id": latest.get("turn_id", "none"),
            "recall_status": latest.get("recall_status", "none"),
            "recall_source": latest.get("recall_source", "none"),
            "tail_count": latest.get("tail_count", 0),
            "archive_recovered_count": latest.get("archive_recovered_count", 0),
            "recent_user_count": latest.get("recent_user_count", 0),
            "recent_assistant_count": latest.get("recent_assistant_count", 0),
            "notes": latest.get("notes", []),
            "latest_user_ref": latest.get("latest_user_ref", "none"),
            "latest_assistant_ref": latest.get("latest_assistant_ref", "none"),
            "tail_storage_status": latest.get("tail_storage_status", "not_checked"),
            "tail_storage_reason": latest.get("tail_storage_reason", "not_checked"),
            "tail_storage_usable_row_count": latest.get("tail_storage_usable_row_count", 0),
            "tail_storage_filtered_row_count": latest.get("tail_storage_filtered_row_count", 0),
            "tail_storage_invalid_line_count": latest.get("tail_storage_invalid_line_count", 0),
        },
        "diagnostics": {
            "working_tail_status": _working_tail_status(latest),
            "working_memory_storage_status": latest.get("tail_storage_status", "not_checked"),
            "working_memory_storage_reason": latest.get("tail_storage_reason", "not_checked"),
            "working_memory_storage_usable_row_count": latest.get("tail_storage_usable_row_count", 0),
            "working_memory_storage_filtered_row_count": latest.get("tail_storage_filtered_row_count", 0),
            "working_memory_storage_invalid_line_count": latest.get("tail_storage_invalid_line_count", 0),
            "archive_fallback_status": archive["status"],
            "archive_reason": archive["reason"],
            "archive_db_exists": storage["archive_db_exists"],
            "archive_message_count": storage["archive_message_count"],
            "working_memory_file_count": storage["working_memory_file_count"],
            "working_memory_row_count": storage["working_memory_row_count"],
            "prompt_report_status": prompt["report_status"],
            "prompt_report_turn_match": prompt["turn_match"],
            "prompt_admission_status": prompt["admission_status"],
            "prompt_reason": prompt["reason"],
            "prompt_char_count": prompt["char_count"],
            "prompt_budget_status": budget,
            "classification_basis": _classification_basis(primary_failure, latest, prompt, archive, budget),
        },
        "privacy": {
            "raw_owner_text_in_report": False,
            "visible_reply_text_in_report": False,
            "state_contains_hashes_counts_only": True,
            "stable_memory_write": "blocked",
        },
    }
    return report


def render_short_term_recall_diagnostics(report: dict[str, Any]) -> str:
    latest = report.get("latest_direct_reference") if isinstance(report.get("latest_direct_reference"), dict) else {}
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines = [
        "# XinYu Short-Term Recall Diagnostics",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        f"- direct_reference_count: {report.get('direct_reference_count', 0)}",
        f"- primary_failure_class: {report.get('primary_failure_class', 'unknown')}",
        "- claim_boundary: diagnostics only; no raw dialogue text and no consciousness claim",
        "",
        "## Latest Direct Reference",
    ]
    for key in (
        "checked_at",
        "turn_id",
        "recall_status",
        "recall_source",
        "tail_count",
        "archive_recovered_count",
        "recent_user_count",
        "recent_assistant_count",
        "latest_user_ref",
        "latest_assistant_ref",
        "tail_storage_status",
        "tail_storage_reason",
        "tail_storage_usable_row_count",
        "tail_storage_filtered_row_count",
        "tail_storage_invalid_line_count",
    ):
        lines.append(f"- {key}: {latest.get(key, 'missing')}")
    notes = latest.get("notes")
    lines.append(f"- notes: {', '.join(notes) if isinstance(notes, list) and notes else 'none'}")
    lines.extend(["", "## Diagnostic Classes"])
    for key in (
        "working_tail_status",
        "working_memory_storage_status",
        "working_memory_storage_reason",
        "working_memory_storage_usable_row_count",
        "working_memory_storage_filtered_row_count",
        "working_memory_storage_invalid_line_count",
        "archive_fallback_status",
        "archive_reason",
        "archive_db_exists",
        "archive_message_count",
        "working_memory_file_count",
        "working_memory_row_count",
        "prompt_report_status",
        "prompt_report_turn_match",
        "prompt_admission_status",
        "prompt_reason",
        "prompt_char_count",
        "prompt_budget_status",
        "classification_basis",
    ):
        lines.append(f"- {key}: {diagnostics.get(key, 'missing')}")
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def write_short_term_recall_diagnostics(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> dict[str, str]:
    root = root.resolve()
    report_path = write_short_term_recall_report_text(root, render_short_term_recall_diagnostics(report), output=output)
    _write_state(root, report, report_path=report_path)
    _append_trace(root, report)
    return {"report_path": str(report_path), "state_path": str(root / STATE_REL)}


def _write_state(root: Path, report: dict[str, Any], *, report_path: Path) -> None:
    latest = report.get("latest_direct_reference") if isinstance(report.get("latest_direct_reference"), dict) else {}
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    text = f"""---
title: Short Term Recall Diagnostics State
memory_type: short_term_recall_diagnostics_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_short_term_recall_diagnostics
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [continuity, recall, diagnostics, input-anchor]
---

# Short Term Recall Diagnostics State

## Current Window
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- direct_reference_count: {report.get('direct_reference_count', 0)}
- primary_failure_class: {report.get('primary_failure_class', 'unknown')}

## Latest Direct Reference
- latest_checked_at: {latest.get('checked_at', 'none')}
- latest_turn_id: {latest.get('turn_id', 'none')}
- latest_recall_status: {latest.get('recall_status', 'none')}
- latest_recall_source: {latest.get('recall_source', 'none')}
- latest_tail_count: {latest.get('tail_count', 0)}
- latest_archive_recovered_count: {latest.get('archive_recovered_count', 0)}
- latest_user_ref: {latest.get('latest_user_ref', 'none')}
- latest_assistant_ref: {latest.get('latest_assistant_ref', 'none')}
- latest_tail_storage_status: {latest.get('tail_storage_status', 'not_checked')}
- latest_tail_storage_reason: {latest.get('tail_storage_reason', 'not_checked')}
- latest_tail_storage_usable_row_count: {latest.get('tail_storage_usable_row_count', 0)}
- latest_tail_storage_filtered_row_count: {latest.get('tail_storage_filtered_row_count', 0)}
- latest_tail_storage_invalid_line_count: {latest.get('tail_storage_invalid_line_count', 0)}

## Diagnostic Classes
- working_tail_status: {diagnostics.get('working_tail_status', 'missing')}
- working_memory_storage_status: {diagnostics.get('working_memory_storage_status', 'missing')}
- working_memory_storage_reason: {diagnostics.get('working_memory_storage_reason', 'missing')}
- working_memory_storage_usable_row_count: {diagnostics.get('working_memory_storage_usable_row_count', 0)}
- working_memory_storage_filtered_row_count: {diagnostics.get('working_memory_storage_filtered_row_count', 0)}
- working_memory_storage_invalid_line_count: {diagnostics.get('working_memory_storage_invalid_line_count', 0)}
- archive_fallback_status: {diagnostics.get('archive_fallback_status', 'missing')}
- archive_reason: {diagnostics.get('archive_reason', 'missing')}
- archive_db_exists: {str(diagnostics.get('archive_db_exists', False)).lower()}
- archive_message_count: {diagnostics.get('archive_message_count', 0)}
- working_memory_file_count: {diagnostics.get('working_memory_file_count', 0)}
- working_memory_row_count: {diagnostics.get('working_memory_row_count', 0)}
- prompt_report_status: {diagnostics.get('prompt_report_status', 'missing')}
- prompt_report_turn_match: {diagnostics.get('prompt_report_turn_match', 'missing')}
- prompt_admission_status: {diagnostics.get('prompt_admission_status', 'missing')}
- prompt_reason: {diagnostics.get('prompt_reason', 'missing')}
- prompt_char_count: {diagnostics.get('prompt_char_count', 0)}
- prompt_budget_status: {diagnostics.get('prompt_budget_status', 'missing')}
- classification_basis: {diagnostics.get('classification_basis', 'missing')}

## Boundaries
- report_path: {report_path.as_posix()}
- raw_owner_text_in_state: false
- visible_reply_text_in_state: false
- stable_memory_write: blocked
"""
    write_short_term_recall_state_text(root, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "direct_reference_count": report.get("direct_reference_count", 0),
        "primary_failure_class": report.get("primary_failure_class", "unknown"),
        "working_tail_status": diagnostics.get("working_tail_status", "missing"),
        "working_memory_storage_status": diagnostics.get("working_memory_storage_status", "missing"),
        "archive_fallback_status": diagnostics.get("archive_fallback_status", "missing"),
        "prompt_admission_status": diagnostics.get("prompt_admission_status", "missing"),
        "prompt_budget_status": diagnostics.get("prompt_budget_status", "missing"),
        "raw_owner_text_in_trace": False,
        "visible_reply_text_in_trace": False,
    }
    append_short_term_recall_trace_event(root, row)


def _safe_event(row: dict[str, Any]) -> dict[str, Any]:
    notes = row.get("notes")
    if not isinstance(notes, list):
        notes = []
    return {
        "checked_at": _safe_str(row.get("checked_at")),
        "turn_id": _safe_str(row.get("turn_id")) or "none",
        "recall_status": _safe_str(row.get("recall_status")),
        "recall_source": _safe_str(row.get("recall_source")),
        "tail_count": _as_int(row.get("tail_count")),
        "archive_recovered_count": _as_int(row.get("archive_recovered_count")),
        "recent_user_count": _as_int(row.get("recent_user_count")),
        "recent_assistant_count": _as_int(row.get("recent_assistant_count")),
        "latest_user_ref": _safe_str(row.get("latest_user_ref")) or "none",
        "latest_assistant_ref": _safe_str(row.get("latest_assistant_ref")) or "none",
        "tail_storage_status": _safe_str(row.get("tail_storage_status")) or "not_checked",
        "tail_storage_reason": _safe_str(row.get("tail_storage_reason")) or "not_checked",
        "tail_storage_usable_row_count": _as_int(row.get("tail_storage_usable_row_count")),
        "tail_storage_filtered_row_count": _as_int(row.get("tail_storage_filtered_row_count")),
        "tail_storage_invalid_line_count": _as_int(row.get("tail_storage_invalid_line_count")),
        "notes": [_safe_str(note) for note in notes if _safe_str(note)],
    }


def _prompt_sidecar_status(prompt_report: dict[str, Any], latest: dict[str, Any]) -> dict[str, Any]:
    if not prompt_report:
        return {
            "report_status": "missing",
            "turn_match": "unknown",
            "admission_status": "missing",
            "reason": "prompt_pressure_report_missing",
            "char_count": 0,
        }
    report_turn = _safe_str(prompt_report.get("turn_id")) or "unknown"
    event_turn = _safe_str(latest.get("turn_id"))
    if not latest:
        turn_match = "no_direct_reference"
    elif event_turn and event_turn not in {"none", "unknown"} and report_turn != event_turn:
        turn_match = "mismatch"
    else:
        turn_match = "matched_or_unscoped"

    admitted = _find_sidecar(prompt_report.get("admitted_sidecars"), SHORT_TERM_SIDECAR)
    if admitted:
        return {
            "report_status": "available",
            "turn_match": turn_match,
            "admission_status": "admitted",
            "reason": _safe_str(admitted.get("reason")) or "admitted",
            "char_count": _as_int(admitted.get("char_count")),
        }
    blocked = _find_sidecar(prompt_report.get("blocked_sidecars"), SHORT_TERM_SIDECAR)
    if blocked:
        return {
            "report_status": "available",
            "turn_match": turn_match,
            "admission_status": "blocked",
            "reason": _safe_str(blocked.get("reason")) or "blocked",
            "char_count": _as_int(blocked.get("char_count")),
        }
    return {
        "report_status": "available",
        "turn_match": turn_match,
        "admission_status": "missing",
        "reason": "short_term_continuity_sidecar_not_listed",
        "char_count": 0,
    }


def _find_sidecar(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, list):
        return {}
    for item in value:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return {}


def _archive_fallback_status(latest: dict[str, Any], storage: dict[str, Any]) -> dict[str, str]:
    if not latest:
        return {"status": "not_checked", "reason": "no_direct_reference"}
    if latest.get("recall_source") == "dialogue_archive":
        return {"status": "recovered", "reason": "archive_tail_recovered"}
    if latest.get("recall_source") == "dialogue_working_memory":
        return {"status": "not_needed", "reason": "dialogue_working_memory_available"}
    if latest.get("recall_source") == "dialogue_tail":
        return {"status": "not_needed", "reason": "dialogue_tail_available"}
    notes = set(latest.get("notes") if isinstance(latest.get("notes"), list) else [])
    if any(note.startswith("archive_fallback_error:") for note in notes):
        return {"status": "error", "reason": next(note for note in notes if note.startswith("archive_fallback_error:"))}
    if "archive_fallback_no_payload" in notes:
        return {"status": "read_path_error", "reason": "archive_fallback_no_payload"}
    if "archive_fallback_unavailable" in notes or not storage.get("archive_db_exists"):
        return {"status": "not_indexed", "reason": "archive_fallback_unavailable"}
    if "archive_fallback_empty" in notes:
        if _as_int(storage.get("archive_message_count")) > 0:
            return {"status": "filtered_or_scope_mismatch", "reason": "archive_fallback_empty_with_archive_rows"}
        return {"status": "not_written", "reason": "archive_fallback_empty"}
    return {"status": "unknown", "reason": "no_archive_fallback_note"}


def _working_tail_status(latest: dict[str, Any]) -> str:
    if not latest:
        return "not_checked"
    if latest.get("recall_status") == "tail_available":
        return "available"
    storage_status = _safe_str(latest.get("tail_storage_status"))
    if storage_status in {"available", "available_with_filtered_rows"}:
        return "available_but_not_loaded"
    if storage_status in {"session_unscoped", "read_error", "decode_failed"}:
        return "read_path_problem"
    if storage_status == "filtered_only":
        return "filtered_only"
    if storage_status in {"missing_file", "empty_file"}:
        return storage_status
    return "missing"


def _budget_status(prompt: dict[str, Any]) -> str:
    if prompt.get("admission_status") != "admitted":
        return "unknown"
    if _as_int(prompt.get("char_count")) >= SIDECAR_CLIP_WARN_CHARS:
        return "near_sidecar_clip_limit"
    return "ok"


def _primary_failure_class(
    latest: dict[str, Any],
    prompt: dict[str, Any],
    archive: dict[str, str],
    budget: str,
    storage: dict[str, Any],
) -> str:
    if not latest:
        return "none"
    if latest.get("recall_status") == "tail_available" and prompt.get("turn_match") == "mismatch":
        return "none"
    if budget == "near_sidecar_clip_limit":
        return "budget"
    if prompt.get("admission_status") == "blocked":
        return "filtered"
    if prompt.get("admission_status") == "missing" or prompt.get("report_status") == "missing":
        return "read_path"
    if prompt.get("turn_match") == "mismatch":
        return "read_path"
    if latest.get("recall_status") == "tail_available":
        return "none"

    storage_status = _safe_str(latest.get("tail_storage_status"))
    if storage_status in {"available", "available_with_filtered_rows"}:
        return "read_path"
    if storage_status in {"session_unscoped", "read_error", "decode_failed"}:
        return "read_path"
    if storage_status == "filtered_only":
        return "filtered"
    if storage_status in {"missing_file", "empty_file"}:
        return "not_written"

    archive_status = archive.get("status")
    if archive_status in {"read_path_error", "error"}:
        return "read_path"
    if archive_status == "not_indexed":
        return "not_indexed"
    if archive_status == "filtered_or_scope_mismatch":
        return "filtered"
    if archive_status == "not_written":
        return "not_written"
    if _as_int(storage.get("working_memory_row_count")) <= 0 and _as_int(storage.get("archive_message_count")) <= 0:
        return "not_written"
    return "unknown"


def _classification_basis(
    primary_failure: str,
    latest: dict[str, Any],
    prompt: dict[str, Any],
    archive: dict[str, str],
    budget: str,
) -> str:
    if not latest:
        return "no_direct_reference_sample"
    if primary_failure == "none":
        if latest.get("recall_status") == "tail_available" and prompt.get("turn_match") == "mismatch":
            return "direct_reference_tail_available_prompt_report_stale"
        return "direct_reference_tail_available_and_prompt_sidecar_admitted"
    if primary_failure == "budget":
        return f"short_term_sidecar_char_count={prompt.get('char_count', 0)}; budget={budget}"
    if primary_failure == "filtered":
        return (
            f"prompt={prompt.get('admission_status')}; "
            f"storage={latest.get('tail_storage_status', 'not_checked')}; "
            f"archive={archive.get('status')}"
        )
    if primary_failure == "read_path":
        return (
            f"prompt={prompt.get('report_status')}/{prompt.get('turn_match')}; "
            f"storage={latest.get('tail_storage_status', 'not_checked')}; "
            f"archive={archive.get('reason')}"
        )
    if primary_failure == "not_indexed":
        return archive.get("reason", "archive_not_indexed")
    if primary_failure == "not_written":
        return (
            f"storage={latest.get('tail_storage_status', 'not_checked')}; "
            f"archive={archive.get('reason', 'tail_and_archive_missing')}"
        )
    return "insufficient_diagnostic_evidence"


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu short-term recall diagnostics.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--trace-limit", type=int, default=200)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_short_term_recall_diagnostics(args.root, trace_limit=max(1, args.trace_limit))
    if args.write:
        report.update(write_short_term_recall_diagnostics(args.root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_short_term_recall_diagnostics(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
