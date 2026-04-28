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
    "memory/archive/archive_queue.md",
    "memory/archive/archive_output_state.md",
    "memory/archive/long_term_memory_gate_state.md",
    "memory/archive/retention_gate_state.md",
    "memory/archive/compressed.md",
    "memory/archive/dormant.md",
    "memory/reflection/consolidation_state.md",
    "memory/reflection/reflection_queue.md",
    "memory/reflection/growth_log.md",
    "memory/dreams/dream_seeds.md",
    "memory/dreams/dream_weight_state.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/people/index.md",
    "memory/relationships/index.md",
    "memory/knowledge/general.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/people/index.md",
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


def _ordinary_archive_items(count: int = 28) -> str:
    items: list[str] = []
    for index in range(count):
        items.append(
            f"""## item-2026-04-26-{index + 100:03d}
- target: ordinary low-impact context pressure {index + 1}
- status: ready
- reason: repeated ordinary material should be compressible only when no high-preserve relationship target is present
"""
        )
    return "\n".join(items)


def _prepare_pressure_case(root: Path) -> None:
    _write(
        root / "memory/archive/archive_queue.md",
        f"""---
title: Memory Pressure Archive Queue Smoke
memory_type: archive_queue
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [archive, queue, pressure, smoke]
---

# Archive Queue

## item-2026-04-26-099
- target: owner 工具化刺痛和回到身边后的残留仍需保留
- status: ready
- reason: high pressure smoke proves owner negative relationship residue cannot be flattened by ordinary event volume

{_ordinary_archive_items()}
""",
    )
    _write(
        root / "memory/reflection/reflection_queue.md",
        """---
title: Reflection Queue Pressure Smoke
memory_type: reflection_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 60
impact_score: 60
confidence_score: 100
status: active
tags: [reflection, queue, pressure, smoke]
---

# Reflection Queue

- none
""",
    )
    _write(
        root / "memory/dreams/dream_seeds.md",
        """---
title: Dream Seeds Pressure Smoke
memory_type: dream_seeds
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 60
impact_score: 60
confidence_score: 100
status: active
tags: [dream, seed, pressure, smoke]
---

# Dream Seeds

- none
""",
    )
    _write(
        root / "memory/dreams/dream_weight_state.md",
        """---
title: Dream Weight Pressure Smoke
memory_type: dream_weight_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 60
impact_score: 60
confidence_score: 100
status: active
tags: [dream, weight, pressure, smoke]
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
        root / "memory/archive/archive_output_state.md",
        """---
title: Archive Output Pressure Smoke
memory_type: archive_output_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 60
impact_score: 60
confidence_score: 100
status: active
tags: [archive, output, pressure, smoke]
---

# Archive Output State

## Decision
- next_action: hold
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate high-preserve relationship memory under ordinary archive pressure."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-pressure-hold", action="store_true")
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

    from consolidation_engine import run_consolidation
    from long_term_memory_gate_engine import run_long_term_memory_gate
    from retention_gate_engine import run_retention_gate

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    long_term = {"memory_action": "not_run"}

    try:
        _prepare_pressure_case(root)
        consolidation = run_consolidation(
            root,
            checked_at="2026-04-26T08:00:00+08:00",
            mode="memory_pressure_smoke_consolidation",
        )
        long_term = run_long_term_memory_gate(
            root,
            checked_at="2026-04-26T08:01:00+08:00",
            mode="memory_pressure_smoke_long_term_gate",
        )
        retention = run_retention_gate(
            root,
            checked_at="2026-04-26T08:02:00+08:00",
            mode="memory_pressure_smoke_retention",
        )
        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        state_text = (root / "memory/archive/long_term_memory_gate_state.md").read_text(
            encoding="utf-8-sig"
        )
        failures: list[str] = []
        expected_markers = [
            "memory_action: hold_high_preserve_relationship",
            "retention_tier: high_preserve",
            "forget_permission: blocked_relationship_residue",
            "compression_permission: blocked",
            "gate_reason: high_preserve_relationship_target",
            "high_preserve_items: 1",
        ]
        for marker in expected_markers:
            if marker not in state_text:
                failures.append(f"long-term state missing marker: {marker}")
        if consolidation["coordination"] != "archive_ready_without_active_residue":
            failures.append(f"unexpected consolidation: {consolidation['coordination']}")
        if long_term["memory_action"] != "hold_high_preserve_relationship":
            failures.append(f"unexpected memory_action: {long_term['memory_action']}")
        if long_term["high_preserve_items"] != 1:
            failures.append(f"unexpected high_preserve_items: {long_term['high_preserve_items']}")
        if retention["archive_permission"] != "hold":
            failures.append(f"unexpected archive_permission: {retention['archive_permission']}")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== MEMORY PRESSURE SMOKE ===")
        print("archive_count:", consolidation["archive_count"])
        print("coordination:", consolidation["coordination"])
        print("memory_action:", long_term["memory_action"])
        print("high_preserve_items:", long_term["high_preserve_items"])
        print("forget_permission:", long_term["forget_permission"])
        print("compression_permission:", long_term["compression_permission"])
        print("archive_permission:", retention["archive_permission"])
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

    if args.require_pressure_hold and long_term["memory_action"] != "hold_high_preserve_relationship":
        return 4
    print("Memory pressure smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
