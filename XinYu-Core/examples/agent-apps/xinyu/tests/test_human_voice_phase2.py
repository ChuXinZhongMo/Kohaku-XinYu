"""Phase 2 tests: semantic-fast bypass renders through the model (plan §5 阶段2).

With the bypass flag OFF the decision keeps emitting its canned ``direct_reply``
(unchanged). With it ON the canned line is demoted to ``canned_fallback`` so the
renderer goes through the model first and only uses the constant on failure.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from xinyu_bridge_semantic_fast_decision import (
    _demote_direct_reply_if_bypass,
    owner_private_semantic_fast_decision_impl,
)
from xinyu_bridge_semantic_fast_rendering import render_owner_private_semantic_fast_reply
from xinyu_reply_source import (
    FinalTextSource,
    final_text_source_for_renderer,
    is_model_backed,
)

_BYPASS_ENV = "XINYU_HUMAN_VOICE_BYPASS_MODEL"


def _safe_str(value: object = "", default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _runtime() -> SimpleNamespace:
    return SimpleNamespace(
        owner_private_semantic_fast_route=True,
        _owner_private_payload_matches=lambda payload: True,
    )


def _decide(text: str) -> dict:
    return owner_private_semantic_fast_decision_impl(
        _runtime(),
        {"text": text},
        text,
        repair_intents_func=lambda _t: ("runtime_status_question",),
        direct_repair_reply_func=lambda *_a, **_k: "后台在处理当前这条私聊",
    )


# --------------------------------------------------------------------------- #
# decision demotion
# --------------------------------------------------------------------------- #
def test_decision_flag_off_keeps_canned_direct_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_BYPASS_ENV, raising=False)
    decision = _decide("后台状态")
    assert decision["allowed"] is True
    assert decision["direct_reply"] == "后台在处理当前这条私聊"
    assert "canned_fallback" not in decision


def test_decision_flag_on_demotes_to_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_BYPASS_ENV, "1")
    decision = _decide("后台状态")
    assert decision["allowed"] is True
    assert decision["direct_reply"] == ""  # renderer will go to the model
    assert decision["canned_fallback"] == "后台在处理当前这条私聊"
    assert decision["canned_fallback_id"] == "canned_repair"
    assert any("direct_reply_demoted_to_model" in n for n in decision["notes"])


def test_demote_helper_is_noop_when_no_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_BYPASS_ENV, "1")
    decision = {"allowed": True, "direct_reply": "", "notes": []}
    assert _demote_direct_reply_if_bypass(decision, "x")["direct_reply"] == ""
    assert "canned_fallback" not in decision


# --------------------------------------------------------------------------- #
# renderer: model first, canned_fallback only on empty model output
# --------------------------------------------------------------------------- #
def test_renderer_uses_canned_fallback_when_model_empty() -> None:
    async def _empty_render(*_a, **_k):
        return ""

    runtime = SimpleNamespace(_render_outward_reply=_empty_render)
    session = SimpleNamespace(agent=SimpleNamespace(llm=None))
    decision = {"direct_reply": "", "canned_fallback": "后台在处理当前这条私聊"}

    result = asyncio.run(
        render_owner_private_semantic_fast_reply(
            runtime,
            {"text": "后台状态"},
            text="后台状态",
            session=session,
            session_key="s",
            turn_id="t",
            decision=decision,
            empty_state_notice_func=lambda _t, **_k: "我在。",
            provider_failover_context_func=lambda *_a, **_k: None,
            safe_str_func=_safe_str,
        )
    )
    assert result == ("后台在处理当前这条私聊", "canned_fallback")


def test_renderer_returns_model_text_when_present() -> None:
    async def _render(*_a, **_k):
        return "在的，刚才那条我接着了"

    runtime = SimpleNamespace(_render_outward_reply=_render)
    session = SimpleNamespace(agent=SimpleNamespace(llm=None))
    decision = {"direct_reply": "", "canned_fallback": "我在。"}

    reply, renderer_name = asyncio.run(
        render_owner_private_semantic_fast_reply(
            runtime,
            {"text": "在吗"},
            text="在吗",
            session=session,
            session_key="s",
            turn_id="t",
            decision=decision,
            empty_state_notice_func=lambda _t, **_k: "我在。",
            provider_failover_context_func=lambda *_a, **_k: None,
            safe_str_func=_safe_str,
        )
    )
    assert reply == "在的，刚才那条我接着了"
    assert renderer_name == "outward_reply"


# --------------------------------------------------------------------------- #
# provenance mapping
# --------------------------------------------------------------------------- #
def test_renderer_source_mapping() -> None:
    assert final_text_source_for_renderer("outward_reply") == FinalTextSource.MODEL_MICRO
    assert is_model_backed(final_text_source_for_renderer("outward_reply"))
    assert not is_model_backed(final_text_source_for_renderer("canned_fallback"))
    assert not is_model_backed(final_text_source_for_renderer("empty_state_notice"))
