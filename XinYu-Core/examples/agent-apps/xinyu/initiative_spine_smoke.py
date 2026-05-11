from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_initiative_spine import (
    STATE_MD_REL,
    TRACE_REL,
    build_initiative_spine_prompt_block,
    run_initiative_spine,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-initiative-spine-") as tmp:
        root = Path(tmp)
        _write(
            root / "memory/context/self_thought_state.md",
            """# Self Thought State
- pass_id: selfthought-smoke
- status: held
- outcome: queue_reflection
- focus_kind: reflection_queue
- intention: share_reflection
- candidate_enabled: false
""",
        )
        _write(
            root / "memory/context/emotion_council_state.md",
            """# Emotion Council State
- status: active
- strongest_lens: concern
- output_bias: stay concrete
- active_lens_count: 1
""",
        )
        _write(
            root / "memory/context/impulse_soup_state.md",
            """# Impulse Soup State
- status: active
- top_thoughtlet_id: impulse-smoke
- top_desire_shape: expression_repair_habit
- top_energy: 58
- top_action: stabilize_expression_habit
- outward_action_allowed: false
""",
        )
        _write(
            root / "memory/context/proactive_decision_state.md",
            """# Proactive Decision State
- decision_id: prodecision-smoke
- source_type: style_repair
- total_score: 99
- recommendation: send_now
- preferred_channel: qq
- shadow_only: true
""",
        )
        _write(
            root / "memory/context/proactive_request_state.md",
            """# Proactive Request State
- request_id: proreq-smoke
- status: answered
- kind: reflection_share
- request_answer_state: owner_replied
- concrete_question: should I keep following the repair thread?
- owner_reply_feedback: updates_request_and_source_thread
""",
        )
        _write(
            root / "memory/self/learning_closed_loop_state.md",
            """# Learning Closed Loop State
- status: trial_active
- latest_failure_kind: owner_reported_template_voice_failure
- next_action: apply_trial_habit_on_similar_turn
- repair_count: 3
- success_count: 1
- success_streak: 1
""",
        )

        result = run_initiative_spine(
            root,
            checked_at="2026-05-11T00:20:00+08:00",
            trigger="smoke",
        )
        state = (root / STATE_MD_REL).read_text(encoding="utf-8")
        trace = (root / TRACE_REL).read_text(encoding="utf-8")
        block = build_initiative_spine_prompt_block(
            root,
            checked_at="2026-05-11T00:21:00+08:00",
            trigger="prompt_smoke",
            write_state=False,
        )

        if result.get("emergence_level") != "feedback_absorption":
            failures.append(f"unexpected emergence level: {result}")
        for marker in (
            "Initiative Spine Runtime Context",
            "not_a_template: true",
            "pressure -> choice -> action permission -> feedback",
            "action_permission: owner_thread_answered_feedback_only",
            "feedback_lane: trial_active",
        ):
            if marker not in block:
                failures.append(f"prompt block missing marker: {marker}")
        for marker in (
            "Initiative Spine State",
            "emergence_level: feedback_absorption",
            "self_thought_lane: held/queue_reflection/reflection_queue/share_reflection",
            "impulse_lane: active/expression_repair_habit/energy=58/action=stabilize_expression_habit/outward=false",
            "never authorizes QQ send",
        ):
            if marker not in state:
                failures.append(f"state missing marker: {marker}")
        if "initiative_spine_synthesized" not in trace:
            failures.append("trace missing synthesis event")

    if failures:
        print("Initiative spine smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Initiative spine smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
