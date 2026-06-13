from __future__ import annotations

import xinyu_bridge_turn_sidecars


def test_looks_like_time_fact_correction_requires_correction_and_time_cues() -> None:
    assert xinyu_bridge_turn_sidecars.looks_like_time_fact_correction("不是 5.5 假期才结束吗") is True
    assert xinyu_bridge_turn_sidecars.looks_like_time_fact_correction("不是这样的") is False
    assert xinyu_bridge_turn_sidecars.looks_like_time_fact_correction("今天星期几") is False
    assert xinyu_bridge_turn_sidecars.looks_like_time_fact_correction("") is False
