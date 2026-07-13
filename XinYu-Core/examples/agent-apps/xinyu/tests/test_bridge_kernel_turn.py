"""Tests for K-010 bridge turn hooks."""

from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_kernel_turn import inject_kernel_pre_turn_context, run_kernel_post_turn_cycle


def test_inject_kernel_pre_turn_context(tmp_path):
    runtime = SimpleNamespace(xinyu_dir=tmp_path)
    payload = {"metadata": {}}
    result = inject_kernel_pre_turn_context(runtime, payload)
    assert "notes" in result
    if result.get("included"):
        assert payload.get("kernel_context_included") is True
        assert "kernel_pre_turn" in payload["metadata"]


def test_run_kernel_post_turn_cycle_skips_when_already_closed(tmp_path):
    runtime = SimpleNamespace(xinyu_dir=tmp_path)
    result = run_kernel_post_turn_cycle(
        runtime,
        payload={"source": "qq", "turn_mode": "chat"},
        text="hello",
        reply="hi",
        turn_id="t1",
        event_sidecar={"cognitive_cycle_closed": True, "cognitive_reorg_mode": "slow"},
    )
    assert result.get("skipped") is True