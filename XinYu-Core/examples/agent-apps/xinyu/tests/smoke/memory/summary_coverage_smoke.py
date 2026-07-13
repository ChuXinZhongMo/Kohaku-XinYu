from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import sys
import tempfile
from pathlib import Path


CUSTOM = ROOT / "custom"
if str(CUSTOM) not in sys.path:
    sys.path.insert(0, str(CUSTOM))

from archive_commit_engine import run_archive_commit  # noqa: E402
from memory_event_schema import dump_jsonl, sha256_text  # noqa: E402


CHECKED_AT = "2026-04-28T02:00:00+08:00"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_archive_ready_state(root: Path, *, event_sourced: bool) -> None:
    coverage_lines = ""
    if event_sourced:
        coverage_lines = """
- coverage_required: true
- source_event_ids: [evt-voice-001]
- retained_claim_ids: [claim-voice-001]
"""
    _write(
        root / "memory/archive/retention_gate_state.md",
        """# Retention Gate State

- archive_permission: compress_ready
""",
    )
    _write(
        root / "memory/archive/archive_output_state.md",
        """# Archive Output State

- next_action: summarize_then_compress
""",
    )
    _write(
        root / "memory/archive/archive_queue.md",
        f"""# Archive Queue

## item-2026-04-28-901
- target: owner voice correction should be compressed only after coverage is proven
- status: ready
- reason: summary coverage smoke fixture
{coverage_lines}""",
    )
    _write(root / "memory/archive/compressed.md", "# Compressed Archive\n")
    _write(root / "memory/archive/dormant.md", "# Dormant Archive\n")


def _write_event_sidecars(root: Path, *, include_summary: bool) -> None:
    event_dir = root / "memory/events"
    raw_text = "你刚才那个回复太像接待腔了，我不喜欢。"
    span_text = "太像接待腔了"
    span_start = raw_text.index(span_text)
    raw_events = [
        {
            "event_id": "evt-voice-001",
            "timestamp": CHECKED_AT,
            "source_channel": "owner_private",
            "actor_scope": "owner",
            "raw_text": raw_text,
            "raw_hash": sha256_text(raw_text),
            "privacy_scope": "owner_private",
        }
    ]
    structured_events = [
        {
            "structured_id": "se-voice-001",
            "event_id": "evt-voice-001",
            "event_kind": "owner_voice_correction",
            "turn_mode": "owner_private_visible_turn",
            "allowed_memory_layers": ["self/voice_review", "reflection"],
            "blocked_memory_layers": ["stable_personality_direct_write"],
            "salience": 86,
            "routing_notes": ["voice_candidate", "review_only"],
        }
    ]
    claims = [
        {
            "claim_id": "claim-voice-001",
            "claim_type": "voice_correction",
            "subject": "xinyu_visible_reply_style",
            "predicate": "owner_negative_feedback",
            "object": "customer-service-like reply",
            "status": "review_only",
            "target_memory_layer": "self/voice_review",
            "evidence_event_ids": ["evt-voice-001"],
            "evidence_spans": [
                {
                    "event_id": "evt-voice-001",
                    "text": span_text,
                    "start": span_start,
                    "end": span_start + len(span_text),
                }
            ],
            "confidence": 92,
        }
    ]
    summaries = []
    if include_summary:
        summaries = [
            {
                "summary_id": "summary-voice-001",
                "summary_text": "Owner disliked a customer-service-like reply style.",
                "retained_claim_ids": ["claim-voice-001"],
                "source_event_ids": ["evt-voice-001"],
                "loss_notes": ["full raw wording remains in raw_events.jsonl"],
                "discarded_signals": ["no unrelated chatter in fixture"],
                "blocked_from_discard": ["owner voice correction"],
            }
        ]
    dump_jsonl(event_dir / "raw_events.jsonl", raw_events)
    dump_jsonl(event_dir / "structured_events.jsonl", structured_events)
    dump_jsonl(event_dir / "atomic_claims.jsonl", claims)
    dump_jsonl(event_dir / "summary_views.jsonl", summaries)


def _valid_event_sourced_case() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_archive_ready_state(root, event_sourced=True)
        _write_event_sidecars(root, include_summary=True)
        result = run_archive_commit(root, checked_at=CHECKED_AT, mode="summary_coverage_smoke_valid")
        queue = (root / "memory/archive/archive_queue.md").read_text(encoding="utf-8-sig")
        coverage_state = (root / "memory/events/summary_coverage_state.md").read_text(encoding="utf-8-sig")
        if result["commit_action"] != "committed":
            failures.append(f"valid event-sourced case did not commit: {result}")
        if result["summary_coverage_permission"] != "allowed":
            failures.append(f"valid event-sourced case was not coverage-allowed: {result}")
        if "- status: compressed" not in queue:
            failures.append("valid event-sourced queue item was not marked compressed")
        if "coverage_status: covered" not in coverage_state:
            failures.append("valid event-sourced case did not write covered state")
    return failures


def _missing_summary_case() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_archive_ready_state(root, event_sourced=True)
        _write_event_sidecars(root, include_summary=False)
        result = run_archive_commit(root, checked_at=CHECKED_AT, mode="summary_coverage_smoke_missing")
        queue = (root / "memory/archive/archive_queue.md").read_text(encoding="utf-8-sig")
        compressed = (root / "memory/archive/compressed.md").read_text(encoding="utf-8-sig")
        if result["commit_action"] != "blocked":
            failures.append(f"missing summary case was not blocked: {result}")
        if result["commit_reason"] != "summary_coverage_not_ready":
            failures.append(f"missing summary case had wrong reason: {result}")
        if result["summary_coverage_permission"] != "blocked":
            failures.append(f"missing summary case had wrong coverage permission: {result}")
        if "- status: compressed" in queue:
            failures.append("missing summary case incorrectly marked queue compressed")
        if "source_item: item-2026-04-28-901" in compressed:
            failures.append("missing summary case incorrectly wrote compressed archive")
    return failures


def _legacy_archive_case() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_archive_ready_state(root, event_sourced=False)
        result = run_archive_commit(root, checked_at=CHECKED_AT, mode="summary_coverage_smoke_legacy")
        queue = (root / "memory/archive/archive_queue.md").read_text(encoding="utf-8-sig")
        if result["commit_action"] != "committed":
            failures.append(f"legacy case did not commit: {result}")
        if result["summary_coverage_permission"] != "allowed_legacy":
            failures.append(f"legacy case was not marked allowed_legacy: {result}")
        if "- status: compressed" not in queue:
            failures.append("legacy queue item was not marked compressed")
    return failures


def main() -> int:
    failures: list[str] = []
    failures.extend(_valid_event_sourced_case())
    failures.extend(_missing_summary_case())
    failures.extend(_legacy_archive_case())
    if failures:
        print("Summary coverage smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Summary coverage smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

