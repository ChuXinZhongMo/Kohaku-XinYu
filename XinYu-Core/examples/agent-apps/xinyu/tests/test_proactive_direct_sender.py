from __future__ import annotations

import json
from pathlib import Path

from xinyu_proactive_direct_sender import main, send_proactive_direct
from xinyu_proactive_request_loop import run_proactive_request_loop


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


def _seed_direct_ready(
    root: Path,
    *,
    grant: bool = True,
    share_enabled: bool = True,
    share_paused: bool = False,
    question: str = "要不要我先把人格状态卡接到 Desktop？",
) -> None:
    _seed_share_grant(root, enabled=share_enabled, paused=share_paused)
    _write(root / "xinyu_qq_gateway.config.json", '{"owner_user_ids": ["owner-1"]}')
    _write(root / "memory/context/current_life_posture.md", "- no_proactive_constraint: unchanged\n")
    _write(root / "memory/context/owner_permission_grants.md", "")
    capability = "- proactive_qq_send: enabled_gated_one_short_message\n" if grant else ""
    _write(root / "memory/context/capability_zones_state.md", capability)
    _write(
        root / "memory/context/self_thought_state.md",
        f"""
---
title: Self Thought State
---

# Self Thought State

## Latest Pass
- pass_id: selfthought-direct-test
- focus_kind: active_question
- focus_label: persona next step
- evidence_label: owner asked XinYu to directly send proactive messages
- evidence_hash: sha256:direct1234567890

## Inner Intention
- intention_id: intent-direct-test
- intention: ask_owner

## Request Candidate
- candidate_enabled: true
- concrete_question: {question}
- requested_action: owner_answer
- why_now: owner asked for direct proactive delivery instead of candidate-only flow
- after_owner_replies: continue with the approved next step
""",
    )


def test_proactive_direct_sender_enqueues_owner_private_outbox(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path)

    result = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:55:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-1",
    )

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    items = queue["items"]
    state = (tmp_path / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")
    dispatch = (tmp_path / "memory/context/proactive_qq_dispatch_state.md").read_text(encoding="utf-8")

    assert result["accepted"] is True
    assert result["status"] == "queued_qq"
    assert len(items) == 1
    assert items[0]["target"] == {"message_kind": "private", "user_id": "owner-1", "group_id": ""}
    assert items[0]["metadata"]["direct_proactive"] is True
    assert items[0]["message"] in {
        "Desktop 那张卡还要吗",
        "这个还要吗",
        "Desktop 那张卡还看吗",
    }
    assert "我想问你一件小事" not in items[0]["message"]
    assert "persona next step" not in items[0]["message"]
    assert "- status: queued_qq" in state
    assert f"- qq_outbox_message_id: {items[0]['id']}" in state
    assert "- request_answer_state: sent_waiting_owner_reply" in state
    assert "- last_ack_status: queued" in dispatch
    assert not (tmp_path / "memory/people/owner.md").exists()
    assert not (tmp_path / "memory/self/personality_profile.md").exists()


def test_proactive_direct_sender_requires_owner_enabled_grant(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path, grant=False)

    result = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:55:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-blocked",
    )

    assert result["queued"] is False
    assert result["status"] == "not_ready"
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_proactive_direct_sender_blocks_when_owner_private_share_paused(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path, share_enabled=True, share_paused=True)

    result = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-06-03T23:45:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-share-paused",
    )

    assert result["queued"] is False
    assert result["status"] == "blocked"
    assert "owner_private_autonomous_share_paused" in result["notes"]
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_proactive_direct_sender_blocks_when_owner_private_share_disabled(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path, share_enabled=False, share_paused=True)

    result = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-06-03T23:45:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-share-disabled",
    )

    assert result["queued"] is False
    assert result["status"] == "blocked"
    assert "owner_private_autonomous_share_disabled" in result["notes"]
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_proactive_direct_sender_dedupes_repeated_message(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path)

    first = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:55:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-1",
    )
    second = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:56:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-2",
    )

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    assert first["status"] == "queued_qq"
    assert second["queued"] is False
    assert len(queue["items"]) == 1
    assert "direct_send_not_claimed" in second["notes"]


def test_proactive_direct_sender_can_ground_generic_question_from_owner_journal(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path, question="要不要继续？")
    _write(
        tmp_path / "memory/context/interaction_journal.jsonl",
        json.dumps(
            {
                "privacy": "group_context",
                "group_id": "123",
                "owner_private": False,
                "user_text": "群里提到 Desktop 卡片",
            },
            ensure_ascii=False,
        )
        + "\n"
        + json.dumps(
            {
                "privacy": "owner_private",
                "owner_private": True,
                "user_text": "表达层契约这里先接上",
                "reply": "我先看表现那块",
            },
            ensure_ascii=False,
        ),
    )

    result = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:55:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-context",
    )

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    message = queue["items"][0]["message"]
    assert result["status"] == "queued_qq"
    assert message in {"表现那块我接着？", "那我接着？", "表现那块继续吗"}
    assert "群里" not in message


def test_proactive_direct_sender_blocks_generic_attention_check(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path, question="你在吗？")

    result = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:55:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-generic",
    )

    assert result["queued"] is False
    assert result["status"] == "not_ready"
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_proactive_direct_sender_dry_run_acknowledges_claim_without_outbox(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path)

    result = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:55:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-dry",
        dry_run=True,
    )

    dispatch = (tmp_path / "memory/context/proactive_qq_dispatch_state.md").read_text(encoding="utf-8")
    request_state = (tmp_path / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")
    assert result["status"] == "dry_run_claimed_not_enqueued"
    assert result["queued"] is False
    assert "- last_ack_status: dry_run" in dispatch
    assert "- adapter_error: none" in dispatch
    assert "- status: ready" in request_state
    assert "- request_answer_state: not_requested" in request_state
    assert "- qq_outbox_message_id: none" in request_state
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()

    followup = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:56:00+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-after-dry",
    )

    assert followup["status"] == "queued_qq"


def test_proactive_direct_sender_cli_json_outputs_result(tmp_path: Path, capsys) -> None:
    _seed_direct_ready(tmp_path)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--evaluated-at",
            "2026-05-23T23:55:00+08:00",
            "--min-interval-seconds",
            "0",
            "--claim-id",
            "claim-direct-cli-json",
            "--dry-run",
            "--json",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["status"] == "dry_run_claimed_not_enqueued"
    assert output["queued"] is False


def test_proactive_direct_sender_can_claim_existing_ready_request(tmp_path: Path) -> None:
    _seed_direct_ready(tmp_path)
    request = run_proactive_request_loop(
        tmp_path,
        evaluated_at="2026-05-23T23:55:00+08:00",
        delivery_level="queue_owner_private",
        cooldown_seconds=0,
    )

    result = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-23T23:55:10+08:00",
        min_interval_seconds=0,
        claim_id="claim-direct-existing",
        prepare_request=False,
    )

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    assert request["status"] == "ready"
    assert result["status"] == "queued_qq"
    assert result["queued"] is True
    assert len(queue["items"]) == 1
