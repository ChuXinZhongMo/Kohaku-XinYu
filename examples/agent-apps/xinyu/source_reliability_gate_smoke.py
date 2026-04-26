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

SOURCE_RELIABILITY_TRACKED_FILES = [
    "memory/knowledge/source_gate_state.md",
    "memory/knowledge/source_reliability_state.md",
    "memory/knowledge/source_integration_gate_state.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_source_gate(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_gate_state.md",
        """---
title: Source Gate State Smoke
memory_type: source_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 79
impact_score: 79
confidence_score: 100
status: active
tags: [knowledge, source_gate, smoke]
---

# Source Gate State

## Last Evaluation
- checked_at: 2026-04-25T00:00:00+08:00
- mode: source_reliability_gate_smoke_gate

## Current Candidates
- q-910: human-relationship
- q-911: memory-emotion
- q-912: unstable-rumor
- q-913: ai-self-understanding
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate source reliability and integration gates with restore."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from source_integration_gate_engine import run_source_integration_gate
    from source_reliability_engine import run_source_reliability

    restore_paths = (
        _discover_restore_files(root, SOURCE_RELIABILITY_TRACKED_FILES)
        if args.restore_after
        else SOURCE_RELIABILITY_TRACKED_FILES
    )
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in SOURCE_RELIABILITY_TRACKED_FILES}

    reliability_result = {"candidate_count": 0, "pairs": []}
    integration_result = {
        "integration_permission": "unknown",
        "ready_candidates": 0,
        "source_gate_candidates": 0,
        "reliability_ready": 0,
    }
    failures: list[str] = []

    try:
        _prepare_source_gate(root)
        reliability_result = run_source_reliability(
            root, mode="source_reliability_gate_smoke_reliability"
        )
        integration_result = run_source_integration_gate(
            root, mode="source_reliability_gate_smoke_integration"
        )

        pair_map = {qid: level for qid, _, level in reliability_result["pairs"]}
        if reliability_result["candidate_count"] != 4:
            failures.append("source_reliability did not read all source-gate candidates")
        if pair_map.get("q-910") != "medium_ready":
            failures.append("q-910 was not marked medium_ready")
        if pair_map.get("q-911") != "medium_ready":
            failures.append("q-911 was not marked medium_ready")
        if pair_map.get("q-912") != "unknown":
            failures.append("q-912 was not kept unknown")
        if pair_map.get("q-913") != "high_ready":
            failures.append("q-913 was not marked high_ready")
        if integration_result["integration_permission"] != "prepare_only":
            failures.append("source_integration_gate did not open prepare_only")
        if int(integration_result["ready_candidates"]) != 3:
            failures.append("source_integration_gate ready_candidates should be 3")
        if int(integration_result["source_gate_candidates"]) != 4:
            failures.append("source_integration_gate source_gate_candidates should be 4")
        if int(integration_result["reliability_ready"]) != 3:
            failures.append("source_integration_gate reliability_ready should be 3")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in SOURCE_RELIABILITY_TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== SOURCE RELIABILITY GATE SMOKE ===")
        print("source_reliability_candidates:", reliability_result["candidate_count"])
        print(
            "source_reliability_pairs:",
            ", ".join(
                f"{qid}:{target}:{level}"
                for qid, target, level in reliability_result["pairs"]
            )
            or "none",
        )
        print("integration_permission:", integration_result["integration_permission"])
        print("ready_candidates:", integration_result["ready_candidates"])
        print("source_gate_candidates:", integration_result["source_gate_candidates"])
        print("reliability_ready:", integration_result["reliability_ready"])
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(SOURCE_RELIABILITY_TRACKED_FILES)}")
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
            for item in failures:
                print("-", item)
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if failures:
        return 5
    if args.require_ready and (
        integration_result["integration_permission"] != "prepare_only"
        or int(integration_result["ready_candidates"]) != 3
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
