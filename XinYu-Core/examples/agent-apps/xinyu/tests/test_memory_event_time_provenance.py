from __future__ import annotations

from datetime import datetime
from pathlib import Path

from xinyu_dialogue_archive import (
    OWNER_PRIVATE_SCOPE,
    archive_dialogue_turn,
    list_memory_candidates,
    list_temporal_traces,
    search_dialogue_archive,
)
from xinyu_memory_candidate_extractor import extract_memory_candidates


def _timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp())


def test_memory_write_paths_preserve_payload_event_time(tmp_path: Path) -> None:
    event_time = "2026-05-18T13:30:00+08:00"
    event_timestamp = _timestamp(event_time)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:event-time",
        "user_id": "42",
        "timestamp": event_timestamp * 1000,
        "metadata": {"is_owner_user": True, "qq_event_time_iso": "2026-01-01T00:00:00+00:00"},
    }

    archive = archive_dialogue_turn(
        tmp_path,
        payload,
        user_text="Codex runtime event-time provenance marker",
        assistant_reply="noted",
        message_type="technical_work",
    )
    extract_memory_candidates(
        tmp_path,
        payload,
        user_text="remember this Codex runtime bridge event-time provenance marker",
        assistant_reply="queued for review",
        source_message_ids=archive["message_ids"],
    )

    archived_messages = search_dialogue_archive(
        tmp_path,
        "event-time provenance marker",
        scopes=(OWNER_PRIVATE_SCOPE,),
        session_key="qq:private:event-time",
        limit=5,
    )
    user_message = next(item for item in archived_messages if item.role == "user")
    candidates = list_memory_candidates(tmp_path)
    traces = list_temporal_traces(tmp_path)

    assert _timestamp(user_message.created_at) == event_timestamp
    assert candidates
    assert traces
    assert {_timestamp(row["created_at"]) for row in candidates} == {event_timestamp}
    assert {_timestamp(row["created_at"]) for row in traces} == {event_timestamp}
    assert {_timestamp(row["updated_at"]) for row in traces} == {event_timestamp}
