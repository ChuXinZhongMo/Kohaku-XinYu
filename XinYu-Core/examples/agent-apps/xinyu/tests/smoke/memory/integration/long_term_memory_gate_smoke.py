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
    "memory/archive/archive_queue.md",
    "memory/archive/long_term_memory_gate_state.md",
    "memory/archive/compressed.md",
    "memory/archive/dormant.md",
    "memory/reflection/reflection_queue.md",
    "memory/reflection/growth_log.md",
    "memory/dreams/dream_weight_state.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/knowledge/general.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/knowledge/general.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_active_residue_case(root: Path) -> None:
    _write(
        root / "memory/archive/archive_queue.md",
        """---
title: Long Term Gate Archive Queue Smoke
memory_type: archive_queue
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [archive, queue, smoke]
---

# Archive Queue

## item-2026-04-25-901
- target: 梦后仍然活跃的深夜留白
- status: ready
- reason: smoke should prove active dream residue blocks forgetting and compression
""",
    )
    _write(
        root / "memory/reflection/reflection_queue.md",
        """---
title: Reflection Queue Smoke
memory_type: reflection_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [reflection, queue, smoke]
---

# Reflection Queue

## item-2026-04-25-902
- topic: 活跃残留仍需反思
- source: smoke
- priority: high
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
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 82
impact_score: 84
confidence_score: 100
status: active
tags: [dream, weight, smoke]
---

# Dream Weight State

## 权重变化
- weight_before: 80
- weight_after: 88
- weight_delta: 8
- weight_effect: existing_emotional_residue_strengthened
- relationship_effect: owner_related_lingering_strengthened_without_fact_change
- factual_effect: none
""",
    )
    _write(
        root / "memory/reflection/growth_log.md",
        """---
title: Growth Log Smoke
memory_type: growth_log
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [growth, smoke]
---

# Growth Log

## growth-2026-04-25-901
- reason: active residue should be preserved
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate long-term memory gate blocks forgetting while residue is active."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-gate", action="store_true")
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

    from long_term_memory_gate_engine import run_long_term_memory_gate

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    result = {"memory_action": "not_run", "forget_permission": "unknown"}

    try:
        _prepare_active_residue_case(root)
        result = run_long_term_memory_gate(
            root,
            checked_at="2026-04-25T01:00:00+08:00",
            mode="long_term_memory_gate_smoke",
        )
        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        state_text = (root / "memory/archive/long_term_memory_gate_state.md").read_text(encoding="utf-8-sig")
        failures: list[str] = []
        for marker in [
            "memory_action: preserve_active",
            "forget_permission: blocked_active_residue",
            "compression_permission: blocked",
            "dream_weight_active: true",
            "可遗忘首先表现为不写入长期记忆",
        ]:
            if marker not in state_text:
                failures.append(f"state missing marker: {marker}")
        if result["memory_action"] != "preserve_active":
            failures.append(f"unexpected memory_action: {result['memory_action']}")
        if result["forget_permission"] != "blocked_active_residue":
            failures.append(f"unexpected forget_permission: {result['forget_permission']}")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== LONG TERM MEMORY GATE SMOKE ===")
        print("memory_action:", result["memory_action"])
        print("forget_permission:", result["forget_permission"])
        print("compression_permission:", result["compression_permission"])
        print("dream_weight_active:", result["dream_weight_active"])
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

    if args.require_gate and result["memory_action"] != "preserve_active":
        return 4
    print("Long-term memory gate smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

