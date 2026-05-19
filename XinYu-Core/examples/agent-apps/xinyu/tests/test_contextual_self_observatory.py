from __future__ import annotations

import json
from pathlib import Path

from xinyu_contextual_self_observatory import run_contextual_self_observatory
from xinyu_initiative_orchestrator import run_initiative_orchestrator
from test_initiative_orchestrator import _seed_context_gate, _seed_proactive_request


def _append_jsonl(path: Path, events: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n", encoding="utf-8")


def test_contextual_self_observatory_aggregates_recent_loop_recall_and_initiative(tmp_path: Path) -> None:
    _append_jsonl(
        tmp_path / "runtime/contextual_self_loop_trace.jsonl",
        [
            {
                "ts": "2026-05-13T02:00:00+08:00",
                "current_scene": "casual_chat",
                "working_self": "plain_conversation_partner",
                "initiative_posture": "quiet_by_default",
            },
            {
                "ts": "2026-05-13T02:05:00+08:00",
                "current_scene": "initiative_feedback",
                "working_self": "restrained_initiative_operator",
                "initiative_posture": "feedback_shaped",
            },
        ],
    )
    _append_jsonl(
        tmp_path / "runtime/contextual_recall_trace.jsonl",
        [
            {
                "ts": "2026-05-13T02:05:05+08:00",
                "current_scene": "initiative_feedback",
                "admitted_recall_count": 2,
                "suppressed_recall_count": 1,
                "source_count": 2,
            }
        ],
    )
    _append_jsonl(
        tmp_path / "runtime/initiative_lifecycle_events.jsonl",
        [
            {
                "ts": "2026-05-13T02:06:00+08:00",
                "stage": "decision",
                "status": "hold_private",
                "candidate_id": "procand-held",
                "gate": {
                    "held_by": ["context_gate_quiet_by_default"],
                    "negative_reasons": ["context_gate_quiet_by_default"],
                    "notes": ["context_gate_held_private"],
                },
            },
            {
                "ts": "2026-05-13T02:07:00+08:00",
                "stage": "decision",
                "status": "desktop_inbox",
                "candidate_id": "procand-allowed",
                "gate": {
                    "held_by": [],
                    "negative_reasons": [],
                    "notes": ["context_gate_passed"],
                },
            },
            {
                "ts": "2026-05-13T02:08:00+08:00",
                "stage": "feedback",
                "status": "replied",
                "candidate_id": "procand-allowed",
            },
        ],
    )

    summary = run_contextual_self_observatory(
        tmp_path,
        observed_at="2026-05-13T03:00:00+08:00",
    )
    state = (tmp_path / "memory/context/contextual_self_observatory_state.md").read_text(encoding="utf-8")
    written = json.loads((tmp_path / "runtime/contextual_self_observatory.json").read_text(encoding="utf-8"))

    assert summary["scene_counts_24h"]["casual_chat"] == 1
    assert summary["scene_counts_24h"]["initiative_feedback"] == 1
    assert summary["recall_admitted_count_24h"] == 2
    assert summary["initiative_held_by_context_count_24h"] == 1
    assert summary["initiative_allowed_by_context_count_24h"] == 1
    assert summary["quiet_default_hold_count_24h"] == 1
    assert summary["feedback_after_context_allowed_count_24h"] == 1
    assert "observatory_only: true" in state
    assert written["latest_scene"] == "initiative_feedback"


def test_contextual_self_observatory_counts_real_context_gate_pass_event(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)
    _seed_context_gate(
        tmp_path,
        scene="initiative_feedback",
        posture="feedback_shaped",
        recall_count=1,
        next_action="adjust_bias_before_action",
    )
    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
    )

    summary = run_contextual_self_observatory(
        tmp_path,
        observed_at="2026-05-13T03:00:00+08:00",
    )

    assert result["status"] == "desktop_inbox"
    assert summary["initiative_allowed_by_context_count_24h"] == 1
