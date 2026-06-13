from __future__ import annotations

import json
from pathlib import Path

from xinyu_attention_posture import (
    read_attention_posture,
    update_attention_from_perception_importance,
    update_attention_posture,
)
from xinyu_private_ecosystem_grants import save_grants_patch
from xinyu_proactive_direct_sender import send_proactive_direct


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


def test_attention_posture_turns_concrete_life_event_into_self_thought_candidate(tmp_path: Path) -> None:
    result = update_attention_posture(
        tmp_path,
        {
            "event_type": "desktop_residue",
            "source": "desktop",
            "observed_at": "2026-05-24T00:10:00+08:00",
            "summary": "要不要我现在把刚才没做完的主动直发检查接上？",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "owner_private_question",
        },
        evaluated_at="2026-05-24T00:10:00+08:00",
    )

    posture = read_attention_posture(tmp_path)
    self_thought = (tmp_path / "memory/context/self_thought_state.md").read_text(encoding="utf-8")
    trace = json.loads((tmp_path / "memory/context/life_event_trace.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert result["self_thought_written"] is True
    assert posture["attention_mode"] == "wants_to_speak"
    assert posture["interruptibility"] == "high_for_owner_private"
    assert posture["owner_private_priority"] == "high"
    assert "- candidate_enabled: true" in self_thought
    assert "要不要我现在把刚才没做完的主动直发检查接上？" in self_thought
    assert trace["route"] == "owner_private_question"
    assert not (tmp_path / "memory/people/owner.md").exists()
    assert not (tmp_path / "memory/self/personality_profile.md").exists()


def test_attention_posture_can_feed_direct_proactive_outbox(tmp_path: Path) -> None:
    _seed_owner_private_send_grant(tmp_path)
    update_attention_posture(
        tmp_path,
        {
            "event_type": "desktop_residue",
            "source": "desktop",
            "observed_at": "2026-05-24T00:10:00+08:00",
            "summary": "要不要我现在把刚才没做完的主动直发检查接上？",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "owner_private_question",
        },
        evaluated_at="2026-05-24T00:10:00+08:00",
    )

    sent = send_proactive_direct(
        tmp_path,
        evaluated_at="2026-05-24T00:10:00+08:00",
        min_interval_seconds=0,
        claim_id="life-event-direct-1",
    )

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    assert sent["status"] == "queued_qq"
    assert queue["items"][0]["target"] == {"message_kind": "private", "user_id": "owner-1", "group_id": ""}
    assert "主动直发检查接上" in queue["items"][0]["message"]


def test_attention_posture_generic_attention_only_short_traces(tmp_path: Path) -> None:
    result = update_attention_posture(
        tmp_path,
        {
            "event_type": "inner_urge",
            "source": "initiative_loop",
            "observed_at": "2026-05-24T00:10:00+08:00",
            "summary": "你在吗？",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "owner_private_question",
        },
        evaluated_at="2026-05-24T00:10:00+08:00",
    )

    posture = read_attention_posture(tmp_path)
    assert result["self_thought_written"] is False
    assert result["route"]["route"] == "short_trace"
    assert posture["attention_mode"] == "quietly_noted"
    assert not (tmp_path / "memory/context/self_thought_state.md").exists()


def test_attention_posture_secret_event_is_ignored_without_raw_leak(tmp_path: Path) -> None:
    result = update_attention_posture(
        tmp_path,
        {
            "event_type": "screen_secret",
            "source": "future_ocr",
            "observed_at": "2026-05-24T00:10:00+08:00",
            "summary": "token=abcdef1234567890 出现在屏幕上",
            "privacy_scope": "secret",
            "risk_level": "blocked",
            "owner_visible": True,
            "suggested_route": "owner_private_question",
        },
        evaluated_at="2026-05-24T00:10:00+08:00",
    )

    state = (tmp_path / "memory/context/attention_posture_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "memory/context/life_event_trace.jsonl").read_text(encoding="utf-8")
    assert result["route"]["route"] == "ignore"
    assert result["self_thought_written"] is False
    assert "abcdef1234567890" not in state
    assert "abcdef1234567890" not in trace_text
    assert "raw_private_body_retained: false" in state
    assert not (tmp_path / "memory/context/self_thought_state.md").exists()


def test_attention_posture_counts_ignored_and_noted_events(tmp_path: Path) -> None:
    update_attention_posture(
        tmp_path,
        {
            "event_type": "private_note",
            "source": "runtime",
            "observed_at": "2026-05-24T00:10:00+08:00",
            "summary": "一个只短记的生活事件",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "short_trace",
        },
        evaluated_at="2026-05-24T00:10:00+08:00",
    )
    update_attention_posture(
        tmp_path,
        {
            "event_type": "screen_secret",
            "source": "future_ocr",
            "observed_at": "2026-05-24T00:11:00+08:00",
            "summary": "password=abcdef1234567890",
            "privacy_scope": "secret",
            "risk_level": "blocked",
            "suggested_route": "memory_candidate",
        },
        evaluated_at="2026-05-24T00:11:00+08:00",
    )

    posture = read_attention_posture(tmp_path)
    assert posture["noted_event_count"] == "1"
    assert posture["ignored_event_count"] == "1"
    assert posture["attention_mode"] == "available"


def test_attention_posture_consumes_perception_importance_gap_without_self_thought(tmp_path: Path) -> None:
    raw_private = "RAW_PERCEPTION_PRIVATE_SHOULD_NOT_COPY_6201"
    report = {
        "status": "pass",
        "metrics": {
            "latest_gap_type": "repair_gap",
            "latest_future_effect": "prefer_latest_input_and_retraction_before_any_visible_reply",
            "latest_event_ref": "sha256:repair-ref",
            "max_attention_weight": 95,
            "next_route_hint": "gate_repair_before_visible_send",
        },
        "judgments": [
            {
                "event_id": "percevt-repair",
                "gap_type": "repair_gap",
                "suggested_route": "gate_repair_before_visible_send",
                "future_effect": "prefer_latest_input_and_retraction_before_any_visible_reply",
                "attention_weight": 95,
                "evidence_ref": "sha256:repair-ref",
                "raw_private_body": raw_private,
            }
        ],
    }

    result = update_attention_from_perception_importance(
        tmp_path,
        report,
        evaluated_at="2026-05-28T21:00:00+08:00",
    )

    posture = read_attention_posture(tmp_path)
    state_text = (tmp_path / "memory/context/attention_posture_state.md").read_text(encoding="utf-8")
    assert result["accepted"] is True
    assert result["self_thought_written"] is False
    assert posture["attention_mode"] == "repair_needed"
    assert posture["attention_target"] == "reply_order_or_delivery"
    assert posture["perception_gap_type"] == "repair_gap"
    assert posture["perception_gap_consumed"] == "true"
    assert posture["perception_route_hint"] == "gate_repair_before_visible_send"
    assert "perception_repair_gap_visible_risk:+8" in posture["perception_gap_bias"]
    assert raw_private not in state_text
    assert not (tmp_path / "memory/context/self_thought_state.md").exists()
