from __future__ import annotations

from xinyu_voice_style_observations import (
    analyse_public_examples,
    proactive_style_guard,
    write_voice_style_observations,
)


def test_public_reference_analysis_is_aggregate_only():
    analysis = analyse_public_examples()

    assert analysis["example_count"] >= 80
    assert analysis["corpus_finding_count"] >= 7
    assert analysis["average_visible_chars"] < 30
    assert analysis["short_reply_count"] > analysis["long_reply_count"]
    assert analysis["question_like_count"] >= 5
    assert analysis["first_person_start_count"] < analysis["example_count"]
    assert analysis["common_endings"]


def test_proactive_style_guard_blocks_customer_service_templates():
    blocked = proactive_style_guard("我想问你一件小事：要不要我现在跑一遍生活事件到主动消息的闭环？")
    accepted = proactive_style_guard("刚才那条链还接吗")

    assert not blocked["accepted"]
    assert "我想问你一件小事" in blocked["forbidden_patterns"]
    assert accepted["accepted"]


def test_write_voice_style_observations_keeps_memory_boundaries(tmp_path):
    path = write_voice_style_observations(tmp_path, updated_at="2026-05-23T00:00:00+00:00")
    text = path.read_text(encoding="utf-8")

    assert path.relative_to(tmp_path).as_posix() == "memory/self/voice_style_observations.md"
    assert "stable_persona_write: blocked" in text
    assert "owner_memory_write: blocked" in text
    assert "raw_private_body_retained: false" in text
    assert "B 站" in text or "bilibili" in text
    assert "LCCC-base" in text
    assert "Tieba Corpus" in text
    assert "short_reply_count" in text
    assert "我想问你一件小事" in text
