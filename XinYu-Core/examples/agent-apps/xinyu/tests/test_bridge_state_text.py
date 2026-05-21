from __future__ import annotations

from datetime import datetime, timezone

from xinyu_bridge_desktop_state_text import (
    desktop_replace_frontmatter_field as compat_frontmatter,
    desktop_replace_list_field as compat_list,
)
from xinyu_bridge_session import AgentSession
from xinyu_bridge_state_text import (
    build_payload_time_context_block,
    desktop_replace_frontmatter_field,
    desktop_replace_list_field,
    payload_event_time_iso,
    payload_event_timestamp_seconds,
    replace_frontmatter_field,
    replace_list_field,
)
from xinyu_core_bridge import XinYuBridgeRuntime


def _timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp())


def _field_value(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{field}: "):
            return line.split(": ", 1)[1]
        if line.startswith(f"- {field}: "):
            return line.split(": ", 1)[1]
    raise AssertionError(f"missing field: {field}")


def test_replace_frontmatter_field_updates_or_appends_with_default() -> None:
    assert replace_frontmatter_field("updated_at: old\nname: x\n", "updated_at", "new") == "updated_at: new\nname: x\n"
    updated = replace_frontmatter_field("name: x\n", "updated_at", "")

    datetime.fromisoformat(_field_value(updated, "updated_at"))
    assert updated != "name: x\nupdated_at: none\n"
    assert replace_frontmatter_field("name: x\n", "status", "") == "name: x\nstatus: none\n"


def test_replace_list_field_updates_or_appends_with_default() -> None:
    assert replace_list_field("- status: requested\n- owner: x\n", "status", "sent") == "- status: sent\n- owner: x\n"
    assert replace_list_field("- owner: x\n", "status", "") == "- owner: x\n- status: none\n"
    updated = replace_list_field("- owner: x\n", "updated_at", "")

    datetime.fromisoformat(_field_value(updated, "updated_at"))
    assert "- updated_at: none" not in updated


def test_desktop_state_text_compat_exports_shared_functions() -> None:
    assert desktop_replace_frontmatter_field is replace_frontmatter_field
    assert desktop_replace_list_field is replace_list_field
    assert compat_frontmatter is replace_frontmatter_field
    assert compat_list is replace_list_field


def test_payload_event_time_prefers_top_level_timestamp() -> None:
    top_level_timestamp = int(datetime(2026, 1, 1, 22, 17, tzinfo=timezone.utc).timestamp())
    payload = {"timestamp": top_level_timestamp, "metadata": {"created_at": "2026-01-01T00:00:00+00:00"}}

    assert _timestamp(payload_event_time_iso(payload)) == top_level_timestamp
    assert payload_event_timestamp_seconds(payload) == top_level_timestamp


def test_payload_event_time_accepts_iso_metadata_fallback() -> None:
    payload = {"metadata": {"qq_event_time_iso": "2026-05-18T13:30:00+08:00"}}
    expected_timestamp = _timestamp("2026-05-18T13:30:00+08:00")

    assert _timestamp(payload_event_time_iso(payload)) == expected_timestamp
    assert payload_event_timestamp_seconds(payload) == expected_timestamp


def test_payload_event_time_accepts_millisecond_timestamp() -> None:
    expected_timestamp = _timestamp("2026-05-18T13:30:00+08:00")

    assert payload_event_timestamp_seconds({"timestamp": expected_timestamp * 1000}) == expected_timestamp


def test_payload_time_context_block_separates_event_time_from_runtime_time() -> None:
    event_timestamp = _timestamp("2026-05-18T13:30:00+08:00")
    payload = {
        "timestamp": event_timestamp,
        "metadata": {"qq_event_time_iso": "2026-01-01T00:00:00+00:00"},
    }

    block = build_payload_time_context_block(payload, observed_at="2026-05-18T13:32:05+08:00")

    assert "## Live Time Context" in block
    assert "current_runtime_time:" in block
    assert f"message_event_unix: {event_timestamp}" in block
    assert "message_age_seconds: 125" in block
    assert "event_time_source: payload.timestamp" in block
    assert "clock_skew_possible: false" in block
    assert "use message_event_time for when the owner actually said the message" in block


def test_payload_time_context_block_falls_back_to_runtime_time() -> None:
    block = build_payload_time_context_block({}, observed_at="2026-05-18T13:32:05+08:00")

    assert "event_time_source: runtime_fallback" in block
    assert "message_age_seconds: 0" in block


def test_core_bridge_dialogue_tail_uses_payload_time_for_user_turn(tmp_path) -> None:
    runtime = object.__new__(XinYuBridgeRuntime)
    runtime.xinyu_dir = tmp_path
    runtime.dialogue_session_tail_entries = 8
    runtime.dialogue_persisted_tail_entries = 8
    session = AgentSession(key="qq:private:test", agent=None, prompt_signature="test")
    payload = {"timestamp": _timestamp("2026-05-18T13:30:00+08:00")}

    runtime._append_dialogue_tail(session, user_text="woke up", reply="awake", payload=payload)

    assert [item["role"] for item in session.dialogue_tail] == ["user", "assistant"]
    assert _timestamp(session.dialogue_tail[0]["recorded_at"]) == payload["timestamp"]
    assert session.dialogue_tail[1]["recorded_at"]
