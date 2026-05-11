from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_turn_coherence import (
    STATE_MD_REL,
    TRACE_REL,
    build_turn_coherence_prompt_block,
    finish_turn_coherence,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-turn-coherence-") as tmp:
        root = Path(tmp)
        _write(
            root / "memory/context/memory_braid_state.md",
            "# Memory Braid State\n- owner_visible_address: 哥\n- continuity_available: true",
        )
        _write(
            root / "memory/self/private_thought_state.md",
            "# Private Thought State\n- event_id: private-thought-smoke\n- intended_behavior: stay concrete",
        )
        _write(
            root / "memory/context/self_thought_state.md",
            "# Self Thought State\n- focus_kind: expression_repair",
        )
        _write(
            root / "memory/context/proactive_request_state.md",
            "# Proactive Request State\n- status: ready\n- kind: dream_share",
        )

        block = build_turn_coherence_prompt_block(
            root,
            payload={"metadata": {"is_owner_user": True}},
            user_text="不仅记忆要串起来，思维和动作也要保持一致性",
            turn_id="turn-smoke",
            memory_braid_block="## Memory Braid Runtime Context\nowner_visible_address: 哥",
            recalled_context="recalled",
            continuity_context="continuity",
            persona_context="persona",
            emotion_council_context="emotion",
            recent_action_context="recent action",
            checked_at="2026-05-10T23:40:00+08:00",
            write_state=True,
        )
        for marker in (
            "Turn Coherence Runtime Context",
            "not_a_template: true",
            "turn_spine: turn-smoke|coherence_pressure",
            "current_turn_intent: coherence_pressure",
            "memory_lane: memory_braid_active",
            "private_thought=private-thought-smoke",
            "action_lane: current_turn_requests_coherence_repair",
            "memory lane, thought lane, visible reply, and action lane",
            "visible reply, memory candidates, private-thought link, and any action/follow-up",
        ):
            if marker not in block:
                failures.append(f"turn coherence block missing marker: {marker}")

        project_block = build_turn_coherence_prompt_block(
            root,
            payload={"metadata": {"is_owner_user": True}},
            user_text="不是套模板，我们整个项目是为了接近活生生的人",
            turn_id="turn-template-pressure",
            checked_at="2026-05-10T23:40:30+08:00",
            write_state=False,
        )
        if "current_turn_intent: coherence_pressure" not in project_block:
            failures.append("template/personhood pressure was not classified as coherence_pressure")

        status_block = build_turn_coherence_prompt_block(
            root,
            payload={"metadata": {"is_owner_user": True}},
            user_text="现在好了吗？",
            turn_id="turn-status-pressure",
            checked_at="2026-05-10T23:40:40+08:00",
            write_state=False,
        )
        if "current_turn_intent: technical_or_repair_action" not in status_block:
            failures.append("runtime repair status question was not classified as technical_or_repair_action")

        result = finish_turn_coherence(
            root,
            turn_id="turn-smoke",
            payload={"metadata": {"is_owner_user": True}},
            user_text="不仅记忆要串起来，思维和动作也要保持一致性",
            reply="我开始把这三条链路接成同一个 turn。",
            action_result="none",
            memory_changed=True,
            final_guard_flags=["owner_address_label_blocked"],
            component_notes={
                "private_thought_link": {"notes": ["private_thought_reply_linked"]},
                "emotion_council": {"notes": ["emotion_council:observed"]},
                "persona_sidecar": {"notes": ["persona_state_updated"]},
                "memory_self_review": {"notes": ["memory_self_review_completed"]},
            },
            checked_at="2026-05-10T23:41:00+08:00",
        )
        state = (root / STATE_MD_REL).read_text(encoding="utf-8")
        trace = (root / TRACE_REL).read_text(encoding="utf-8")
        if result.get("action_lane") != "coherence_reply_or_repair_recorded":
            failures.append(f"finish result did not keep action lane: {result}")
        if "phase: post_reply" not in state or "turn_spine: turn-smoke|coherence_pressure" not in state:
            failures.append("post-reply coherence state missing turn spine")
        if "emotion_council: emotion_council:observed" not in state:
            failures.append("post-reply coherence state missing emotion council component note")
        if "coherence_reply_or_repair_recorded" not in state:
            failures.append("post-reply coherence state missing final action lane")
        if "turn_coherence_started" not in trace or "turn_coherence_finished" not in trace:
            failures.append("turn coherence trace did not record both phases")
        if "reply template" not in state:
            failures.append("turn coherence state missing non-template boundary")

    if failures:
        print("Turn coherence smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Turn coherence smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
