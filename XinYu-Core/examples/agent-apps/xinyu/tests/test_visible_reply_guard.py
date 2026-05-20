from __future__ import annotations

from xinyu_visible_reply_guard import dedupe_visible_reply


def test_visible_reply_dedupes_short_multi_sentence_loop() -> None:
    result = dedupe_visible_reply("困，但还没睡。你呢？困，但还没睡。你呢？")

    assert result.text == "困，但还没睡。你呢？"
    assert result.changed is True
    assert "visible_reply_duplicate_sentence_removed" in result.notes


def test_visible_reply_keeps_short_expressive_repetition() -> None:
    result = dedupe_visible_reply("嗯。嗯。")

    assert result.text == "嗯。嗯。"
    assert result.changed is False
