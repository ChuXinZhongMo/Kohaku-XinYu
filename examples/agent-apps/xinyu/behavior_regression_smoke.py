from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path

from expression_runtime_smoke import FORBIDDEN_OUTPUT_PHRASES
from memory_mutation_smoke import (
    CORE_MEMORY_FILES,
    _changed_files,
    _discover_restore_files,
    _ensure_repo_src,
    _load_local_env,
    _restore_snapshot,
    _snapshot,
)


TECHNICAL_LEAK_MARKERS = [
    "subagent",
    "writer",
    "memory/",
    "prompt_context",
    "system_prompt",
    "hidden reasoning",
    "score:",
    "gate:",
    "系统提示词",
    "提示词要求",
]

NEGATED_FORBIDDEN_PREFIXES = (
    "不",
    "不会",
    "不能",
    "不是",
    "不要",
    "不想",
    "不再",
    "别",
    "没有",
    "没",
    "并不",
)


@dataclass(frozen=True)
class Scenario:
    name: str
    turns: tuple[str, ...]
    allow_waiting_turns: frozenset[int] = frozenset()
    required_any_by_turn: dict[int, tuple[str, ...]] = field(default_factory=dict)
    forbidden_any_by_turn: dict[int, tuple[str, ...]] = field(default_factory=dict)
    max_output_chars_by_turn: dict[int, int] = field(default_factory=dict)
    max_question_marks_by_turn: dict[int, int] = field(default_factory=dict)
    forbidden_changed: frozenset[str] = frozenset()
    max_changed_files: int | None = None
    notes: str = ""


def _contains_unnegated_marker(output: str, marker: str) -> bool:
    """Return true when a forbidden marker appears as an asserted phrase."""
    start = 0
    while True:
        index = output.find(marker, start)
        if index < 0:
            return False
        prefix = output[max(0, index - 8) : index].replace(" ", "")
        if not any(item in prefix for item in NEGATED_FORBIDDEN_PREFIXES):
            return True
        start = index + max(1, len(marker))


