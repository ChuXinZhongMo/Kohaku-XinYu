from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_group_memory_pipeline import (  # noqa: E402
    group_full_memory_pipeline_enabled,
    group_owner_relationship_candidates_allowed,
    structured_event_for_group,
)
from xinyu_memory_candidate_extractor import build_candidate_specs, extract_memory_candidates  # noqa: E402
from xinyu_memory_event_sourcing import record_chat_event  # noqa: E402
from xinyu_memory_immune_gate import BLOCK, OBSERVE_MORE, evaluate_memory_immune_gate  # noqa: E402


def _owner_group_payload() -> dict:
    return {
        "message_type": "group_text",
        "group_id": "12345",
        "metadata": {"is_owner_user": True},
    }


def test_group_pipeline_enabled_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", raising=False)
    assert group_full_memory_pipeline_enabled(tmp_path) is True


def test_group_pipeline_disabled_by_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "0")
    assert group_full_memory_pipeline_enabled(tmp_path) is False


def test_structured_event_expands_layers_when_pipeline_on(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "1")
    cfg = structured_event_for_group(tmp_path, source_channel="qq_group", actor_scope="owner")
    assert "reflection" in cfg["allowed"]
    assert "relationships/owner_candidate" in cfg["allowed"]
    assert cfg["turn_mode"] == "group_owner_full_pipeline_candidate"
    assert cfg["salience"] == 64


def test_record_chat_event_group_owner_uses_full_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "1")
    (tmp_path / "memory" / "events").mkdir(parents=True, exist_ok=True)
    result = record_chat_event(tmp_path, _owner_group_payload(), text="我在乎这段关系，别敷衍我")
    assert result["recorded"] is True
    structured = (tmp_path / "memory/events/structured_events.jsonl").read_text(encoding="utf-8")
    assert "group_owner_full_pipeline_candidate" in structured
    assert "reflection" in structured


def test_owner_in_group_relationship_candidate_extracted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "1")
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    specs = build_candidate_specs(
        payload=_owner_group_payload(),
        user_text="我有点失望，希望你别敷衍",
        assistant_reply="我在。",
        root=tmp_path,
    )
    types = {spec.candidate_type for spec in specs}
    assert "relationship_signal" in types

    result = extract_memory_candidates(
        tmp_path,
        _owner_group_payload(),
        user_text="我有点失望，希望你别敷衍",
        assistant_reply="我在。",
    )
    assert result["candidate_count"] >= 1
    assert "group_full_pipeline_owner_candidates_enabled" in result["notes"]


def test_non_owner_group_still_blocks_owner_relationship_candidates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "1")
    payload = {"message_type": "group_text", "group_id": "999"}
    specs = build_candidate_specs(
        payload=payload,
        user_text="我有点失望",
        assistant_reply="嗯",
        root=tmp_path,
    )
    assert "relationship_signal" not in {spec.candidate_type for spec in specs}


def test_immune_gate_allows_group_owner_relationship_candidate_when_pipeline_on(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "1")
    decision = evaluate_memory_immune_gate(
        tmp_path,
        payload=_owner_group_payload(),
        candidate_type="relationship_signal",
        target_memory_layer="memory/relationships/index.md",
        candidate_text="owner-in-group relationship candidate",
        confidence_score=54,
    )
    assert decision.immune_status == OBSERVE_MORE
    assert "scope_mismatch_group_to_owner_memory" not in decision.danger_signals


def test_immune_gate_blocks_group_relationship_when_pipeline_off(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "0")
    decision = evaluate_memory_immune_gate(
        tmp_path,
        payload={"message_type": "group", "group_id": "g1"},
        candidate_type="relationship_signal",
        target_memory_layer="memory/relationships/index.md",
        candidate_text="group-scoped relationship candidate",
        confidence_score=64,
    )
    assert decision.immune_status == BLOCK
    assert "scope_mismatch_group_to_owner_memory" in decision.danger_signals


def test_group_owner_relationship_gate_helper(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "1")
    assert group_owner_relationship_candidates_allowed(tmp_path, _owner_group_payload()) is True
    assert group_owner_relationship_candidates_allowed(tmp_path, {"message_type": "group_text", "group_id": "1"}) is False