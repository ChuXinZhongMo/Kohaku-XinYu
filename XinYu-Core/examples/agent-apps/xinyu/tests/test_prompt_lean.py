from __future__ import annotations

from types import SimpleNamespace

import pytest

from xinyu_bridge_turn_prompt_payload import (
    build_lean_live_system_prompt,
    build_live_system_prompt,
)
from xinyu_prompt_lean import lean_prompt_enabled, lean_sidecar_admitted
from xinyu_prompt_pressure import PromptSidecar, select_prompt_sidecars


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("XINYU_LEAN_PROMPT", raising=False)


def _live_state() -> SimpleNamespace:
    def block(text: str):
        return SimpleNamespace(to_prompt_block=lambda text=text: text)

    return SimpleNamespace(
        visible_turn=SimpleNamespace(turn_kind="ordinary_owner_chat", to_prompt_block=lambda: "VISIBLE_TURN"),
        life_posture=block("LIFE_POSTURE_BLOCK"),
        persona_runtime=block("PERSONA_RUNTIME_IDENTITY"),
        relation_posture=block("RELATION_POSTURE_BLOCK"),
        intention_ecology=block("INTENTION_ECOLOGY_BLOCK_VERY_LONG"),
        source_line="qq_private",
        relationship_line="owner",
        sender_name="owner",
        time_context_block="TIME_CONTEXT",
        residue_line="RESIDUE_LINE",
        tail_block="TAIL_BLOCK_RECENT_MESSAGES",
        pressure_line="PRESSURE_LINE",
    )


def test_flag_defaults_off() -> None:
    assert lean_prompt_enabled() is False


def test_flag_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_LEAN_PROMPT", "1")
    assert lean_prompt_enabled() is True


def test_lean_prompt_keeps_identity_continuity_and_drops_meta() -> None:
    prompt = build_lean_live_system_prompt(
        _live_state(),
        sidecar_lines=["recalled context sidecar: a memory"],
        codex_delegate_contract="",
    )
    # kept: identity, continuity tail, time, current-turn sidecar
    assert "PERSONA_RUNTIME_IDENTITY" in prompt
    assert "TAIL_BLOCK_RECENT_MESSAGES" in prompt
    assert "TIME_CONTEXT" in prompt
    assert "recalled context sidecar: a memory" in prompt
    # dropped: internal meta-state header bulk
    assert "INTENTION_ECOLOGY_BLOCK_VERY_LONG" not in prompt
    assert "LIFE_POSTURE_BLOCK" not in prompt
    assert "RELATION_POSTURE_BLOCK" not in prompt
    assert "RESIDUE_LINE" not in prompt
    assert "PRESSURE_LINE" not in prompt


def test_lean_prompt_is_dramatically_smaller_than_legacy() -> None:
    state = _live_state()
    sidecars = ["recalled context sidecar: a memory"]
    legacy = build_live_system_prompt(state, sidecar_lines=sidecars, codex_delegate_contract="")
    lean = build_lean_live_system_prompt(state, sidecar_lines=sidecars, codex_delegate_contract="")
    assert len(lean) < len(legacy)


def test_build_live_system_prompt_routes_to_lean_when_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_LEAN_PROMPT", "1")
    prompt = build_live_system_prompt(
        _live_state(),
        sidecar_lines=["recalled context sidecar: a memory"],
        codex_delegate_contract="",
    )
    assert "INTENTION_ECOLOGY_BLOCK_VERY_LONG" not in prompt
    assert "PERSONA_RUNTIME_IDENTITY" in prompt


def test_lean_sidecar_selection_drops_meta_keeps_current_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_LEAN_PROMPT", "1")
    candidates = [
        PromptSidecar.from_parts("intention_ecology", ["x" * 4000], required=True, admission="current_turn"),
        PromptSidecar.from_parts("memory_braid", ["x" * 1800], required=True, admission="core"),
        PromptSidecar.from_parts("recalled_context", ["a memory"], admission="core"),
        PromptSidecar.from_parts("owner_address", ["owner is here"], required=True, admission="core"),
        PromptSidecar.from_parts("persona", ["x" * 1200], admission="support"),
    ]
    selection = select_prompt_sidecars(
        candidates,
        payload={"metadata": {"is_owner_user": True}},
        user_text="hi",
        visible_turn=SimpleNamespace(turn_kind="ordinary_owner_chat", technical_work=False),
    )
    admitted = {s.name for s in selection.admitted}
    assert admitted == {"recalled_context", "owner_address"}
    assert lean_sidecar_admitted("recalled_context") is True
    assert lean_sidecar_admitted("intention_ecology") is False
