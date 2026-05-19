from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from memory_structured_p0_triage import (  # noqa: E402
    build_p0_triage,
    build_reference_index,
    reference_result_from_index,
    render_markdown,
    rule_for_path,
)


def test_rule_for_path_classifies_known_structured_files() -> None:
    qq_queue_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/context/qq_outbox_queue.json")
    assert qq_queue_rule.category == "runtime_queue"
    assert qq_queue_rule.initial_decision == "manifested_private_runtime_queue"
    assert qq_queue_rule.target_boundary == "stores/queue_boundary_manifest"
    self_action_rule = rule_for_path(
        "XinYu-Core/examples/agent-apps/xinyu/memory/context/self_action_gateway_approval_queue.jsonl"
    )
    assert self_action_rule.category == "runtime_queue"
    assert self_action_rule.initial_decision == "compat_store_owner_exists"
    assert self_action_rule.target_boundary == "stores/self_action_queue"
    impulse_trace_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_trace.jsonl")
    assert impulse_trace_rule.category == "runtime_trace_log"
    assert impulse_trace_rule.initial_decision == "manifested_runtime_trace_log"
    assert impulse_trace_rule.target_boundary == "stores/runtime_trace_manifest"
    goldmark_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/self/goldmark_positive_overlay.json")
    assert goldmark_rule.category == "persona_runtime_overlay"
    assert goldmark_rule.initial_decision == "compat_store_owner_exists"
    assert goldmark_rule.target_boundary == "stores/persona_runtime_overlay"
    digest_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/context/daily_digest.json")
    assert digest_rule.category == "durable_runtime_state"
    assert digest_rule.initial_decision == "compat_store_owner_exists"
    assert digest_rule.target_boundary == "stores/daily_digest_state"
    impulse_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_state.json")
    assert impulse_rule.category == "durable_runtime_state"
    assert impulse_rule.initial_decision == "compat_store_owner_exists"
    assert impulse_rule.target_boundary == "stores/impulse_soup_state"
    slow_state_rule = rule_for_path(
        "XinYu-Core/examples/agent-apps/xinyu/memory/context/slow_state_modulator_state.json"
    )
    assert slow_state_rule.category == "durable_runtime_state"
    assert slow_state_rule.initial_decision == "compat_store_owner_exists"
    assert slow_state_rule.target_boundary == "stores/slow_state_modulator_state"
    sticker_state_rule = rule_for_path(
        "XinYu-Core/examples/agent-apps/xinyu/memory/context/sticker_send_state.generated.json"
    )
    assert sticker_state_rule.category == "durable_runtime_state"
    assert sticker_state_rule.initial_decision == "compat_store_owner_exists"
    assert sticker_state_rule.target_boundary == "stores/sticker_send_state"
    interaction_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/context/interaction_journal.jsonl")
    assert interaction_rule.category == "episodic_event_log"
    assert interaction_rule.initial_decision == "manifested_compat_event_log"
    assert interaction_rule.target_boundary == "stores/event_boundary_manifest"
    proactive_history_rule = rule_for_path(
        "XinYu-Core/examples/agent-apps/xinyu/memory/context/proactive_request_history.jsonl"
    )
    assert proactive_history_rule.category == "episodic_event_log"
    assert proactive_history_rule.initial_decision == "manifested_compat_event_log"
    assert proactive_history_rule.target_boundary == "stores/event_boundary_manifest"
    owner_events_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/relationships/owner_recent_events.jsonl")
    assert owner_events_rule.category == "private_relationship_event_log"
    assert owner_events_rule.initial_decision == "manifested_private_event_log"
    assert owner_events_rule.target_boundary == "stores/event_boundary_manifest"
    review_cursor_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/context/review_inbox_cursor.json")
    assert review_cursor_rule.category == "runtime_cursor_or_decision_store"
    assert review_cursor_rule.initial_decision == "compat_store_owner_exists"
    assert review_cursor_rule.target_boundary == "stores/review_state"
    review_decisions_rule = rule_for_path(
        "XinYu-Core/examples/agent-apps/xinyu/memory/context/review_inbox_decisions.json"
    )
    assert review_decisions_rule.category == "runtime_cursor_or_decision_store"
    assert review_decisions_rule.initial_decision == "compat_store_owner_exists"
    assert review_decisions_rule.target_boundary == "stores/review_state"
    source_extract_rule = rule_for_path(
        "XinYu-Core/examples/agent-apps/xinyu/memory/creative/planning/inspiration/safe_extracts.jsonl"
    )
    assert source_extract_rule.category == "source_extract_log"
    assert source_extract_rule.initial_decision == "compat_source_extract_store_exists"
    assert source_extract_rule.target_boundary == "stores/source_extracts"
    initiative_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/initiative.json")
    assert initiative_rule.category == "durable_runtime_state"
    assert initiative_rule.initial_decision == "held_orphan_runtime_state"
    assert initiative_rule.target_boundary == "stores/orphan_runtime_state_manifest"
    mind_loop_rule = rule_for_path("XinYu-Core/examples/agent-apps/xinyu/memory/mind_loop_state.json")
    assert mind_loop_rule.category == "durable_runtime_state"
    assert mind_loop_rule.initial_decision == "held_orphan_runtime_state"
    assert mind_loop_rule.target_boundary == "stores/orphan_runtime_state_manifest"


