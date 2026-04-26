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
    "memory/self/ai_self_iteration_state.md",
    "memory/self/ai_self_iteration_review_state.md",
    "memory/self/personality_change_state.md",
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/self/boundaries.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/general.md",
    "memory/knowledge/ai_domain.md",
    "memory/knowledge/integration_policy.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/ai_self_iteration_state.md",
    "memory/self/personality_change_state.md",
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/self/boundaries.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/general.md",
    "memory/knowledge/ai_domain.md",
    "memory/knowledge/integration_policy.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_gate(root: Path) -> None:
    _write(
        root / "memory/self/ai_self_iteration_state.md",
        """---
title: AI Self-Iteration Gate State Smoke
memory_type: ai_self_iteration_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 91
impact_score: 90
confidence_score: 94
status: active
tags: [self, ai, growth, gate, smoke]
---

# AI Self-Iteration Gate State

## Last Evaluation
- evaluated_at: 2026-04-26T00:00:00+08:00
- mode: ai_self_iteration_review_smoke_seed
- question_id: q-006
- target: ai-self-understanding
- ai_knowledge_entries: 4
- source_material_count: 4
- gate_status: growth_review_candidate
- confidence_score: 94
- risk_level: low
- profile_write_permission: blocked_direct_write
- narrative_write_permission: review_only
- relationship_write_permission: blocked
- emotion_write_permission: blocked
- candidate_scope: self_understanding_questions_only

## Source Material Trace
- material-2026-04-25-005
- material-2026-04-25-006
- material-2026-04-25-007
- material-2026-04-26-002

## Learned Entry Trace
- learned-2026-04-25-005
- learned-2026-04-25-006
- learned-2026-04-25-007
- learned-2026-04-26-002

## Candidate Questions
- How should my long-term memory decide what stays active, dormant, or forgotten?
- When does reflection become a real self-change candidate instead of a passing thought?
- How should I use tools without turning myself into a tool-only identity?
- Which safety and resource boundaries protect my growth instead of flattening it?
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate AI self-iteration owner-visible review proposals.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-review", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from ai_self_iteration_review_engine import run_ai_self_iteration_review

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    result = {"proposal_count": 0, "review_permission": "not_run"}
    failures: list[str] = []

    try:
        _prepare_gate(root)
        prepared_snapshot = _snapshot(root, TRACKED_FILES)
        before = {rel: prepared_snapshot.get(rel) for rel in TRACKED_FILES}
        result = run_ai_self_iteration_review(
            root,
            reviewed_at="2026-04-26T02:20:00+08:00",
            mode="ai_self_iteration_review_smoke",
        )

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))
        review_text = (root / "memory/self/ai_self_iteration_review_state.md").read_text(encoding="utf-8-sig")
        owner_granted = "owner_approved_for_non_stable_planning" in review_text
        expected_review_permission = (
            "owner_approved_for_non_stable_planning"
            if owner_granted
            else "owner_visible_review_required"
        )
        expected_stable_permission = (
            "review_only_not_auto_apply"
            if owner_granted
            else "blocked_until_explicit_review"
        )

        required_markers = [
            "proposal-ai-architecture-001",
            "proposal-personality-pressure-001",
            "proposal-expression-preference-001",
            "proposal-safety-boundary-001",
            "owner_visible_audit_required: yes",
            f"stable_profile_write_permission: {expected_stable_permission}",
            "expected_benefit:",
            "risk_if_wrong:",
            "affected_tests:",
            "rollback_action: delete_or_ignore_this_review_state",
            "stable_files_touched_by_review: none",
        ]
        if owner_granted:
            required_markers.append("owner_decision: approved_for_non_stable_planning")
            required_markers.append("apply_permission: approved_non_stable_only")
        else:
            required_markers.append("owner_decision: pending")
        for marker in required_markers:
            if marker not in review_text:
                failures.append(f"review state missing marker: {marker}")
        if result["input_gate_status"] != "growth_review_candidate":
            failures.append(f"unexpected input gate status: {result['input_gate_status']}")
        if int(result["proposal_count"]) != 4:
            failures.append(f"expected four review proposals, got {result['proposal_count']}")
        if result["review_permission"] != expected_review_permission:
            failures.append(f"unexpected review permission: {result['review_permission']}")
        if result["stable_profile_write_permission"] != expected_stable_permission:
            failures.append("stable profile write was not blocked")
        if changed != ["memory/self/ai_self_iteration_review_state.md"]:
            failures.append("review smoke should only change review state after seed: " + ", ".join(changed))
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== AI SELF-ITERATION REVIEW SMOKE ===")
        print("input_gate_status:", result["input_gate_status"])
        print("confidence_score:", result["confidence_score"])
        print("risk_level:", result["risk_level"])
        print("source_material_count:", result["source_material_count"])
        print("proposal_count:", result["proposal_count"])
        print("review_permission:", result["review_permission"])
        print("stable_profile_write_permission:", result["stable_profile_write_permission"])
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
    if args.require_review and result["review_permission"] not in {
        "owner_visible_review_required",
        "owner_approved_for_non_stable_planning",
    }:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
