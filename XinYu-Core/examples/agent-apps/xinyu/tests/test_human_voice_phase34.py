"""Phase 3/4 tests: slow-live post-processing regenerates instead of canning.

With the regen flag ON the sync replace-steps clear the reply (and keep their
flag) so the already-async, model-first empty-recovery step regenerates a real
line; the canned constants remain only as last-resort insurance. With the flag
OFF the canned behavior is unchanged (covered by test_bridge_slow_live_turn.py).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import xinyu_bridge_slow_live_turn as slow_live
from xinyu_bridge_slow_live_turn import (
    apply_slow_live_reply_bubble_policy,
    apply_slow_live_stale_context_repair,
    apply_slow_live_style_pressure_empty_fallback,
    recover_slow_live_empty_visible_reply,
)

_REGEN_ENV = "XINYU_HUMAN_VOICE_REGEN_PIPELINE"


def test_bubble_policy_clears_instead_of_canned_when_regen_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_REGEN_ENV, "1")
    calls: list[tuple[str, object]] = []
    agent = object()
    runtime = SimpleNamespace(
        _owner_requested_reply_bubble_units=lambda **_k: [],
        _looks_like_false_single_bubble_limitation=lambda user_text, reply: True,
        _replace_last_assistant_message=lambda a, reply: calls.append(("replace", reply)),
    )
    result = apply_slow_live_reply_bubble_policy(
        runtime,
        SimpleNamespace(agent=agent),
        reply="original reply",
        user_text="can you split",
        dialogue_tail=[],
        final_guard_flags=["existing"],
    )
    assert result["reply"] == ""  # cleared, not the canned bubble line
    assert "false_single_bubble_regen_pending" in result["final_guard_flags"]
    assert result["reply"] != slow_live.FALSE_SINGLE_BUBBLE_REPLY
    # no canned replacement was pushed to the session
    assert calls == []


def test_style_pressure_empty_stays_empty_for_regen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_REGEN_ENV, "1")
    calls: list[tuple[str, object]] = []
    agent = object()
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda a, reply: calls.append(("replace", reply)),
    )
    result = apply_slow_live_style_pressure_empty_fallback(
        runtime,
        SimpleNamespace(agent=agent),
        reply="",
        final_guard_flags=["style_pressure_template_blocked"],
    )
    assert result["reply"] == ""
    assert "style_pressure_empty_regen_pending" in result["final_guard_flags"]
    assert slow_live.STYLE_PRESSURE_EMPTY_REPLY not in result["reply"]
    assert calls == []


def test_stale_repair_clears_for_regen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_REGEN_ENV, "1")
    calls: list[tuple[str, object]] = []
    agent = object()
    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "reply_looks_like_stale_plan_residue",
        lambda reply: True,
    )
    # the canned repair func must NOT be consulted when regen clears the reply
    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "owner_private_direct_repair_reply",
        lambda runtime, text: calls.append(("repair", text)) or "后台在处理当前这条私聊",
    )
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: True,
        _replace_last_assistant_message=lambda a, reply: calls.append(("replace", reply)),
    )
    result = apply_slow_live_stale_context_repair(
        runtime,
        SimpleNamespace(agent=agent),
        {"scope": "owner"},
        reply="stale reply",
        user_text="now",
        final_guard_flags=["existing"],
        blocked_by_delegate=False,
    )
    assert result["reply"] == ""
    assert "stale_context_regen_pending" in result["final_guard_flags"]
    assert ("repair", "now") not in calls  # canned repair was skipped
    assert ("replace", "") in calls


def test_empty_recovery_tags_model_regen_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_REGEN_ENV, "1")
    agent = object()

    async def recover(a, **_k):
        return "我在想你刚才那句", ["empty_visible_reply_regenerated"]

    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: True,
        _recover_empty_visible_reply=recover,
        _empty_visible_reply_fallback=lambda **_k: "我在。",
        _replace_last_assistant_message=lambda a, reply: None,
    )
    result = asyncio.run(
        recover_slow_live_empty_visible_reply(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            reply="",
            user_text="user",
            final_guard_flags=["existing"],
            rendered=False,
            renderer_reason="",
            recalled_context=SimpleNamespace(prompt_block="mem"),
            blocked_by_delegate=False,
        )
    )
    assert result["reply"] == "我在想你刚才那句"
    assert "final_text_source:model_regen" in result["final_guard_flags"]
