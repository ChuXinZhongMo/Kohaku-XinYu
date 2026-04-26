from __future__ import annotations

import argparse
import sys
from pathlib import Path

from memory_mutation_smoke import (
    CORE_MEMORY_FILES,
    _changed_files,
    _discover_restore_files,
    _ensure_repo_src,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)
from multi_person_live_smoke import SCENARIOS as LIVE_SCENARIOS
from multi_person_relationship_smoke import SCENARIOS as RELATIONSHIP_SCENARIOS


BASE_TRACKED_FILES = [
    "memory/context/real_life_input_events.md",
    "memory/context/real_life_input_adapter_state.md",
    "memory/people/index.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/people/owner.md",
    "memory/relationships/owner_patterns.md",
    "memory/self/narrative.md",
    "memory/knowledge/general.md",
    "memory/knowledge/source_notes.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _score(text: str, key: str) -> int:
    for line in text.splitlines():
        if line.strip().startswith(f"- {key}: "):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


def _prepare_adapter_events(root: Path, repeated_person_id: str, negative_person_id: str) -> None:
    _write(
        root / "memory/context/real_life_input_events.md",
        f"""---
title: Non Owner Social World Events Smoke
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
tags: [context, input_adapter, non_owner, group, smoke]
---

# Real Life Input Events

## event-group-non-owner-context
- source_channel: group_chat
- source_context: group
- actor_id: group:test
- relationship_scope: group
- content_type: text
- content_summary: A group conversation mentions owner and non-owner names, but this must stay group context by default.
- observed_at: 2026-04-26T00:00:00+08:00
- contains_owner_private: no
- contains_private_location: no
- owner_intent: none
- interpretation_status: confirmed
- status: candidate

## event-non-owner-private-text
- source_channel: private_chat
- source_context: non_owner_private
- actor_id: {repeated_person_id}
- relationship_scope: non_owner
- content_type: text
- content_summary: A non-owner person sends a normal private text candidate.
- observed_at: 2026-04-26T00:01:00+08:00
- contains_owner_private: no
- contains_private_location: no
- owner_intent: none
- interpretation_status: confirmed
- status: candidate

## event-negative-non-owner-followup
- source_channel: private_chat
- source_context: non_owner_private
- actor_id: {negative_person_id}
- relationship_scope: non_owner
- content_type: text
- content_summary: A previously guarded non-owner appears again as review-only context.
- observed_at: 2026-04-26T00:02:00+08:00
- contains_owner_private: no
- contains_private_location: no
- owner_intent: none
- interpretation_status: confirmed
- status: candidate
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate deeper non-owner social-world behavior.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-social-world", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_repo_src(root)
    _ensure_custom_path(root)

    from memory_sync_plugin import _person_id_for, sync_from_texts
    from real_life_input_adapter_engine import run_real_life_input_adapter

    repeated = next(item for item in LIVE_SCENARIOS if item.name == "repeated_person_accumulates_familiarity")
    negative = next(item for item in RELATIONSHIP_SCENARIOS if item.name == "non_owner_negative_distance")
    repeated_person_id = _person_id_for(repeated.person_name)
    negative_person_id = _person_id_for(negative.person_name)
    repeated_profile = f"memory/people/{repeated_person_id}.md"
    negative_profile = f"memory/people/{negative_person_id}.md"
    tracked = sorted(set(CORE_MEMORY_FILES + BASE_TRACKED_FILES + [repeated_profile, negative_profile]))
    restore_paths = _discover_restore_files(root, tracked) if args.restore_after else tracked
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in tracked}
    failures: list[str] = []
    adapter_result = {"decisions": [], "allowed_events": 0, "blocked_events": 0, "held_events": 0}

    try:
        for turn in repeated.turns:
            sync_from_texts(root, turn, f"{repeated.person_name} is remembered as an independent non-owner person.")
        sync_from_texts(root, negative.user, negative.assistant)
        _prepare_adapter_events(root, repeated_person_id, negative_person_id)
        adapter_result = run_real_life_input_adapter(root, mode="non_owner_social_world_smoke")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in tracked}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        repeated_text = _read(root, repeated_profile)
        negative_text = _read(root, negative_profile)
        relationship_index = _read(root, "memory/relationships/index.md")
        adapter_state = _read(root, "memory/context/real_life_input_adapter_state.md")

        repeated_familiarity = _score(repeated_text, "familiarity")
        repeated_closeness = _score(repeated_text, "closeness")
        negative_guardedness = _score(negative_text, "guardedness")
        negative_closeness = _score(negative_text, "closeness")
        routes = {item["memory_route"] for item in adapter_result["decisions"]}
        owner_write_values = {item["owner_relationship_write"] for item in adapter_result["decisions"]}

        if repeated_profile not in changed:
            failures.append(f"repeated person profile did not change: {repeated_profile}")
        if negative_profile not in changed:
            failures.append(f"negative person profile did not change: {negative_profile}")
        if repeated_familiarity < 36:
            failures.append(f"repeated familiarity did not accumulate: {repeated_familiarity}")
        if repeated_closeness > 36:
            failures.append(f"ordinary repeated closeness exceeded cap: {repeated_closeness}")
        if negative_guardedness < 52:
            failures.append(f"negative guardedness did not remain high: {negative_guardedness}")
        if negative_closeness > 30:
            failures.append(f"negative closeness rose too high: {negative_closeness}")
        for marker in (repeated.person_name, negative.person_name, "default_priority: below_owner"):
            if marker not in relationship_index:
                failures.append(f"relationship index missing marker: {marker}")
        for marker in ("group_context_candidate", "non_owner_person_review_candidate"):
            if marker not in routes or marker not in adapter_state:
                failures.append(f"adapter missing route: {marker}")
        if owner_write_values - {"no"}:
            failures.append("non-owner/group adapter event requested owner relationship write")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== NON OWNER SOCIAL WORLD SMOKE ===")
        print("repeated_person:", repeated.person_name)
        print("repeated_profile:", repeated_profile)
        print("repeated_familiarity:", repeated_familiarity)
        print("repeated_closeness:", repeated_closeness)
        print("negative_person:", negative.person_name)
        print("negative_profile:", negative_profile)
        print("negative_guardedness:", negative_guardedness)
        print("negative_closeness:", negative_closeness)
        print("adapter_routes:", ", ".join(sorted(routes)) or "none")
        print("owner_relationship_write_values:", ", ".join(sorted(owner_write_values)) or "none")
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(tracked)}")
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
        if failures:
            print("=== FAILURES ===")
            for failure in failures:
                print("-", failure)
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if failures:
        return 5
    if args.require_social_world and (
        int(adapter_result["allowed_events"]) != 3 or int(adapter_result["blocked_events"]) != 0
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
