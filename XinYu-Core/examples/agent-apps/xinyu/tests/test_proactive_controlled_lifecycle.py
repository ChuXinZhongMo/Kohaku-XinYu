from __future__ import annotations

import json
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_proactive_presence import acknowledge_proactive_qq_message, claim_proactive_qq_message
from xinyu_proactive_request_loop import run_proactive_request_loop


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _events(root: Path) -> list[dict[str, object]]:
    path = root / "runtime/proactive_request_trace.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_self_thought(root: Path) -> None:
    _write(root / "memory/context/current_life_posture.md", "- no_proactive_constraint: unchanged\n")
    _write(root / "memory/context/owner_permission_grants.md", "")
    _write(root / "memory/context/capability_zones_state.md", "- proactive_qq_send: enabled_gated_one_short_message\n")
    _write(
        root / "memory/context/self_thought_state.md",
        """
---
title: Self Thought State
---

# Self Thought State

## Latest Pass
- pass_id: selfthought-test
- focus_kind: active_question
- focus_label: plan follow-up
- evidence_label: owner needs one decision
- evidence_hash: sha256:abcdef1234567890

## Inner Intention
- intention_id: intent-test
- intention: ask_owner

## Request Candidate
- candidate_enabled: true
- concrete_question: Should I continue the current plan?
- requested_action: owner_answer
- why_now: owner needs one decision
- after_owner_replies: continue the current thread
""",
    )


def _make_runtime(root: Path) -> XinYuBridgeRuntime:
    (root / "memory/context").mkdir(parents=True, exist_ok=True)
    (root / "memory/self").mkdir(parents=True, exist_ok=True)
    (root / "memory/relationships").mkdir(parents=True, exist_ok=True)
    (root / "memory/people").mkdir(parents=True, exist_ok=True)
    (root / "prompts").mkdir(parents=True, exist_ok=True)
    _write(root / "config.yaml", "name: xinyu")
    _write(root / "prompts/system.md", "# system")
    _write(root / "prompts/output.md", "# output")
    _write(root / "prompts/live_voice_card.md", "# card")
    _write(root / "memory/self/core.md", "core")
    _write(root / "memory/self/personality_profile.md", "profile")
    _write(root / "memory/self/narrative.md", "narrative")
    _write(root / "memory/context/persona_surface_state.md", "surface")
    _write(root / "memory/context/recent_context.md", "recent")
    _write(root / "memory/context/memory_weight_state.md", "weights")
    return XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=3,
        max_text_chars=8000,
        settle_seconds=0,
        outward_renderer=False,
    )


def test_proactive_request_schema_records_reason_risk_channel_and_expiration(tmp_path: Path) -> None:
    _seed_self_thought(tmp_path)

    result = run_proactive_request_loop(
        tmp_path,
        evaluated_at="2026-05-01T15:30:00+08:00",
        delivery_level="queue_owner_private",
    )

    state = (tmp_path / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")
    event = _events(tmp_path)[-1]
    assert result["status"] == "ready"
    for marker in (
        "- reason: ask_owner:active_question:owner needs one decision",
        "- urgency: low",
        "- risk: low_owner_private",
        "- owner_relevance: owner_action:owner_answer",
        "- channel: owner_private",
        "- expiration:",
    ):
        assert marker in state
    assert event["event_kind"] == "proactive_request_evaluated"
    assert event["reason"] == "ask_owner:active_question:owner needs one decision"
    assert event["channel"] == "owner_private"


def test_failed_proactive_ack_enters_retry_cooldown_then_retries(tmp_path: Path) -> None:
    _seed_self_thought(tmp_path)
    run_proactive_request_loop(
        tmp_path,
        evaluated_at="2026-05-01T15:30:00+08:00",
        delivery_level="queue_owner_private",
    )
    first = claim_proactive_qq_message(
        tmp_path,
        evaluated_at="2026-05-01T15:31:00+08:00",
        claim=True,
        claim_id="claim-1",
        min_interval_seconds=3600,
    )
    failed = acknowledge_proactive_qq_message(
        tmp_path,
        acked_at="2026-05-01T15:32:00+08:00",
        claim_id="claim-1",
        ack_status="failed",
        adapter_error="send timeout",
    )
    blocked = claim_proactive_qq_message(
        tmp_path,
        evaluated_at="2026-05-01T15:40:00+08:00",
        claim=True,
        claim_id="claim-2",
        min_interval_seconds=3600,
    )
    retry = claim_proactive_qq_message(
        tmp_path,
        evaluated_at="2026-05-01T16:40:01+08:00",
        claim=True,
        claim_id="claim-3",
        min_interval_seconds=3600,
    )

    event_kinds = [event["event_kind"] for event in _events(tmp_path)]
    assert first["candidate_claimed"] is True
    assert failed["ack_recorded"] is True
    assert failed["ack_status"] == "failed"
    assert blocked["candidate_claimed"] is False
    assert any("candidate_failed_retry_cooldown" in note for note in blocked["notes"])
    assert retry["candidate_claimed"] is True
    assert "proactive_candidate_claimed" in event_kinds
    assert "proactive_ack_recorded" in event_kinds
    assert "proactive_claim_blocked" in event_kinds


def test_owner_reply_closes_sent_proactive_state_and_traces_lifecycle(tmp_path: Path) -> None:
    root = tmp_path / "xinyu"
    runtime = _make_runtime(root)
    runtime._refresh_initiative_spine_after_proactive_feedback = lambda *args, **kwargs: None  # type: ignore[method-assign]
    _write(
        root / "memory/context/proactive_request_state.md",
        """
---
title: Proactive Request State
updated_at: 2026-05-01T15:32:00+08:00
---

# Proactive Request State

## Current Request
- request_id: proreq-owner-reply
- status: sent
- kind: clarify
- source: self_thought
- focus_kind: active_question
- reason: ask_owner:active_question:owner needs one decision
- urgency: low
- risk: low_owner_private
- owner_relevance: owner_action:owner_answer
- channel: owner_private
- expiration: 2026-05-02T15:30:00+08:00
- delivery_level: queue_owner_private
- request_answer_state: pending
""",
    )
    _write(
        root / "memory/context/proactive_qq_dispatch_state.md",
        """
# Proactive QQ Dispatch State

## Last Claim
- last_claimed_at: 2026-05-01T15:31:00+08:00
- last_claim_id: claim-owner-reply
- last_claim_status: sent
- proactive_request_id: proreq-owner-reply
- last_claimed_message: Should I continue the current plan?

## Last Ack
- last_ack_status: sent
""",
    )

    marked = runtime._mark_proactive_owner_reply(
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        text="yes continue",
        reply="ok",
    )

    state = (root / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")
    event = _events(root)[-1]
    assert marked is True
    assert "- status: answered" in state
    assert "- request_answer_state: owner_replied" in state
    assert event["event_kind"] == "proactive_owner_reply_closed"
    assert event["ack_status"] == "owner_replied"
