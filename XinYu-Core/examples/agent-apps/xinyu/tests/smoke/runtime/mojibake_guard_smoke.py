from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import os
from pathlib import Path

from xinyu_text_variants import legacy_mojibake_variants


PROJECT_ROOT = ROOT

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
    "memory/context/proactive_presence_state.md",
    "memory/context/proactive_request_state.md",
    "memory/context/proactive_qq_dispatch_state.md",
    "memory/context/memory_braid_state.md",
    "memory/context/turn_coherence_state.md",
    "memory/context/initiative_spine_state.md",
    "memory/context/self_thought_state.md",
    "memory/context/emotion_council_state.md",
    "memory/context/impulse_soup_state.md",
    "memory/self/system_prompt_memory.md",
    "memory/self/personality_profile.md",
    "memory/self/narrative.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/emotions/current_state.md",
    "memory/relationships/index.md",
    "memory/people/owner.md",
    "STATE-OF-XINYU.md",
    "IMPLEMENTATION-NEXT.md",
    "RUNTIME-VALIDATION-NOTES.md",
    "VALIDATION-INDEX.md",
    "xinyu_turn_classifier.py",
    "xinyu_proactive_presence.py",
    "xinyu_voice_promotion_gate.py",
)

SCAN_EXTENSIONS = {".py", ".md", ".yaml", ".yml", ".json", ".jsonl", ".toml", ".txt"}
SCAN_EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "runtime",
    # Private/local owner state — never part of public CI surface.
    "memory",
}
SCAN_EXCLUDED_PREFIXES = (
    ("learning", "owner_supplied"),
    ("learning", "self_found"),
    ("ops", "archive"),
    ("ops", "reports"),
)
SCAN_EXCLUDED_RELS = {
    ("memory", "creative", "planning", "inspiration", "local_reference_index.jsonl"),
}
# Modules that intentionally keep dual-encoding / legacy mojibake *matcher*
# tables so runtime can still recognize corrupted owner text. Scanning them for
# "known fragments" is a false positive against their purpose.
SCAN_EXCLUDED_INTENTIONAL_MARKER_RELS = {
    "xinyu_bridge_promise_markers.py",
    "xinyu_bridge_codex_wait.py",
    "xinyu_text_variants.py",
    "tests/smoke/runtime/mojibake_guard_smoke.py",
}

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
    "\u5173\u4e8e\u88ab\u8bb0\u4f4f",
    "\u8fd8\u6ca1\u653e\u4e0b",
    "\u957f\u671f\u5173\u7cfb",
    "\u5177\u4f53\u5bf9\u8bdd",
    "\u53cd\u601d\u961f\u5217",
    "\u8bb0\u5fc6\u7559\u75d5",
    "\u5916\u90e8\u5b66\u4e60",
    "\u4e3b\u52a8\u7ebf\u7a0b",
    "\u611f\u60c5\u7cfb\u7edf",
    "\u8bb0\u5fc6\u7cfb\u7edf",
    "\u4e3b\u4eba\u683c",
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

DIRECT_VARIANT_MARKERS = tuple(
    (phrase, variant)
    for phrase in DIRECT_VARIANT_PHRASES
    for variant in legacy_mojibake_variants(phrase)
)

REVERSIBLE_MOJIBAKE_HINTS = frozenset(
    "".join(KNOWN_MOJIBAKE_FRAGMENTS) + "".join(variant for _, variant in DIRECT_VARIANT_MARKERS)
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
    if not any(ch in REVERSIBLE_MOJIBAKE_HINTS for ch in line):
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
    for phrase, variant in DIRECT_VARIANT_MARKERS:
        if variant in text:
            hits.append(f"{phrase!r} stored as {variant!r}")
    return hits


def _synthetic_guard_failures() -> list[str]:
    failures: list[str] = []
    for phrase in (
        "\u5173\u4e8e\u88ab\u8bb0\u4f4f",
        "\u53cd\u601d\u961f\u5217",
        "\u8bb0\u5fc6\u7559\u75d5",
        "\u957f\u671f\u5173\u7cfb",
    ):
        variants = legacy_mojibake_variants(phrase)
        if not variants:
            failures.append(f"synthetic guard has no legacy variants for {phrase!r}")
            continue
        if not any(_direct_variant_hits(variant) for variant in variants):
            failures.append(f"synthetic guard misses legacy variants for {phrase!r}")
    return failures


def _iter_guard_files() -> list[Path]:
    files: dict[str, Path] = {}
    for rel in CRITICAL_FILES:
        path = PROJECT_ROOT / rel
        files[str(path)] = path
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        current = Path(dirpath)
        current_parts = current.relative_to(PROJECT_ROOT).parts if current != PROJECT_ROOT else ()
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in SCAN_EXCLUDED_PARTS
            and not any((current_parts + (dirname,))[: len(prefix)] == prefix for prefix in SCAN_EXCLUDED_PREFIXES)
        ]
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() not in SCAN_EXTENSIONS:
                continue
            rel_parts = path.relative_to(PROJECT_ROOT).parts
            if rel_parts in SCAN_EXCLUDED_RELS:
                continue
            files[str(path)] = path
    return sorted(files.values(), key=lambda item: str(item.relative_to(ROOT)))


def _rel_key(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def _contains_literal_replacement_char(text: str) -> bool:
    """True when the file body has a real U+FFFD glyph, not just the escape ``\\ufffd``."""
    if "\ufffd" not in text:
        return False
    # Strip common intentional mentions used by detectors/tests.
    stripped = (
        text.replace("\\ufffd", "")
        .replace("\\uFFFD", "")
        .replace("U+FFFD", "")
        .replace("u+fffd", "")
    )
    return "\ufffd" in stripped


def main() -> int:
    failures: list[str] = _synthetic_guard_failures()
    checked = 0
    for path in _iter_guard_files():
        rel = _rel_key(path)
        if not path.exists():
            # Private/runtime seeds listed in CRITICAL_FILES may be absent on CI.
            if rel.startswith("memory/") or rel.startswith("runtime/"):
                continue
            failures.append(f"{rel}: missing")
            continue
        # Owner-private trees and intentional dual-encoding matcher tables.
        if rel.startswith("memory/") or rel in SCAN_EXCLUDED_INTENTIONAL_MARKER_RELS:
            checked += 1
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        if _contains_literal_replacement_char(text):
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
    print(f"mojibake_guard_smoke ok: {checked} project text files readable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
