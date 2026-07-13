from __future__ import annotations

from xinyu_bridge_observation_reports import (
    _append_section,
    _ensure_observation_file,
    _update_real_life_events,
)
from xinyu_bridge_stores import (
    observation_report_exists,
    read_observation_report_text,
    read_observation_report_text_safe,
    write_observation_report_text,
)


def test_observation_report_store_reads_and_writes_text(tmp_path) -> None:
    path = tmp_path / "memory/knowledge/group_learning_observations.md"

    assert observation_report_exists(path) is False
    assert read_observation_report_text_safe(path) == ""
    assert read_observation_report_text_safe(path, default="fallback") == "fallback"

    write_observation_report_text(path, "# Report")
    assert observation_report_exists(path) is True
    assert read_observation_report_text(path) == "# Report\n"

    path.write_bytes(b"\xef\xbb\xbf# Bom Report\n")
    assert read_observation_report_text(path) == "# Bom Report\n"


def test_observation_report_helpers_create_append_and_touch_headers(tmp_path) -> None:
    memory_root = tmp_path / "memory"
    observation_path = memory_root / "knowledge/group_learning_observations.md"

    _ensure_observation_file(observation_path, "2026-01-01T08:00:00+08:00")
    _append_section(observation_path, "## obs-1\n- status: candidate")
    _ensure_observation_file(observation_path, "2026-01-02T08:00:00+08:00")

    observation_text = observation_path.read_text(encoding="utf-8")
    assert "title: Group Learning Observations" in observation_text
    assert "updated_at: 2026-01-02T08:00:00+08:00" in observation_text
    assert "last_confirmed_at: 2026-01-02T08:00:00+08:00" in observation_text
    assert "## obs-1" in observation_text

    _update_real_life_events(
        memory_root,
        "2026-01-03T08:00:00+08:00",
        {
            "observation_id": "1",
            "group_id": "group-hash",
            "actor_hash": "actor-hash",
            "text_excerpt": "source excerpt",
        },
    )

    events_path = memory_root / "context/real_life_input_events.md"
    events_text = events_path.read_text(encoding="utf-8")
    assert "title: Real Life Input Events" in events_text
    assert "updated_at: 2026-01-03T08:00:00+08:00" in events_text
    assert "## event-1" in events_text
    assert "- actor_id: external_group_member:actor-hash" in events_text
