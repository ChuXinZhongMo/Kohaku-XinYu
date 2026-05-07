from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_curiosity import evaluate_previous_reaction, record_reply_prediction


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_dialogue_curiosity_records_and_evaluates_high_error(tmp_path) -> None:
    root = tmp_path / "xinyu"
    root.mkdir()
    session_key = "qq:private:owner"
    payload = {
        "text": "早",
        "session_id": session_key,
        "metadata": {"is_owner_user": True},
    }

    predicted = record_reply_prediction(
        root,
        payload,
        user_text="早",
        reply="早。",
        session_key=session_key,
        recorded_at="2026-04-29T10:00:00+08:00",
    )

    assert "dialogue_curiosity_prediction_recorded" in predicted["notes"]

    evaluated = evaluate_previous_reaction(
        root,
        payload,
        text="还是很接待腔，完全没接住。",
        session_key=session_key,
        observed_at="2026-04-29T10:01:00+08:00",
    )

    assert evaluated["evaluated"] is True
    assert evaluated["prediction_error"] >= 0.55
    assert "dialogue_curiosity_high_error" in evaluated["notes"]
    assert "dialogue_curiosity_soft_hint" in evaluated["notes"]
    assert "Dialogue Curiosity Soft Hint" in evaluated["prompt_block"]
    assert "stable_memory_write: blocked" in evaluated["prompt_block"]

    runtime_dir = root / "runtime" / "dialogue_curiosity"
    assert len(load_jsonl(runtime_dir / "predictions.jsonl")) == 1
    assert len(load_jsonl(runtime_dir / "evaluations.jsonl")) == 1
    assert len(load_jsonl(runtime_dir / "error_cases.jsonl")) == 1


def test_dialogue_curiosity_group_context_has_lower_weight(tmp_path) -> None:
    root = tmp_path / "xinyu"
    root.mkdir()
    session_key = "qq:group:123:u"
    payload = {
        "text": "不像人",
        "session_id": session_key,
        "group_id": "123",
        "message_type": "group_text",
        "metadata": {},
    }

    record_reply_prediction(
        root,
        payload,
        user_text="不像人",
        reply="我理解你的反馈，我会继续优化用户体验。",
        session_key=session_key,
        recorded_at="2026-04-29T10:00:00+08:00",
    )
    evaluated = evaluate_previous_reaction(
        root,
        payload,
        text="还是很接待腔",
        session_key=session_key,
        observed_at="2026-04-29T10:01:00+08:00",
    )

    assert evaluated["evaluated"] is True
    assert evaluated["prediction_error"] < 0.55
    assert "dialogue_curiosity_high_error" not in evaluated["notes"]
    assert evaluated["prompt_block"] == ""
