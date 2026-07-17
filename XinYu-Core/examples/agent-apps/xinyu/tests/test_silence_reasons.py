from __future__ import annotations

from xinyu_silence_reasons import (
    ALL_REASONS,
    EMPTY_CONCRETE,
    normalize_silence_reason,
    silence_explain_rate,
)


def test_normalize_known() -> None:
    assert normalize_silence_reason("empty_concrete") == EMPTY_CONCRETE
    assert normalize_silence_reason("owner long idle") == "owner_long_idle_silent"


def test_explain_rate() -> None:
    rate = silence_explain_rate(["empty_concrete", "no_finding", "weird_custom"])
    assert 0.0 < rate < 1.0
    assert silence_explain_rate(list(ALL_REASONS)) == 1.0
