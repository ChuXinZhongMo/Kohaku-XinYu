from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_archive import archive_dialogue_turn, initialize_dialogue_archive
from xinyu_short_term_recall_diagnostics import (
    build_short_term_recall_diagnostics,
    render_short_term_recall_diagnostics,
    write_short_term_recall_diagnostics,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _trace_row(
    *,
    recall_status: str = "tail_available",
    recall_source: str = "dialogue_tail",
    tail_count: int = 4,
    archive_recovered_count: int = 0,
    turn_id: str = "turn-recall-diag",
    tail_storage_status: str = "available",
    tail_storage_reason: str = "working_memory_rows_available",
    tail_storage_usable_row_count: int = 4,
    tail_storage_filtered_row_count: int = 0,
    tail_storage_invalid_line_count: int = 0,
    notes: list[str] | None = None,
) -> dict:
    return {
        "checked_at": "2026-05-27T14:00:00+08:00",
        "turn_id": turn_id,
        "status": "active",
        "direct_reference": True,
        "recall_status": recall_status,
        "recall_source": recall_source,
        "tail_count": tail_count,
        "archive_recovered_count": archive_recovered_count,
        "recent_user_count": 2 if recall_status == "tail_available" else 0,
        "recent_assistant_count": 2 if recall_status == "tail_available" else 0,
        "latest_user_ref": "sha256:userhash",
        "latest_assistant_ref": "sha256:assistanthash",
        "tail_storage_status": tail_storage_status,
        "tail_storage_reason": tail_storage_reason,
        "tail_storage_usable_row_count": tail_storage_usable_row_count,
        "tail_storage_filtered_row_count": tail_storage_filtered_row_count,
        "tail_storage_invalid_line_count": tail_storage_invalid_line_count,
        "notes": notes or ["direct_reference_requested"],
        "raw_private_body_retained": False,
        "visible_reply_text_retained": False,
    }


def _prompt_report(
    *,
    turn_id: str = "turn-recall-diag",
    admitted: bool = True,
    char_count: int = 900,
    reason: str = "required",
) -> dict:
    sidecar = {
        "name": "short_term_continuity",
        "admission": "current_turn",
        "required": True,
        "char_count": char_count,
        "reason": reason,
    }
    return {
        "generated_at": "2026-05-27T14:00:01+08:00",
        "turn_id": turn_id,
        "candidate_sidecar_count": 1,
        "admitted_sidecar_count": 1 if admitted else 0,
        "blocked_sidecar_count": 0 if admitted else 1,
        "admitted_sidecars": [sidecar] if admitted else [],
        "blocked_sidecars": [] if admitted else [sidecar],
    }


def _write_prompt_report(root: Path, report: dict) -> None:
    path = root / "runtime/prompt_pressure/last_live_prompt_pressure.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def test_recall_diagnostics_passes_when_tail_and_prompt_sidecar_are_available(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [_trace_row()])
    _write_prompt_report(tmp_path, _prompt_report())

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert report["primary_failure_class"] == "none"
    assert report["diagnostics"]["working_tail_status"] == "available"
    assert report["diagnostics"]["prompt_admission_status"] == "admitted"
    assert report["diagnostics"]["prompt_budget_status"] == "ok"


def test_recall_diagnostics_classifies_missing_payload_as_read_path(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_SURFACE_4412"
    row = _trace_row(
        recall_status="tail_missing",
        recall_source="none",
        tail_count=0,
        tail_storage_status="session_unscoped",
        tail_storage_reason="missing_session_key",
        tail_storage_usable_row_count=0,
        notes=["direct_reference_requested", "archive_fallback_no_payload", "recent_tail_missing"],
    )
    row["raw_owner_text"] = raw_private
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [row])
    _write_prompt_report(tmp_path, _prompt_report())

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")
    output = render_short_term_recall_diagnostics(report)

    assert report["ok"] is False
    assert report["primary_failure_class"] == "read_path"
    assert report["diagnostics"]["working_memory_storage_status"] == "session_unscoped"
    assert report["diagnostics"]["archive_fallback_status"] == "read_path_error"
    assert raw_private not in output


def test_recall_diagnostics_classifies_empty_initialized_archive_as_not_written(tmp_path: Path) -> None:
    initialize_dialogue_archive(tmp_path)
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            _trace_row(
                recall_status="tail_missing",
                recall_source="none",
                tail_count=0,
                tail_storage_status="empty_file",
                tail_storage_reason="working_memory_file_empty",
                tail_storage_usable_row_count=0,
                notes=["direct_reference_requested", "archive_fallback_empty", "recent_tail_missing"],
            )
        ],
    )
    _write_prompt_report(tmp_path, _prompt_report())

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is False
    assert report["primary_failure_class"] == "not_written"
    assert report["diagnostics"]["archive_fallback_status"] == "not_written"


