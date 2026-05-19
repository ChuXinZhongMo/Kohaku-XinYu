from __future__ import annotations

from types import SimpleNamespace

from xinyu_temporal_memory_context import (
    build_temporal_memory_context,
    parse_memory_time,
    render_temporal_memory_context,
)


def _item(recall_id: str, time: str, summary: str) -> SimpleNamespace:
    return SimpleNamespace(recall_id=recall_id, time=time, summary=summary)


def test_parse_memory_time_accepts_dotted_human_timestamp() -> None:
    parsed = parse_memory_time("2026.5.18 22\uff1a37")

    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 5
    assert parsed.day == 18
    assert parsed.hour == 22
    assert parsed.minute == 37


def test_parse_memory_time_preserves_iso_timezone() -> None:
    parsed = parse_memory_time("2026-05-18T22:37:00+08:00")

    assert parsed is not None
    assert parsed.utcoffset() is not None
    assert parsed.utcoffset().total_seconds() == 8 * 60 * 60


def test_temporal_context_labels_recent_same_scene() -> None:
    context = build_temporal_memory_context(
        [_item("nap-start", "2026.5.18 12:30", "owner said they would take a nap")],
        user_text="\u6211\u9192\u4e86",
        evaluated_at="2026-05-18T13:30:00+08:00",
    )

    item = context.item_contexts[0]
    assert item.relation == "recent_same_scene"
    assert item.age_minutes == 60
    assert "likely still affects current physical/emotional state" in item.human_hint
    assert "temporal_context:absolute_time_available" in context.notes


def test_temporal_context_infers_recent_wake_from_nap() -> None:
    context = build_temporal_memory_context(
        [
            _item("nap-start", "2026.5.18 12:30", "owner said they would take a nap"),
            _item("nap-end", "2026.5.18 13:30", "owner woke up from the nap"),
        ],
        user_text="\u6211\u9192\u4e86",
        evaluated_at="2026-05-18T13:35:00+08:00",
    )

    assert context.life_inferences
    assert context.life_inferences[0].startswith("recent_wake_from_nap|")
    assert "sleep_to_wake_minutes: 60" in context.life_inferences[0]
    rendered = render_temporal_memory_context(context)
    assert "## Temporal Context" in rendered
    assert "inference: recent_wake_from_nap" in rendered


def test_temporal_context_infers_recent_wake_from_chinese_nap_sequence() -> None:
    context = build_temporal_memory_context(
        [
            _item("nap-start", "2026.5.18 12:30", "我12:30去午睡一会。"),
            _item("nap-end", "2026.5.18 13:30", "我13:30睡醒了。"),
        ],
        user_text="我现在醒了",
        evaluated_at="2026-05-18T13:35:00+08:00",
    )

    assert context.life_inferences
    assert context.life_inferences[0].startswith("recent_wake_from_nap|")
    assert "sleep_to_wake_minutes: 60" in context.life_inferences[0]


def test_temporal_context_does_not_infer_recency_without_time() -> None:
    context = build_temporal_memory_context(
        [_item("stable", "stable memory file", "owner often likes quiet replies")],
        user_text="quiet reply",
        evaluated_at="2026-05-18T13:35:00+08:00",
    )

    assert context.item_contexts[0].relation == "stable_or_plan_time"
    assert context.item_contexts[0].age_minutes is None
    assert context.life_inferences == ()
