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
        "xinyu_personality_evolution.py",
        "xinyu_persona_runtime.py",
        "personality_evolution_smoke.py",
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
        "xinyu_thought_seeds.py",
        "xinyu_private_thought_events.py",
        "private_thought_events_smoke.py",
        "custom/desktop_thoughts_bridge_plugin.py",
    ],
}

REQUIRED_MARKERS = {
    "xinyu_autonomy_journal.py": [
        "Private Thought Event Material For XinYu Owner-Visible Note",
        "render_persona_thoughts",
        "build_private_thought_note_material",
    ],
    "xinyu_thought_seeds.py": [
        "Thought Seeds",
        "output_form: owner-visible private desktop note",
    ],
    "xinyu_private_thought_events.py": [
        "Private Thought State",
        "record_private_thought_reply_link",
        "record_private_thought_outcome",
        "Self Model State",
    ],
    "xinyu_persona_runtime.py": [
        "Persona Runtime",
        "Growth Trial Layer",
        "LIFE_ANCHOR_MARKERS",
        "life_anchor_hit",
        "background texture is optional",
    ],
    "xinyu_personality_evolution.py": [
        "Personality Evolution State",
        "runtime_trial_only",
        "Deprecated Reactions",
    ],
    "xinyu_voice_learning.py": [
        "record_voice_correction",
        "voice_calibration",
    ],
}


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []
    for group, rels in REQUIRED_CAPABILITIES.items():
        for rel in rels:
            if not (root / rel).exists():
                failures.append(f"{group} missing {rel}")

    for rel, markers in REQUIRED_MARKERS.items():
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker not in text:
                failures.append(f"{rel} missing marker: {marker}")

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