def test_recall_diagnostics_classifies_missing_working_memory_file_as_not_written(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            _trace_row(
                recall_status="tail_missing",
                recall_source="none",
                tail_count=0,
                tail_storage_status="missing_file",
                tail_storage_reason="working_memory_file_missing",
                tail_storage_usable_row_count=0,
                notes=["direct_reference_requested", "archive_fallback_unavailable", "recent_tail_missing"],
            )
        ],
    )
    _write_prompt_report(tmp_path, _prompt_report())

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is False
    assert report["primary_failure_class"] == "not_written"
    assert report["diagnostics"]["archive_db_exists"] is False


def test_recall_diagnostics_classifies_archive_rows_without_match_as_filtered(tmp_path: Path) -> None:
    payload = {
        "session_id": "qq:private:owner",
        "message_type": "private_text",
        "user_id": "owner",
        "platform": "qq",
        "metadata": {"is_owner_user": True},
    }
    archive_dialogue_turn(
        tmp_path,
        payload,
        user_text="unrelated archived line",
        assistant_reply="unrelated archived reply",
        message_type="private_text",
    )
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            _trace_row(
                recall_status="tail_missing",
                recall_source="none",
                tail_count=0,
                tail_storage_status="filtered_only",
                tail_storage_reason="working_memory_rows_filtered",
                tail_storage_usable_row_count=0,
                tail_storage_filtered_row_count=2,
                notes=["direct_reference_requested", "archive_fallback_empty", "recent_tail_missing"],
            )
        ],
    )
    _write_prompt_report(tmp_path, _prompt_report())

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is False
    assert report["primary_failure_class"] == "filtered"
    assert report["diagnostics"]["working_memory_storage_status"] == "filtered_only"
    assert report["diagnostics"]["archive_fallback_status"] == "filtered_or_scope_mismatch"
    assert report["diagnostics"]["archive_message_count"] == 2


def test_recall_diagnostics_classifies_prompt_block_as_filtered(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [_trace_row()])
    _write_prompt_report(tmp_path, _prompt_report(admitted=False, reason="test_blocked"))

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is False
    assert report["primary_failure_class"] == "filtered"
    assert report["diagnostics"]["prompt_admission_status"] == "blocked"


def test_recall_diagnostics_classifies_available_working_memory_with_empty_tail_as_read_path(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            _trace_row(
                recall_status="tail_missing",
                recall_source="none",
                tail_count=0,
                tail_storage_status="available",
                tail_storage_reason="working_memory_rows_available",
                tail_storage_usable_row_count=6,
                notes=["direct_reference_requested", "recent_tail_missing"],
            )
        ],
    )
    _write_prompt_report(tmp_path, _prompt_report())

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is False
    assert report["primary_failure_class"] == "read_path"
    assert report["diagnostics"]["working_tail_status"] == "available_but_not_loaded"
    assert report["diagnostics"]["working_memory_storage_usable_row_count"] == 6


def test_recall_diagnostics_accepts_tail_available_when_prompt_report_is_stale(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [_trace_row(turn_id="turn-old-direct")])
    _write_prompt_report(tmp_path, _prompt_report(turn_id="turn-newer-unrelated", admitted=False))

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert report["primary_failure_class"] == "none"
    assert report["diagnostics"]["prompt_report_turn_match"] == "mismatch"
    assert report["diagnostics"]["classification_basis"] == "direct_reference_tail_available_prompt_report_stale"


def test_recall_diagnostics_classifies_near_clip_sidecar_as_budget(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [_trace_row()])
    _write_prompt_report(tmp_path, _prompt_report(char_count=1600))

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is False
    assert report["primary_failure_class"] == "budget"
    assert report["diagnostics"]["prompt_budget_status"] == "near_sidecar_clip_limit"


def test_recall_diagnostics_write_outputs_counts_and_hashes_only(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_SURFACE_5038"
    row = _trace_row()
    row["raw_owner_text"] = raw_private
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [row])
    _write_prompt_report(tmp_path, _prompt_report())

    report = build_short_term_recall_diagnostics(tmp_path, generated_at="2026-05-27T14:01:00+08:00")
    paths = write_short_term_recall_diagnostics(tmp_path, report)

    report_text = Path(paths["report_path"]).read_text(encoding="utf-8")
    state_text = Path(paths["state_path"]).read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/short_term_recall_diagnostics_trace.jsonl").read_text(encoding="utf-8")
    combined = report_text + state_text + trace_text

    assert raw_private not in combined
    assert "raw_owner_text_in_trace" in trace_text
    assert "visible_reply_text_in_trace" in trace_text
