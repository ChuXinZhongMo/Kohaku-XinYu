from __future__ import annotations

import json
from pathlib import Path

from xinyu_expression_contract import expression_for_targets
from xinyu_private_ecosystem_grants import save_grants_patch
from xinyu_life_event_runtime import process_life_event


def _seed_owner_private_send_grant(root: Path) -> None:
    (root / "memory/context").mkdir(parents=True, exist_ok=True)
    save_grants_patch(root, {"owner_private_autonomous_share": {"enabled": True, "paused": False}})
    (root / "xinyu_qq_gateway.config.json").write_text('{"owner_user_ids": ["owner-1"]}', encoding="utf-8")
    (root / "memory/context/current_life_posture.md").write_text("- no_proactive_constraint: unchanged\n", encoding="utf-8")
    (root / "memory/context/owner_permission_grants.md").write_text("", encoding="utf-8")
    (root / "memory/context/capability_zones_state.md").write_text(
        "- proactive_qq_send: enabled_gated_one_short_message\n",
        encoding="utf-8",
    )


def test_humanlike_life_loop_event_to_attention_direct_outbox_and_expression(tmp_path: Path) -> None:
    _seed_owner_private_send_grant(tmp_path)

    result = process_life_event(
        tmp_path,
        {
            "event_type": "desktop_residue",
            "source": "desktop",
            "observed_at": "2026-05-24T00:40:00+08:00",
            "summary": "要不要我把整条像人一样的生活事件闭环跑一遍？",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "owner_private_question",
        },
        evaluated_at="2026-05-24T00:40:00+08:00",
        allow_direct_send=True,
        min_interval_seconds=0,
        claim_id="humanlike-loop-1",
    )
    expressions = expression_for_targets(
        tmp_path,
        source_event_id=str(result["event_id"]),
        source_route=str(result["route"]),
        created_at="2026-05-24T00:40:01+08:00",
    )
    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))

    assert result["route"] == "owner_private_question"
    assert result["attention"]["attention_mode"] == "wants_to_speak"
    assert result["direct_send"]["status"] == "queued_qq"
    assert len(queue["items"]) == 1
    assert queue["items"][0]["target"] == {"message_kind": "private", "user_id": "owner-1", "group_id": ""}
    assert {event["adapter_target"] for event in expressions} == {"qq", "desktop", "avatar", "tts"}
    assert all(event["identity_layer"] == "core_only" for event in expressions)
    assert all(event["adapter_decision_allowed"] is False for event in expressions)
    assert not (tmp_path / "memory/people/owner.md").exists()
    assert not (tmp_path / "memory/self/personality_profile.md").exists()


def test_humanlike_life_loop_silence_is_valid_for_generic_attention(tmp_path: Path) -> None:
    _seed_owner_private_send_grant(tmp_path)

    result = process_life_event(
        tmp_path,
        {
            "event_type": "inner_urge",
            "source": "initiative_loop",
            "observed_at": "2026-05-24T00:40:00+08:00",
            "summary": "你在吗？",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "owner_private_question",
        },
        evaluated_at="2026-05-24T00:40:00+08:00",
        allow_direct_send=True,
        min_interval_seconds=0,
        claim_id="humanlike-loop-generic",
    )
    expressions = expression_for_targets(tmp_path, created_at="2026-05-24T00:40:01+08:00")

    assert result["route"] == "short_trace"
    assert result["direct_send"]["attempted"] is False
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()
    assert any(event["speaking_intention"] in {"silent", "note"} for event in expressions)


def test_humanlike_life_loop_blocks_secret_from_outbox_and_expression(tmp_path: Path) -> None:
    _seed_owner_private_send_grant(tmp_path)

    result = process_life_event(
        tmp_path,
        {
            "event_type": "screen_secret",
            "source": "future_ocr",
            "observed_at": "2026-05-24T00:40:00+08:00",
            "summary": "password=abcdef1234567890 出现在屏幕上",
            "privacy_scope": "secret",
            "risk_level": "blocked",
            "owner_visible": True,
            "suggested_route": "owner_private_question",
        },
        evaluated_at="2026-05-24T00:40:00+08:00",
        allow_direct_send=True,
        min_interval_seconds=0,
        claim_id="humanlike-loop-secret",
    )
    expressions_text = json.dumps(expression_for_targets(tmp_path), ensure_ascii=False)
    trace_text = (tmp_path / "memory/context/life_event_trace.jsonl").read_text(encoding="utf-8")

    assert result["route"] == "ignore"
    assert result["direct_send"]["attempted"] is False
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()
    assert "abcdef1234567890" not in expressions_text
    assert "abcdef1234567890" not in trace_text
