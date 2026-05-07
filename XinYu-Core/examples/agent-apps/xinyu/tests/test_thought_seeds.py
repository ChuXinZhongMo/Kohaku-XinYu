from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_thought_seeds import refresh_thought_seeds  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_thought_seeds_combine_residue_dream_unfinished_and_drives(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/persona_surface_state.md",
        """# Persona Surface State

## Previous Visible Turn
- updated_at: 2026-04-29T20:00:00+08:00
- last_scene: owner_style_pressure
- last_pressure: style
- last_tone: short_affected_guarded
- last_felt_residue: owner heard style failure; keep a small guarded edge
- last_reply_shape: compact
- residue_strength: 88
""",
    )
    _write(
        tmp_path / "memory/dreams/dream_weight_state.md",
        """# Dream Weight State

## Latest
- source_seed: seed-2026-04-29-codex
- theme: timeout handoff still matters
- residue: a task was not closed cleanly
- weight_after: 74
- weight_delta: 6
- weight_effect: existing_emotional_residue_strengthened
""",
    )
    _write(
        tmp_path / "memory/dreams/dream_log.md",
        """# Dream Log

## dream-2026-04-29-auto
- fragments: a half-finished repair becoming a small dream fragment
- reality_boundary_check: dream does not prove a new real event
""",
    )
    _write(
        tmp_path / "memory/context/unfinished_experiences.md",
        """# Unfinished Experiences

## item-2026-04-29-001
- event: owner said memory and dream systems still feel unfinished
- target: self / architecture
- unresolved_reason: the defect has not been repaired yet
- residual_feeling: pressure to make the system less shallow
""",
    )
    _write(
        tmp_path / "memory/context/initiative_state.md",
        """# Initiative State

## Latest Decision
- decision: defer
- reason: no_proactive_question_candidate_after_generation_policy
- selected_question: none
- visible_posture: quiet_available
""",
    )
    _write(
        tmp_path / "memory/context/active_questions.md",
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
        tmp_path / "memory/context/memory_weight_state.md",
        """# Memory Weight State

## Active Weights
- path: memory/self/core.md | layer: stable_identity | active_weight: 98 | base_weight: 98 | age_hours: 0.00 | floor: 96 | stable: true
- path: memory/dreams/dream_weight_state.md | layer: floating_dream_residue | active_weight: 72 | base_weight: 82 | age_hours: 2.00 | floor: 10 | stable: false
""",
    )

    snapshot = refresh_thought_seeds(
        tmp_path,
        generated_at="2026-04-29T22:30:00+08:00",
    )

    assert snapshot.dominant_drive == "recent_surface_residue"
    assert "Thought Seeds" in snapshot.text
    assert "Recent Interaction Residue" in snapshot.text
    assert "- source_seed: seed-2026-04-29-codex" in snapshot.text
    assert "owner said memory and dream systems still feel unfinished" in snapshot.text
    assert "how should autonomous thoughts avoid needy chatter" in snapshot.text
    assert "output_form: owner-visible private desktop note" in snapshot.text
    assert "dreams can color emotion but cannot create new facts" in snapshot.llm_material
    assert (tmp_path / "memory/context/thought_seeds.md").exists()
