from __future__ import annotations

import json
from pathlib import Path

from xinyu_qq_reply_integrity_diagnostics import (
    build_qq_reply_integrity_diagnostics,
    render_qq_reply_integrity_diagnostics,
    write_qq_reply_integrity_diagnostics,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _reply(
    *,
    created_at: str = "2026-05-28T22:30:00+08:00",
    turn_id: str = "turn-ok",
    visible_text: str = "stable visible reply",
    archive: bool = True,
) -> dict:
    return {
        "event": "pending",
        "created_at": created_at,
        "payload": {
            "route": "chat",
            "turn_id": turn_id,
            "sent_at": created_at,
            "visible_text": visible_text,
            "archive_message_ids": [1, 2] if archive else [],
            "archive_assistant_message_id": "2" if archive else "",
        },
    }


def _semantic_fast_direct(
    *,
    observed_at: str = "2026-05-28T22:30:00+08:00",
    turn_id: str = "turn-fast",
) -> dict:
    return {
        "observed_at": observed_at,
        "stage": "route_finished",
        "status": "ok",
        "route": "owner_private_semantic_fast",
        "turn_id": turn_id,
        "notes": [
            "owner_private_semantic_fast_intercepted",
            "semantic_fast_direct_reply",
            "event_sourcing_deferred_for_semantic_fast",
        ],
    }


def _working_memory(root: Path, *assistant_texts: str) -> None:
    rows = [{"role": "assistant", "content": text, "recorded_at": "2026-05-28T22:30:01+08:00"} for text in assistant_texts]
    _write_jsonl(root / "runtime/dialogue_working_memory/session.jsonl", rows)


def test_qq_reply_integrity_passes_for_recent_archived_reply_in_working_memory(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "runtime/gateway_ack_spool.jsonl", [_reply()])
    _working_memory(tmp_path, "stable visible reply")

    report = build_qq_reply_integrity_diagnostics(
        tmp_path,
        generated_at="2026-05-28T22:31:00+08:00",
    )

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert report["metrics"]["visible_chat_reply_count"] == 1
    assert report["metrics"]["visible_reply_missing_working_memory_count"] == 0
    assert report["metrics"]["naked_ack_visible_reply_count"] == 0


def test_qq_reply_integrity_flags_naked_ack_without_leaking_text(tmp_path: Path) -> None:
    private_reply = "\u55ef\u3002"
    _write_jsonl(tmp_path / "runtime/gateway_ack_spool.jsonl", [_reply(visible_text=private_reply)])
    _working_memory(tmp_path, private_reply)

    report = build_qq_reply_integrity_diagnostics(
        tmp_path,
        generated_at="2026-05-28T22:31:00+08:00",
    )
    output = render_qq_reply_integrity_diagnostics(report)

    assert report["ok"] is False
    assert report["status"] == "needs_check"
    assert report["metrics"]["naked_ack_visible_reply_count"] == 1
    assert private_reply not in output
    assert private_reply not in json.dumps(report, ensure_ascii=False)


def test_qq_reply_integrity_flags_semantic_fast_direct_reply_without_archive(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/turn_route_trace.jsonl",
        [_semantic_fast_direct(turn_id="turn-fast")],
    )
    _write_jsonl(
        tmp_path / "runtime/gateway_ack_spool.jsonl",
        [_reply(turn_id="turn-fast", visible_text="direct reply", archive=False)],
    )
    _working_memory(tmp_path, "direct reply")

    report = build_qq_reply_integrity_diagnostics(
        tmp_path,
        generated_at="2026-05-28T22:31:00+08:00",
    )

    assert report["ok"] is False
    assert report["metrics"]["semantic_fast_direct_reply_count"] == 1
    assert report["metrics"]["semantic_fast_direct_reply_without_archive_count"] == 1
    assert any(issue["issue_type"] == "semantic_fast_direct_reply_without_archive" for issue in report["issues"])


def test_qq_reply_integrity_flags_visible_reply_missing_working_memory(tmp_path: Path) -> None:
    private_reply = "PRIVATE_VISIBLE_SHOULD_NOT_SURFACE_4551"
    _write_jsonl(tmp_path / "runtime/gateway_ack_spool.jsonl", [_reply(visible_text=private_reply)])
    _working_memory(tmp_path, "different reply")

    report = build_qq_reply_integrity_diagnostics(
        tmp_path,
        generated_at="2026-05-28T22:31:00+08:00",
    )
    output = render_qq_reply_integrity_diagnostics(report)

    assert report["ok"] is False
    assert report["metrics"]["visible_reply_missing_working_memory_count"] == 1
    assert any(issue["issue_type"] == "visible_reply_missing_working_memory" for issue in report["issues"])
    assert private_reply not in output
    assert private_reply not in json.dumps(report, ensure_ascii=False)


def test_qq_reply_integrity_lookback_ignores_old_naked_ack(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/gateway_ack_spool.jsonl",
        [
            _reply(
                created_at="2026-05-28T17:00:00+08:00",
                turn_id="turn-old",
                visible_text="\u55ef\u3002",
                archive=False,
            ),
            _reply(
                created_at="2026-05-28T22:30:00+08:00",
                turn_id="turn-new",
                visible_text="new stable reply",
                archive=True,
            ),
        ],
    )
    _working_memory(tmp_path, "new stable reply")

    report = build_qq_reply_integrity_diagnostics(
        tmp_path,
        lookback_minutes=120,
        generated_at="2026-05-28T22:31:00+08:00",
    )

    assert report["ok"] is True
    assert report["metrics"]["visible_chat_reply_count"] == 1
    assert report["metrics"]["naked_ack_visible_reply_count"] == 0


def test_qq_reply_integrity_write_outputs_hashes_and_counts_only(tmp_path: Path) -> None:
    private_reply = "PRIVATE_VISIBLE_SHOULD_NOT_SURFACE_9281"
    _write_jsonl(tmp_path / "runtime/gateway_ack_spool.jsonl", [_reply(visible_text=private_reply)])
    _working_memory(tmp_path, private_reply)

    report = build_qq_reply_integrity_diagnostics(
        tmp_path,
        generated_at="2026-05-28T22:31:00+08:00",
    )
    paths = write_qq_reply_integrity_diagnostics(tmp_path, report)

    report_text = Path(paths["report_path"]).read_text(encoding="utf-8")
    state_text = Path(paths["state_path"]).read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/qq_reply_integrity_diagnostics_trace.jsonl").read_text(encoding="utf-8")
    combined = report_text + state_text + trace_text + json.dumps(report, ensure_ascii=False)

    assert private_reply not in combined
    assert "raw_owner_text_in_trace" in trace_text
    assert "visible_reply_text_in_trace" in trace_text
