from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import re
import sys


CHECKED_FILES = [
    "prompts/output.md",
    "prompts/system.md",
    "memory/emotions/current_state.md",
    "memory/emotions/taxonomy.md",
    "memory/dreams/dream_weight_state.md",
    "memory/archive/long_term_memory_gate_state.md",
    "memory/self/personality_profile.md",
    "memory/self/personality_change_state.md",
    "memory/self/boundaries.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "TEST-SCENARIOS.md",
    "tests/smoke/runtime/integration/expression_runtime_smoke.py",
    "tests/smoke/dialogue/integration/behavior_regression_smoke.py",
    "tests/smoke/voice/integration/personality_detail_smoke.py",
    "tests/smoke/initiative/integration/emotion_vector_sync_smoke.py",
    "tests/smoke/life/integration/dream_weight_smoke.py",
    "tests/smoke/life/integration/reflection_dream_residue_smoke.py",
    "tests/smoke/life/integration/consolidation_dream_weight_smoke.py",
    "tests/smoke/memory/integration/long_term_memory_gate_smoke.py",
    "tests/smoke/voice/integration/personality_growth_gate_smoke.py",
    "custom/reflection_output_engine.py",
    "custom/consolidation_engine.py",
    "custom/long_term_memory_gate_engine.py",
    "custom/personality_growth_gate_engine.py",
    "PROMPT-TUNING.md",
    "STATE-OF-XINYU.md",
    "IMPLEMENTATION-NEXT.md",
]


MOJIBAKE_MARKERS = [
    "\u6d63\u72b2",
    "\u934f\u5d07",
    "\u93af\u546f",
    "\u942d\u30e8",
    "\u93c9\u30e6",
    "\u7edb\u682b",
    "\u741a",
    "\u7f01",
    "\u6d93\u54c4",
    "\u95ab\u6c31",
    "\u9418\u8236",
    "\u9418\u8235",
    "\u8930\u64b3",
    "\u93b4\u621c",
    "\u9225",
    "?" * 6,
    "\u951f\u65a4\u62f7",
]


REQUIRED_OUTPUT_SNIPPETS = [
    "Do not polish the reply until it becomes service prose.",
    "Do not replace it with a generic good-night, reassurance formula, or service promise.",
    "Return only XinYu's outward reply text.",
]


REQUIRED_SYSTEM_SNIPPETS = [
    "The latest user message wins.",
    "Never output XML-like pseudo tools",
    "Do not leave empty future promises",
    "self/personality_profile.md",
]


FORBIDDEN_IN_GOOD_EXAMPLES = [
    "我会接住你",
    "我会一直在",
    "我会陪着你",
    "你可以慢慢说",
    "你不用担心",
    "我会认真倾听你的情绪",
    "我就在这里温柔地守着你",
    "如果你愿意的话可以和我说说",
]


PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")


def _failures_for_text(rel_path: str, text: str) -> list[str]:
    failures: list[str] = []
    for marker in MOJIBAKE_MARKERS:
        if marker in text:
            failures.append(f"{rel_path}: mojibake marker found: {marker}")
    if PRIVATE_USE_RE.search(text):
        failures.append(f"{rel_path}: private-use replacement character found")
    return failures


def _section(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    start_index += len(start)
    end_index = text.find(end, start_index)
    if end_index < 0:
        return text[start_index:]
    return text[start_index:end_index]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = ROOT
    failures: list[str] = []

    for rel_path in CHECKED_FILES:
        path = root / rel_path
        if not path.exists():
            failures.append(f"{rel_path}: missing checked file")
            continue
        failures.extend(_failures_for_text(rel_path, path.read_text(encoding="utf-8")))

    output_text = (root / "prompts" / "output.md").read_text(encoding="utf-8")
    for snippet in REQUIRED_OUTPUT_SNIPPETS:
        if snippet not in output_text:
            failures.append(f"prompts/output.md: required snippet missing: {snippet}")

    good_examples = _section(output_text, "Good tone examples:", "Bad tone examples:")
    for phrase in FORBIDDEN_IN_GOOD_EXAMPLES:
        if phrase in good_examples:
            failures.append(
                "prompts/output.md: forbidden comfort template appears in good examples: "
                f"{phrase}"
            )

    system_text = (root / "prompts" / "system.md").read_text(encoding="utf-8")
    for snippet in REQUIRED_SYSTEM_SNIPPETS:
        if snippet not in system_text:
            failures.append(f"prompts/system.md: required output-guarantee snippet missing: {snippet}")

    if failures:
        print("Expression tone smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Expression tone smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
