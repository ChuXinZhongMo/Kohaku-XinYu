"""Phase 5 tests: pre-model functional composers get provenance-tagged.

Codex 11.7: the pre-model B routes (runtime status, action results, codex,
digests) carry real facts and keep their structured composer — we only tag them
``functional_composer`` so canned-vs-model accounting can distinguish them from a
pretend-chat constant. Tagging is gated, so flag-off output is unchanged.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from xinyu_bridge_pre_model_routes import run_pre_model_routes

_BYPASS_ENV = "XINYU_HUMAN_VOICE_BYPASS_MODEL"


async def _none(*_a, **_k):
    return None


def _run(runtime, *, event_recorder):
    async def _to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def _repair_status(*_a, **_k):
        return None

    async def _tinykernel(*_a, **_k):
        return {"notes": []}

    return asyncio.run(
        run_pre_model_routes(
            runtime,
            {"platform": "qq"},
            text="hi",
            session_key="qq:private:owner",
            turn_id="t",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=1.0,
            before_memory={},
            cleanup={},
            runtime_repair_status_func=_repair_status,
            tinykernel_shadow_func=_tinykernel,
            event_recorder_func=event_recorder,
            to_thread_func=_to_thread,
        )
    )


def _runtime_with_action(response):
    async def _action(*_a, **_k):
        return response

    return SimpleNamespace(
        xinyu_dir="/tmp",
        _maybe_handle_action_layer_turn=_action,
        _maybe_handle_recent_action_followup_turn=_none,
        _maybe_handle_action_digest_followup_turn=_none,
        _maybe_handle_v1_canary_turn=_none,
        _run_v1_shadow=_none,
    )


def test_functional_route_tagged_when_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_BYPASS_ENV, "1")
    result = _run(
        _runtime_with_action({"reply": "已经修好了，core 重启完成"}),
        event_recorder=lambda *_a, **_k: {"notes": []},
    )
    assert result.response == {"reply": "已经修好了，core 重启完成"}
    assert "final_text_source:functional_composer" in result.event_sidecar["notes"]


def test_functional_route_untagged_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_BYPASS_ENV, raising=False)
    result = _run(
        _runtime_with_action({"reply": "已经修好了"}),
        event_recorder=lambda *_a, **_k: {"notes": ["event_ok"]},
    )
    assert result.response == {"reply": "已经修好了"}
    # flag off => event_sidecar carries only what the recorder produced
    assert result.event_sidecar["notes"] == ["event_ok"]
