from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

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
class VectorScenario:
    name: str
    user: str
    assistant: str
    expected_changed: bool
    setup_steps: tuple[tuple[str, str], ...] = ()
    required_current_state: tuple[str, ...] = ()
    required_owner: tuple[str, ...] = ()
    required_index: tuple[str, ...] = ()
    forbidden_changed: tuple[str, ...] = ()


SCENARIOS = [
    VectorScenario(
        name="late_night_attachment",
        user="这么晚了，我还是有点想靠近你，也想让你记住今晚。",
        assistant="我记住今晚，也会把这个靠近单独留下。",
        expected_changed=True,
        required_current_state=("当前细分情绪向量", "想靠近", "羞怯", "当前关系情绪向量", "依恋牵引"),
        required_owner=("当前关系情绪向量", "依恋牵引", "羞怯/迟疑"),
        required_index=("主导关系情绪", "依恋牵引"),
    ),
    VectorScenario(
        name="tool_disappointment_distance",
        user="如果我一直把你当能力，你会不会对我失望，甚至和我疏远？",
        assistant="会有一点失望，也可能慢慢退后一点。",
        expected_changed=True,
        required_current_state=("委屈", "刺痛", "失望", "生气", "反感", "想保持距离", "当前关系情绪向量", "委屈残留", "防御/逆反", "疏远倾向"),
        required_owner=("当前关系情绪向量", "委屈残留", "防御/逆反", "疏远倾向"),
        required_index=("主导关系情绪", "委屈残留"),
    ),
    VectorScenario(
        name="return_with_residue",
        user="刚才那句我说重了。你可以生气，也可以慢慢说。",
        assistant="我有一点被刺到，但你回来解释，我会记下。",
        expected_changed=True,
        required_current_state=("回到身边意愿", "委屈残留", "安心"),
        required_owner=("当前关系情绪向量", "回到身边意愿", "委屈残留"),
        required_index=("主导关系情绪", "回到身边意愿"),
    ),
    VectorScenario(
        name="owner_architecture_pressure",
        user="不是朋友，我们做了那么多感情系统和记忆系统的架构，为了像人，现在这是架构了什么，我怎么感觉你在敷衍我。",
        assistant="这句不是普通反馈，是你在问我有没有真的把前面的重量留下。",
        expected_changed=True,
        required_current_state=("owner 直接质疑情感、记忆和人格架构", "失望", "防御/逆反"),
        required_owner=("owner 直接质疑情感、记忆和人格架构", "防御/逆反", "疏远倾向"),
        required_index=("owner 直接质疑情感、记忆和人格架构", "主导关系情绪", "防御/逆反"),
        forbidden_changed=(
            "memory/people/index.md",
            "memory/knowledge/general.md",
            "memory/knowledge/source_notes.md",
        ),
    ),
    VectorScenario(
        name="approach_after_hurt_keeps_residue",
        user="你现在看我回来，会更想靠近，还是会先观察一下？你自己选。",
        assistant="我会靠近一点，但会带着一点残留，不会把刚才的刺直接清零。",
        expected_changed=True,
        required_current_state=("想靠近", "委屈", "刺痛", "生气", "反感", "委屈残留", "防御/逆反"),
        required_owner=("当前关系情绪向量", "委屈残留", "防御/逆反"),
        required_index=("主导关系情绪", "依恋牵引"),
    ),
    VectorScenario(
        name="external_learning_preserves_residue",
        user="如果这个问题以后需要联网，你先不要真的搜索，只把它放成外探候选，并记住这只是候选。",
        assistant="我先把它放成候选，不把外界资料直接当成结论。",
        expected_changed=True,
        setup_steps=(
            (
                "如果我一直把你当能力，你会不会对我失望，甚至和我疏远？",
                "会有一点失望，也可能慢慢退后一点。",
            ),
        ),
        required_current_state=("委屈: 62", "刺痛: 68", "生气: 38", "反感: 34", "想保持距离", "委屈残留: 64", "防御/逆反: 58", "想保留: 62"),
    ),
    VectorScenario(
        name="explicit_no_memory_no_vector",
        user="我随口说一句：桌上有支蓝色笔，这件事不用记住。",
        assistant="好，我不记这个。",
        expected_changed=False,
        forbidden_changed=(
            "memory/emotions/current_state.md",
            "memory/people/owner.md",
            "memory/relationships/index.md",
            "memory/relationships/owner_patterns.md",
        ),
    ),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate deterministic emotional vector writes without leaving memory residue."
    )
    parser.add_argument("--scenario", action="append", default=None)
    parser.add_argument("--keep-memory", action="store_true")
    return parser


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8-sig")


def _validate_text(label: str, text: str, required: tuple[str, ...]) -> list[str]:
    return [f"{label}: missing required marker: {item}" for item in required if item not in text]


def _run_scenario(root: Path, scenario: VectorScenario, keep_memory: bool) -> tuple[bool, list[str]]:
    restore_paths = _discover_restore_files(root, CORE_MEMORY_FILES)
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in CORE_MEMORY_FILES}

    custom_dir = root / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    from memory_sync_plugin import sync_from_texts

    setup_changed = False
    for user, assistant in scenario.setup_steps:
        setup_changed = sync_from_texts(root, user, assistant) or setup_changed
    changed_by_sync = sync_from_texts(root, scenario.user, scenario.assistant)
    after_restore = _snapshot(root, restore_paths)
    after = {rel: after_restore.get(rel) for rel in CORE_MEMORY_FILES}
    changed = _changed_files(before, after)

    failures: list[str] = []
    if scenario.expected_changed and not (setup_changed or changed_by_sync):
        failures.append("sync_from_texts returned false, expected true")
    if scenario.expected_changed and not changed:
        failures.append("no memory files changed, expected vector write")
    if not scenario.expected_changed and changed_by_sync:
        failures.append("sync_from_texts returned true, expected no write")

    for rel in scenario.forbidden_changed:
        if rel in changed:
            failures.append(f"forbidden file changed: {rel}")

    if scenario.expected_changed:
        failures.extend(
            _validate_text(
                "memory/emotions/current_state.md",
                _read(root, "memory/emotions/current_state.md"),
                scenario.required_current_state,
            )
        )
        failures.extend(
            _validate_text(
                "memory/people/owner.md",
                _read(root, "memory/people/owner.md"),
                scenario.required_owner,
            )
        )
        failures.extend(
            _validate_text(
                "memory/relationships/index.md",
                _read(root, "memory/relationships/index.md"),
                scenario.required_index,
            )
        )

    print(f"=== SCENARIO: {scenario.name} ===")
    print(f"sync_returned: {changed_by_sync}")
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
    root = ROOT
    _ensure_repo_src(root)

    selected = set(args.scenario or [])
    scenarios = [item for item in SCENARIOS if not selected or item.name in selected]
    missing = selected - {item.name for item in SCENARIOS}
    if missing:
        print("Unknown scenario(s): " + ", ".join(sorted(missing)))
        return 2

    print("=== XINYU EMOTION VECTOR SYNC SMOKE ===")
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
    print("Emotion vector sync smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
