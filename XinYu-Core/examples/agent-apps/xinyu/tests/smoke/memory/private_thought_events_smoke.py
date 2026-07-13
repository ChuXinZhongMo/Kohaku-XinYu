from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_private_thought_events import (
    build_private_thought_note_material,
    record_private_thought_outcome,
    record_private_thought_reply_link,
    refresh_private_thought_event_sync,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-private-thought-") as tmp:
        root = Path(tmp)
        _write(
            root / "memory/context/persona_surface_state.md",
            """# Persona Surface State

## Previous Visible Turn
- last_scene: owner_style_pressure
- last_pressure: style
- last_tone: short_affected_guarded
- last_felt_residue: owner still heard the reply as mechanical
- last_reply_shape: compact
- residue_strength: 86
""",
        )
        _write(
            root / "memory/context/initiative_state.md",
            """# Initiative State

## Latest Decision
- decision: defer
- reason: wait for owner signal
- selected_question: none
- visible_posture: quiet_available
""",
        )
        _write(
            root / "memory/context/memory_weight_state.md",
            """# Memory Weight State

## Active Weights
- path: memory/self/core.md | layer: stable_identity | active_weight: 98 | base_weight: 98 | age_hours: 0.00 | floor: 96 | stable: true
""",
        )

        snapshot = refresh_private_thought_event_sync(
            root,
            generated_at="2026-04-30T10:00:00+08:00",
            source_kind="private_thought_smoke",
            trigger="smoke",
        )
        material = build_private_thought_note_material(root, generated_at="2026-04-30T10:00:00+08:00")
        record_private_thought_reply_link(
            root,
            {},
            user_text="你还是太机械了",
            reply="知道了，我这次不解释，直接改。",
            session_key="owner-session",
            linked_at="2026-04-30T10:01:00+08:00",
        )
        outcome = record_private_thought_outcome(
            root,
            {},
            text="还是没变",
            session_key="owner-session",
            evaluation={"evaluated": True, "prediction_error": 0.72, "notes": ["dialogue_curiosity_high_error"]},
            observed_at="2026-04-30T10:02:00+08:00",
        )
        joined = "\n".join(
            [
                snapshot.text,
                material,
                (root / "memory/self/private_thought_state.md").read_text(encoding="utf-8"),
                (root / "memory/self/self_model_state.md").read_text(encoding="utf-8"),
                (root / "memory/self/private_thought_feedback_state.md").read_text(encoding="utf-8"),
            ]
        )
        required = (
            "Private Thought State",
            "private_thought_event_state",
            "safe private-thought event summary",
            "Self Model State",
            "compare_loop: private thought event -> visible behavior link -> next owner reaction -> self-model update",
            "outcome: needs_repair",
        )
        for marker in required:
            if marker not in joined:
                failures.append(f"missing marker: {marker}")
        if outcome.get("outcome") != "needs_repair":
            failures.append("outcome did not mark needs_repair")

    if failures:
        print("Private thought events smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Private thought events smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

