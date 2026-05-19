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

LEARNER_TRACKED_FILES = [
    "memory/context/active_questions.md",
    "memory/knowledge/source_materials.md",
    "memory/knowledge/source_integration_gate_state.md",
    "memory/knowledge/learner_integration_state.md",
    "memory/knowledge/general.md",
    "memory/knowledge/source_notes.md",
    "memory/context/question_states.md",
    "memory/context/exploration_queue.md",
]


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_ready_case(root: Path, comparison_status: str = "corroborated", evidence_hosts: int = 2) -> None:
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
- mode: learner_smoke_gate

## Gate Decision
- integration_permission: prepare_only
- gate_reason: smoke_ready_material
- ready_candidates: 1
""",
    )
    _write(
        root / "memory/knowledge/source_materials.md",
        f"""---
title: Source Materials Smoke
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
tags: [knowledge, sources, materials, smoke]
---

# Source Materials

## material-2026-04-24-901
- question_id: q-902
- source_type: curated_public_note
- reliability: medium_ready
- integration_scope: knowledge_only
- status: ready
- comparison_status: {comparison_status}
- evidence_hosts: {evidence_hosts}
- comparison_checked_at: 2026-04-24T00:00:00+08:00
- claim: approach and distance can both be meaningful relationship signals; boundaries should not be treated as rejection by default
""",
    )
    _write(
        root / "memory/context/active_questions.md",
        """---
title: Active Questions Smoke
memory_type: active_questions
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 88
impact_score: 88
confidence_score: 100
status: active
tags: [question, curiosity, exploration, smoke]
---

# Active Questions

## q-902
- created_at: 2026-04-24T00:00:00+08:00
- question: How should approach and distance coexist in a human relationship?
- source_trigger: learner integration smoke
- target: human-relationship
- urgency: medium
- emotional_weight: 70
- status: pending_exploration
- next_action: learner integration
""",
    )
    _write(
        root / "memory/context/question_states.md",
        """---
title: Question States Smoke
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
### q-902
- state: pending_exploration
- reason: smoke question waits for learner integration
""",
    )
    _write(
        root / "memory/context/exploration_queue.md",
        """---
title: Exploration Queue Smoke
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

## item-2026-04-24-901
- question_id: q-902
- status: pending
- exploration_stage: source_gate
- target: human-relationship
- reason: smoke source material is ready for knowledge-only integration
- next_action: learner integration
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate learner integration path with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-integration", action="store_true")
    parser.add_argument("--single-source", action="store_true")
    parser.add_argument("--require-blocked", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    from learner_integration_engine import run_learner_integration

    restore_paths = _discover_restore_files(root, LEARNER_TRACKED_FILES) if args.restore_after else LEARNER_TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in LEARNER_TRACKED_FILES}

    try:
        _prepare_ready_case(
            root,
            comparison_status="single_source" if args.single_source else "corroborated",
            evidence_hosts=1 if args.single_source else 2,
        )
        result = run_learner_integration(root, mode="learner_integration_smoke")
        active_synced = "- status: partially_answered" in (
            root / "memory/context/active_questions.md"
        ).read_text(encoding="utf-8-sig")
        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in LEARNER_TRACKED_FILES}
        changed = _changed_files(before, after)

        print("=== LEARNER INTEGRATION SMOKE ===")
        print("permission:", result["permission"])
        print("ready_materials:", result["ready_materials"])
        print("integrated_materials:", result["integrated_materials"])
        print("integrated_ids:", ", ".join(result["integrated_ids"]) or "none")
        print("skipped_reason:", result["skipped_reason"])
        print("active_question_synced:", "yes" if active_synced else "no")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(LEARNER_TRACKED_FILES)}")
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
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if args.require_integration and (result["integrated_materials"] <= 0 or not active_synced):
        return 4
    if args.require_blocked and result["integrated_materials"] != 0:
        return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
