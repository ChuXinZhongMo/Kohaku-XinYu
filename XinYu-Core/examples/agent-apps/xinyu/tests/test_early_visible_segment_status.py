from __future__ import annotations

import json

from xinyu_early_visible_segment import TRACE_REL
from xinyu_early_visible_segment_status import build_status_report
from xinyu_early_visible_segment_status import render_text_report


def _append_rows(root, rows) -> None:
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _row(index: int, *, status: str = "accepted_shadow", reasons: list[str] | None = None) -> dict[str, object]:
    return {
        "event_kind": "early_visible_segment_shadow",
        "checked_at": f"2026-05-23T00:{index:02d}:00+08:00",
        "status": status,
        "accepted_shadow": status == "accepted_shadow",
        "elapsed_ms": 800 + index,
        "segment_chars": 12,
        "reasons": reasons or [],
        "raw_user_text_saved": False,
        "raw_segment_saved": False,
    }


def test_status_report_blocks_until_enough_shadow_samples(tmp_path) -> None:
    _append_rows(
        tmp_path,
        [
            _row(0),
            _row(1, status="rejected_shadow", reasons=["generic_presence_or_meta_prefix"]),
            _row(2, status="no_candidate", reasons=["no_natural_segment_observed"]),
        ],
    )

    report = build_status_report(tmp_path)
    text = render_text_report(report)

    assert report["canary_review_ready"] is False
    assert report["missing_eligible_count"] == 17
    assert "eligible_count_below_minimum" in report["blocking_reasons"]
    assert "shadow_only: true" in text
    assert "no_outbox_send: true" in text
    assert "blocking_reasons: eligible_count_below_minimum" in text


def test_status_report_marks_owner_private_canary_review_ready(tmp_path) -> None:
    _append_rows(tmp_path, [_row(index) for index in range(20)])

    report = build_status_report(tmp_path)
    text = render_text_report(report)

    assert report["canary_review_ready"] is True
    assert report["blocking_reasons"] == []
    assert report["summary"]["accepted_shadow_count"] == 20
    assert report["summary"]["acceptance_rate_pct"] == 100
    assert "canary_review_ready: true" in text
    assert "blocking_reasons: none" in text


def test_status_report_never_renders_raw_chat_body(tmp_path) -> None:
    raw_user_text = "raw owner private text should never appear"
    raw_segment = "raw candidate segment should never appear"
    _append_rows(
        tmp_path,
        [
            {
                **_row(0),
                "user_text_hash": "sha256:test",
                "segment_hash": "sha256:segment",
                "unsafe_user_text_field": raw_user_text,
                "unsafe_segment_field": raw_segment,
            }
        ],
    )

    report = build_status_report(tmp_path)
    rendered = json.dumps(report, ensure_ascii=False) + "\n" + render_text_report(report)

    assert raw_user_text not in rendered
    assert raw_segment not in rendered
    assert "sha256:test" not in rendered
    assert "sha256:segment" not in rendered
