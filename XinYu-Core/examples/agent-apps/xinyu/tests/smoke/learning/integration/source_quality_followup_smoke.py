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
    "memory/context/active_questions.md",
    "memory/knowledge/learning_quality_state.md",
    "memory/knowledge/source_gate_state.md",
    "memory/knowledge/source_reliability_state.md",
    "memory/knowledge/source_integration_gate_state.md",
    "memory/knowledge/source_requests.md",
    "memory/knowledge/source_request_planner_state.md",
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


def _prepare_case(root: Path) -> None:
    _write(
        root / "memory/context/active_questions.md",
        """---
title: Quality Follow-up Active Questions Smoke
memory_type: active_questions
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 88
impact_score: 88
confidence_score: 100
status: active
tags: [question, followup, smoke]
---

# Active Questions

## q-920
- created_at: 2026-04-26T00:00:00+08:00
- question: How can emotional memory be supported by independent sources?
- source_trigger: learning quality follow-up smoke
- target: memory-emotion
- urgency: medium
- emotional_weight: 70
- status: partially_answered
- next_action: source diversity follow-up
""",
    )
    _write(
        root / "memory/knowledge/learning_quality_state.md",
        """---
title: Learning Quality Follow-up Smoke
memory_type: learning_quality_state
time_scope: mid_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 83
impact_score: 82
confidence_score: 100
status: active
tags: [knowledge, learning, quality, smoke]
---

# Learning Quality State

## Last Evaluation
- evaluated_at: 2026-04-26T00:00:00+08:00
- mode: source_quality_followup_smoke_quality
- quality_grade: review_needed
- warning_count: 1

## Warnings
- repeated_question_host: severity=review; target=q-920@alpha.example; detail=2/2 learned entries for q-920 come from the same host
""",
    )
    _write(
        root / "memory/knowledge/source_gate_state.md",
        """---
title: Source Gate Follow-up Smoke
memory_type: source_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 79
impact_score: 79
confidence_score: 100
status: active
tags: [knowledge, source_gate, smoke]
---

# Source Gate State

## Current Candidates
- none
""",
    )
    _write(
        root / "memory/knowledge/source_reliability_state.md",
        """---
title: Source Reliability Follow-up Smoke
memory_type: source_reliability_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 81
impact_score: 80
confidence_score: 100
status: active
tags: [knowledge, source, reliability, smoke]
---

# Source Reliability State

## Reliability Snapshot
- none
""",
    )
    _write(
        root / "memory/knowledge/source_requests.md",
        """---
title: Source Requests Follow-up Smoke
memory_type: source_requests
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 74
impact_score: 72
confidence_score: 100
status: active
tags: [knowledge, outward, requests, smoke]
---

# Source Requests

## request-none
- question_id: none
- target: none
- query: none
- url: none
- status: hold
- source_policy: controlled_fetch_only
- reason: smoke baseline
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate learning-quality-driven source follow-up planning.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-followup", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    from source_integration_gate_engine import run_source_integration_gate
    from source_request_planner_engine import run_source_request_planner

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    integration_result = {"integration_permission": "unknown", "quality_followup_candidates": 0}
    planner_result = {"planned_requests": 0, "pending_url_requests": 0}
    protected_changed: list[str] = []

    try:
        _prepare_case(root)
        integration_result = run_source_integration_gate(root, mode="source_quality_followup_smoke_integration")
        planner_result = run_source_request_planner(root, mode="source_quality_followup_smoke_planner")
        request_text = (root / "memory/knowledge/source_requests.md").read_text(encoding="utf-8-sig")
        followup_written = "followup_kind: source_diversity" in request_text and "avoid_host: alpha.example" in request_text

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        print("=== SOURCE QUALITY FOLLOW-UP SMOKE ===")
        print("integration_permission:", integration_result["integration_permission"])
        print("quality_followup_candidates:", integration_result["quality_followup_candidates"])
        print("planned_requests:", planner_result["planned_requests"])
        print("pending_url_requests:", planner_result["pending_url_requests"])
        print("followup_written:", "yes" if followup_written else "no")
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
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")

    if protected_changed:
        return 5
    if args.require_followup and (
        integration_result["integration_permission"] != "prepare_only"
        or int(integration_result["quality_followup_candidates"]) <= 0
        or int(planner_result["planned_requests"]) <= 0
        or int(planner_result["pending_url_requests"]) <= 0
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
