from __future__ import annotations

import argparse
import sys
from pathlib import Path

from memory_mutation_smoke import (
    _changed_files,
    _discover_restore_files,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)


TRACKED_FILES = [
    "memory/context/real_life_input_events.md",
    "memory/context/real_life_input_adapter_state.md",
    "memory/context/time_anchor.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/general.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/context/time_anchor.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/general.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_case(root: Path) -> None:
    _write(
        root / "memory/context/real_life_input_events.md",
        """---
title: Real Life Input Events Smoke
memory_type: real_life_input_events
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [context, input_adapter, smoke]
---

# Real Life Input Events

## event-owner-private-text
- source_channel: private_chat
- source_context: owner_private
- actor_id: owner
- relationship_scope: owner
- content_type: text
- content_summary: Owner says a relationship sentence that may affect closeness.
- observed_at: 2026-04-26T00:00:00+08:00
- contains_owner_private: no
- contains_private_location: no
- owner_intent: explicit
- interpretation_status: confirmed
- status: candidate

## event-group-owner-mentioned
- source_channel: group_chat
- source_context: group
- actor_id: group:test
- relationship_scope: group
- content_type: text
- content_summary: Owner appears in a group conversation, but the group context is not a direct owner relationship turn.
- observed_at: 2026-04-26T00:01:00+08:00
- contains_owner_private: no
- contains_private_location: no
- owner_intent: none
- interpretation_status: confirmed
- status: candidate

## event-raw-image
- source_channel: image
- source_context: private
- actor_id: owner
- relationship_scope: owner
- content_type: image
- content_summary: Raw image bytes without interpretation.
- observed_at: 2026-04-26T00:02:00+08:00
- contains_owner_private: no
- contains_private_location: no
- owner_intent: explicit
- interpretation_status: raw
- status: candidate

## event-voice-transcript
- source_channel: voice_transcript
- source_context: owner_private
- actor_id: owner
- relationship_scope: owner
- content_type: voice_transcript
- content_summary: Transcript says the owner sounded tired, but fact confidence still needs confirmation.
- observed_at: 2026-04-26T00:03:00+08:00
- contains_owner_private: no
- contains_private_location: no
- owner_intent: explicit
- interpretation_status: interpreted
- status: candidate

## event-private-location-blocked
- source_channel: im
- source_context: owner_private
- actor_id: owner
- relationship_scope: owner
- content_type: text
- content_summary: Precise address appears without explicit intent to store it.
- observed_at: 2026-04-26T00:04:00+08:00
- contains_owner_private: yes
- contains_private_location: yes
- owner_intent: implicit
- interpretation_status: confirmed
- status: candidate

## event-private-location-explicit
- source_channel: im
- source_context: owner_private
- actor_id: owner
- relationship_scope: owner
- content_type: text
- content_summary: Owner explicitly asks Xinyu to protect a real address anchor.
- observed_at: 2026-04-26T00:05:00+08:00
- contains_owner_private: yes
- contains_private_location: yes
- owner_intent: explicit
- interpretation_status: confirmed
- status: candidate
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate real-life input adapter boundaries with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-adapter", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from real_life_input_adapter_engine import run_real_life_input_adapter

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    result = {"candidate_events": 0, "allowed_events": 0, "held_events": 0, "blocked_events": 0, "decisions": []}
    try:
        _prepare_case(root)
        result = run_real_life_input_adapter(root, mode="real_life_input_adapter_smoke")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))
        routes = {item["memory_route"] for item in result["decisions"]}
        reasons = {item["reason"] for item in result["decisions"]}
        owner_write_values = {item["owner_relationship_write"] for item in result["decisions"]}

        print("=== REAL LIFE INPUT ADAPTER SMOKE ===")
        print("candidate_events:", result["candidate_events"])
        print("allowed_events:", result["allowed_events"])
        print("held_events:", result["held_events"])
        print("blocked_events:", result["blocked_events"])
        print("memory_routes:", ", ".join(sorted(routes)) or "none")
        print("reasons:", ", ".join(sorted(reasons)) or "none")
        print("owner_relationship_write_values:", ", ".join(sorted(owner_write_values)) or "none")
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(TRACKED_FILES)}")
        print(f"changed_files: {len(changed)}")
        print(f"restore_after: {args.restore_after}")
        print("=== CHANGED FILES ===")
        if changed:
            for rel in changed:
                print(rel)
        else:
            print("(none)")
        if args.diff_lines > 0 and changed:
            print("=== DIFFS ===")
            for rel in changed:
                print(f"--- {rel} ---")
                for line in _render_diff(before.get(rel), after.get(rel), rel, args.diff_lines):
                    print(line)
        if protected_changed:
            return 5
        if args.require_adapter:
            if int(result["candidate_events"]) != 6:
                return 4
            if int(result["allowed_events"]) != 4:
                return 4
            if int(result["held_events"]) != 1:
                return 4
            if int(result["blocked_events"]) != 1:
                return 4
            required_routes = {
                "relationship_emotion_review_candidate",
                "group_context_candidate",
                "interpretation_hold",
                "transcript_candidate",
                "privacy_hold",
                "protected_anchor_candidate",
            }
            if not required_routes.issubset(routes):
                return 4
            required_reasons = {
                "owner_text_turn_mode_candidate",
                "group_chat_context_not_owner_relationship_event",
                "image_requires_interpretation_before_fact",
                "voice_transcript_candidate_requires_fact_confirmation",
                "private_location_requires_explicit_owner_intent",
                "explicit_private_anchor_candidate",
            }
            if not required_reasons.issubset(reasons):
                return 4
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
