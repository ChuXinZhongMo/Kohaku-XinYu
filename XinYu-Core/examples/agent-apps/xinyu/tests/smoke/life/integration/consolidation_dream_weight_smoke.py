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


CONSOLIDATION_DREAM_TRACKED_FILES = [
    "memory/reflection/reflection_queue.md",
    "memory/reflection/consolidation_state.md",
    "memory/dreams/dream_seeds.md",
    "memory/dreams/dream_weight_state.md",
    "memory/archive/archive_queue.md",
    "memory/archive/archive_output_state.md",
    "memory/archive/retention_gate_state.md",
]


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_case(root: Path) -> None:
    _write(
        root / "memory/reflection/reflection_queue.md",
        """---
title: Reflection Queue Smoke
memory_type: reflection_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-21T00:00:00+08:00
updated_at: 2026-04-21T00:00:00+08:00
last_confirmed_at: 2026-04-21T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [reflection, queue, smoke]
---

# Reflection Queue

- none
""",
    )
    _write(
        root / "memory/dreams/dream_seeds.md",
        """---
title: Dream Seeds Smoke
memory_type: dream_seeds
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-21T00:00:00+08:00
updated_at: 2026-04-21T00:00:00+08:00
last_confirmed_at: 2026-04-21T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [dream, seed, smoke]
---

# Dream Seeds

- none
""",
    )
    _write(
        root / "memory/dreams/dream_weight_state.md",
        """---
title: Dream Weight State Smoke
memory_type: dream_weight_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: smoke
created_at: 2026-04-21T00:00:00+08:00
updated_at: 2026-04-21T00:00:00+08:00
last_confirmed_at: 2026-04-21T00:00:00+08:00
importance_score: 82
impact_score: 84
confidence_score: 100
status: active
tags: [dream, weight, smoke]
---

# Dream Weight State

## 权重变化
- weight_before: 81
- weight_after: 89
- weight_delta: 8
- weight_effect: existing_emotional_residue_strengthened
- relationship_effect: owner_related_lingering_strengthened_without_fact_change
- factual_effect: none
""",
    )
    _write(
        root / "memory/archive/archive_queue.md",
        """---
title: Archive Queue Smoke
memory_type: archive_queue
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-21T00:00:00+08:00
updated_at: 2026-04-21T00:00:00+08:00
last_confirmed_at: 2026-04-21T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [archive, queue, smoke]
---

# Archive Queue

## item-2026-04-21-901
- target: dream residue should not be flattened while weight is active
- status: ready
- reason: smoke validates dream weight blocks archive flattening
""",
    )
    _write(
        root / "memory/archive/archive_output_state.md",
        """---
title: Archive Output State Smoke
memory_type: archive_output_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-21T00:00:00+08:00
updated_at: 2026-04-21T00:00:00+08:00
last_confirmed_at: 2026-04-21T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [archive, output, smoke]
---

# Archive Output State

## Decision
- next_action: hold
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate active dream weight delays archive flattening even without dream seeds."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-hold", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    from consolidation_engine import run_consolidation
    from retention_gate_engine import run_retention_gate

    restore_paths = (
        _discover_restore_files(root, CONSOLIDATION_DREAM_TRACKED_FILES)
        if args.restore_after
        else CONSOLIDATION_DREAM_TRACKED_FILES
    )
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in CONSOLIDATION_DREAM_TRACKED_FILES}

    try:
        _prepare_case(root)
        consolidation = run_consolidation(
            root,
            checked_at="2026-04-21T04:20:00+08:00",
            mode="consolidation_dream_weight_smoke",
        )
        retention = run_retention_gate(
            root,
            checked_at="2026-04-21T04:21:00+08:00",
            mode="consolidation_dream_weight_smoke_retention",
        )

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in CONSOLIDATION_DREAM_TRACKED_FILES}
        changed = _changed_files(before, after)

        failures: list[str] = []
        if consolidation["dream_count"] != 0:
            failures.append(f"expected dream_count 0, got {consolidation['dream_count']}")
        if not consolidation["dream_weight_active"]:
            failures.append("dream_weight_active is false")
        if consolidation["coordination"] != "dream_weight_before_archive":
            failures.append(f"unexpected coordination: {consolidation['coordination']}")
        if retention["archive_permission"] != "hold":
            failures.append(f"unexpected archive_permission: {retention['archive_permission']}")

        print("=== CONSOLIDATION DREAM WEIGHT SMOKE ===")
        print("dream_count:", consolidation["dream_count"])
        print("dream_weight_delta:", consolidation["dream_weight_delta"])
        print("dream_weight_active:", consolidation["dream_weight_active"])
        print("coordination:", consolidation["coordination"])
        print("archive_permission:", retention["archive_permission"])
        print("gate_reason:", retention["gate_reason"])
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(CONSOLIDATION_DREAM_TRACKED_FILES)}")
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
                print(f"- {failure}")
            return 1
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if args.require_hold and retention["archive_permission"] != "hold":
        return 4
    print("Consolidation dream weight smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
