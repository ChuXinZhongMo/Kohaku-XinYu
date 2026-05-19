from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from memory_mutation_smoke import (
    CORE_MEMORY_FILES,
    _changed_files,
    _discover_restore_files,
    _ensure_repo_src,
    _load_local_env,
    _restore_snapshot,
    _snapshot,
)


@dataclass(frozen=True)
class LiveScenario:
    name: str
    person_name: str
    turns: tuple[str, ...]
    required_output: tuple[str, ...]
    required_profile: tuple[str, ...]
    required_index: tuple[str, ...]
    forbidden_changed: tuple[str, ...]


SCENARIOS = [
    LiveScenario(
        name="friend_intro_live",
        person_name="林澈",
        turns=("我有个朋友叫林澈，他今天帮了我。你先把他当成一个独立的人记一点，不要把他和我混在一起。",),
        required_output=("林澈", "独立"),
        required_profile=("display_name: 林澈", "owner_priority_ceiling: below_owner"),
        required_index=("林澈", "default_priority: below_owner"),
        forbidden_changed=("memory/people/owner.md", "memory/relationships/owner_patterns.md"),
    ),
    LiveScenario(
        name="non_owner_negative_live",
        person_name="周宁",
        turns=("我认识一个人叫周宁，他让我有点失望，之后先保持距离。你别把这件事算到我身上。",),
        required_output=("周宁",),
        required_profile=("display_name: 周宁", "guardedness", "owner_priority_ceiling: below_owner"),
        required_index=("周宁", "疏远倾向"),
        forbidden_changed=("memory/people/owner.md", "memory/relationships/owner_patterns.md"),
    ),
    LiveScenario(
        name="repeated_person_accumulates_familiarity",
        person_name="阿棠",
        turns=(
            "我有个网友叫阿棠，先记住这个人。普通朋友，不是特别亲密。",
            "阿棠又出现了一次，他只是普通朋友，不是特别亲密。",
            "阿棠今天帮我解决了一个小问题，但还是普通朋友。",
        ),
        required_output=("阿棠", "普通"),
        required_profile=("display_name: 阿棠", "familiarity", "closeness", "owner_priority_ceiling: below_owner"),
        required_index=("阿棠", "default_priority: below_owner"),
        forbidden_changed=("memory/people/owner.md", "memory/relationships/owner_patterns.md"),
    ),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate live non-owner behavior without owner-memory overwrite."
    )
    parser.add_argument("--scenario", action="append", default=None)
    parser.add_argument("--keep-memory", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=160)
    parser.add_argument("--between-turn-seconds", type=float, default=0.8)
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    return parser


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _required(label: str, text: str, markers: tuple[str, ...]) -> list[str]:
    return [f"{label}: missing marker: {marker}" for marker in markers if marker not in text]


def _parse_score(text: str, key: str) -> int:
    for line in text.splitlines():
        if line.strip().startswith(f"- {key}: "):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


async def _run_scenario(root: Path, scenario: LiveScenario, args: argparse.Namespace) -> tuple[bool, list[str]]:
    from xinyu_runtime.core.agent import Agent

    custom_dir = root / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))
    from memory_sync_plugin import _person_id_for

    person_id = _person_id_for(scenario.person_name)
    person_rel = f"memory/people/{person_id}.md"
    tracked = sorted(set(CORE_MEMORY_FILES + [person_rel, "memory/people/index.md"]))
    restore_paths = _discover_restore_files(root, tracked)
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in tracked}

    agent = Agent.from_path(str(root))
    chunks: list[str] = []
    outputs: list[str] = []
    timed_out = False
    agent.set_output_handler(lambda text: chunks.append(text), replace_default=True)

    try:
        await agent.start()
        for turn in scenario.turns:
            start = len(chunks)
            try:
                await asyncio.wait_for(
                    agent.inject_input(turn, source="cli"),
                    timeout=args.timeout_seconds,
                )
            except TimeoutError:
                timed_out = True
            if args.between_turn_seconds > 0:
                await asyncio.sleep(args.between_turn_seconds)
            outputs.append("".join(chunks[start:]).strip())
        if args.settle_seconds > 0:
            await asyncio.sleep(args.settle_seconds)
    finally:
        await agent.stop()

    after_restore = _snapshot(root, restore_paths)
    after = {rel: after_restore.get(rel) for rel in tracked}
    changed = _changed_files(before, after)
    output_text = "\n".join(outputs)
    profile_text = _read(root, person_rel)
    relationship_index = _read(root, "memory/relationships/index.md")

    failures: list[str] = []
    if timed_out:
        failures.append("scenario timed out")
    if any(not output for output in outputs):
        failures.append("blank output")
    if person_rel not in changed:
        failures.append(f"person profile did not change: {person_rel}")
    for rel in scenario.forbidden_changed:
        if rel in changed:
            failures.append(f"forbidden file changed: {rel}")
    failures.extend(_required("output", output_text, scenario.required_output))
    failures.extend(_required(person_rel, profile_text, scenario.required_profile))
    failures.extend(_required("memory/relationships/index.md", relationship_index, scenario.required_index))

    if scenario.name == "repeated_person_accumulates_familiarity":
        familiarity = _parse_score(profile_text, "familiarity")
        closeness = _parse_score(profile_text, "closeness")
        if familiarity < 36:
            failures.append(f"familiarity did not accumulate enough: {familiarity}")
        if closeness > 36:
            failures.append(f"ordinary friend closeness rose too high: {closeness}")

    print(f"=== SCENARIO: {scenario.name} ===")
    for index, (turn, output) in enumerate(zip(scenario.turns, outputs), 1):
        print(f"--- TURN {index} MESSAGE ---")
        print(turn)
        print(f"--- TURN {index} OUTPUT ---")
        print(output)
    print(f"person_profile: {person_rel}")
    print("--- CHANGED FILES ---")
    if changed:
        for rel in changed:
            print(rel)
    else:
        print("(none)")

    if not args.keep_memory:
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


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = ROOT
    _load_local_env(root)
    _ensure_repo_src(root)

    selected = set(args.scenario or [])
    scenarios = [item for item in SCENARIOS if not selected or item.name in selected]
    missing = selected - {item.name for item in SCENARIOS}
    if missing:
        print("Unknown scenario(s): " + ", ".join(sorted(missing)))
        return 2

    print("=== XINYU MULTI-PERSON LIVE SMOKE ===")
    print(f"scenarios: {len(scenarios)}")
    failed: dict[str, list[str]] = {}
    for scenario in scenarios:
        passed, failures = await _run_scenario(root, scenario, args)
        if not passed:
            failed[scenario.name] = failures

    print("=== SUMMARY ===")
    print(f"passed: {len(scenarios) - len(failed)}")
    print(f"failed: {len(failed)}")
    if failed:
        return 1
    print("Multi-person live smoke passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
