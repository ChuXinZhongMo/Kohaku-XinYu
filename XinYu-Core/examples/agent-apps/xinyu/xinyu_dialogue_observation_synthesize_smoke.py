from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_dialogue_observation_synthesize import main, parse_accepted_drafts, synthesize_rules


def _snapshot_memory(root: Path) -> set[str]:
    memory = root / "memory"
    if not memory.exists():
        return set()
    return {str(path.relative_to(root)) for path in memory.rglob("*") if path.is_file()}


def run_smoke() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-dialogue-observation-synth-") as tmp:
        root = Path(tmp)
        input_path = root / "accepted_rule_card_drafts.md"
        output_path = root / "auto_rule_synthesis_drafts.md"
        input_path.write_text(
            """# Dialogue Observation Accepted Rule Card Drafts

## Draft 1: dlgobs-a

source_ref: audio_2087_cocktail / dlgobs-a
source_review: audio_review.md
source_file: source.docx
line_index: 10
speaker:
signals: low_mood, gentle_attention
reject_risks: audio_roleplay_intimacy
xinyu_fit_score: 10

scene_summary:
xinyu_rule:

## Draft 2: dlgobs-b

source_ref: game_va11halla / dlgobs-b
source_review: game_review.md
source_file: source.txt
line_index: 20
speaker:
signals: remembered_detail, repair
reject_risks:
xinyu_fit_score: 12

scene_summary:
xinyu_rule:
""",
            encoding="utf-8",
        )
        before_memory = _snapshot_memory(root)
        rc = main(["--input", str(input_path), "--output", str(output_path)])
        after_memory = _snapshot_memory(root)
        accepted = parse_accepted_drafts(input_path)
        text = output_path.read_text(encoding="utf-8-sig")
        inline_text = synthesize_rules(accepted)

        if rc != 0:
            failures.append("main should return 0")
        if len(accepted) != 2:
            failures.append("accepted drafts should parse")
        if "低情绪先接住" not in text:
            failures.append("low mood rule candidate missing")
        if "被纠正后下一句直接变" not in text:
            failures.append("repair rule candidate missing")
        if "记得旧事，但不暴露检索机制" not in text:
            failures.append("remembered detail rule candidate missing")
        if "音声台本只取低强度关系动作" not in text:
            failures.append("audio guardrail missing")
        if "stable_profile_write: blocked" not in text:
            failures.append("boundary marker missing")
        if "runtime_integration: blocked" not in text:
            failures.append("runtime boundary marker missing")
        if "```text" in text or "prev:" in text or "line:" in text or "next:" in text:
            failures.append("source excerpt leaked into synthesis output")
        if "auto_synthesized_owner_review_required" not in inline_text:
            failures.append("synthesis function output missing status")
        if before_memory != after_memory:
            failures.append("synthesis must not write memory")

    return failures


def main_smoke() -> int:
    failures = run_smoke()
    if failures:
        print("xinyu_dialogue_observation_synthesize_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS xinyu_dialogue_observation_synthesize_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_smoke())
