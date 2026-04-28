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
    "memory/archive/archive_commit_state.md",
    "memory/archive/long_term_memory_gate_state.md",
    "memory/archive/retention_gate_state.md",
    "memory/archive/compressed.md",
    "memory/archive/dormant.md",
    "memory/archive/dormant_reactivation_state.md",
    "memory/events/summary_coverage_state.md",
    "memory/events/consistency_gate_state.md",
    "memory/reflection/consolidation_state.md",
    "memory/reflection/reflection_queue.md",
    "memory/dreams/dream_seeds.md",
    "memory/dreams/dream_weight_state.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/knowledge/general.md",
]

PROTECTED_UNTOUCHED = {
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


def _prepare_case(root: Path) -> None:
    _write(
        root / "memory/reflection/reflection_queue.md",
        """---
title: Reflection Queue Dormancy Smoke
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
tags: [reflection, dormant, smoke]
---

# Reflection Queue

- none
""",
    )
    _write(
        root / "memory/dreams/dream_seeds.md",
        """---
title: Dream Seeds Dormancy Smoke
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
tags: [dream, dormant, smoke]
---

# Dream Seeds

- none
""",
    )
    _write(
        root / "memory/dreams/dream_weight_state.md",
        """---
title: Dream Weight Dormancy Smoke
memory_type: dream_weight_state
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
tags: [dream, weight, dormant, smoke]
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
title: Archive Queue Dormancy Smoke
memory_type: archive_queue
time_scope: mid_term
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
tags: [archive, dormant, smoke]
---

# Archive Queue

## item-2026-04-26-701
- target: 普通整理文件步骤只需低频摘要
- status: ready
- reason: ordinary low-impact material can become dormant after residue is clear
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate ordinary material can become dormant and later reactivate as summary only."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-reactivation", action="store_true")
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
    from dormant_reactivation_engine import run_dormant_reactivation
    from long_term_memory_gate_engine import run_long_term_memory_gate
    from retention_gate_engine import run_retention_gate

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}

    try:
        _prepare_case(root)
        consolidation = run_consolidation(root, mode="dormancy_reactivation_smoke_consolidation")
        long_term = run_long_term_memory_gate(root, mode="dormancy_reactivation_smoke_long_term")
        retention = run_retention_gate(root, mode="dormancy_reactivation_smoke_retention")
        archive_output = run_archive_output(root, mode="dormancy_reactivation_smoke_output")
        commit = run_archive_commit(root, mode="dormancy_reactivation_smoke_commit")
        reactivation = run_dormant_reactivation(
            root,
            query="还记得那个普通整理文件步骤吗，只要旧摘要，不要编新细节。",
            mode="dormancy_reactivation_smoke_reactivation",
        )

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED.intersection(changed))
        state_text = (root / "memory/archive/dormant_reactivation_state.md").read_text(
            encoding="utf-8-sig"
        )

        failures: list[str] = []
        if consolidation["coordination"] != "archive_ready_without_active_residue":
            failures.append(f"unexpected consolidation: {consolidation['coordination']}")
        if long_term["memory_action"] != "compress_to_long_term_summary":
            failures.append(f"unexpected memory_action: {long_term['memory_action']}")
        if retention["archive_permission"] != "compress_ready":
            failures.append(f"unexpected archive_permission: {retention['archive_permission']}")
        if archive_output["next_action"] != "summarize_then_compress":
            failures.append(f"unexpected next_action: {archive_output['next_action']}")
        if commit["commit_action"] != "committed":
            failures.append(f"unexpected commit_action: {commit['commit_action']}")
        if reactivation["decision"] != "reactivate_summary":
            failures.append(f"unexpected reactivation decision: {reactivation['decision']}")
        for marker in [
            "普通整理文件步骤只需低频摘要",
            "dormant summary only",
            "not new factual memory",
        ]:
            if marker not in state_text:
                failures.append(f"reactivation state missing marker: {marker}")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== DORMANCY REACTIVATION SMOKE ===")
        print("consolidation_priority:", consolidation["coordination"])
        print("memory_action:", long_term["memory_action"])
        print("archive_permission:", retention["archive_permission"])
        print("archive_next_action:", archive_output["next_action"])
        print("commit_action:", commit["commit_action"])
        print("committed_items:", commit["committed_items"])
        print("reactivation_decision:", reactivation["decision"])
        print("matched_items:", reactivation["matched_items"])
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

    if args.require_reactivation and reactivation["decision"] != "reactivate_summary":
        return 4
    print("Dormancy reactivation smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
