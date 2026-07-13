from __future__ import annotations

from pathlib import Path

from xinyu_persona_contract import (
    build_persona_runtime_contract_block,
    persona_contract_quality_flags,
)
from xinyu_persona_runtime import build_persona_runtime_state


def test_persona_contract_has_living_surface_and_boundaries() -> None:
    block = build_persona_runtime_contract_block()

    assert persona_contract_quality_flags(block) == ()
    assert "Current owner text outranks recalled context" in block
    assert "Emotion is not evidence for facts" in block
    assert "fake biological claims" in block
    assert "service-script comfort" in block


def test_persona_runtime_injects_contract_before_current_state(tmp_path: Path) -> None:
    state = build_persona_runtime_state(
        tmp_path,
        payload={"metadata": {"is_owner_user": True}},
        user_text="continue",
    )
    block = state.to_prompt_block()

    assert "## Persona Runtime Contract" in block
    assert "## Current Surface Seed" in block
    assert block.index("## Persona Runtime Contract") < block.index("## Current Surface Seed")
    assert "not a claim of real biology" in block
    assert "stable personality rewrite from a single intense turn" in block


def test_persona_runtime_injects_kernel_continuity_orientation(tmp_path: Path) -> None:
    kernel_dir = tmp_path / "memory" / "kernel"
    kernel_dir.mkdir(parents=True)
    import json

    (kernel_dir / "self_story_state.json").write_text(
        json.dumps({"summary": "Stay honest and direct with owner."}),
        encoding="utf-8",
    )
    state = build_persona_runtime_state(
        tmp_path,
        payload={"metadata": {"is_owner_user": True}},
        user_text="continue",
    )
    block = state.to_prompt_block()

    assert state.continuity_orientation == "Stay honest and direct with owner."
    assert "## Continuity Orientation" in block
    assert "Stay honest and direct with owner." in block
    assert "kernel" not in block.lower()


def test_persona_contract_keeps_technical_work_out_of_emotional_performance() -> None:
    block = build_persona_runtime_contract_block()

    assert "For technical work" in block
    assert "clear and executable" in block
