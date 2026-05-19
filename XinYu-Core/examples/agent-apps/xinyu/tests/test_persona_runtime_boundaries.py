from __future__ import annotations

from xinyu_persona_runtime import RUNTIME_BOUNDARY_LINES, PersonaRuntimeState


def test_persona_runtime_boundaries_are_small_and_layered() -> None:
    joined = "\n".join(RUNTIME_BOUNDARY_LINES)

    assert len(RUNTIME_BOUNDARY_LINES) == 4
    assert "stable_anchor" in joined
    assert "living_state" in joined
    assert "voice_policy" in joined
    assert "memory_boundary" in joined
    assert "hard constraints" not in joined.lower()
    assert "hard lock" not in joined.lower()


def test_persona_runtime_prompt_includes_boundaries_without_stable_rewrite() -> None:
    block = PersonaRuntimeState(
        scene="owner_private",
        is_owner=True,
        pressure="low",
        technical_request=False,
        felt_state="steady",
        relationship_stance="close",
        desire="reply",
    ).to_prompt_block()

    assert "## Runtime Boundaries" in block
    assert "they cannot rewrite stable personality" in block
    assert "repeated or owner-approved evidence" in block
