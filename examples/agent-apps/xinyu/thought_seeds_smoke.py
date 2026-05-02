from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_thought_seeds import refresh_thought_seeds


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-thought-seeds-") as tmp:
        root = Path(tmp)
        _write(
            root / "memory/context/persona_surface_state.md",
            """# Persona Surface State

## Previous Visible Turn
- last_scene: owner_style_pressure
- last_pressure: style
- last_tone: short_affected_guarded
- last_felt_residue: owner heard style failure; keep a small guarded edge
- last_reply_shape: compact
- residue_strength: 88
""",
        )
        _write(
            root / "memory/dreams/dream_weight_state.md",
            """# Dream Weight State

## Latest
- source_seed: seed-2026-04-29-smoke
- theme: smoke dream residue
- residue: a repair remained unfinished
- weight_after: 74
- weight_delta: 6
- weight_effect: existing_emotional_residue_strengthened
""",
        )
        _write(
            root / "memory/dreams/dream_log.md",
            """# Dream Log

## dream-2026-04-29-auto
- fragments: unfinished repair as a dream fragment
- reality_boundary_check: dream does not prove a new real event
""",
        )
        _write(
            root / "memory/context/unfinished_experiences.md",
            """# Unfinished Experiences

## item-2026-04-29-001
- event: owner said memory and dream systems still feel unfinished
- target: self / architecture
- unresolved_reason: the defect has not been repaired yet
- residual_feeling: pressure to make the system less shallow
""",
        )
        _write(
            root / "memory/context/initiative_state.md",
            """# Initiative State

## Latest Decision
- decision: defer
- reason: no_proactive_question_candidate_after_generation_policy
- selected_question: none
- visible_posture: quiet_available
""",
        )
        _write(
            root / "memory/context/active_questions.md",
            """# Active Questions

## q-100
- question: how should autonomous thoughts avoid needy chatter
- target: self
- status: open
- emotional_weight: 80
- outward_scope: internal_only
""",
        )
        _write(
            root / "memory/context/memory_weight_state.md",
            """# Memory Weight State

## Active Weights
- path: memory/self/core.md | layer: stable_identity | active_weight: 98 | base_weight: 98 | age_hours: 0.00 | floor: 96 | stable: true
- path: memory/dreams/dream_weight_state.md | layer: floating_dream_residue | active_weight: 72 | base_weight: 82 | age_hours: 2.00 | floor: 10 | stable: false
""",
        )

        snapshot = refresh_thought_seeds(root, generated_at="2026-04-29T22:30:00+08:00")
        required = (
            "Thought Seeds",
            "dominant_drive: recent_surface_residue",
            "source_seed: seed-2026-04-29-smoke",
            "owner said memory and dream systems still feel unfinished",
            "output_form: owner-visible private desktop note",
            "dreams can color emotion but cannot create new facts",
        )
        joined = snapshot.text + "\n" + snapshot.llm_material
        for marker in required:
            if marker not in joined:
                failures.append(f"missing marker: {marker}")
        if not (root / "memory/context/thought_seeds.md").exists():
            failures.append("thought_seeds.md was not written")

    if failures:
        print("Thought seeds smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Thought seeds smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
