from __future__ import annotations

from xinyu_life_event_contract import event_to_short_trace, normalize_life_event, route_life_event


def test_life_event_normalizes_sanitized_owner_private_question() -> None:
    event = normalize_life_event(
        {
            "event_type": "desktop_idle_residue",
            "source": "desktop",
            "observed_at": "2026-05-23T23:59:00+08:00",
            "summary": "要不要我把刚才没做完的 Desktop 状态接上？",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "owner_visible": True,
            "suggested_route": "owner_private_question",
        }
    )
    route = route_life_event(event)

    assert event.event_id.startswith("lifeevt-")
    assert event.evidence_hash.startswith("sha256:")
    assert route["route"] == "owner_private_question"
    assert route["proactive_direct_send_allowed"] is True
    assert route["direct_writes_allowed"] is False
    assert "memory/context/proactive_request_state.md" in route["allowed_memory_layers"]
    assert "memory/self/personality_profile.md" in route["blocked_memory_layers"]
    assert "memory/people/owner.md" in route["blocked_memory_layers"]


def test_life_event_does_not_retain_raw_private_body_or_secret() -> None:
    event = normalize_life_event(
        {
            "event_type": "qq_private",
            "source": "qq",
            "observed_at": "2026-05-23T23:59:00+08:00",
            "raw_text": "owner private sentence password=abc123456789 token=abcdef1234567890",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "short_trace",
        }
    )
    trace = event_to_short_trace(event)

    assert "owner private sentence" not in event.summary
    assert "abc123456789" not in event.summary
    assert "abcdef1234567890" not in event.summary
    assert event.summary == "private body received but not retained"
    assert "raw_text" not in trace
    assert trace["route"] == "short_trace"


def test_life_event_blocks_generic_attention_as_direct_question() -> None:
    event = normalize_life_event(
        {
            "event_type": "inner_urge",
            "source": "initiative_loop",
            "observed_at": "2026-05-23T23:59:00+08:00",
            "summary": "你在吗？",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "owner_private_question",
        }
    )
    route = route_life_event(event)

    assert route["route"] == "short_trace"
    assert route["proactive_direct_send_allowed"] is False
    assert "generic_attention_blocked" in route["notes"]


def test_life_event_downgrades_non_question_direct_route_to_initiative_candidate() -> None:
    event = normalize_life_event(
        {
            "event_type": "reflection_residue",
            "source": "reflection",
            "observed_at": "2026-05-23T23:59:00+08:00",
            "summary": "刚才的反思留下了一点想继续整理的余波",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "owner_private_question",
        }
    )
    route = route_life_event(event)

    assert route["route"] == "initiative_candidate"
    assert route["proactive_direct_send_allowed"] is False
    assert "owner_private_question_requires_concrete_question" in route["notes"]


def test_life_event_blocks_secret_and_hides_owner_visible() -> None:
    event = normalize_life_event(
        {
            "event_type": "credential_seen",
            "source": "screen_ocr_future",
            "observed_at": "2026-05-23T23:59:00+08:00",
            "summary": "api_key=abcdef1234567890 出现在屏幕上",
            "privacy_scope": "secret",
            "risk_level": "blocked",
            "owner_visible": True,
            "suggested_route": "owner_private_question",
        }
    )
    route = route_life_event(event)

    assert "abcdef1234567890" not in event.summary
    assert "<secret>" in event.summary
    assert event.owner_visible is False
    assert route["route"] == "ignore"
    assert route["owner_visible"] is False
    assert route["proactive_direct_send_allowed"] is False
    assert "route_blocked_by_risk_or_secret" in route["notes"]
    assert "owner_visible_blocked_by_privacy" in route["notes"]


def test_life_event_sensitive_privacy_cannot_be_initiative_or_direct() -> None:
    event = normalize_life_event(
        {
            "event_type": "private_emotion",
            "source": "owner_private",
            "observed_at": "2026-05-23T23:59:00+08:00",
            "summary": "一个敏感情绪片段，只能留短迹",
            "privacy_scope": "sensitive",
            "risk_level": "medium",
            "suggested_route": "initiative_candidate",
        }
    )
    route = route_life_event(event)

    assert route["route"] == "short_trace"
    assert route["allowed_memory_layers"] == ["memory/context/life_event_trace.jsonl"]
    assert route["direct_writes_allowed"] is False
    assert "route_downgraded_for_sensitive_privacy" in route["notes"]
