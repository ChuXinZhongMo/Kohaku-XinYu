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
    "memory/knowledge/source_integration_gate_state.md",
    "memory/knowledge/source_materials.md",
    "memory/knowledge/source_comparison_state.md",
    "memory/knowledge/learner_integration_state.md",
    "memory/knowledge/learning_quality_state.md",
    "memory/knowledge/general.md",
    "memory/knowledge/source_notes.md",
    "memory/context/question_states.md",
    "memory/context/exploration_queue.md",
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


def _append(path: Path, text: str) -> None:
    existing = path.read_text(encoding="utf-8-sig").rstrip()
    path.write_text(existing + "\n\n" + text.strip() + "\n", encoding="utf-8")


def _prepare_base(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_integration_gate_state.md",
        """---
title: Source Integration Gate State
memory_type: source_integration_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 82
impact_score: 81
confidence_score: 100
status: active
tags: [knowledge, integration, gate, smoke]
---

# Source Integration Gate State

## Last Evaluation
- checked_at: 2026-04-24T00:00:00+08:00
- mode: learning_session_gate

## Gate Decision
- integration_permission: prepare_only
- gate_reason: learning_session_smoke
- ready_candidates: 3
""",
    )
    _write(
        root / "memory/knowledge/source_materials.md",
        """---
title: Source Materials Learning Session Smoke
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
tags: [knowledge, learning, session, smoke]
---

# Source Materials
""",
    )
    _write(
        root / "memory/knowledge/general.md",
        """---
title: General Knowledge Learning Session Smoke
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
""",
    )
    _write(
        root / "memory/knowledge/source_notes.md",
        """---
title: Source Notes Learning Session Smoke
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
    _write(
        root / "memory/context/question_states.md",
        """---
title: Question States Learning Session Smoke
memory_type: question_states
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 84
impact_score: 83
confidence_score: 100
status: active
tags: [questions, states, smoke]
---

# Current Question States

## Current Question Entries
### q-910
- state: pending_exploration
- reason: first learning session batch

### q-911
- state: pending_exploration
- reason: second learning session batch
""",
    )
    _write(
        root / "memory/context/exploration_queue.md",
        """---
title: Exploration Queue Learning Session Smoke
memory_type: exploration_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 82
impact_score: 80
confidence_score: 100
status: active
tags: [exploration, queue, smoke]
---

# Exploration Queue

## item-2026-04-24-910
- question_id: q-910
- status: pending
- exploration_stage: source_comparison
- target: relationship-memory
- reason: first learning session batch
- next_action: compare then integrate

## item-2026-04-24-911
- question_id: q-911
- status: pending
- exploration_stage: source_comparison
- target: repeated-source-risk
- reason: second learning session batch
- next_action: compare then integrate
""",
    )


def _append_batch_one(root: Path) -> None:
    _append(
        root / "memory/knowledge/source_materials.md",
        """## material-2026-04-24-910
- question_id: q-910
- url: https://alpha.example/session-one
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Relationship memory can preserve closeness and disappointment together.

## material-2026-04-24-911
- question_id: q-910
- url: https://beta.example/session-one
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Relationship memory can preserve closeness and disappointment without forcing either one to vanish.
""",
    )


def _append_batch_two(root: Path) -> None:
    _append(
        root / "memory/knowledge/source_materials.md",
        """## material-2026-04-24-912
- question_id: q-911
- url: https://alpha.example/session-two-a
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: A repeated source should not become stronger just because it appears often.

## material-2026-04-24-913
- question_id: q-911
- url: https://alpha.example/session-two-b
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: A repeated source should be treated as a quality warning until independent support appears.
""",
    )


def _run_cycle(root: Path, mode: str) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    from learner_integration_engine import run_learner_integration
    from learning_quality_engine import run_learning_quality
    from source_comparison_engine import run_source_comparison

    comparison = run_source_comparison(root, mode=f"{mode}_comparison")
    learner = run_learner_integration(root, mode=f"{mode}_learner")
    quality = run_learning_quality(root, mode=f"{mode}_quality")
    return comparison, learner, quality


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate repeated learning sessions with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-session", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    first_quality = {"quality_grade": "unknown", "learned_entries": 0, "warning_count": 0}
    second_quality = {"quality_grade": "unknown", "learned_entries": 0, "warning_count": 0}
    first_learner = {"integrated_materials": 0}
    second_learner = {"integrated_materials": 0}
    try:
        _prepare_base(root)
        _append_batch_one(root)
        _, first_learner, first_quality = _run_cycle(root, "learning_session_first")
        _append_batch_two(root)
        _, second_learner, second_quality = _run_cycle(root, "learning_session_second")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        print("=== LEARNING SESSION SMOKE ===")
        print("first_integrated_materials:", first_learner["integrated_materials"])
        print("first_quality_grade:", first_quality["quality_grade"])
        print("first_warning_count:", first_quality["warning_count"])
        print("second_integrated_materials:", second_learner["integrated_materials"])
        print("second_quality_grade:", second_quality["quality_grade"])
        print("second_learned_entries:", second_quality["learned_entries"])
        print("second_warning_count:", second_quality["warning_count"])
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

    if args.require_session and (
        int(first_learner["integrated_materials"]) != 2
        or first_quality["quality_grade"] != "stable"
        or int(second_learner["integrated_materials"]) != 2
        or second_quality["quality_grade"] not in {"caution", "review_needed"}
        or int(second_quality["warning_count"]) <= 0
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
