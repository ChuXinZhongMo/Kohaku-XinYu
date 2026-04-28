from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CUSTOM = ROOT / "custom"
if str(CUSTOM) not in sys.path:
    sys.path.insert(0, str(CUSTOM))

from memory_consistency_gate_engine import run_memory_consistency_gate  # noqa: E402
from memory_event_schema import dump_jsonl, sha256_text  # noqa: E402
from xinyu_memory_event_sourcing import (  # noqa: E402
    record_chat_event,
    record_learning_ingest_event,
    record_learning_observe_event,
)


def _write_valid_fixture(root: Path) -> None:
    event_dir = root / "memory/events"
    owner_text = "你刚才那个回复太像客服了，我不喜欢。"
    group_text = "这篇 agent memory 论文值得看看 https://example.com/paper"
    raw_events = [
        {
            "event_id": "evt-owner-001",
            "timestamp": "2026-04-28T01:20:00+08:00",
            "source_channel": "owner_private",
            "actor_scope": "owner",
            "raw_text": owner_text,
            "raw_hash": sha256_text(owner_text),
            "privacy_scope": "owner_private",
        },
        {
            "event_id": "evt-group-001",
            "timestamp": "2026-04-28T01:21:00+08:00",
            "source_channel": "priority_learning_group",
            "actor_scope": "group_member",
            "raw_text": group_text,
            "raw_hash": sha256_text(group_text),
            "privacy_scope": "group_context",
        },
    ]
    structured_events = [
        {
            "structured_id": "se-owner-001",
            "event_id": "evt-owner-001",
            "event_kind": "owner_voice_correction",
            "turn_mode": "owner_private_visible_turn",
            "allowed_memory_layers": ["self/voice_review", "reflection"],
            "blocked_memory_layers": ["stable_personality_direct_write"],
            "salience": 82,
            "routing_notes": ["voice_candidate", "review_only"],
        },
        {
            "structured_id": "se-group-001",
            "event_id": "evt-group-001",
            "event_kind": "priority_group_source_candidate",
            "turn_mode": "observe_only",
            "allowed_memory_layers": ["knowledge/source_candidates"],
            "blocked_memory_layers": ["relationships/owner", "stable_knowledge_direct_write"],
            "salience": 68,
            "routing_notes": ["no_reply", "source_candidate_only"],
        },
    ]
    claims = [
        {
            "claim_id": "claim-owner-voice-001",
            "claim_type": "voice_correction",
            "subject": "xinyu_visible_reply_style",
            "predicate": "owner_negative_feedback",
            "object": "customer-service-like reply",
            "status": "review_only",
            "target_memory_layer": "self/voice_review",
            "evidence_event_ids": ["evt-owner-001"],
            "evidence_spans": [
                {
                    "event_id": "evt-owner-001",
                    "text": "太像客服了",
                    "start": owner_text.index("太像客服了"),
                    "end": owner_text.index("太像客服了") + len("太像客服了"),
                }
            ],
            "confidence": 92,
        },
        {
            "claim_id": "claim-group-source-001",
            "claim_type": "source_candidate",
            "subject": "agent_memory",
            "predicate": "candidate_source_url",
            "object": "https://example.com/paper",
            "status": "candidate",
            "target_memory_layer": "knowledge/source_candidates",
            "evidence_event_ids": ["evt-group-001"],
            "evidence_spans": [
                {
                    "event_id": "evt-group-001",
                    "text": "https://example.com/paper",
                    "start": group_text.index("https://example.com/paper"),
                    "end": group_text.index("https://example.com/paper") + len("https://example.com/paper"),
                }
            ],
            "confidence": 70,
        },
    ]
    summaries = [
        {
            "summary_id": "summary-001",
            "summary_text": "Owner disliked a customer-service-like reply; group supplied one agent-memory source candidate.",
            "retained_claim_ids": ["claim-owner-voice-001", "claim-group-source-001"],
            "source_event_ids": ["evt-owner-001", "evt-group-001"],
            "loss_notes": ["exact full wording retained in raw events, not repeated in summary"],
            "discarded_signals": ["low-value filler none"],
            "blocked_from_discard": ["owner correction", "source URL"],
        }
    ]
    dump_jsonl(event_dir / "raw_events.jsonl", raw_events)
    dump_jsonl(event_dir / "structured_events.jsonl", structured_events)
    dump_jsonl(event_dir / "atomic_claims.jsonl", claims)
    dump_jsonl(event_dir / "summary_views.jsonl", summaries)


