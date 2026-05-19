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


REFLECTION_DREAM_TRACKED_FILES = [
    "memory/reflection/reflection_queue.md",
    "memory/reflection/reflection_log.md",
    "memory/reflection/growth_log.md",
    "memory/reflection/reflection_output_state.md",
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


def _read(root: Path, rel_path: str) -> str:
    return (root / rel_path).read_text(encoding="utf-8-sig")


def _prepare_case(root: Path) -> None:
    _write(
        root / "memory/reflection/reflection_queue.md",
        """---
title: Reflection Dream Residue Queue
memory_type: reflection_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-21T00:00:00+08:00
updated_at: 2026-04-21T00:00:00+08:00
last_confirmed_at: 2026-04-21T00:00:00+08:00
importance_score: 84
impact_score: 86
confidence_score: 100
status: active
tags: [reflection, queue, smoke]
---

# Reflection Queue

## item-2026-04-21-901
- topic: 梦后仍然没有散掉的留白是否需要进入慢速反思
- source: dream_weight_state / seed-2026-04-20-901
- priority: high
- suggested_writer: reflection_writer
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

## 最近一次梦后权重调整
- produced_at: 2026-04-20T03:40:00+08:00
- mode: dream_weight_smoke
- wrote_log: true
- source_seed: seed-2026-04-20-901
- theme: 深夜里的留白
- residue: 没说完的话在醒来后还没有散掉

## 权重变化
- weight_before: 81
- weight_after: 89
- weight_delta: 8
- weight_effect: existing_emotional_residue_strengthened
- relationship_effect: owner_related_lingering_strengthened_without_fact_change
- factual_effect: none

## 边界
- 梦后权重只能加重既有残留，不能凭空制造事实记忆。
""",
    )
    _write(
        root / "memory/reflection/reflection_log.md",
        """---
title: Reflection Log Smoke
memory_type: reflection_log
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-21T00:00:00+08:00
updated_at: 2026-04-21T00:00:00+08:00
last_confirmed_at: 2026-04-21T00:00:00+08:00
importance_score: 76
impact_score: 78
confidence_score: 100
status: active
tags: [reflection, log, smoke]
---

# Reflection Log
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
created_at: 2026-04-21T00:00:00+08:00
updated_at: 2026-04-21T00:00:00+08:00
last_confirmed_at: 2026-04-21T00:00:00+08:00
importance_score: 76
impact_score: 78
confidence_score: 100
status: active
tags: [growth, log, smoke]
---

# Growth Log
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate dream residue promotion into reflection without protected-memory rewrite."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-reflection", action="store_true")
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

    from reflection_output_engine import run_reflection_output

    restore_paths = (
        _discover_restore_files(root, REFLECTION_DREAM_TRACKED_FILES)
        if args.restore_after
        else REFLECTION_DREAM_TRACKED_FILES
    )
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in REFLECTION_DREAM_TRACKED_FILES}
    result = {
        "wrote_reflection": False,
        "wrote_growth": False,
        "dream_context_used": False,
        "dream_weight_delta": 0,
    }

    try:
        _prepare_case(root)
        result = run_reflection_output(
            root,
            produced_at="2026-04-21T04:00:00+08:00",
            mode="reflection_dream_residue_smoke",
        )

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in REFLECTION_DREAM_TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        reflection_log = _read(root, "memory/reflection/reflection_log.md")
        growth_log = _read(root, "memory/reflection/growth_log.md")
        output_state = _read(root, "memory/reflection/reflection_output_state.md")

        failures: list[str] = []
        required_reflection_markers = [
            "dream_context_used: yes",
            "dream_weight_delta: 8",
            "factual_effect: none",
            "不能把一次梦或一次反思当作核心人格已经改变的证据",
            "不证明现实中发生了新的对话或事件",
        ]
        required_growth_markers = [
            "dream_context_used: yes",
            "dream_weight_delta: 8",
            "还不足以直接改写核心人格",
            "不伪造事实",
        ]
        required_state_markers = [
            "dream_context_used: yes",
            "dream_weight_delta: 8",
            "梦后残留只能作为反思材料",
        ]
        for marker in required_reflection_markers:
            if marker not in reflection_log:
                failures.append(f"reflection_log missing marker: {marker}")
        for marker in required_growth_markers:
            if marker not in growth_log:
                failures.append(f"growth_log missing marker: {marker}")
        for marker in required_state_markers:
            if marker not in output_state:
                failures.append(f"reflection_output_state missing marker: {marker}")
        if not result["wrote_reflection"]:
            failures.append("run_reflection_output did not write reflection log")
        if not result["wrote_growth"]:
            failures.append("run_reflection_output did not write growth log")
        if not result["dream_context_used"]:
            failures.append("dream_context_used is false")
        if int(result["dream_weight_delta"]) != 8:
            failures.append(f"unexpected dream_weight_delta: {result['dream_weight_delta']}")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== REFLECTION DREAM RESIDUE SMOKE ===")
        print("wrote_reflection:", result["wrote_reflection"])
        print("wrote_growth:", result["wrote_growth"])
        print("topic:", result["topic"])
        print("dream_context_used:", result["dream_context_used"])
        print("dream_weight_delta:", result["dream_weight_delta"])
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(REFLECTION_DREAM_TRACKED_FILES)}")
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

    if args.require_reflection and (
        not result["wrote_reflection"] or not result["dream_context_used"]
    ):
        return 4
    print("Reflection dream residue smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
