from __future__ import annotations

from pathlib import Path

from xinyu_text_variants import legacy_mojibake_variants


ROOT = Path(__file__).resolve().parent

CRITICAL_FILES = (
    "prompts/live_voice_card.md",
    "prompts/system.md",
    "prompts/output.md",
    "memory-seeds/context/persona_life_anchors.md",
    "memory-seeds/context/real_world_anchor_policy.md",
    "memory-seeds/context/life_month_slots.md",
    "memory-seeds/self/system_prompt_memory.md",
    "memory/context/real_world_anchor_policy.md",
    "memory/context/codex_delegation_policy.md",
    "memory/context/life_month_slots.md",
    "memory/context/current_life_month_context.md",
    "memory/context/persona_life_anchors.md",
    "memory/context/recent_context.md",
    "memory/self/system_prompt_memory.md",
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/emotions/current_state.md",
    "memory/relationships/index.md",
    "memory/people/owner.md",
    "plan.md",
    "STATE-OF-XINYU.md",
    "IMPLEMENTATION-NEXT.md",
    "RUNTIME-VALIDATION-NOTES.md",
    "VALIDATION-INDEX.md",
    "xinyu_turn_classifier.py",
    "xinyu_proactive_presence.py",
    "xinyu_voice_promotion_gate.py",
)

COMMON_CHARS = (
    "\u5fc3\u7389\u54e5\u54e5\u4eba\u683c\u8bb0\u5fc6\u58f0\u97f3"
    "\u60c5\u7eea\u751f\u6d3b\u4e0d\u662f\u4e0d\u8981\u8bf4\u8bdd"
    "\u7528\u6237\u4e3b\u4eba\u5ba2\u6237\u604b\u4eba\u53d8\u5316"
    "\u9879\u76ee\u6587\u4ef6\u8ba1\u5212\u73b0\u5728\u77e5\u9053"
    "\u771f\u5b9e\u4e2d\u6587\u7ef4\u62a4\u9636\u6bb5\u5173\u952e"
    "\u4fee\u590d\u5173\u7cfb\u95ee\u9898\u56de\u7b54\u7cfb\u7edf"
)

DIRECT_VARIANT_PHRASES = (
    "\u5fc3\u7389",
    "\u54e5\u54e5",
    "\u8bb0\u5fc6",
    "\u4eba\u683c",
    "\u58f0\u97f3",
    "\u60c5\u7eea",
    "\u751f\u6d3b",
    "\u4e0d\u50cf\u4eba",
    "\u4e0d\u81ea\u7136",
    "\u673a\u68b0",
    "\u6a21\u677f",
    "\u5ba2\u670d",
    "\u7528\u8bcd",
    "\u4e2d\u6587\u4e92\u8054\u7f51",
    "\u6ca1\u4ec0\u4e48\u53d8\u5316",
    "\u6ca1\u843d\u5230\u8bf4\u8bdd\u91cc",
    "\u611f\u60c5\u7cfb\u7edf",
    "\u8bb0\u5fc6\u7cfb\u7edf",
    "\u67b6\u6784",
    "\u7cfb\u7edf",
)

KNOWN_MOJIBAKE_FRAGMENTS = (
    "\u93b4",
    "\u9422",
    "\u6d63",
    "\u9359",
    "\u93c4",
    "\u7ecb",
    "\u9366",
    "\u6d93",
    "\u951b",
    "\u9239",
    "\u8e47\u51a6\u7bf8\u5e00",
    "\u9361",
)


def _common_hits(text: str) -> int:
    return sum(text.count(ch) for ch in COMMON_CHARS)


def _rareish_count(text: str) -> int:
    count = 0
    for ch in text:
        codepoint = ord(ch)
        if 0x7000 <= codepoint <= 0x9FFF or 0xE000 <= codepoint <= 0xF8FF:
            count += 1
        elif ch in {"\u20ac", "\u2103", "\u2032", "\u2033"}:
            count += 1
    return count


def _looks_reversible_mojibake(line: str) -> bool:
    if len(line.strip()) < 2:
        return False
    try:
        fixed = line.encode("gb18030").decode("utf-8")
    except UnicodeDecodeError:
        return False
    if fixed == line:
        return False
    return _rareish_count(line) + _common_hits(fixed) - _common_hits(line) >= 3


def _direct_variant_hits(text: str) -> list[str]:
    hits: list[str] = []
    for phrase in DIRECT_VARIANT_PHRASES:
        for variant in legacy_mojibake_variants(phrase):
            if variant in text:
                hits.append(f"{phrase!r} stored as {variant!r}")
    return hits


def main() -> int:
    failures: list[str] = []
    for rel in CRITICAL_FILES:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"{rel}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        if "\ufffd" in text:
            failures.append(f"{rel}: contains replacement character U+FFFD")
        fragment_hits = [fragment for fragment in KNOWN_MOJIBAKE_FRAGMENTS if fragment in text]
        if fragment_hits:
            failures.append(f"{rel}: contains known mojibake fragments: {fragment_hits[:3]!r}")
        for line_number, line in enumerate(text.splitlines(), 1):
            if _looks_reversible_mojibake(line):
                failures.append(f"{rel}:{line_number}: likely reversible mojibake")
                break
        direct_hits = _direct_variant_hits(text)
        if direct_hits:
            failures.append(f"{rel}: direct mojibake markers: {direct_hits[:3]!r}")
    if failures:
        print("mojibake_guard_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"mojibake_guard_smoke ok: {len(CRITICAL_FILES)} critical files readable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
