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

ARCHIVE_COMMIT_TRACKED_FILES = [
    "memory/archive/archive_queue.md",
    "memory/archive/compressed.md",
    "memory/archive/dormant.md",
    "memory/archive/retention_gate_state.md",
    "memory/archive/archive_output_state.md",
    "memory/archive/archive_commit_state.md",
    "memory/reflection/consolidation_state.md",
    "memory/reflection/reflection_queue.md",
    "memory/dreams/dream_seeds.md",
    "memory/dreams/dream_weight_state.md",
    "memory/archive/long_term_memory_gate_state.md",
]


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_ready_case(root: Path) -> None:
    _write(
        root / "memory/reflection/reflection_queue.md",
        """---
title: Reflection Queue
memory_type: reflection_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [reflection, queue, smoke]
---

# Waiting Reflection Topics

- none
""",
    )
    _write(
        root / "memory/dreams/dream_seeds.md",
        """---
title: Dream Seeds
memory_type: dream_seeds
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
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
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [dream, weight, smoke]
---

# Dream Weight State

## 权重变化
- weight_before: 0
- weight_after: 0
- weight_delta: 0
- weight_effect: none
- relationship_effect: none
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
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [archive, queue, smoke]
---

# Current Archive Candidates

## item-2026-04-24-901
- target: smoke test archival candidate after residue has cleared
- status: ready
- reason: isolated smoke case proves archive commit can compress without touching live relationship memory
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate archive commit compression path with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-commit", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from archive_commit_engine import run_archive_commit
    from archive_output_engine import run_archive_output
    from consolidation_engine import run_consolidation
    from long_term_memory_gate_engine import run_long_term_memory_gate
    from retention_gate_engine import run_retention_gate

    restore_paths = _discover_restore_files(root, ARCHIVE_COMMIT_TRACKED_FILES) if args.restore_after else ARCHIVE_COMMIT_TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in ARCHIVE_COMMIT_TRACKED_FILES}

    try:
        _prepare_ready_case(root)
        consolidation = run_consolidation(root, mode="archive_commit_smoke_consolidation")
        long_term = run_long_term_memory_gate(root, mode="archive_commit_smoke_long_term_memory_gate")
        retention = run_retention_gate(root, mode="archive_commit_smoke_retention")
        archive_output = run_archive_output(root, mode="archive_commit_smoke_output")
        commit = run_archive_commit(root, mode="archive_commit_smoke_commit")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in ARCHIVE_COMMIT_TRACKED_FILES}
        changed = _changed_files(before, after)

        print("=== ARCHIVE COMMIT SMOKE ===")
        print("consolidation_priority:", consolidation["coordination"])
        print("long_term_memory_action:", long_term["memory_action"])
        print("long_term_compression_permission:", long_term["compression_permission"])
        print("retention_permission:", retention["archive_permission"])
        print("archive_next_action:", archive_output["next_action"])
        print("commit_action:", commit["commit_action"])
        print("commit_reason:", commit["commit_reason"])
        print("committed_items:", commit["committed_items"])
        print("committed_item_ids:", ", ".join(commit["committed_item_ids"]) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(ARCHIVE_COMMIT_TRACKED_FILES)}")
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

    if args.require_commit and commit["committed_items"] <= 0:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
