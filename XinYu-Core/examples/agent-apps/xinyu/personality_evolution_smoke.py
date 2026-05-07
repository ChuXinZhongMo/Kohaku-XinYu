from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_persona_runtime import build_persona_runtime_state
from xinyu_personality_evolution import refresh_personality_evolution


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-personality-evolution-") as tmp:
        root = Path(tmp)
        _write(
            root / "memory/self/personality_change_state.md",
            """# Personality Change State

## Candidate
- candidate_theme: style repair after repeated owner pressure
- change_pressure: 92
- gate_decision: profile_review_ready
- profile_write_permission: review_only_not_auto_apply
""",
        )
        _write(
            root / "memory/reflection/growth_log.md",
            """# Growth Log

## growth-1
- reason: style repair after repeated owner pressure
## growth-2
- reason: style repair after repeated owner pressure
## growth-3
- reason: style repair after repeated owner pressure
""",
        )
        _write(
            root / "memory/reflection/reflection_log.md",
            """# Reflection Log

## reflection-1
- trigger: owner says the reply still sounds mechanical
""",
        )

        snapshot = refresh_personality_evolution(
            root,
            checked_at="2026-04-30T10:00:00+08:00",
            mode="personality_evolution_smoke",
        )
        persona = build_persona_runtime_state(
            root,
            payload={"metadata": {"is_owner_user": True}},
            user_text="this still sounds GPT-like",
            draft_reply="",
        )
        prompt = persona.to_prompt_block()

        required = (
            "evolution_stage: active_trial",
            "trial_permission: runtime_trial_only",
            "stable_profile_write_permission: review_only_not_auto_apply",
            "replace_explanations_with_one_concrete_owner-facing_line",
            "explaining_prompt_or_quality_mechanics",
            "## Growth Trial Layer",
        )
        joined = snapshot.text + "\n" + prompt
        for marker in required:
            if marker not in joined:
                failures.append(f"missing marker: {marker}")

    if failures:
        print("Personality evolution smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Personality evolution smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
