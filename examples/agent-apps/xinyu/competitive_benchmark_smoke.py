from __future__ import annotations

from pathlib import Path


REQUIRED_CAPABILITIES = {
    "memory_retrieval_target": [
        "memory/self/mind_loop_policy.md",
        "memory/self/mind_loop_state.md",
        "memory/context/recent_context.md",
        "memory/archive/long_term_memory_gate_state.md",
    ],
    "proactive_presence_target": [
        "memory/context/initiative_state.md",
        "memory/context/proactive_presence_state.md",
        "xinyu_proactive_presence.py",
    ],
    "self_learning_target": [
        "memory/self/voice_profile_zh.md",
        "memory/self/voice_calibration_log.md",
        "xinyu_voice_learning.py",
    ],
    "persona_runtime_target": [
        "xinyu_persona_runtime.py",
        "persona_runtime_smoke.py",
        "chinese_voice_guard_smoke.py",
    ],
    "ai_research_target": [
        "memory/knowledge/research_loop_dry_run_state.md",
        "xinyu_research_loop_dry_run.py",
        "memory/self/ai_self_iteration_review_state.md",
    ],
    "desktop_thoughts_target": [
        "xinyu_desktop_thoughts.py",
        "xinyu_autonomy_journal.py",
        "project-plans/core-mind-loop/plan.md",
    ],
}


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []
    for group, rels in REQUIRED_CAPABILITIES.items():
        for rel in rels:
            if not (root / rel).exists():
                failures.append(f"{group} missing {rel}")

    plan = (root / "project-plans/core-mind-loop/plan.md").read_text(encoding="utf-8")
    roadmap = (root / "project-plans/XINYU-COMPETITIVE-ROADMAP.md").read_text(encoding="utf-8")
    for marker in (
        "must not copy their path",
        "guarded self-directed growth",
        "Desktop Thoughts",
        "Persona Runtime",
        "AI Research Loop",
    ):
        if marker not in plan:
            failures.append(f"core mind-loop plan missing marker: {marker}")
    for marker in (
        "Desktop Thoughts",
        "Memory Retrieval v2",
        "Chinese Voice Learning v1",
        "Proactive Presence v1",
    ):
        if marker not in roadmap:
            failures.append(f"competitive roadmap missing marker: {marker}")

    if failures:
        print("Competitive benchmark smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Competitive benchmark smoke passed")
    print(f"capability_groups: {len(REQUIRED_CAPABILITIES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
