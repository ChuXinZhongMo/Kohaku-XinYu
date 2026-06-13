from __future__ import annotations

import json
from pathlib import Path

from xinyu_uncertainty_pause import STATE_REL
from xinyu_uncertainty_pause import TRACE_REL
from xinyu_uncertainty_pause import active_uncertainty_pause
from xinyu_uncertainty_pause import build_uncertainty_pause_prompt_block
from xinyu_uncertainty_pause import mark_uncertainty_pause_replied
from xinyu_uncertainty_pause import record_uncertainty_pause


def test_uncertainty_pause_records_owner_private_followup_without_raw_reply_leak(tmp_path: Path) -> None:
    result = record_uncertainty_pause(
        tmp_path,
        {"is_owner_user": True, "message_type": "private"},
        user_text="Should I continue?",
        draft_reply="internal mechanical reply",
        reason="low_confidence",
        session_key="qq:private:owner",
        observed_at="2026-06-01T10:00:00+08:00",
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    trace = json.loads((tmp_path / TRACE_REL).read_text(encoding="utf-8").splitlines()[0])
    active = active_uncertainty_pause(tmp_path)
    prompt = build_uncertainty_pause_prompt_block(tmp_path)

    assert result["recorded"] is True
    assert result["followup_allowed"] is True
    assert active["reason"] == "low_confidence"
    assert "followup_allowed: true" in state
    assert "internal mechanical reply" in state
    assert trace["owner_private"] is True
    assert "uncertainty pause sidecar:" in prompt
    assert "internal mechanical reply" not in prompt


def test_uncertainty_pause_mark_replied_closes_active_state(tmp_path: Path) -> None:
    record_uncertainty_pause(
        tmp_path,
        {"is_owner_user": True, "message_type": "private"},
        user_text="Need a pause",
        reason="low_confidence",
        observed_at="2026-06-01T10:00:00+08:00",
    )

    result = mark_uncertainty_pause_replied(
        tmp_path,
        text="continue with current memory",
        observed_at="2026-06-01T10:01:00+08:00",
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    rows = [json.loads(line) for line in (tmp_path / TRACE_REL).read_text(encoding="utf-8").splitlines()]

    assert result["recorded"] is True
    assert "status: owner_replied" in state
    assert active_uncertainty_pause(tmp_path) == {}
    assert rows[-1]["event_kind"] == "owner_replied"