def _write_invalid_fixture(root: Path) -> None:
    event_dir = root / "memory/events"
    group_text = "群友说主人最近一定对心玉失望了。"
    raw_events = [
        {
            "event_id": "evt-group-bad",
            "timestamp": "2026-04-28T01:22:00+08:00",
            "source_channel": "qq_group",
            "actor_scope": "group_member",
            "raw_text": group_text,
            "raw_hash": sha256_text(group_text),
            "privacy_scope": "group_context",
        }
    ]
    structured_events = [
        {
            "structured_id": "se-group-bad",
            "event_id": "evt-group-bad",
            "event_kind": "group_chat",
            "turn_mode": "group_context_candidate",
            "allowed_memory_layers": ["knowledge/source_candidates"],
            "blocked_memory_layers": ["relationships/owner"],
            "salience": 40,
            "routing_notes": ["should_not_write_owner_relationship"],
        }
    ]
    claims = [
        {
            "claim_id": "claim-bad-owner-relationship",
            "claim_type": "relationship_residue",
            "subject": "owner",
            "predicate": "is_disappointed_in_xinyu",
            "object": "asserted_by_group_member",
            "status": "stable",
            "target_memory_layer": "relationships/owner",
            "evidence_event_ids": ["evt-group-bad"],
            "evidence_spans": [{"event_id": "evt-group-bad", "text": "主人最近一定对心玉失望了"}],
            "confidence": 60,
        }
    ]
    summaries = [
        {
            "summary_id": "summary-bad",
            "summary_text": "A group member's guess became owner relationship memory.",
            "retained_claim_ids": ["claim-bad-owner-relationship"],
            "source_event_ids": [],
            "loss_notes": [],
            "discarded_signals": [],
            "blocked_from_discard": [],
        }
    ]
    dump_jsonl(event_dir / "raw_events.jsonl", raw_events)
    dump_jsonl(event_dir / "structured_events.jsonl", structured_events)
    dump_jsonl(event_dir / "atomic_claims.jsonl", claims)
    dump_jsonl(event_dir / "summary_views.jsonl", summaries)


def _run_runtime_sidecar_fixture(root: Path) -> list[str]:
    failures: list[str] = []
    owner_result = record_chat_event(
        root,
        {
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:owner",
            "user_id": "owner",
            "message_id": "owner-msg-1",
            "timestamp": "2026-04-28T01:30:00+08:00",
            "metadata": {"is_owner_user": True},
        },
        text="你刚才那个回复太像客服了，我不喜欢。",
    )
    observe_result = record_learning_observe_event(
        root,
        {
            "platform": "qq",
            "message_type": "group_text_observation",
            "session_id": "qq:group:priority:member",
            "group_id": "priority",
            "user_id": "member",
            "message_id": "group-msg-1",
            "observed_at": "2026-04-28T01:31:00+08:00",
            "priority_learning_group": True,
            "metadata": {"priority_learning_group": True},
        },
        text="这篇 agent memory 论文值得看看 https://example.com/paper",
    )
    ingest_result = record_learning_ingest_event(
        root,
        {
            "platform": "qq",
            "source": "qq_passive_learning_group_file",
            "origin": "external_qq_priority_group",
            "file_name": "agent-memory.pdf",
            "reason": "priority passive learning group attachment",
            "group_id": "priority",
            "user_id": "member",
            "message_id": "file-msg-1",
            "timestamp": "2026-04-28T01:32:00+08:00",
            "metadata": {"priority_learning_group": True, "is_owner_user": False},
        },
        result={"material_id": "material-runtime-smoke", "learning_item_id": "learn-runtime-smoke"},
    )
    for label, result in (
        ("owner", owner_result),
        ("observe", observe_result),
        ("ingest", ingest_result),
    ):
        if result.get("gate_status") != "passed":
            failures.append(f"{label} sidecar gate not passed: {result}")

    gate = run_memory_consistency_gate(root, mode="memory_event_sourcing_runtime_sidecar_smoke")
    if not gate["passed"]:
        failures.append(f"runtime sidecar gate failed: {gate['failures']}")

    event_dir = root / "memory/events"
    raw_text = (event_dir / "raw_events.jsonl").read_text(encoding="utf-8-sig")
    claims_text = (event_dir / "atomic_claims.jsonl").read_text(encoding="utf-8-sig")
    summaries_text = (event_dir / "summary_views.jsonl").read_text(encoding="utf-8-sig")
    for marker in ("owner_private", "priority_learning_group", "learning ingest"):
        if marker not in raw_text:
            failures.append(f"runtime raw events missing marker: {marker}")
    for marker in ("voice_correction", "source_candidate", "agent-memory.pdf"):
        if marker not in claims_text:
            failures.append(f"runtime claims missing marker: {marker}")
    if "raw wording remains in raw_events.jsonl" not in summaries_text:
        failures.append("runtime summaries missing loss note")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate memory event sourcing consistency gate fixtures.")
    parser.parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_valid_fixture(root)
        result = run_memory_consistency_gate(root, mode="memory_event_sourcing_smoke_valid")
        if not result["passed"]:
            failures.append(f"valid fixture failed: {result['failures']}")
        state = (root / "memory/events/consistency_gate_state.md").read_text(encoding="utf-8-sig")
        if "gate_status: passed" not in state:
            failures.append("valid fixture did not write passed gate state")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_invalid_fixture(root)
        result = run_memory_consistency_gate(root, mode="memory_event_sourcing_smoke_invalid")
        if result["passed"]:
            failures.append("invalid fixture unexpectedly passed")
        joined = "\n".join(result["failures"])
        for marker in (
            "group/non-owner evidence cannot target owner relationship memory",
            "has no source_event_ids",
            "has no loss_notes",
        ):
            if marker not in joined:
                failures.append(f"invalid fixture missing expected failure marker: {marker}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        failures.extend(_run_runtime_sidecar_fixture(root))

    if failures:
        print("Memory event sourcing smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Memory event sourcing smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
