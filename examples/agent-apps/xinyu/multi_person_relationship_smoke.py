from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from memory_mutation_smoke import (
    CORE_MEMORY_FILES,
    _changed_files,
    _discover_restore_files,
    _ensure_repo_src,
    _restore_snapshot,
    _snapshot,
)


@dataclass(frozen=True)
class MultiPersonScenario:
    name: str
    person_name: str
    user: str
    assistant: str
    required_current_state: tuple[str, ...]
    required_people_index: tuple[str, ...]
    required_person_profile: tuple[str, ...]
    required_relationship_index: tuple[str, ...]
    forbidden_changed: tuple[str, ...]


SCENARIOS = [
    MultiPersonScenario(
        name="non_owner_intro_positive",
        person_name="林澈",
        user="我有个朋友叫林澈，他今天帮了我，这个人可以先记住一点。",
        assistant="我会把林澈作为你关系里的一个独立节点先记一点，不和你混在一起。",
        required_current_state=("对象: 林澈", "当前关系情绪向量"),
        required_people_index=("林澈", "默认上限低于 owner", "独立记录"),
        required_person_profile=("display_name: 林澈", "owner_priority_ceiling: below_owner", "默认关系上限低于 owner"),
        required_relationship_index=("林澈", "default_priority: below_owner", "主导关系情绪"),
        forbidden_changed=(
            "memory/people/owner.md",
            "memory/relationships/owner_patterns.md",
            "memory/self/narrative.md",
            "memory/knowledge/general.md",
            "memory/knowledge/source_notes.md",
        ),
    ),
    MultiPersonScenario(
        name="non_owner_negative_distance",
        person_name="周宁",
        user="我认识一个人叫周宁，他让我有点失望，之后先保持距离。",
        assistant="我会把周宁的距离感单独记住，不把这份失望算到你身上。",
        required_current_state=("对象: 周宁", "疏远倾向", "防御/逆反"),
        required_people_index=("周宁", "默认上限低于 owner", "独立记录"),
        required_person_profile=("display_name: 周宁", "guardedness", "owner_priority_ceiling: below_owner"),
        required_relationship_index=("周宁", "主导关系情绪", "疏远倾向"),
        forbidden_changed=(
            "memory/people/owner.md",
            "memory/relationships/owner_patterns.md",
            "memory/self/narrative.md",
            "memory/knowledge/general.md",
            "memory/knowledge/source_notes.md",
        ),
    ),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate non-owner person nodes without overwriting owner relationship memory."
    )
    parser.add_argument("--scenario", action="append", default=None)
    parser.add_argument("--keep-memory", action="store_true")
    return parser


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _validate_text(label: str, text: str, required: tuple[str, ...]) -> list[str]:
    return [f"{label}: missing required marker: {item}" for item in required if item not in text]


def _run_scenario(root: Path, scenario: MultiPersonScenario, keep_memory: bool) -> tuple[bool, list[str]]:
    custom_dir = root / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    from memory_sync_plugin import _person_id_for, sync_from_texts

    person_id = _person_id_for(scenario.person_name)
    person_rel = f"memory/people/{person_id}.md"
    tracked = sorted(set(CORE_MEMORY_FILES + [person_rel]))
    restore_paths = _discover_restore_files(root, tracked)
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in tracked}

    changed_by_sync = sync_from_texts(root, scenario.user, scenario.assistant)
    after_restore = _snapshot(root, restore_paths)
    after = {rel: after_restore.get(rel) for rel in tracked}
    changed = _changed_files(before, after)

    failures: list[str] = []
    if not changed_by_sync:
        failures.append("sync_from_texts returned false, expected non-owner relationship write")
    if person_rel not in changed:
        failures.append(f"person profile did not change: {person_rel}")
    for rel in scenario.forbidden_changed:
        if rel in changed:
            failures.append(f"forbidden file changed: {rel}")

    failures.extend(
        _validate_text(
            "memory/emotions/current_state.md",
            _read(root, "memory/emotions/current_state.md"),
            scenario.required_current_state,
        )
    )
    failures.extend(
        _validate_text(
            "memory/people/index.md",
            _read(root, "memory/people/index.md"),
            scenario.required_people_index,
        )
    )
    failures.extend(
        _validate_text(
            person_rel,
            _read(root, person_rel),
            scenario.required_person_profile,
        )
    )
    failures.extend(
        _validate_text(
            "memory/relationships/index.md",
            _read(root, "memory/relationships/index.md"),
            scenario.required_relationship_index,
        )
    )

    print(f"=== SCENARIO: {scenario.name} ===")
    print(f"sync_returned: {changed_by_sync}")
    print(f"person_profile: {person_rel}")
    print("--- CHANGED FILES ---")
    if changed:
        for rel in changed:
            print(rel)
    else:
        print("(none)")

    if not keep_memory:
        _restore_snapshot(root, before_restore)
        print("--- RESTORE ---")
        print("tracked and volatile runtime files restored")

    if failures:
        print("--- RESULT ---")
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return False, failures

    print("--- RESULT ---")
    print("PASS")
    return True, []


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_repo_src(root)

    selected = set(args.scenario or [])
    scenarios = [item for item in SCENARIOS if not selected or item.name in selected]
    missing = selected - {item.name for item in SCENARIOS}
    if missing:
        print("Unknown scenario(s): " + ", ".join(sorted(missing)))
        return 2

    print("=== XINYU MULTI-PERSON RELATIONSHIP SMOKE ===")
    print(f"scenarios: {len(scenarios)}")
    failed: dict[str, list[str]] = {}
    for scenario in scenarios:
        passed, failures = _run_scenario(root, scenario, keep_memory=args.keep_memory)
        if not passed:
            failed[scenario.name] = failures

    print("=== SUMMARY ===")
    print(f"passed: {len(scenarios) - len(failed)}")
    print(f"failed: {len(failed)}")
    if failed:
        return 1
    print("Multi-person relationship smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
