from __future__ import annotations

from ops.validation.live_chat_regression_baseline import _hard_quality_failed, _quality_snapshot, _summary


def test_quality_summary_counts_empty_reply() -> None:
    quality = _quality_snapshot("")
    summary = _summary([{"ok": True, "quality": quality, "reply_chars": 0, "pressure_changed": False}])

    assert quality["empty_reply"] is True
    assert summary["empty_reply_count"] == 1
    assert _hard_quality_failed(summary) is True


def test_quality_snapshot_allows_softened_i_will_change_phrase() -> None:
    quality = _quality_snapshot("别反复念叨了，我知道啦，我会改的啦。")

    assert quality["reportish"] is False
    assert quality["reportish_hits"] == []
