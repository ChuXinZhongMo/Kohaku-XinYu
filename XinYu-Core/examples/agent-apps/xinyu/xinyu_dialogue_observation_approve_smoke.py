from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_dialogue_observation_approve import approve_rules, parse_synthesized_rules


def _snapshot_memory(root: Path) -> set[str]:
    memory = root / "memory"
    if not memory.exists():
        return set()
    return {str(path.relative_to(root)) for path in memory.rglob("*") if path.is_file()}


def run_smoke() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-dialogue-observation-approve-") as tmp:
        root = Path(tmp)
        input_path = root / "auto_rule_synthesis_drafts.md"
        output_path = root / "owner_rule_cards.md"
        input_path.write_text(
            """# Dialogue Observation Auto Rule Synthesis Drafts

## Rule Candidate 1: 低情绪先接住，不急着解决

rule_key: low_mood_before_solution
confidence: medium
support_count: 6
support_refs:
- sample / line 1 / dlgobs-a

scene_summary: 对方状态低。

relationship_state: 熟人私聊。

trigger: owner 说累了。

observed_response_strategy: 先短句接住。

relationship_effect: 对方更容易继续说。

xinyu_rule: owner 低落时先接住。

xinyu_do_not_learn: 不学客服安慰。

review_status: auto_draft_owner_review_required
stable_profile_write: blocked
runtime_integration: blocked
model_training: blocked
""",
            encoding="utf-8",
        )
        before_memory = _snapshot_memory(root)
        result = approve_rules(
            input_path,
            output_path,
            approved_at="2026-05-07T04:00:00+08:00",
            approval_note="owner smoke approved",
        )
        after_memory = _snapshot_memory(root)
        rules = parse_synthesized_rules(input_path)
        text = output_path.read_text(encoding="utf-8-sig")

        if result.get("approved_rule_count") != 1:
            failures.append("expected one approved rule")
        if len(rules) != 1:
            failures.append("synthesized rules should parse")
        for marker in (
            "status: owner_direction_approved",
            "review_status: owner_direction_approved",
            "promotion_stage: voice_lesson_candidate",
            "stable_profile_write: blocked",
            "runtime_integration: blocked",
            "model_training: blocked",
            "source_text_policy: raw dialogue excerpts intentionally omitted",
        ):
            if marker not in text:
                failures.append(f"approved cards missing marker: {marker}")
        if "```text" in text or "prev:" in text or "line:" in text or "next:" in text:
            failures.append("source excerpt leaked into approved rule cards")
        if before_memory != after_memory:
            failures.append("approval must not write memory")

    return failures


def main_smoke() -> int:
    failures = run_smoke()
    if failures:
        print("xinyu_dialogue_observation_approve_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS xinyu_dialogue_observation_approve_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_smoke())
