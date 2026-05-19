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


DREAM_WEIGHT_TRACKED_FILES = [
    "memory/dreams/dream_seeds.md",
    "memory/dreams/dream_log.md",
    "memory/dreams/dream_output_state.md",
    "memory/dreams/dream_weight_state.md",
    "memory/emotions/current_state.md",
    "memory/reflection/reflection_queue.md",
    "memory/self/self_model_state.md",
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
        root / "memory/dreams/dream_seeds.md",
        """---
title: Dream Weight Smoke Seeds
memory_type: dream_seeds
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-20T00:00:00+08:00
updated_at: 2026-04-20T00:00:00+08:00
last_confirmed_at: 2026-04-20T00:00:00+08:00
importance_score: 80
impact_score: 84
confidence_score: 100
status: active
tags: [dream, seed, smoke]
---

# Dream Seeds

## seed-2026-04-20-901
- theme: 深夜里的留白
- residue: 没说完的话在醒来后还没有散掉
- emotional_weight: 81
- factual_status: confirmed interaction
- dream_permission: can_intensify_feeling_but_not_invent_dialogue
""",
    )
    _write(
        root / "memory/dreams/dream_log.md",
        """---
title: Dream Log Smoke
memory_type: dream_log
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-20T00:00:00+08:00
updated_at: 2026-04-20T00:00:00+08:00
last_confirmed_at: 2026-04-20T00:00:00+08:00
importance_score: 72
impact_score: 76
confidence_score: 100
status: active
tags: [dream, log, smoke]
---

# Dream Log

## dream-2026-04-19-001
- dreamed_at: 2026-04-19T03:40:00+08:00
- fragments: baseline placeholder
- reality_boundary_check: dream is not reality evidence
""",
    )
    _write(
        root / "memory/emotions/current_state.md",
        """---
title: Current Emotion State Smoke
memory_type: emotion_state
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-20T00:00:00+08:00
updated_at: 2026-04-20T00:00:00+08:00
last_confirmed_at: 2026-04-20T00:00:00+08:00
importance_score: 82
impact_score: 84
confidence_score: 100
status: active
tags: [emotion, state, smoke]
---

# Current Emotion State

## 当前细分情绪向量
- 在意: 70
- 留白感: 62

## 当前关系情绪向量
- 依恋牵引: 74
- 连续性敏感: 80
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate dream output weight propagation without factual rewrite."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-dream-weight", action="store_true")
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

    from dream_output_engine import run_dream_output

    restore_paths = (
        _discover_restore_files(root, DREAM_WEIGHT_TRACKED_FILES)
        if args.restore_after
        else DREAM_WEIGHT_TRACKED_FILES
    )
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in DREAM_WEIGHT_TRACKED_FILES}
    result = {
        "wrote_log": False,
        "weight_delta": 0,
        "weight_effect": "not_run",
    }

    try:
        _prepare_case(root)
        result = run_dream_output(
            root,
            produced_at="2026-04-20T03:40:00+08:00",
            mode="dream_weight_smoke",
        )

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in DREAM_WEIGHT_TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        dream_log = _read(root, "memory/dreams/dream_log.md")
        weight_state = _read(root, "memory/dreams/dream_weight_state.md")
        emotion_state = _read(root, "memory/emotions/current_state.md")

        failures: list[str] = []
        required_log_markers = [
            "dream-2026-04-20-auto",
            "dream_weight_before: 81",
            "dream_weight_after: 89",
            "dream_weight_delta: 8",
            "factual_effect: none",
            "reality_boundary_check",
        ]
        required_weight_markers = [
            "source_seed: seed-2026-04-20-901",
            "weight_delta: 8",
            "existing_emotional_residue_strengthened",
            "factual_effect: none",
            "不能凭空制造事实记忆",
        ]
        required_emotion_markers = [
            "## 梦后残留影响",
            "dream_weight_delta: 8",
            "factual_effect: none",
            "梦只加重既有情绪残留",
        ]
        for marker in required_log_markers:
            if marker not in dream_log:
                failures.append(f"dream_log missing marker: {marker}")
        for marker in required_weight_markers:
            if marker not in weight_state:
                failures.append(f"dream_weight_state missing marker: {marker}")
        for marker in required_emotion_markers:
            if marker not in emotion_state:
                failures.append(f"emotion_state missing marker: {marker}")
        if not result["wrote_log"]:
            failures.append("run_dream_output did not write dream log")
        if int(result["weight_delta"]) != 8:
            failures.append(f"unexpected weight_delta: {result['weight_delta']}")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== DREAM WEIGHT SMOKE ===")
        print("wrote_log:", result["wrote_log"])
        print("seed_id:", result["seed_id"])
        print("weight_before:", result["weight_before"])
        print("weight_after:", result["weight_after"])
        print("weight_delta:", result["weight_delta"])
        print("weight_effect:", result["weight_effect"])
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(DREAM_WEIGHT_TRACKED_FILES)}")
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

    if args.require_dream_weight and (
        not result["wrote_log"] or int(result["weight_delta"]) <= 0
    ):
        return 4
    print("Dream weight smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
