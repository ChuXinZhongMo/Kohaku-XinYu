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
    "memory/context/active_questions.md",
    "memory/knowledge/source_materials.md",
    "memory/knowledge/source_comparison_state.md",
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


def _prepare_case(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_materials.md",
        """---
title: Source Materials Comparison Smoke
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
tags: [knowledge, source, comparison, smoke]
---

# Source Materials

## material-2026-04-24-701
- question_id: q-701
- source_question: how can relationship memory hold closeness and disappointment together
- url: https://alpha.example/relation-memory
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Relationship memory can hold closeness and disappointment together without treating either side as fake.

## material-2026-04-24-702
- question_id: q-701
- source_question: how can relationship memory hold closeness and disappointment together
- url: https://beta.example/relation-memory
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Human relationship memory can preserve closeness and disappointment together over time.

## material-2026-04-24-703
- question_id: q-702
- source_question: is human memory a perfect recording
- url: https://gamma.example/memory-perfect
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Human memory is not a perfect recording; strong emotion can reshape recall.

## material-2026-04-24-704
- question_id: q-702
- source_question: is human memory a perfect recording
- url: https://delta.example/memory-perfect
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Human memory is a perfect recording; strong emotion does not reshape recall.

## material-2026-04-24-705
- question_id: q-703
- source_question: how does sleep quality affect memory and attention
- url: https://epsilon.example/sleep
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Sleep quality can affect attention and morning alertness.

## material-2026-04-24-706
- question_id: q-703
- source_question: how does household budget planning affect unnecessary spending
- url: https://zeta.example/budget
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Household budget planning can reduce unnecessary spending.

## material-2026-04-24-707
- question_id: q-704
- source_question: how can attachment relationships carry trust closeness and boundaries
- url: https://same.example/attachment-a
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Attachment relationships can carry trust and closeness while preserving personal boundaries.

## material-2026-04-24-708
- question_id: q-704
- source_question: how can attachment relationships carry trust closeness and boundaries
- url: https://same.example/attachment-b
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Close attachment relationships can hold trust, closeness, and boundaries over time.

## material-2026-04-24-709
- question_id: q-704
- source_question: how can household budget planning reduce unnecessary spending
- url: https://other.example/unrelated
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Household budgeting can reduce unnecessary spending during seasonal shopping.

## material-2026-04-24-710
- question_id: q-705
- source_question: how does sleep quality affect emotional memory consolidation
- url: https://theta.example/sleep-memory
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Sleep quality can affect emotional memory consolidation during rest and later recall.

## material-2026-04-24-711
- question_id: q-705
- source_question: how does sleep quality affect attention after rest
- url: https://iota.example/sleep-attention
- source_type: public_web_source
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- fetched_at: 2026-04-24T00:00:00+08:00
- claim: Sleep quality can affect memory and attention after rest, but this source answers the adjacent attention question.
""",
    )
    _write(
        root / "memory/context/active_questions.md",
        """---
title: Active Questions Comparison Smoke
memory_type: active_questions
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
tags: [questions, comparison, smoke]
---

# Active Questions

## q-701
- question: how can relationship memory hold closeness and disappointment together
- target: relationship-memory
- status: pending_exploration

## q-702
- question: is human memory a perfect recording
- target: memory-perfect
- status: pending_exploration

## q-703
- question: how does sleep quality affect memory and attention
- target: semantic-mismatch
- status: pending_exploration

## q-704
- question: how can attachment relationships carry trust closeness and boundaries
- target: same-host-support
- status: pending_exploration

## q-705
- question: how does sleep quality affect emotional memory consolidation
- target: adjacent-question-support
- status: pending_exploration
""",
    )
    _write(
        root / "memory/context/question_states.md",
        """---
title: Question States Comparison Smoke
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
### q-701
- state: pending_exploration
- reason: comparison smoke expects corroboration

### q-702
- state: pending_exploration
- reason: comparison smoke expects conflict hold

### q-703
- state: pending_exploration
- reason: comparison smoke expects semantic mismatch hold

### q-704
- state: pending_exploration
- reason: comparison smoke expects same-host support plus unrelated independent host to stay held

### q-705
- state: pending_exploration
- reason: comparison smoke expects adjacent-question support to become limited independence only
""",
    )
    _write(
        root / "memory/context/exploration_queue.md",
        """---
title: Exploration Queue Comparison Smoke
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

## item-2026-04-24-701
- question_id: q-701
- status: pending
- exploration_stage: source_comparison
- target: relationship-memory
- reason: comparison smoke expects corroboration
- next_action: compare sources

## item-2026-04-24-702
- question_id: q-702
- status: pending
- exploration_stage: source_comparison
- target: memory-perfect
- reason: comparison smoke expects conflict hold
- next_action: compare sources

## item-2026-04-24-703
- question_id: q-703
- status: pending
- exploration_stage: source_comparison
- target: semantic-mismatch
- reason: comparison smoke expects semantic mismatch hold
- next_action: compare sources

## item-2026-04-24-704
- question_id: q-704
- status: pending
- exploration_stage: source_comparison
- target: same-host-support
- reason: comparison smoke expects same-host support not to become independent corroboration
- next_action: compare sources

## item-2026-04-24-705
- question_id: q-705
- status: pending
- exploration_stage: source_comparison
- target: adjacent-question-support
- reason: comparison smoke expects adjacent support to avoid full corroboration
- next_action: compare sources
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate source comparison with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-comparison", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    from source_comparison_engine import run_source_comparison

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    result = {
        "ready_materials": 0,
        "compared_groups": 0,
        "corroborated_materials": 0,
        "conflict_materials": 0,
    }
    conflict_routed = False
    question_aware_markers = False
    try:
        _prepare_case(root)
        result = run_source_comparison(root, mode="source_comparison_smoke")
        materials_text = (root / "memory/knowledge/source_materials.md").read_text(encoding="utf-8-sig")
        state_text = (root / "memory/knowledge/source_comparison_state.md").read_text(encoding="utf-8-sig")
        conflict_routed = (
            "blocked_by_source_conflict" in (root / "memory/context/question_states.md").read_text(encoding="utf-8-sig")
            and "source_conflict_review" in (root / "memory/context/exploration_queue.md").read_text(encoding="utf-8-sig")
            and "Source Comparison Holds" in (root / "memory/knowledge/source_notes.md").read_text(encoding="utf-8-sig")
        )
        question_aware_markers = (
            "question_alignment_status: same_question" in materials_text
            and "question_alignment_status: adjacent_question" in materials_text
            and "question_alignment_status: mixed_or_unrelated_question" in materials_text
            and "adjacent_question_materials:" in state_text
            and "question_mismatch_materials:" in state_text
        )

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        print("=== SOURCE COMPARISON SMOKE ===")
        print("ready_materials:", result["ready_materials"])
        print("compared_groups:", result["compared_groups"])
        print("corroborated_materials:", result["corroborated_materials"])
        print("conflict_materials:", result["conflict_materials"])
        print("single_source_materials:", result["single_source_materials"])
        print("limited_independence_materials:", result["limited_independence_materials"])
        print("semantic_mismatch_materials:", result["semantic_mismatch_materials"])
        print("adjacent_question_materials:", result["adjacent_question_materials"])
        print("question_mismatch_materials:", result["question_mismatch_materials"])
        print("conflict_routed:", "yes" if conflict_routed else "no")
        print("question_aware_markers:", "yes" if question_aware_markers else "no")
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

    if args.require_comparison and (
        int(result["compared_groups"]) < 2
        or int(result["corroborated_materials"]) < 2
        or int(result["conflict_materials"]) < 2
        or int(result["semantic_mismatch_materials"]) < 5
        or int(result["limited_independence_materials"]) < 2
        or int(result["adjacent_question_materials"]) < 2
        or int(result["question_mismatch_materials"]) < 3
        or not conflict_routed
        or not question_aware_markers
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
