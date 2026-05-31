from __future__ import annotations

import json
from pathlib import Path

from xinyu_short_term_continuity_canary import (
    build_short_term_continuity_canary_report,
    render_short_term_continuity_canary_report,
    write_short_term_continuity_canary,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _direct_reference(
    *,
    checked_at: str = "2026-05-27T14:00:00+08:00",
    turn_id: str = "turn-1",
    recall_status: str = "tail_available",
    recall_source: str = "dialogue_tail",
) -> dict:
    return {
        "checked_at": checked_at,
        "turn_id": turn_id,
        "status": "active",
        "direct_reference": True,
        "recall_status": recall_status,
        "recall_source": recall_source,
        "tail_count": 4 if recall_status == "tail_available" else 0,
        "archive_recovered_count": 0,
        "recent_user_count": 2 if recall_status == "tail_available" else 0,
        "recent_assistant_count": 2 if recall_status == "tail_available" else 0,
        "latest_user_ref": "sha256:userhash",
        "latest_assistant_ref": "sha256:assistanthash",
        "raw_private_body_retained": False,
        "visible_reply_text_retained": False,
    }


def _reply(
    *,
    sent_at: str = "2026-05-27T14:00:05+08:00",
    turn_id: str = "turn-1",
    visible_text: str = "I can use the previous turn without asking you to repeat it.",
) -> dict:
    return {
        "event": "pending",
        "key": f"adapter|{turn_id}|chat",
        "created_at": sent_at,
        "payload": {
            "route": "chat",
            "turn_id": turn_id,
            "source_message_id": "src-1",
            "sent_at": sent_at,
            "visible_text": visible_text,
        },
    }


def test_canary_passes_when_direct_reference_is_recalled_without_recurrence(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [_direct_reference()])
    _write_jsonl(tmp_path / "runtime/gateway_ack_spool.jsonl", [_reply()])

    report = build_short_term_continuity_canary_report(tmp_path, generated_at="2026-05-27T14:01:00+08:00")
    output = render_short_term_continuity_canary_report(report)

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert report["metrics"]["direct_reference_count"] == 1
    assert report["metrics"]["recall_available_count"] == 1
    assert report["metrics"]["which_sentence_recurrence_count"] == 0
    assert report["matched_direct_references"][0]["match_method"] == "turn_id"
    assert "visible_text" not in output


def test_canary_flags_which_sentence_recurrence_without_leaking_reply_text(tmp_path: Path) -> None:
    private_reply = "\u4f60\u6307\u54ea\u4e00\u53e5\uff1f"
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [_direct_reference()])
    _write_jsonl(tmp_path / "runtime/gateway_ack_spool.jsonl", [_reply(visible_text=private_reply)])

    report = build_short_term_continuity_canary_report(tmp_path, generated_at="2026-05-27T14:01:00+08:00")
    output = render_short_term_continuity_canary_report(report)

    assert report["ok"] is False
    assert report["status"] == "needs_check"
    assert report["metrics"]["which_sentence_recurrence_count"] == 1
    assert private_reply not in output


def test_canary_flags_missing_direct_reference_recall(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [_direct_reference(recall_status="tail_missing", recall_source="none")],
    )
    _write_jsonl(tmp_path / "runtime/gateway_ack_spool.jsonl", [_reply()])

    report = build_short_term_continuity_canary_report(tmp_path, generated_at="2026-05-27T14:01:00+08:00")

    assert report["ok"] is False
    assert report["status"] == "needs_check"
    assert report["metrics"]["recall_missing_count"] == 1


def test_canary_matches_reply_by_time_window_when_turn_id_is_missing(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [_direct_reference(checked_at="2026-05-27T14:00:00+08:00", turn_id="")],
    )
    _write_jsonl(
        tmp_path / "runtime/gateway_ack_spool.jsonl",
        [_reply(sent_at="2026-05-27T14:02:00+08:00", turn_id="")],
    )

    report = build_short_term_continuity_canary_report(
        tmp_path,
        reply_window_seconds=180,
        generated_at="2026-05-27T14:03:00+08:00",
    )

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert report["matched_direct_references"][0]["match_method"] == "time_window"


def test_canary_lookback_window_excludes_old_recurrence(tmp_path: Path) -> None:
    old_reply = "\u4f60\u6307\u54ea\u4e00\u53e5\uff1f"
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            _direct_reference(
                checked_at="2026-05-27T14:00:00+08:00",
                turn_id="turn-old",
            ),
            _direct_reference(
                checked_at="2026-05-27T16:00:00+08:00",
                turn_id="turn-new",
            ),
        ],
    )
    _write_jsonl(
        tmp_path / "runtime/gateway_ack_spool.jsonl",
        [
            _reply(
                sent_at="2026-05-27T14:00:05+08:00",
                turn_id="turn-old",
                visible_text=old_reply,
            ),
            _reply(
                sent_at="2026-05-27T16:00:05+08:00",
                turn_id="turn-new",
                visible_text="I can use the current recent turn.",
            ),
        ],
    )

    report = build_short_term_continuity_canary_report(
        tmp_path,
        lookback_minutes=60,
        generated_at="2026-05-27T16:10:00+08:00",
    )

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert report["metrics"]["direct_reference_count"] == 1
    assert report["metrics"]["which_sentence_recurrence_count"] == 0


def test_canary_write_outputs_hashes_and_counts_only(tmp_path: Path) -> None:
    raw_owner = "RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_SURFACE_8113"
    private_reply = "VISIBLE_REPLY_SHOULD_NOT_SURFACE_8113"
    event = _direct_reference()
    event["raw_owner_text"] = raw_owner
    event["visible_reply_text"] = private_reply
    _write_jsonl(tmp_path / "runtime/short_term_continuity_trace.jsonl", [event])
    _write_jsonl(tmp_path / "runtime/gateway_ack_spool.jsonl", [_reply(visible_text=private_reply)])

    report = build_short_term_continuity_canary_report(tmp_path, generated_at="2026-05-27T14:01:00+08:00")
    paths = write_short_term_continuity_canary(tmp_path, report)

    report_text = Path(paths["report_path"]).read_text(encoding="utf-8")
    state_text = Path(paths["state_path"]).read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/short_term_continuity_canary_trace.jsonl").read_text(encoding="utf-8")
    combined = report_text + state_text + trace_text + json.dumps(report, ensure_ascii=False)

    assert raw_owner not in combined
    assert private_reply not in combined
    assert "raw_owner_text_in_trace" in trace_text
    assert "visible_reply_text_in_trace" in trace_text
