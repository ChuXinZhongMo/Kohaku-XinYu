from __future__ import annotations

import sys
from pathlib import Path


CUSTOM_DIR = Path(__file__).resolve().parents[1] / "custom"
if str(CUSTOM_DIR) not in sys.path:
    sys.path.insert(0, str(CUSTOM_DIR))

from source_request_planner_engine import run_source_request_planner  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_quality_followup_reuses_existing_question_target_when_active_question_is_missing(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/active_questions.md",
        """# Active Questions

## q-902
- target: memory-emotion
""",
    )
    _write(
        tmp_path / "memory/knowledge/source_integration_gate_state.md",
        """# Source Integration Gate State

- integration_permission: prepare_only
""",
    )
    _write(
        tmp_path / "memory/knowledge/source_gate_state.md",
        """# Source Gate State

## Current Candidates
- none
""",
    )
    _write(
        tmp_path / "memory/knowledge/learning_quality_state.md",
        """# Learning Quality State

## Warnings
- repeated_question_host: severity=review; target=q-903@alpha.example; detail=2/2 learned entries for q-903 come from the same host
""",
    )
    _write(
        tmp_path / "memory/knowledge/source_requests.md",
        """# Source Requests

## request-2026-05-18-001
- question_id: q-903
- target: human-relationship
- query: human relationships attachment boundaries closeness distance trust reliable source
- url: https://alpha.example/first
- status: ready
- reason: existing learned source

## request-2026-05-19-001
- question_id: q-903
- target: general
- query: general reliable source
- url: none
- status: pending_url
- followup_kind: source_diversity
- avoid_host: alpha.example
- followup_slot: 1
- reason: source diversity follow-up for repeated host alpha.example

## request-2026-05-19-002
- question_id: q-903
- target: general
- query: general reliable source
- url: none
- status: pending_url
- followup_kind: source_diversity
- avoid_host: alpha.example
- followup_slot: 2
- reason: source diversity follow-up for repeated host alpha.example
""",
    )

    result = run_source_request_planner(
        tmp_path,
        planned_at="2026-05-21T12:00:00+08:00",
        mode="target_recovery_test",
    )

    request_text = (tmp_path / "memory/knowledge/source_requests.md").read_text(encoding="utf-8")
    assert result["normalized_requests"] == 2
    assert result["planned_requests"] == 0
    assert result["skipped_reason"] == "requests_already_planned_target_normalized"
    assert request_text.count("- target: human-relationship") == 3
    assert "human relationships attachment boundaries closeness distance trust reliable source" in request_text
    assert "general reliable source" not in request_text