def test_build_p0_triage_uses_reference_file_names_without_reading_memory_body(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    memory_file = app / "memory/context/qq_outbox_queue.json"
    source_file = app / "xinyu_qq_outbox.py"
    memory_file.parent.mkdir(parents=True)
    source_file.parent.mkdir(parents=True, exist_ok=True)
    memory_file.write_text('{"body": "secret queued message"}\n', encoding="utf-8")
    source_file.write_text('QUEUE = "memory/context/qq_outbox_queue.json"\n', encoding="utf-8")

    triage = build_p0_triage(tmp_path)

    assert triage["total_p0_items"] == 1
    item = triage["items"][0]
    assert item["category"] == "runtime_queue"
    assert item["initial_decision"] == "manifested_private_runtime_queue"
    assert item["reference_count"] == 1
    assert "XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_outbox.py" in item["reference_examples"]
    assert "secret queued message" not in str(triage)


def test_reference_index_maps_candidates_without_memory_body(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    memory_file = app / "memory/context/daily_digest.json"
    source_file = app / "services/daily_digest.py"
    ignored_test = app / "tests/test_daily_digest.py"
    memory_file.parent.mkdir(parents=True)
    source_file.parent.mkdir(parents=True, exist_ok=True)
    ignored_test.parent.mkdir(parents=True, exist_ok=True)
    memory_file.write_text('{"body": "private digest body"}\n', encoding="utf-8")
    source_file.write_text('DIGEST = "memory/context/daily_digest.json"\n', encoding="utf-8")
    ignored_test.write_text('DIGEST = "memory/context/daily_digest.json"\n', encoding="utf-8")

    index = build_reference_index(tmp_path, ["XinYu-Core/examples/agent-apps/xinyu/memory/context/daily_digest.json"])
    result = reference_result_from_index(
        index,
        "XinYu-Core/examples/agent-apps/xinyu/memory/context/daily_digest.json",
    )

    assert result["count"] == 1
    assert result["examples"] == ["XinYu-Core/examples/agent-apps/xinyu/services/daily_digest.py"]
    assert "private digest body" not in str(index)


def test_render_markdown_reports_triage_without_secret_body() -> None:
    triage = {
        "total_p0_items": 1,
        "by_category": {"runtime_queue": 1},
        "by_initial_decision": {"migrate_candidate_after_caller_update": 1},
        "items": [
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/qq_outbox_queue.json",
                "category": "runtime_queue",
                "initial_decision": "migrate_candidate_after_caller_update",
                "target_boundary": "stores/queues-or-runtime",
                "reference_count": 1,
                "reference_examples": ["XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_outbox.py"],
                "handling": "Queues are operational state.",
            }
        ],
    }

    rendered = render_markdown(triage)

    assert "total_p0_items: 1" in rendered
    assert "runtime_queue" in rendered
    assert "JSON/JSONL memory bodies" in rendered
