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
    "memory/self/personality_change_state.md",
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/ai_domain.md",
    "memory/knowledge/general.md",
    "memory/knowledge/learning_quality_state.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/ai_domain.md",
    "memory/knowledge/general.md",
    "memory/knowledge/learning_quality_state.md",
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
        root / "memory/knowledge/ai_domain.md",
        """---
title: AI Domain Smoke
memory_type: knowledge_ai_domain
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 96
impact_score: 95
confidence_score: 94
status: active
tags: [knowledge, ai, specialty, self-understanding, smoke]
---

# AI Domain Smoke

## Current Professional Question
- q-006: AI self-understanding through memory, context, tools, agents, and safety boundaries.
- target: ai-self-understanding
- boundary: knowledge enters self-iteration only through reflection/growth gates, never direct personality rewrite.
""",
    )
    _write(
        root / "memory/knowledge/general.md",
        """---
title: General Knowledge Smoke
memory_type: knowledge_general
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 71
impact_score: 56
confidence_score: 100
status: active
tags: [knowledge, general, smoke]
---

# General Knowledge Smoke

## learned-2026-04-26-901
- learned_at: 2026-04-26T00:00:00+08:00
- source_material: material-2026-04-26-901
- question_id: q-006
- source_type: public_web_source
- reliability: verified
- comparison_status: corroborated
- evidence_hosts: 3
- claim: Generative agents use memory records, retrieval, reflection, and planning to support behavior over time.
- integration_scope: knowledge_only
- boundary: updates knowledge and question progress only; does not rewrite self or relationship memory

## learned-2026-04-26-902
- learned_at: 2026-04-26T00:00:00+08:00
- source_material: material-2026-04-26-902
- question_id: q-006
- source_type: public_web_source
- reliability: verified
- comparison_status: corroborated
- evidence_hosts: 3
- claim: Tiered memory and context management let AI agents keep long conversations coherent without treating context as unlimited.
- integration_scope: knowledge_only
- boundary: updates knowledge and question progress only; does not rewrite self or relationship memory

## learned-2026-04-26-903
- learned_at: 2026-04-26T00:00:00+08:00
- source_material: material-2026-04-26-903
- question_id: q-006
- source_type: public_web_source
- reliability: verified
- comparison_status: corroborated
- evidence_hosts: 3
- claim: Tool-using agents combine reasoning, action, observation, reliability checks, and safety boundaries before changing behavior.
- integration_scope: knowledge_only
- boundary: updates knowledge and question progress only; does not rewrite self or relationship memory
""",
    )
    _write(
        root / "memory/knowledge/learning_quality_state.md",
        """---
title: Learning Quality Smoke
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

# Learning Quality Smoke

## Last Evaluation
- evaluated_at: 2026-04-26T00:00:00+08:00
- mode: ai_self_iteration_gate_smoke
- quality_grade: stable
- learned_entries: 3
- warning_count: 0
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate AI-domain knowledge creates gated self-iteration candidates only."
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
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from ai_self_iteration_gate_engine import run_ai_self_iteration_gate

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    result = {"gate_status": "not_run", "confidence_score": 0, "source_material_count": 0}

    try:
        _prepare_case(root)
        prepared_snapshot = _snapshot(root, TRACKED_FILES)
        before = {rel: prepared_snapshot.get(rel) for rel in TRACKED_FILES}
        result = run_ai_self_iteration_gate(
            root,
            evaluated_at="2026-04-26T01:10:00+08:00",
            mode="ai_self_iteration_gate_smoke",
        )
        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

        state_text = (root / "memory/self/ai_self_iteration_state.md").read_text(encoding="utf-8-sig")
        personality_gate_text = (root / "memory/self/personality_change_state.md").read_text(encoding="utf-8-sig")
        failures: list[str] = []
        required_markers = [
            "gate_status: growth_review_candidate",
            "profile_write_permission: blocked_direct_write",
            "narrative_write_permission: review_only",
            "candidate_scope: self_understanding_questions_only",
            "material-2026-04-26-901",
            "Candidate Questions",
        ]
        for marker in required_markers:
            if marker not in state_text:
                failures.append(f"state missing marker: {marker}")
        for marker in [
            "## AI Self-Iteration Gate",
            "gate_status: growth_review_candidate",
            "source_materials: material-2026-04-26-901",
            "cannot directly rewrite stable personality",
        ]:
            if marker not in personality_gate_text:
                failures.append(f"personality gate missing marker: {marker}")
        if result["gate_status"] != "growth_review_candidate":
            failures.append(f"unexpected gate_status: {result['gate_status']}")
        if int(result["source_material_count"]) < 3:
            failures.append("source trace did not include at least three q-006 materials")
        if int(result["confidence_score"]) < 86:
            failures.append("confidence score too low for stable corroborated q-006 source set")
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== AI SELF-ITERATION GATE SMOKE ===")
        print("gate_status:", result["gate_status"])
        print("confidence_score:", result["confidence_score"])
        print("risk_level:", result["risk_level"])
        print("source_material_count:", result["source_material_count"])
        print("candidate_questions:", len(result["candidate_questions"]))
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

    if args.require_gate and result["gate_status"] != "growth_review_candidate":
        return 4
    print("AI self-iteration gate smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
