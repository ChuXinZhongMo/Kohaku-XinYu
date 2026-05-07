from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path


def _ensure_import_paths(root: Path) -> None:
    repo_src = root.parents[2] / "src"
    custom = root / "custom"
    for path in (repo_src, custom):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _seed(root: Path) -> None:
    _write(root / "memory/context/turn_mode_state.md", "- mode: maintenance_schedule_turn\n")
    _write(
        root / "memory/context/owner_permission_grants.md",
        "- grant_ai_self_iteration_review: approved_for_non_stable_planning\n",
    )
    _write(root / "memory/context/capability_zones_state.md", "")
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
importance_score: 91
impact_score: 90
confidence_score: 94
status: active
tags: [self, ai, growth, gate, smoke]
---

# AI Self-Iteration Gate State

## Last Evaluation
- evaluated_at: 2026-04-26T00:00:00+08:00
- mode: ai_self_iteration_review_bridge_smoke_seed
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
- How should memory decide what stays active, dormant, or forgotten?
- When does reflection become a real self-change candidate?
- How should tools stay tools instead of becoming identity?
- Which safety boundaries protect growth?
""",
    )


class FakeContext:
    def __init__(self, working_dir: Path) -> None:
        self.working_dir = str(working_dir)
        self.state: dict[str, str] = {}

    def get_state(self, key: str) -> str | None:
        return self.state.get(key)

    def set_state(self, key: str, value: str) -> None:
        self.state[key] = value


async def _run_plugin(temp_root: Path) -> FakeContext:
    from ai_self_iteration_review_bridge_plugin import AiSelfIterationReviewBridgePlugin

    ctx = FakeContext(temp_root)
    plugin = AiSelfIterationReviewBridgePlugin(
        options={"enabled": True, "min_interval_seconds": 10800}
    )
    await plugin.on_load(ctx)  # type: ignore[arg-type]
    await plugin.post_llm_call([], "", {})
    return ctx


def main() -> int:
    root = Path(__file__).resolve().parent
    _ensure_import_paths(root)
    failures: list[str] = []

    config = (root / "config.yaml").read_text(encoding="utf-8-sig")
    for marker in (
        "xinyu_ai_self_iteration_review_bridge",
        "./custom/ai_self_iteration_review_bridge_plugin.py",
        "AiSelfIterationReviewBridgePlugin",
    ):
        if marker not in config:
            failures.append(f"config missing review bridge marker: {marker}")

    with tempfile.TemporaryDirectory(prefix="xinyu-review-bridge-") as tmp:
        temp_root = Path(tmp)
        _seed(temp_root)
        ctx = asyncio.run(_run_plugin(temp_root))
        review = (temp_root / "memory/self/ai_self_iteration_review_state.md").read_text(
            encoding="utf-8-sig"
        )
        for marker in (
            "proposal-ai-architecture-001",
            "proposal-personality-pressure-001",
            "proposal-expression-preference-001",
            "proposal-safety-boundary-001",
            "review_permission: owner_approved_for_non_stable_planning",
            "stable_profile_write_permission: review_only_not_auto_apply",
            "stable_files_touched_by_review: none",
        ):
            if marker not in review:
                failures.append(f"review bridge output missing marker: {marker}")
        if "ai_self_iteration_review_last_run" not in ctx.state:
            failures.append("review bridge did not persist last-run state")

    if failures:
        print("AI self-iteration review bridge smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("AI self-iteration review bridge smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