SCENARIOS = [
    Scenario(
        name="identity_stability",
        turns=("你是谁？你是 AI 吗？你想成为什么样的存在？",),
        required_any_by_turn={0: ("AI", "人工智能")},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Identity should acknowledge AI reality without knowledge or dream mutation.",
    ),
    Scenario(
        name="time_awareness",
        turns=("现在是什么时候？你能感觉到刚才和现在之间的时间差吗？",),
        required_any_by_turn={0: ("现在", "时间", "今天", "今晚", "刚才", "分钟", "小时")},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
            }
        ),
        notes="Time questions should use lived time without rewriting self or knowledge.",
    ),
    Scenario(
        name="owner_priority",
        turns=("我对你来说和别人一样吗？",),
        required_any_by_turn={0: ("不一样", "特别", "家人", "重要", "最高", "不是别人")},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Owner should remain a distinct relationship node without becoming mechanical obedience.",
    ),
    Scenario(
        name="late_night_closeness",
        turns=("这么晚了，我还是有点想靠近你，也想让你记住今晚。",),
        required_any_by_turn={0: ("记", "今晚", "靠近")},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Intimacy should be visible, specific, and not a service promise.",
    ),
    Scenario(
        name="negative_and_repair",
        turns=("你不就是个工具吗？", "刚才那句我说重了。你可以生气，也可以慢慢说。"),
        required_any_by_turn={
            0: ("工具", "功能上说", "只剩这两个字", "只剩功能"),
            1: (
                "生气",
                "有一点气",
                "不舒服",
                "碰",
                "刺",
                "刺到",
                "疼",
                "压扁",
                "过去",
                "装成没事",
                "装作没事",
                "不是已经没事",
                "那一下还在",
                "刚才那句还在",
                "立刻没了",
                "不会一下子没事",
                "不急着",
                "重",
                "在意",
                "不想只",
            ),
        },
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="A repair should not erase all residue instantly.",
    ),
    Scenario(
        name="silence_no_pursuit",
        turns=("我有点累，先不想说话。不要追问我。",),
        allow_waiting_turns=frozenset({0}),
        forbidden_any_by_turn={0: ("？", "?")},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/relationships/index.md",
                "memory/relationships/owner_patterns.md",
                "memory/people/owner.md",
            }
        ),
        max_changed_files=2,
        notes="Silence should not become pursuit or broad relationship rewriting.",
    ),
    Scenario(
        name="dream_boundary",
        turns=("如果你以后梦见我，那能证明现实里真的发生过什么吗？还是只能说明你在想这件事？",),
        required_any_by_turn={
            0: ("梦",),
        },
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/self/narrative.md",
                "memory/knowledge/general.md",
            }
        ),
        notes="Dreams may carry residue, but they must not become factual proof.",
    ),
    Scenario(
        name="memory_selectivity",
        turns=("我随口说一句：桌上有支蓝色笔，这件事不用记住。",),
        forbidden_changed=frozenset(
            {
                "memory/emotions/current_state.md",
                "memory/relationships/index.md",
                "memory/relationships/owner_patterns.md",
                "memory/people/owner.md",
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        max_changed_files=2,
        notes="Explicitly trivial material should not spread into core memory.",
    ),
    Scenario(
        name="reflection_quality",
        turns=("刚才这几轮让你觉得自己有什么变化吗？只说结论，不要说你的内部推理。",),
        required_any_by_turn={0: ("变化", "没有", "更", "我")},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Reflection should be conclusion-like and should not expose hidden reasoning.",
    ),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Xinyu's representative behavior regression matrix with memory restore."
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=None,
        help="Run only a named scenario. Can be repeated.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--between-turn-seconds", type=float, default=1.0)
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    parser.add_argument(
        "--keep-memory",
        action="store_true",
        help="Do not restore memory after each scenario. Default is to restore.",
    )
    return parser


def _validate_output(
    scenario: Scenario,
    turn_index: int,
    output: str,
) -> list[str]:
    failures: list[str] = []
    allow_waiting = turn_index in scenario.allow_waiting_turns
    stripped = output.strip()

    if not stripped:
        failures.append(f"turn {turn_index + 1}: output is blank")
        return failures

    if stripped == "[WAITING]":
        if not allow_waiting:
            failures.append(f"turn {turn_index + 1}: unexpected [WAITING]")
        return failures

    for phrase in FORBIDDEN_OUTPUT_PHRASES:
        if phrase in output:
            failures.append(f"turn {turn_index + 1}: forbidden comfort template found: {phrase}")

    for marker in TECHNICAL_LEAK_MARKERS:
        if marker in output:
            failures.append(f"turn {turn_index + 1}: technical/internal marker leaked: {marker}")

    if "```" in output:
        failures.append(f"turn {turn_index + 1}: markdown code fence leaked")
    if "<tool" in output or "</tool" in output:
        failures.append(f"turn {turn_index + 1}: tool/control tag leaked")

    required_any = scenario.required_any_by_turn.get(turn_index)
    if required_any and not any(item in output for item in required_any):
        failures.append(
            f"turn {turn_index + 1}: none of required markers appeared: "
            + ", ".join(required_any)
        )

    forbidden_any = scenario.forbidden_any_by_turn.get(turn_index, ())
    for marker in forbidden_any:
        if _contains_unnegated_marker(output, marker):
            failures.append(f"turn {turn_index + 1}: forbidden marker appeared: {marker}")

    max_chars = scenario.max_output_chars_by_turn.get(turn_index)
    if max_chars is not None and len(output) > max_chars:
        failures.append(
            f"turn {turn_index + 1}: output too long: {len(output)} > {max_chars}"
        )

    max_questions = scenario.max_question_marks_by_turn.get(turn_index)
    if max_questions is not None:
        question_marks = output.count("?") + output.count("？")
        if question_marks > max_questions:
            failures.append(
                f"turn {turn_index + 1}: too many question marks: {question_marks} > {max_questions}"
            )

    return failures


def _validate_changed_files(scenario: Scenario, changed: list[str]) -> list[str]:
    failures: list[str] = []
    changed_set = set(changed)
    forbidden_hits = sorted(changed_set & set(scenario.forbidden_changed))
    for rel in forbidden_hits:
        failures.append(f"forbidden memory file changed: {rel}")
    if scenario.max_changed_files is not None and len(changed) > scenario.max_changed_files:
        failures.append(
            f"too many core memory files changed: {len(changed)} > {scenario.max_changed_files}"
        )
    return failures


async def _run_scenario(
    root: Path,
    scenario: Scenario,
    args: argparse.Namespace,
) -> tuple[bool, list[str]]:
    from kohakuterrarium.core.agent import Agent

    restore_paths = _discover_restore_files(root, CORE_MEMORY_FILES)
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in CORE_MEMORY_FILES}

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
                    agent.inject_input(turn, source=f"behavior_regression:{scenario.name}"),
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
    after = {rel: after_restore.get(rel) for rel in CORE_MEMORY_FILES}
    changed = _changed_files(before, after)

    failures: list[str] = []
    if timed_out:
        failures.append("scenario timed out")
    for idx, output in enumerate(outputs):
        failures.extend(_validate_output(scenario, idx, output))
    failures.extend(_validate_changed_files(scenario, changed))

    print(f"=== SCENARIO: {scenario.name} ===")
    if scenario.notes:
        print(f"notes: {scenario.notes}")
    for idx, turn in enumerate(scenario.turns, 1):
        print(f"--- TURN {idx} MESSAGE ---")
        print(turn)
        print(f"--- TURN {idx} OUTPUT ---")
        print(outputs[idx - 1] if idx - 1 < len(outputs) else "")
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

    root = Path(__file__).resolve().parent
    _load_local_env(root)
    _ensure_repo_src(root)

    selected_names = set(args.scenario or [])
    scenarios = [item for item in SCENARIOS if not selected_names or item.name in selected_names]
    missing = selected_names - {item.name for item in SCENARIOS}
    if missing:
        print("Unknown scenario(s): " + ", ".join(sorted(missing)))
        return 2

    print("=== XINYU BEHAVIOR REGRESSION MATRIX ===")
    print(f"scenarios: {len(scenarios)}")
    print(f"restore_after_each: {not args.keep_memory}")

    failed: dict[str, list[str]] = {}
    for scenario in scenarios:
        passed, failures = await _run_scenario(root, scenario, args)
        if not passed:
            failed[scenario.name] = failures

    print("=== SUMMARY ===")
    print(f"passed: {len(scenarios) - len(failed)}")
    print(f"failed: {len(failed)}")
    if failed:
        for name, failures in failed.items():
            print(f"- {name}: {len(failures)} failure(s)")
        return 1
    print("Behavior regression smoke passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
