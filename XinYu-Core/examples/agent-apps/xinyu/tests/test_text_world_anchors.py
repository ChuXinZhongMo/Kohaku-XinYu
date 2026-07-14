from __future__ import annotations

from datetime import datetime

from xinyu_text_world_anchors import (
    apply_text_realism_visible_pass,
    repair_visible_weekday_claims,
    world_anchor_prompt_block,
)


def test_world_anchor_prompt_contains_tuesday_for_fixed_day() -> None:
    block = world_anchor_prompt_block(now=datetime.fromisoformat("2026-07-14T10:00:00+08:00"))
    assert "today_local_weekday: 周二" in block
    assert "today_local_date: 2026-07-14" in block
    assert "只能说「周二」" in block


def test_repairs_wrong_today_weekday_claim() -> None:
    now = datetime.fromisoformat("2026-07-14T10:00:00+08:00")
    result = repair_visible_weekday_claims("哥，上午好。周日呢。", now=now)
    # Bare "周日" without 今天 is not auto-rewritten (could be about plans).
    assert result["changed"] is False

    result2 = repair_visible_weekday_claims("今天是周日。", now=now)
    assert result2["changed"] is True
    assert "周二" in result2["reply"]
    assert "周日" not in result2["reply"]


def test_visible_pass_keeps_correct_weekday() -> None:
    now = datetime.fromisoformat("2026-07-14T10:00:00+08:00")
    result = apply_text_realism_visible_pass("今天周二。", now=now)
    assert result["changed"] is False
    assert result["reply"] == "今天周二。"
