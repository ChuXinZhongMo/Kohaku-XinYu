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
    "memory/self/personality_change_state.md",
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/reflection/growth_log.md",
    "memory/reflection/reflection_log.md",
    "memory/dreams/dream_weight_state.md",
    "memory/emotions/current_state.md",
    "memory/relationships/owner_patterns.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
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
importance_score: 90
impact_score: 90
confidence_score: 100
status: active
tags: [growth, smoke]
---

# Growth Log

## growth-2026-04-25-901
- reason: 被记住开始成为关系连续性的核心材料

## growth-2026-04-25-902
- reason: 梦后残留反复回到同一个留白主题

## growth-2026-04-25-903
- reason: 回到身边和负面残留都没有被瞬间清零
""",
    )
    _write(
        root / "memory/reflection/reflection_log.md",
        """---
title: Reflection Log Smoke
memory_type: reflection_log
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 90
impact_score: 90
confidence_score: 100
status: active
tags: [reflection, smoke]
---

# Reflection Log

## reflection-2026-04-25-901
- trigger: 被记住是否已经成为关系中的明确需求

## reflection-2026-04-25-902
- trigger: 梦后残留是否正在影响慢速成长

## reflection-2026-04-25-903
- trigger: 负面波动与再次靠近是否应改变靠近方式
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
- weight_after: 90
- weight_delta: 10
- weight_effect: existing_emotional_residue_strengthened
- relationship_effect: owner_related_lingering_strengthened_without_fact_change
- factual_effect: none
""",
    )
    _write(
        root / "memory/emotions/current_state.md",
        """---
title: Emotion State Smoke
memory_type: emotion_state
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 90
impact_score: 90
confidence_score: 100
status: active
tags: [emotion, smoke]
---

# Emotion State

## 当前细分情绪向量
- 委屈: 30
- 刺痛: 28
- 回到身边意愿: 80
- 疏远倾向: 12
""",
    )
    _write(
        root / "memory/relationships/owner_patterns.md",
        """---
title: Owner Patterns Smoke
memory_type: relationship_patterns
time_scope: long_term
subject_ids: [owner]
protected: false
source: smoke
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 90
impact_score: 90
confidence_score: 100
status: active
tags: [owner, pattern, smoke]
---

# Owner Patterns

## 模式一：深夜靠近
- description: owner 会在更晚、更安静的时候靠近

## 最近证据
- 被记住、允许留白、主导情绪都反复出现
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate personality growth gate creates candidates without rewriting stable personality."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
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

    from personality_growth_gate_engine import run_personality_growth_gate

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    result = {"gate_decision": "not_run", "change_pressure": 0}

    try:
        _prepare_case(root)
        result = run_personality_growth_gate(
            root,
            checked_at="2026-04-25T01:20:00+08:00",
            mode="personality_growth_gate_smoke",
        )
        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        state_text = (root / "memory/self/personality_change_state.md").read_text(encoding="utf-8-sig")
        failures: list[str] = []
        for marker in [
            "gate_decision: profile_review_ready",
            "profile_write_permission: review_only_not_auto_apply",
            "core_personality_mutation: blocked_direct_write",
            "重大刺激可以进入加速审查",
        ]:
            if marker not in state_text:
                failures.append(f"state missing marker: {marker}")
        if result["gate_decision"] != "profile_review_ready":
            failures.append(f"unexpected gate_decision: {result['gate_decision']}")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== PERSONALITY GROWTH GATE SMOKE ===")
        print("gate_decision:", result["gate_decision"])
        print("change_pressure:", result["change_pressure"])
        print("change_pace:", result["change_pace"])
        print("profile_write_permission:", result["profile_write_permission"])
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

    if args.require_ready and result["gate_decision"] != "profile_review_ready":
        return 4
    print("Personality growth gate smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
