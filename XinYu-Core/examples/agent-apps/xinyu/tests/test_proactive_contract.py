from __future__ import annotations

from xinyu_proactive_contract import (
    desktop_focus_label,
    proactive_source_is_urgent,
    should_surface_desktop_item,
    should_surface_runtime_error,
)


def test_watched_source_runtime_errors_are_internal_only() -> None:
    assert not should_surface_runtime_error(
        label="watched_source",
        detail="last_status=error last_notes=fetch_error_connecttimeout",
    )
    assert should_surface_runtime_error(label="qq_gateway", detail="last_status=error")


def test_desktop_visibility_contract_blocks_internal_runtime_refs() -> None:
    assert not should_surface_desktop_item(
        source_type="runtime_error",
        intent_type="runtime_error",
        source_ref="runtime_program_awareness:watched_source",
    )
    assert should_surface_desktop_item(
        source_type="runtime_error",
        intent_type="runtime_error",
        source_ref="runtime_program_awareness:qq_gateway",
    )


def test_desktop_focus_labels_are_owner_readable() -> None:
    assert desktop_focus_label("reflection_question") == "\u60f3\u6cd5\u5f85\u786e\u8ba4"
    assert desktop_focus_label("runtime_error") == "\u8fd0\u884c\u72b6\u6001\u63d0\u9192"
    assert desktop_focus_label("utility_score", "urgency_score") == "\u4e3b\u52a8\u63d0\u9192"


def test_urgent_source_contract_is_centralized() -> None:
    assert proactive_source_is_urgent("task_failed")
    assert proactive_source_is_urgent("runtime_error")
    assert not proactive_source_is_urgent("style_repair")
