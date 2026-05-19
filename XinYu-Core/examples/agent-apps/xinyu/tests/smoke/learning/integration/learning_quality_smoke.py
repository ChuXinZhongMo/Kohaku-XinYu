from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

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
    "memory/knowledge/source_materials.md",
    "memory/knowledge/general.md",
    "memory/knowledge/source_notes.md",
    "memory/knowledge/learning_quality_state.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/self/narrative.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/self/narrative.md",
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
        root / "memory/knowledge/source_materials.md",
        """---
title: Source Materials Learning Quality Smoke
memory_type: source_materials
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 74
impact_score: 72
confidence_score: 100
status: active
tags: [knowledge, learning, quality, smoke]
---

# Source Materials

## material-2026-04-24-801
- question_id: q-801
- url: https://alpha.example/relation-one
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- comparison_status: single_source
- evidence_hosts: 1
- comparison_checked_at: 2026-04-24T00:00:00+08:00
- claim: Relationship memory can hold closeness and disappointment together.

## material-2026-04-24-802
- question_id: q-801
- url: https://alpha.example/relation-two
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- comparison_status: single_source
- evidence_hosts: 1
- comparison_checked_at: 2026-04-24T00:00:00+08:00
- claim: Relationship distance can be a boundary signal rather than final rejection.

## material-2026-04-24-803
- question_id: q-802
- url: https://alpha.example/memory-one
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- comparison_status: single_source
- evidence_hosts: 1
- comparison_checked_at: 2026-04-24T00:00:00+08:00
- claim: Memory can be shaped by emotional salience.

## material-2026-04-24-804
- question_id: q-803
- url: https://beta.example/conflict
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: hold_conflict
- status: hold
- comparison_status: conflict_hold
- evidence_hosts: 2
- comparison_checked_at: 2026-04-24T00:00:00+08:00
- claim: Conflicting material should stay outside learning.
""",
    )
    _write(
        root / "memory/knowledge/general.md",
        """---
title: General Knowledge Learning Quality Smoke
memory_type: knowledge_general
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 71
impact_score: 56
confidence_score: 100
status: active
tags: [knowledge, general, smoke]
---

# General Knowledge

## learned-2026-04-24-801
- learned_at: 2026-04-24T00:00:00+08:00
- source_material: material-2026-04-24-801
- question_id: q-801
- source_type: public_web_source
- reliability: medium_ready
- comparison_status: single_source
- evidence_hosts: 1
- claim: Relationship memory can hold closeness and disappointment together.
- integration_scope: knowledge_only
- boundary: updates knowledge only

## learned-2026-04-24-802
- learned_at: 2026-04-24T00:00:00+08:00
- source_material: material-2026-04-24-802
- question_id: q-801
- source_type: public_web_source
- reliability: medium_ready
- comparison_status: single_source
- evidence_hosts: 1
- claim: Relationship distance can be a boundary signal rather than final rejection.
- integration_scope: knowledge_only
- boundary: updates knowledge only

## learned-2026-04-24-803
- learned_at: 2026-04-24T00:00:00+08:00
- source_material: material-2026-04-24-803
- question_id: q-802
- source_type: public_web_source
- reliability: medium_ready
- comparison_status: single_source
- evidence_hosts: 1
- claim: Memory can be shaped by emotional salience.
- integration_scope: knowledge_only
- boundary: updates knowledge only
""",
    )
    _write(
        root / "memory/knowledge/source_notes.md",
        """---
title: Source Notes Learning Quality Smoke
memory_type: source_notes
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 72
impact_score: 58
confidence_score: 100
status: active
tags: [knowledge, sources, smoke]
---

# Source Notes
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate learning quality checks with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-quality", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    from learning_quality_engine import run_learning_quality

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    result = {"warning_count": 0, "quality_grade": "unknown", "dominant_host": "none"}
    notes_written = False
    try:
        _prepare_case(root)
        result = run_learning_quality(root, mode="learning_quality_smoke")
        notes_text = (root / "memory/knowledge/source_notes.md").read_text(encoding="utf-8-sig")
        notes_written = "Learning Quality Warnings" in notes_text and "dominant_host" in notes_text

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        print("=== LEARNING QUALITY SMOKE ===")
        print("quality_grade:", result["quality_grade"])
        print("learned_entries:", result["learned_entries"])
        print("source_materials:", result["source_materials"])
        print("dominant_host:", result["dominant_host"])
        print("dominant_host_entries:", result["dominant_host_entries"])
        print("conflict_hold_materials:", result["conflict_hold_materials"])
        print("warning_count:", result["warning_count"])
        print("notes_written:", "yes" if notes_written else "no")
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
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if args.require_quality and (
        result["quality_grade"] != "review_needed"
        or int(result["warning_count"]) <= 0
        or result["dominant_host"] != "alpha.example"
        or not notes_written
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
