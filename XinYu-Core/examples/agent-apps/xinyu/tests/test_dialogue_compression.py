from __future__ import annotations

import pytest

from xinyu_dialogue_compression import (
    SUMMARY_ROLE,
    build_extractive_summary,
    compress_window,
    should_compress,
)
from xinyu_dialogue_working_memory import compact_tail_for_prompt


def _tail(n: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        rows.append({"role": role, "content": f"消息内容编号{i}，这是一段足够长的对话文本用于测试压缩行为。", "recorded_at": f"t{i}"})
    return rows


def test_short_tail_is_not_compressed() -> None:
    tail = _tail(5)
    out = compact_tail_for_prompt(tail, max_entries=32)
    assert all(item["role"] in {"user", "assistant"} for item in out)
    assert not any(item["role"] == SUMMARY_ROLE for item in out)


def test_long_tail_folds_older_turns_into_summary() -> None:
    tail = _tail(30)
    out = compact_tail_for_prompt(tail, max_entries=32, include_timestamps=True)
    # exactly one summary row, placed first, followed by the freshest raw turns.
    summaries = [item for item in out if item["role"] == SUMMARY_ROLE]
    assert len(summaries) == 1
    assert out[0]["role"] == SUMMARY_ROLE
    # the freshest turn must survive verbatim (not dropped by the char budget).
    raw = [item for item in out if item["role"] != SUMMARY_ROLE]
    assert raw, "recent raw turns should remain"
    assert "编号29" in raw[-1]["content"]


def test_compress_can_be_disabled() -> None:
    tail = _tail(30)
    out = compact_tail_for_prompt(tail, max_entries=32, compress=False)
    assert not any(item["role"] == SUMMARY_ROLE for item in out)


def test_summarizer_seam_is_used_when_provided() -> None:
    tail = _tail(30)

    def fake_summarizer(older, budget):
        return f"LLM_SUMMARY_OF_{len(older)}_TURNS"

    out = compact_tail_for_prompt(tail, max_entries=32, summarizer=fake_summarizer)
    assert out[0]["role"] == SUMMARY_ROLE
    assert out[0]["content"].startswith("LLM_SUMMARY_OF_")


def test_summarizer_failure_falls_back_to_extractive() -> None:
    tail = _tail(30)

    def boom(older, budget):
        raise RuntimeError("model down")

    out = compact_tail_for_prompt(tail, max_entries=32, summarizer=boom)
    assert out[0]["role"] == SUMMARY_ROLE
    assert out[0]["content"]  # extractive fallback produced something


def test_build_extractive_summary_respects_budget() -> None:
    older = _tail(20)
    summary = build_extractive_summary(older, 300)
    assert summary
    assert len(summary) <= 300


def test_should_compress_threshold() -> None:
    assert should_compress(20, keep_recent=8, trigger=6) is True
    assert should_compress(12, keep_recent=8, trigger=6) is False


def test_compress_window_returns_recent_unchanged_when_below_threshold() -> None:
    usable = _tail(10)
    summary, recent = compress_window(usable, keep_recent=8, trigger=6)
    assert summary is None
    assert recent == usable
