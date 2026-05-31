from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from xinyu_live_loop_report import _should_wait_for_inflight_reply, build_report, format_human_report


NOW = datetime(2026, 5, 27, 6, 45, tzinfo=timezone.utc)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _status(ok: bool = True) -> dict:
    return {
        "ok": ok,
        "checks": [
            {"name": "core_bridge", "ok": ok, "detail": "running"},
            {"name": "xinyu_qq_gateway_6199", "ok": ok, "detail": "tcp connect"},
            {"name": "napcat_to_xinyu_qq_gateway_ws", "ok": ok, "detail": "established"},
        ],
        "core": {"known_error_count": 0},
    }


def test_live_loop_report_passes_for_matching_private_reply_ack(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
                "text_len": 6,
            },
            {
                "arrival_seq": 1,
                "dispatch_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
            {
                "arrival_seq": 1,
                "dispatch_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "reply_sent",
                "recorded_at": "2026-05-27T14:40:20+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "source": "direct_chat_pre_send",
                "target_kind": "private",
                "route": "chat",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "reply_hash": "sha256:reply",
                "observed_at": "2026-05-27T14:40:19+08:00",
            }
        ],
    )
    _write_jsonl(
        runtime / "gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|22220000|chat",
                "created_at": "2026-05-27T14:40:20+08:00",
                "payload": {
                    "route": "chat",
                    "adapter_message_id": "22220000",
                    "source_message_id": "11110000",
                    "message_type": "private",
                    "visible_text": "不应该出现在报告里",
                },
            },
            {
                "event": "acked",
                "key": "adapter|22220000|chat",
                "acked_at": "2026-05-27T14:40:21+08:00",
                "adapter_message_id": "22220000",
                "route": "chat",
            },
        ],
    )

    report = build_report(tmp_path, status_data=_status(), now=NOW)
    output = format_human_report(report)

    assert report["ok"] is True
    assert "不应该出现在报告里" not in output
    assert "raw_prompt_saved=False" in output
    assert "raw_reply_saved=False" in output


def test_live_loop_report_requires_matching_ack(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "reply_sent",
                "recorded_at": "2026-05-27T14:40:20+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "source": "direct_chat_pre_send",
                "target_kind": "private",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "observed_at": "2026-05-27T14:40:19+08:00",
            }
        ],
    )
    _write_jsonl(
        runtime / "gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|22220000|chat",
                "created_at": "2026-05-27T14:40:20+08:00",
                "payload": {
                    "route": "chat",
                    "adapter_message_id": "22220000",
                    "source_message_id": "99990000",
                },
            },
            {
                "event": "acked",
                "key": "adapter|22220000|chat",
                "acked_at": "2026-05-27T14:40:21+08:00",
                "adapter_message_id": "22220000",
                "route": "chat",
            },
        ],
    )

    report = build_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(check["name"] == "qq_ack" and not check["ok"] for check in report["checks"])


def test_live_loop_report_fails_when_shadow_saves_raw_text(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "reply_sent",
                "recorded_at": "2026-05-27T14:40:20+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "source": "direct_chat_pre_send",
                "target_kind": "private",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": True,
                "raw_reply_saved": False,
                "observed_at": "2026-05-27T14:40:19+08:00",
            }
        ],
    )
    _write_jsonl(
        runtime / "gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|22220000|chat",
                "created_at": "2026-05-27T14:40:20+08:00",
                "payload": {"route": "chat", "source_message_id": "11110000"},
            },
            {
                "event": "acked",
                "key": "adapter|22220000|chat",
                "acked_at": "2026-05-27T14:40:21+08:00",
                "route": "chat",
            },
        ],
    )

    report = build_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "visible_send_shadow_guard" and not check["ok"]
        for check in report["checks"]
    )


