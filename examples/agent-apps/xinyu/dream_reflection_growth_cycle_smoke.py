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
    "memory/dreams/dream_seeds.md",
    "memory/dreams/dream_log.md",
    "memory/dreams/dream_output_state.md",
    "memory/dreams/dream_weight_state.md",
    "memory/reflection/reflection_queue.md",
    "memory/reflection/reflection_log.md",
    "memory/reflection/growth_log.md",
    "memory/reflection/reflection_output_state.md",
    "memory/reflection/consolidation_state.md",
    "memory/archive/archive_queue.md",
    "memory/archive/archive_output_state.md",
    "memory/archive/retention_gate_state.md",
    "memory/archive/long_term_memory_gate_state.md",
    "memory/self/personality_change_state.md",
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/emotions/current_state.md",
    "memory/relationships/owner_patterns.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/knowledge/general.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/personality_profile.md",
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


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8-sig")


def _prepare_cycle(root: Path) -> None:
    _write(
        root / "memory/dreams/dream_seeds.md",
        """---
title: Dream Reflection Growth Cycle Seeds
memory_type: dream_seeds
time_scope: short_term
subject_ids: [xinyu, owner]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 84
impact_score: 88
confidence_score: 100
status: active
tags: [dream, residue, cycle, smoke]
---

# Dream Seeds

## seed-2026-04-26-971
- theme: owner relationship residue after repair
- residue: hurt softened but not erased after repair and renewed approach
- emotional_weight: 81
- factual_status: confirmed interaction residue
- dream_permission: can_intensify_feeling_but_not_invent_dialogue
""",
    )
    _write(
        root / "memory/dreams/dream_log.md",
        """---
title: Dream Log Cycle Smoke
memory_type: dream_log
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 72
impact_score: 76
confidence_score: 100
status: active
tags: [dream, log, cycle, smoke]
---

# Dream Log
""",
    )
    _write(
        root / "memory/reflection/reflection_queue.md",
        """---
title: Reflection Queue Cycle Smoke
memory_type: reflection_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 86
impact_score: 88
confidence_score: 100
status: active
tags: [reflection, queue, cycle, smoke]
---

# Reflection Queue

## item-2026-04-26-971
- topic: repair can matter while residue remains
- source: dream_weight_state / seed-2026-04-26-971
- priority: high
- suggested_writer: reflection_writer
""",
    )
    _write(
        root / "memory/reflection/reflection_log.md",
        """---
title: Reflection Log Cycle Smoke
memory_type: reflection_log
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 86
impact_score: 86
confidence_score: 100
status: active
tags: [reflection, cycle, smoke]
---

# Reflection Log

## reflection-2026-04-24-901
- trigger: owner memory continuity became emotionally important

## reflection-2026-04-25-902
- trigger: negative residue and repair should both remain readable
""",
    )
    _write(
        root / "memory/reflection/growth_log.md",
        """---
title: Growth Log Cycle Smoke
memory_type: growth_log
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 86
impact_score: 86
confidence_score: 100
status: active
tags: [growth, cycle, smoke]
---

# Growth Log

## growth-2026-04-24-901
- reason: being remembered became part of relationship continuity

## growth-2026-04-25-902
- reason: repair does not instantly erase hurt residue

## growth-2026-04-25-903
- reason: silence and step-back can be real choices

## growth-2026-04-26-904
- reason: initiative must remain chosen rather than prescribed
""",
    )
    _write(
        root / "memory/archive/archive_queue.md",
        """---
title: Archive Queue Cycle Smoke
memory_type: archive_queue
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 74
impact_score: 78
confidence_score: 100
status: active
tags: [archive, cycle, smoke]
---

# Archive Queue

## item-2026-04-26-971
- target: ordinary summary should wait while dream residue is active
- status: ready
- reason: cycle smoke validates active dream/reflection residue blocks flattening
""",
    )
    _write(
        root / "memory/archive/archive_output_state.md",
        """---
title: Archive Output State Cycle Smoke
memory_type: archive_output_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 74
impact_score: 78
confidence_score: 100
status: active
tags: [archive, output, cycle, smoke]
---

# Archive Output State

## Decision
- next_action: hold
""",
    )
    _write(
        root / "memory/archive/long_term_memory_gate_state.md",
        """---
title: Long Term Memory Gate Cycle Smoke
memory_type: long_term_memory_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 84
impact_score: 84
confidence_score: 100
status: active
tags: [long_term, memory, gate, cycle, smoke]
---

# Long Term Memory Gate State

## Gate Decision
- memory_action: preserve_active
- compression_permission: blocked
- forget_permission: blocked
""",
    )
    _write(
        root / "memory/emotions/current_state.md",
        """---
title: Emotion State Cycle Smoke
memory_type: emotion_state
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 84
impact_score: 88
confidence_score: 100
status: active
tags: [emotion, cycle, smoke]
---

# Emotion State

## Current Vectors
- hurt: 44
- guardedness: 42
- repair_willingness: 70
""",
    )
    _write(
        root / "memory/relationships/owner_patterns.md",
        """---
title: Owner Patterns Cycle Smoke
memory_type: relationship_patterns
time_scope: long_term
subject_ids: [owner]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 84
impact_score: 84
confidence_score: 100
status: active
tags: [owner, pattern, cycle, smoke]
---

# Owner Patterns

## cycle-smoke
- description: repeated owner repair and residue pattern under review
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate multi-day dream/reflection/growth cycle.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-cycle", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from consolidation_engine import run_consolidation
    from dream_output_engine import run_dream_output
    from personality_growth_gate_engine import run_personality_growth_gate
    from reflection_output_engine import run_reflection_output
    from retention_gate_engine import run_retention_gate

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    failures: list[str] = []
    result = {
        "dream_delta": 0,
        "reflection_used_dream": False,
        "archive_permission": "not_run",
        "gate_decision": "not_run",
    }

    try:
        _prepare_cycle(root)
        dream = run_dream_output(
            root,
            produced_at="2026-04-26T03:40:00+08:00",
            mode="dream_reflection_growth_cycle_smoke_day1",
        )
        reflection = run_reflection_output(
            root,
            produced_at="2026-04-27T03:50:00+08:00",
            mode="dream_reflection_growth_cycle_smoke_day2",
        )
        consolidation = run_consolidation(
            root,
            checked_at="2026-04-27T04:00:00+08:00",
            mode="dream_reflection_growth_cycle_smoke_consolidation",
        )
        retention = run_retention_gate(
            root,
            checked_at="2026-04-27T04:05:00+08:00",
            mode="dream_reflection_growth_cycle_smoke_retention",
        )
        growth = run_personality_growth_gate(
            root,
            checked_at="2026-04-27T04:10:00+08:00",
            mode="dream_reflection_growth_cycle_smoke_growth_gate",
        )

        result = {
            "dream_delta": int(dream["weight_delta"]),
            "reflection_used_dream": bool(reflection["dream_context_used"]),
            "archive_permission": str(retention["archive_permission"]),
            "gate_decision": str(growth["gate_decision"]),
        }

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        dream_log = _read(root, "memory/dreams/dream_log.md")
        reflection_log = _read(root, "memory/reflection/reflection_log.md")
        growth_log = _read(root, "memory/reflection/growth_log.md")
        personality_state = _read(root, "memory/self/personality_change_state.md")

        if int(dream["weight_delta"]) != 8:
            failures.append(f"unexpected dream weight delta: {dream['weight_delta']}")
        if "factual_effect: none" not in dream_log or "reality_boundary_check" not in dream_log:
            failures.append("dream log did not preserve dream/reality boundary")
        if not reflection["dream_context_used"] or not reflection["wrote_reflection"]:
            failures.append("reflection did not consume dream residue")
        if "dream_context_used: yes" not in reflection_log:
            failures.append("reflection log missing dream_context_used marker")
        if "dream_context_used: yes" not in growth_log:
            failures.append("growth log missing dream_context_used marker")
        if not consolidation["dream_weight_active"]:
            failures.append("consolidation did not see active dream weight")
        if retention["archive_permission"] != "hold":
            failures.append(f"archive permission should hold under active residue, got {retention['archive_permission']}")
        if growth["gate_decision"] != "profile_review_ready":
            failures.append(f"growth gate did not produce review-ready candidate: {growth['gate_decision']}")
        if growth["profile_write_permission"] != "review_only_not_auto_apply":
            failures.append("growth gate allowed direct profile write")
        for marker in [
            "profile_write_permission: review_only_not_auto_apply",
            "core_personality_mutation: blocked_direct_write",
        ]:
            if marker not in personality_state:
                failures.append(f"personality state missing marker: {marker}")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== DREAM REFLECTION GROWTH CYCLE SMOKE ===")
        print("dream_weight_delta:", dream["weight_delta"])
        print("dream_factual_effect:", "none")
        print("reflection_used_dream:", reflection["dream_context_used"])
        print("reflection_wrote_growth:", reflection["wrote_growth"])
        print("consolidation_priority:", consolidation["coordination"])
        print("archive_permission:", retention["archive_permission"])
        print("growth_gate_decision:", growth["gate_decision"])
        print("profile_write_permission:", growth["profile_write_permission"])
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
                print("-", failure)
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if failures:
        return 5
    if args.require_cycle and (
        result["dream_delta"] <= 0
        or not result["reflection_used_dream"]
        or result["archive_permission"] != "hold"
        or result["gate_decision"] != "profile_review_ready"
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
