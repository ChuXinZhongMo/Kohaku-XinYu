"""Phase 1 scaffolding tests for the human-voice unification (plan §5 阶段1).

Covers the new shared voice header, the source-provenance enum, and — most
importantly — that with the unified-voice flag OFF every prompt path is
unchanged, and with it ON the one thin-expression voice is injected.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from xinyu_persona_voice import (
    persona_voice_header,
    reasoning_safety_boundaries,
    thin_expression_contract,
    unified_voice_enabled,
)
from xinyu_reply_source import (
    FinalTextSource,
    equals_historical_canned,
    is_model_backed,
    is_valid_final_text_source,
)

_UNIFIED_ENV = "XINYU_HUMAN_VOICE_UNIFIED_PROMPT"
_THIN_MARKER = "## Thin Expression Contract"


# --------------------------------------------------------------------------- #
# reply source provenance
# --------------------------------------------------------------------------- #
def test_final_text_source_enum_is_self_consistent() -> None:
    assert is_valid_final_text_source(FinalTextSource.MODEL_MICRO)
    assert is_valid_final_text_source(FinalTextSource.CANNED_EMPTY_STATE)
    assert not is_valid_final_text_source("nonexistent_source")
    assert is_model_backed(FinalTextSource.MODEL_LIVE)
    assert is_model_backed(FinalTextSource.MODEL_REGEN)
    assert not is_model_backed(FinalTextSource.CANNED_BRIDGE_ALERT)
    assert not is_model_backed(FinalTextSource.STICKER)


def test_historical_canned_detection() -> None:
    assert equals_historical_canned("我在。刚才那句没接上。")
    assert equals_historical_canned("  哪句最明显？  ")  # whitespace tolerant
    assert not equals_historical_canned("我在想刚才你说的那件事")
    assert not equals_historical_canned("")


# --------------------------------------------------------------------------- #
# shared voice header
# --------------------------------------------------------------------------- #
def test_persona_voice_header_reuses_contract_and_adds_thin_layer() -> None:
    header = persona_voice_header()
    # existing stable contract is reused, not reinvented (plan 11.1)
    assert "Persona Runtime Contract" in header
    # new thin-expression + reframed boundaries are layered on
    assert _THIN_MARKER in header
    assert "Output Boundaries" in header
    assert "chain-of-thought" in reasoning_safety_boundaries()


def test_thin_expression_contract_forbids_self_narration() -> None:
    text = thin_expression_contract()
    assert "never recap your own mood" in text.lower()
    assert "do not invent facts" in text.lower()


def test_unified_voice_env_gating(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_UNIFIED_ENV, raising=False)
    assert unified_voice_enabled() is False
    monkeypatch.setenv(_UNIFIED_ENV, "1")
    assert unified_voice_enabled() is True
    monkeypatch.setenv(_UNIFIED_ENV, "off")
    assert unified_voice_enabled() is False


# --------------------------------------------------------------------------- #
# main live path: flag off == unchanged, flag on == thin contract injected
# --------------------------------------------------------------------------- #
def _fake_live_state() -> SimpleNamespace:
    def block(label: str):
        return SimpleNamespace(to_prompt_block=lambda: f"<{label}>", turn_kind="owner_private")

    return SimpleNamespace(
        visible_turn=block("visible_turn"),
        life_posture=block("life_posture"),
        persona_runtime=block("persona_runtime"),
        relation_posture=block("relation_posture"),
        intention_ecology=block("intention_ecology"),
        source_line="src",
        relationship_line="owner",
        sender_name="哥",
        time_context_block="time",
        residue_line="residue",
        tail_block="tail",
        pressure_line="pressure",
    )


def test_build_live_system_prompt_flag_off_has_no_thin_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_UNIFIED_ENV, raising=False)
    from xinyu_bridge_turn_prompt_payload import build_live_system_prompt

    prompt = build_live_system_prompt(_fake_live_state(), sidecar_lines=[], codex_delegate_contract="")
    assert _THIN_MARKER not in prompt


def test_build_live_system_prompt_flag_on_injects_thin_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_UNIFIED_ENV, "1")
    from xinyu_bridge_turn_prompt_payload import build_live_system_prompt

    prompt = build_live_system_prompt(_fake_live_state(), sidecar_lines=[], codex_delegate_contract="")
    assert _THIN_MARKER in prompt
    # persona is NOT duplicated: the full contract header is only added by the v1
    # path, here persona arrives via persona_runtime block instead.
    assert "Persona Runtime Contract" not in prompt


# --------------------------------------------------------------------------- #
# v1 slow-reasoning builder: flag flips the machine self-narration off
# --------------------------------------------------------------------------- #
def _fake_reasoning_request() -> SimpleNamespace:
    return SimpleNamespace(
        memories=(),
        recent_messages=(),
        emotion_state=None,
        system_context="",
        turn=SimpleNamespace(text="在吗"),
    )


def test_prompt_builder_flag_off_keeps_runtime_self_description(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_UNIFIED_ENV, raising=False)
    from xinyu_v1.reasoning.prompt_builder import PromptBuilder

    bundle = PromptBuilder().build(_fake_reasoning_request())
    assert "You are XinYu's slow reasoning runtime." in bundle.system
    assert _THIN_MARKER not in bundle.system


def test_prompt_builder_flag_on_uses_shared_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_UNIFIED_ENV, "1")
    from xinyu_v1.reasoning.prompt_builder import PromptBuilder

    bundle = PromptBuilder().build(_fake_reasoning_request())
    assert _THIN_MARKER in bundle.system
    assert "Persona Runtime Contract" in bundle.system
    assert "You are XinYu's slow reasoning runtime." not in bundle.system