def test_live_loop_report_anchors_reply_ack_and_shadow_to_latest_private_input(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "coalesced_wait",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 1,
                "dispatch_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
            {
                "arrival_seq": 1,
                "dispatch_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "reply_sent",
                "recorded_at": "2026-05-27T14:40:20+08:00",
            },
            {
                "arrival_seq": 0,
                "dispatch_seq": 1,
                "message_kind": "private",
                "message_id": "source-1",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:44:00+08:00",
            },
            {
                "arrival_seq": 0,
                "dispatch_seq": 1,
                "message_kind": "private",
                "message_id": "source-1",
                "stage": "reply_sent",
                "recorded_at": "2026-05-27T14:44:01+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "source": "direct_chat_pre_send",
                "target_kind": "private",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "reply_hash": "sha256:real",
                "observed_at": "2026-05-27T14:40:19+08:00",
            },
            {
                "source": "direct_chat_pre_send",
                "target_kind": "private",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "reply_hash": "sha256:synthetic",
                "observed_at": "2026-05-27T14:44:01+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|22220000|chat",
                "created_at": "2026-05-27T14:40:20+08:00",
                "payload": {"route": "chat", "source_message_id": "11110000"},
            },
            {
                "event": "acked",
                "key": "adapter|22220000|chat",
                "acked_at": "2026-05-27T14:40:21+08:00",
                "route": "chat",
            },
        ],
    )

    report = build_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is True
    assert report["evidence"]["latest_reply_sent"]["message_id"] == "11***00"
    assert report["evidence"]["latest_shadow_guard"]["reply_hash"] == "sha256:real"


def test_runtime_status_passes_when_infra_ok_but_status_aggregate_false(tmp_path: Path) -> None:
    # Regression: stage12 is not ready → xinyu_status.py returns ok=False overall,
    # but core/gateway/napcat_ws are all reachable. runtime_status must still pass
    # so Stage12 can evaluate its own live-loop evidence without circular blocking.
    status_infra_ok_but_aggregate_false = {
        "ok": False,
        "checks": [
            {"name": "core_bridge", "ok": True, "detail": "running"},
            {"name": "xinyu_qq_gateway_6199", "ok": True, "detail": "tcp connect"},
            {"name": "napcat_to_xinyu_qq_gateway_ws", "ok": True, "detail": "established"},
            {"name": "stage12_long_term_evaluation", "ok": False, "detail": "active_needs_check"},
        ],
        "core": {"known_error_count": 0},
    }

    report = build_report(tmp_path, status_data=status_infra_ok_but_aggregate_false, now=NOW)

    runtime_check = next((c for c in report["checks"] if c["name"] == "runtime_status"), None)
    assert runtime_check is not None
    assert runtime_check["ok"] is True, (
        "runtime_status must pass when core/gateway/napcat_ws are all reachable, "
        "even if xinyu_status.py overall ok=False due to Stage12 not being ready"
    )


def test_runtime_status_fails_when_infra_down(tmp_path: Path) -> None:
    # When core bridge is down, runtime_status must fail regardless of aggregate ok.
    status_core_down = {
        "ok": False,
        "checks": [
            {"name": "core_bridge", "ok": False, "detail": "connection refused"},
            {"name": "xinyu_qq_gateway_6199", "ok": False, "detail": "tcp refused"},
            {"name": "napcat_to_xinyu_qq_gateway_ws", "ok": False, "detail": "no connection"},
        ],
        "core": {"known_error_count": 0},
    }

    report = build_report(tmp_path, status_data=status_core_down, now=NOW)

    runtime_check = next((c for c in report["checks"] if c["name"] == "runtime_status"), None)
    assert runtime_check is not None
    assert runtime_check["ok"] is False


def test_live_loop_report_does_not_match_reused_arrival_seq_after_restart(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 6,
                "message_kind": "private",
                "message_id": "old-input",
                "stage": "coalesced_wait",
                "recorded_at": "2026-05-27T13:45:00+08:00",
            },
            {
                "arrival_seq": 6,
                "message_kind": "private",
                "message_id": "old-input",
                "stage": "reply_sent",
                "recorded_at": "2026-05-27T13:45:20+08:00",
            },
            {
                "arrival_seq": 6,
                "message_kind": "private",
                "message_id": "new-input",
                "stage": "coalesced_wait",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 6,
                "message_kind": "private",
                "message_id": "new-input",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "source": "direct_chat_pre_send",
                "target_kind": "private",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "observed_at": "2026-05-27T13:45:19+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|22220000|chat",
                "created_at": "2026-05-27T13:45:20+08:00",
                "payload": {"route": "chat", "source_message_id": "old-input"},
            },
            {
                "event": "acked",
                "key": "adapter|22220000|chat",
                "acked_at": "2026-05-27T13:45:21+08:00",
                "route": "chat",
            },
        ],
    )

    report = build_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    checks = {check["name"]: check for check in report["checks"]}
    assert checks["dispatch_started"]["ok"] is True
    assert checks["visible_reply_sent"]["ok"] is False
    assert report["evidence"]["latest_reply_sent"]["present"] is False
    assert _should_wait_for_inflight_reply(report) is True
