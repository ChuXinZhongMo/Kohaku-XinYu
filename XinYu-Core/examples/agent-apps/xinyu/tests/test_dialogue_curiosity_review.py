from __future__ import annotations

import json
from pathlib import Path

from dialogue_curiosity_review import build_review


def append_jsonl(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def test_dialogue_curiosity_review_summarizes_high_error_cases(tmp_path) -> None:
    root = tmp_path / "xinyu"
    runtime = root / "runtime" / "dialogue_curiosity"
    prediction = {
        "prediction_id": "pred-1",
        "session_key": "qq:private:owner",
        "source_scope": "owner_private",
        "predicted_next": {
            "style_complaint": 0.1,
            "relationship_pressure_up": 0.1,
            "technical_continue": 0.2,
            "softening": 0.8,
        },
        "user_preview": "早",
        "reply_preview": "早。",
    }
    evaluation = {
        "evaluation_id": "eval-1",
        "prediction_id": "pred-1",
        "evaluated_at": "2026-04-29T10:01:00+08:00",
        "source_scope": "owner_private",
        "prediction_error": 0.72,
        "actual_next": {
            "style_complaint": 1.0,
            "relationship_pressure_up": 1.0,
            "technical_continue": 0.0,
            "softening": 0.0,
        },
        "current_user_preview": "还是很接待腔。",
        "reaction_features": {
            "markers": {
                "style": ["接待腔"],
                "relationship": [],
                "technical": [],
                "escalation": ["还是"],
                "softening": [],
            }
        },
    }
    append_jsonl(runtime / "predictions.jsonl", prediction)
    append_jsonl(runtime / "evaluations.jsonl", evaluation)
    append_jsonl(runtime / "error_cases.jsonl", evaluation)

    report = build_review(root, limit=5)

    assert "# Dialogue Curiosity Review" in report
    assert "- predictions: 1" in report
    assert "- evaluations: 1" in report
    assert "- high_error_cases: 1" in report
    assert "- style_complaint: 1" in report
    assert "### Case 1" in report
    assert "previous_reply: 早。" in report
    assert "next_user: 还是很接待腔。" in report
    assert "style:接待腔" in report

