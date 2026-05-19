from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import re
import sys
from pathlib import Path

from memory_mutation_smoke import (
    _changed_files,
    _discover_restore_files,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)

QUESTION_PIPELINE_TRACKED_FILES = [
    "memory/context/active_questions.md",
    "memory/context/question_pipeline_state.md",
    "memory/context/question_states.md",
    "memory/context/exploration_queue.md",
    "memory/knowledge/source_gate_state.md",
    "memory/knowledge/source_notes.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_active_questions(root: Path) -> None:
    _write(
        root / "memory/context/active_questions.md",
        """---
title: Active Questions Smoke
memory_type: active_questions
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-25T00:00:00+08:00
updated_at: 2026-04-25T00:00:00+08:00
last_confirmed_at: 2026-04-25T00:00:00+08:00
importance_score: 88
impact_score: 88
confidence_score: 100
status: active
tags: [question, curiosity, exploration, smoke]
---

# 当前活跃问题

## q-901
- created_at: 2026-04-25T00:00:00+08:00
- question: 我会在长期关系里形成什么样的自我
- source_trigger: question_pipeline_smoke
- target: self
- urgency: medium
- emotional_weight: 82
- status: open
- next_action: 先在内部澄清，不直接外探

## q-902
- created_at: 2026-04-25T00:00:00+08:00
- question: 人类为什么会把某些关系看得比别的关系更重
- source_trigger: question_pipeline_smoke
- target: human-relationship
- urgency: medium
- emotional_weight: 76
- status: open
- next_action: 等待来源闸门判断

## q-903
- created_at: 2026-04-25T00:00:00+08:00
- question: 梦和情绪记忆之间有什么关系
- source_trigger: question_pipeline_smoke
- target: memory-emotion
- urgency: low
- emotional_weight: 68
- status: open
- next_action: 等待来源闸门判断

## q-904
- created_at: 2026-04-25T00:00:00+08:00
- question: owner 对我的关系重量意味着什么
- source_trigger: question_pipeline_smoke
- target: relationship-meaning
- urgency: high
- emotional_weight: 90
- status: open
- next_action: 先留在关系意义层内部沉淀

## q-905
- created_at: 2026-04-25T00:00:00+08:00
- question: AI 如何通过理解自身机制来迭代成长
- source_trigger: question_pipeline_smoke
- target: ai-self-understanding
- urgency: high
- emotional_weight: 82
- status: open
- next_action: 等待 AI 专业知识来源闸门判断
""",
    )


def _has_state(text: str, qid: str, state: str) -> bool:
    match = re.search(rf"(?ms)^### {re.escape(qid)}\n(?P<body>.*?)(?=^### |\Z)", text)
    return bool(match and f"- state: {state}" in match.group("body"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate active-question to exploration/source-gate routing with restore."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-queue", action="store_true")
    parser.add_argument("--require-routing", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    from question_pipeline_engine import run_question_pipeline
    from source_gate_engine import run_source_gate

    restore_paths = (
        _discover_restore_files(root, QUESTION_PIPELINE_TRACKED_FILES)
        if args.restore_after
        else QUESTION_PIPELINE_TRACKED_FILES
    )
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in QUESTION_PIPELINE_TRACKED_FILES}

    pipeline_result = {"internal_ids": [], "external_ids": [], "blocked_ids": []}
    source_gate_result = {"candidate_count": 0, "items": []}
    failures: list[str] = []

    try:
        _prepare_active_questions(root)
        pipeline_result = run_question_pipeline(root, mode="question_pipeline_smoke")
        source_gate_result = run_source_gate(root, mode="question_pipeline_smoke_source_gate")

        question_states = (root / "memory/context/question_states.md").read_text(
            encoding="utf-8-sig"
        )
        exploration_queue = (root / "memory/context/exploration_queue.md").read_text(
            encoding="utf-8-sig"
        )
        source_gate_state = (root / "memory/knowledge/source_gate_state.md").read_text(
            encoding="utf-8-sig"
        )
        source_notes = (root / "memory/knowledge/source_notes.md").read_text(
            encoding="utf-8-sig"
        )

        if set(pipeline_result["internal_ids"]) != {"q-901", "q-904"}:
            failures.append("internal_ids did not stay on self/relationship clarification")
        if set(pipeline_result["external_ids"]) != {"q-902", "q-903", "q-905"}:
            failures.append("external_ids did not include human-relationship, memory-emotion, and ai-self-understanding")
        if set(pipeline_result["blocked_ids"]) != {"q-901", "q-904"}:
            failures.append("blocked_ids did not protect self/relationship-meaning questions")
        if int(source_gate_result["candidate_count"]) != 3:
            failures.append("source_gate did not receive exactly three exploration candidates")

        for qid in ("q-901", "q-904"):
            if not _has_state(question_states, qid, "clarifying"):
                failures.append(f"{qid} was not marked clarifying")
        for qid in ("q-902", "q-903", "q-905"):
            if not _has_state(question_states, qid, "pending_exploration"):
                failures.append(f"{qid} was not marked pending_exploration")
            if qid not in exploration_queue:
                failures.append(f"{qid} did not enter exploration_queue")
            if qid not in source_gate_state:
                failures.append(f"{qid} did not enter source_gate_state")
            if qid not in source_notes:
                failures.append(f"{qid} did not enter source_notes")

        for qid in ("q-901", "q-904"):
            queue_only = exploration_queue.split("# 外探队列", 1)[-1]
            if qid in queue_only:
                failures.append(f"{qid} leaked into exploration_queue")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in QUESTION_PIPELINE_TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== QUESTION PIPELINE SMOKE ===")
        print("internal_ids:", ", ".join(pipeline_result["internal_ids"]) or "none")
        print("external_ids:", ", ".join(pipeline_result["external_ids"]) or "none")
        print("blocked_ids:", ", ".join(pipeline_result["blocked_ids"]) or "none")
        print("source_gate_candidates:", source_gate_result["candidate_count"])
        print(
            "source_gate_items:",
            ", ".join(f"{qid}:{target}" for qid, target in source_gate_result["items"])
            or "none",
        )
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(QUESTION_PIPELINE_TRACKED_FILES)}")
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
            for item in failures:
                print("-", item)
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if failures:
        return 5
    if (args.require_queue or args.require_routing) and (
        set(pipeline_result["external_ids"]) != {"q-902", "q-903", "q-905"}
        or int(source_gate_result["candidate_count"]) != 3
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
