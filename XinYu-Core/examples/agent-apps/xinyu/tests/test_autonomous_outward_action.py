from __future__ import annotations

import json
from pathlib import Path

from xinyu_autonomous_outward_action import (
    LEDGER_REL,
    STATE_REL,
    evaluate_autonomous_outward_policy,
    run_autonomous_outward_action_tick,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _seed_share_grant(root: Path, *, enabled: bool = True, paused: bool = False) -> None:
    _write(
        root / "memory/context/private_ecosystem_grants.json",
        json.dumps(
            {
                "owner_private_autonomous_share": {
                    "enabled": enabled,
                    "paused": paused,
                    "daily_limit": 8,
                    "cooldown_minutes": 30,
                    "max_message_chars": 800,
                    "quiet_hours": "00:00-06:00",
                }
            },
            ensure_ascii=False,
        ),
    )


def _seed_owner_private_candidate(
    root: Path,
    *,
    grant: bool = True,
    share_enabled: bool = True,
    share_paused: bool = False,
) -> None:
    _seed_share_grant(root, enabled=share_enabled, paused=share_paused)
    _write(root / "xinyu_qq_gateway.config.json", '{"owner_user_ids": ["owner-1"]}')
    _write(root / "memory/context/current_life_posture.md", "- no_proactive_constraint: unchanged\n")
    grants = (
        "- grant_autonomous_owner_private_outward_action: approved_owner_only_rate_limited_one_short_message\n"
        if grant
        else ""
    )
    _write(root / "memory/context/owner_permission_grants.md", grants)
    _write(root / "memory/context/capability_zones_state.md", "- proactive_qq_send: enabled_gated_one_short_message\n")
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State

## Latest Pass
- pass_id: selfthought-auto-outward
- focus_kind: active_question
- focus_label: desktop card followup
- evidence_label: owner allowed bounded autonomous owner-private outward action
- evidence_hash: sha256:autooutward123456

## Inner Intention
- intention_id: intent-auto-outward
- intention: ask_owner

## Request Candidate
- candidate_enabled: true
- concrete_question: Should I continue the Desktop card work?
- requested_action: owner_answer
- why_now: the owner granted owner-private autonomous outward action
- after_owner_replies: continue the focused local task

## Gates
- owner_is_right_recipient: true
""",
    )


def _seed_owner_long_idle(
    root: Path,
    *,
    grant: bool = True,
    share_enabled: bool = True,
    share_paused: bool = False,
) -> None:
    _seed_share_grant(root, enabled=share_enabled, paused=share_paused)
    _write(root / "xinyu_qq_gateway.config.json", '{"owner_user_ids": ["owner-1"]}')
    _write(root / "memory/context/current_life_posture.md", "- no_proactive_constraint: unchanged\n")
    grants = (
        "- grant_autonomous_owner_private_outward_action: approved_owner_only_rate_limited_one_short_message\n"
        if grant
        else ""
    )
    _write(root / "memory/context/owner_permission_grants.md", grants)
    _write(root / "memory/context/capability_zones_state.md", "- proactive_qq_send: enabled_gated_one_short_message\n")
    _write(
        root / "memory/context/interaction_journal_state.md",
        """
# Runtime Interaction Journal State

## Recent Continuity
- last_owner_private_at: 2026-06-01T06:00:00+08:00
- minutes_since_last_owner_private: 0
""",
    )


def test_autonomous_outward_action_requires_owner_only_grant(tmp_path: Path) -> None:
    _seed_owner_private_candidate(tmp_path, grant=False)

    result = run_autonomous_outward_action_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        min_interval_seconds=0,
        quiet_hours="",
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    assert result["status"] == "blocked"
    assert result["queued"] is False
    assert "owner_only_auto_send_grant_missing" in result["policy"]["blocks"]
    assert "grant_present: false" in state
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_autonomous_outward_action_ignores_env_grant_bypass(tmp_path: Path, monkeypatch) -> None:
    _seed_owner_private_candidate(tmp_path, grant=False)
    monkeypatch.setenv("XINYU_OWNER_PRIVATE_AUTO_SEND", "1")

    result = run_autonomous_outward_action_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        min_interval_seconds=0,
        quiet_hours="",
    )

    assert result["status"] == "blocked"
    assert "owner_only_auto_send_grant_missing" in result["policy"]["blocks"]
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_autonomous_outward_action_blocks_when_owner_private_share_paused(tmp_path: Path) -> None:
    _seed_owner_private_candidate(tmp_path, grant=True, share_enabled=True, share_paused=True)

    result = run_autonomous_outward_action_tick(
        tmp_path,
        evaluated_at="2026-06-03T23:45:00+08:00",
        min_interval_seconds=0,
        quiet_hours="",
    )

    assert result["status"] == "blocked"
    assert result["queued"] is False
    assert result["prepared_request"]["source"] == "share_inactive"
    assert "owner_private_autonomous_share_paused" in result["policy"]["blocks"]
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_autonomous_outward_action_enqueues_owner_private_when_granted(tmp_path: Path) -> None:
    _seed_owner_private_candidate(tmp_path, grant=True)

    result = run_autonomous_outward_action_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        min_interval_seconds=0,
        quiet_hours="",
    )

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")

    assert result["status"] == "queued_qq"
    assert result["queued"] is True
    assert queue["items"][0]["target"] == {"message_kind": "private", "user_id": "owner-1", "group_id": ""}
    assert queue["items"][0]["metadata"]["owner_private_only"] is True
    assert "Should I continue the Desktop card work?" not in state
    assert "visible_message_text_in_state: false" in state
    assert (tmp_path / LEDGER_REL).exists()


def test_autonomous_outward_action_blocks_daily_budget(tmp_path: Path) -> None:
    _seed_owner_private_candidate(tmp_path, grant=True)
    rows = [
        {
            "event_kind": "autonomous_outward_action",
            "evaluated_at": f"2026-06-01T0{hour}:00:00+08:00",
            "queued": True,
        }
        for hour in (7, 8, 9)
    ]
    _write(tmp_path / LEDGER_REL, "\n".join(json.dumps(row) for row in rows))

    result = run_autonomous_outward_action_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        min_interval_seconds=0,
        quiet_hours="",
        max_messages_per_day=50,
    )

    assert result["status"] == "blocked"
    assert result["queued"] is False
    assert result["policy"]["max_messages_per_day"] == 3
    assert "daily_budget_exhausted" in result["policy"]["blocks"]
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_autonomous_outward_action_respects_quiet_hours(tmp_path: Path) -> None:
    _seed_owner_private_candidate(tmp_path, grant=True)

    result = run_autonomous_outward_action_tick(
        tmp_path,
        evaluated_at="2026-06-01T23:45:00+08:00",
        min_interval_seconds=0,
        quiet_hours="23:30-08:30",
    )

    assert result["status"] == "blocked"
    assert result["queued"] is False
    assert "quiet_hours" in result["policy"]["blocks"]
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_answered_proactive_request_does_not_keep_waiting_gate_closed(tmp_path: Path) -> None:
    _seed_owner_private_candidate(tmp_path, grant=True)
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        """
# Proactive Request State

## Current Request
- status: answered
- request_answer_state: owner_replied
- last_ack_status: sent
""",
    )

    policy = evaluate_autonomous_outward_policy(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        quiet_hours="",
    )

    assert policy["waiting_owner"] is False
    assert "waiting_for_owner_reply" not in policy["blocks"]


def test_owner_long_idle_prepares_but_does_not_queue_owner_private_request(tmp_path: Path) -> None:
    _seed_owner_long_idle(tmp_path, grant=True)

    result = run_autonomous_outward_action_tick(
        tmp_path,
        evaluated_at="2026-06-01T12:00:00+08:00",
        min_interval_seconds=0,
        quiet_hours="",
        prepare_request=True,
    )

    request_state = (tmp_path / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")

    assert result["status"] == "blocked"
    assert result["queued"] is False
    assert result["prepared_request"]["source"] == "owner_long_idle"
    assert "owner_long_idle_direct_send_disabled" in result["policy"]["blocks"]
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()
    assert "- source: owner_long_idle" in request_state
    assert "- request_family: owner_long_idle" in request_state
