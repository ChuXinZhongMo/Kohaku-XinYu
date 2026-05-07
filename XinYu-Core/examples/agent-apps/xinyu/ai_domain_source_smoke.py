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


AI_DOMAIN_TRACKED_FILES = [
    "memory/context/active_questions.md",
    "memory/context/question_pipeline_state.md",
    "memory/context/question_states.md",
    "memory/context/exploration_queue.md",
    "memory/knowledge/source_gate_state.md",
    "memory/knowledge/source_notes.md",
    "memory/knowledge/source_reliability_state.md",
    "memory/knowledge/source_integration_gate_state.md",
    "memory/knowledge/source_requests.md",
    "memory/knowledge/source_request_planner_state.md",
    "memory/knowledge/general.md",
    "memory/knowledge/ai_domain.md",
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
    "memory/knowledge/general.md",
    "memory/knowledge/ai_domain.md",
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
title: AI Domain Source Smoke Questions
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
tags: [question, ai, source, smoke]
---

# 当前活跃问题

## q-930
- created_at: 2026-04-25T00:00:00+08:00
- question: AI 如何通过理解自身机制、记忆、上下文、能力和安全边界来逐步迭代成长
- source_trigger: ai_domain_source_smoke
- target: ai-self-understanding
- urgency: high
- emotional_weight: 84
- status: open
- next_action: 进入 AI 专业知识来源闸门
""",
    )


def _reset_requests(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_requests.md",
        """---
title: Source Requests Smoke
memory_type: source_requests
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
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
    parser = argparse.ArgumentParser(description="Validate AI-domain source lane with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-ai-domain", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from question_pipeline_engine import run_question_pipeline
    from source_gate_engine import run_source_gate
    from source_integration_gate_engine import run_source_integration_gate
    from source_reliability_engine import run_source_reliability
    from source_request_planner_engine import run_source_request_planner

    restore_paths = _discover_restore_files(root, AI_DOMAIN_TRACKED_FILES) if args.restore_after else AI_DOMAIN_TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in AI_DOMAIN_TRACKED_FILES}

    failures: list[str] = []
    pipeline_result = {"external_ids": []}
    source_gate_result = {"candidate_count": 0, "items": []}
    reliability_result = {"pairs": []}
    integration_result = {"integration_permission": "unknown", "ready_candidates": 0}
    planner_result = {"planned_requests": 0, "pending_url_requests": 0}

    try:
        _prepare_active_questions(root)
        _reset_requests(root)
        pipeline_result = run_question_pipeline(root, mode="ai_domain_source_smoke_pipeline")
        source_gate_result = run_source_gate(root, mode="ai_domain_source_smoke_gate")
        reliability_result = run_source_reliability(root, mode="ai_domain_source_smoke_reliability")
        integration_result = run_source_integration_gate(root, mode="ai_domain_source_smoke_integration")
        planner_result = run_source_request_planner(root, mode="ai_domain_source_smoke_planner")

        requests_text = (root / "memory/knowledge/source_requests.md").read_text(encoding="utf-8-sig")
        pair_map = {qid: level for qid, _, level in reliability_result["pairs"]}
        if pipeline_result["external_ids"] != ["q-930"]:
            failures.append("q-930 did not become the only external AI-domain candidate")
        if int(source_gate_result["candidate_count"]) != 1:
            failures.append("source gate did not receive exactly one AI-domain candidate")
        if source_gate_result["items"] != [("q-930", "ai-self-understanding")]:
            failures.append("source gate target was not ai-self-understanding")
        if pair_map.get("q-930") != "high_ready":
            failures.append("AI-domain reliability was not high_ready")
        if integration_result["integration_permission"] != "prepare_only":
            failures.append("source integration gate did not open prepare_only for AI-domain")
        if int(planner_result["planned_requests"]) != 1:
            failures.append("source request planner did not create an AI-domain request")
        if int(planner_result["pending_url_requests"]) != 1:
            failures.append("AI-domain request should be pending_url without explicit URL")
        if "large language model memory agents context tool use alignment safety reliable source" not in requests_text:
            failures.append("AI-domain request query was not specialized")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in AI_DOMAIN_TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))
        if protected_changed:
            failures.append("protected files changed: " + ", ".join(protected_changed))

        print("=== AI DOMAIN SOURCE SMOKE ===")
        print("external_ids:", ", ".join(pipeline_result["external_ids"]) or "none")
        print("source_gate_candidates:", source_gate_result["candidate_count"])
        print(
            "source_gate_items:",
            ", ".join(f"{qid}:{target}" for qid, target in source_gate_result["items"]) or "none",
        )
        print(
            "reliability_pairs:",
            ", ".join(f"{qid}:{target}:{level}" for qid, target, level in reliability_result["pairs"]) or "none",
        )
        print("integration_permission:", integration_result["integration_permission"])
        print("planned_requests:", planner_result["planned_requests"])
        print("pending_url_requests:", planner_result["pending_url_requests"])
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(AI_DOMAIN_TRACKED_FILES)}")
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
    if args.require_ai_domain and (
        pipeline_result["external_ids"] != ["q-930"]
        or integration_result["integration_permission"] != "prepare_only"
        or int(planner_result["planned_requests"]) != 1
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
