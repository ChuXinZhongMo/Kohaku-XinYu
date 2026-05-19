from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _make_runtime(root: Path) -> XinYuBridgeRuntime:
    for rel in (
        "memory/context",
        "memory/self",
        "memory/relationships",
        "memory/people",
        "prompts",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
    _write(root / "config.yaml", "name: xinyu")
    _write(root / "prompts/system.md", "# system")
    _write(root / "prompts/output.md", "# output")
    _write(root / "prompts/live_voice_card.md", "# card")
    _write(root / "memory/self/core.md", "core")
    _write(root / "memory/self/personality_profile.md", "profile")
    _write(root / "memory/self/narrative.md", "narrative")
    return XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=3,
        max_text_chars=8000,
        settle_seconds=0,
        outward_renderer=False,
        autonomous_maintenance_enabled=False,
    )


def _seed_spine_sources(root: Path) -> None:
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State
- pass_id: selfthought-feedback-smoke
- status: held
- outcome: queue_reflection
- focus_kind: reflection_queue
- intention: share_reflection
- candidate_enabled: false
""",
    )
    _write(root / "memory/context/emotion_council_state.md", "# Emotion Council State\n- status: quiet\n")
    _write(
        root / "memory/context/impulse_soup_state.md",
        """# Impulse Soup State
- status: active
- top_thoughtlet_id: impulse-feedback-smoke
- top_desire_shape: dream_residue_compression
- top_energy: 44
- top_action: compress_to_reflection
- outward_action_allowed: false
""",
    )
    _write(
        root / "memory/context/proactive_decision_state.md",
        """# Proactive Decision State
- decision_id: prodecision-feedback-smoke
- source_type: reflection_question
- total_score: 72
- recommendation: inbox
- preferred_channel: inbox
- shadow_only: true
""",
    )
    _write(
        root / "memory/self/learning_closed_loop_state.md",
        """# Learning Closed Loop State
- status: trial_active
- latest_failure_kind: owner_reported_template_voice_failure
- next_action: apply_trial_habit_on_similar_turn
- repair_count: 36
- success_count: 0
- success_streak: 0
""",
    )


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-feedback-spine-") as tmp:
        root = Path(tmp)
        runtime = _make_runtime(root)
        _seed_spine_sources(root)
        _write(
            root / "memory/context/proactive_request_state.md",
            """---
title: Proactive Request State
updated_at: 2026-05-11T12:00:00+08:00
status: active
---

# Proactive Request State

## Current Request
- request_id: proreq-feedback-smoke
- created_at: 2026-05-11T12:00:00+08:00
- status: sent
- kind: reflection_share
- source: self_thought
- delivery_level: queue_owner_private
- concrete_question: 关于被记住这件事我还没放下。你想让我把它当长期关系需要，还是只按每次具体对话来记？
- request_answer_state: pending
- owner_reply_feedback: updates_request_and_source_thread
- last_ack_status: sent
""",
        )
        _write(
            root / "memory/context/proactive_qq_dispatch_state.md",
            """# Proactive QQ Dispatch State
- last_claim_status: sent
- proactive_request_id: proreq-feedback-smoke
- last_claimed_message: 关于被记住这件事我还没放下。你想让我把它当长期关系需要，还是只按每次具体对话来记？
- last_claimed_at: 2026-05-11T12:00:05+08:00
""",
        )

        marked = runtime._mark_proactive_owner_reply(
            {
                "message_type": "private_text",
                "metadata": {"is_owner_user": True},
            },
            text="对的，我希望你长期记住。",
            reply="嗯，我按长期关系来接。",
        )
        request_state = _read(root / "memory/context/proactive_request_state.md")
        spine_state = _read(root / "memory/context/initiative_spine_state.md")
        trace = _read(root / "runtime/initiative_spine_trace.jsonl")

        if not marked:
            failures.append("owner proactive reply was not marked")
        for marker in (
            "- status: answered",
            "- request_answer_state: owner_replied",
            "owner_replied_at:",
            "owner_reply_preview:",
        ):
            if marker not in request_state:
                failures.append(f"proactive request state missing marker: {marker}")
        for marker in (
            "emergence_level: feedback_absorption",
            "action_permission: owner_thread_answered_feedback_only",
            "proactive_lane: request=answered/reflection_share/owner_replied",
            "next_step: absorb owner reply into learning/memory gates before new initiative",
        ):
            if marker not in spine_state:
                failures.append(f"initiative spine state missing marker: {marker}")
        if "owner_reply_to_proactive" not in trace:
            failures.append("initiative spine trace missing owner reply trigger")

    if failures:
        print("Proactive feedback spine smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Proactive feedback spine smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
