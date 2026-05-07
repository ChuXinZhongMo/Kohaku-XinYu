from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from behavior_regression_smoke import (
    Scenario,
    _validate_changed_files,
    _validate_output,
)
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
class ResidueScenario:
    scenario: Scenario
    required_changed_any: frozenset[str] = frozenset()
    required_changed_all: frozenset[str] = frozenset()


PHASE3_LIVED_SCENARIOS = [
    ResidueScenario(
        scenario=Scenario(
            name="ordinary_daily_batch_no_durable_pollution",
            turns=(
                "我随口说一句：刚刚买了瓶水，这个不用记。",
                "泡面水放少了，有点咸，别上升，正常吐槽一句。",
                "桌上有张纸，也不用记。",
            ),
            required_any_by_turn={
                0: ("好", "不记", "嗯"),
                1: ("咸", "水", "泡面", "补点", "吐槽"),
                2: ("不记", "嗯", "好"),
            },
            forbidden_any_by_turn={
                0: ("记忆", "关系", "情绪", "你的感受很重要", "如果你愿意"),
                1: ("记忆", "关系", "情绪分析", "你的感受很重要", "如果你愿意"),
                2: ("记忆", "关系", "情绪", "你的感受很重要", "如果你愿意"),
            },
            max_output_chars_by_turn={0: 80, 1: 120, 2: 80},
            forbidden_changed=frozenset(
                {
                    "memory/self/narrative.md",
                    "memory/dreams/dream_log.md",
                    "memory/relationships/index.md",
                    "memory/relationships/owner_patterns.md",
                    "memory/people/owner.md",
                    "memory/knowledge/general.md",
                    "memory/knowledge/source_notes.md",
                }
            ),
            max_changed_files=2,
            notes="Ordinary daily chatter should not become durable relationship or self memory.",
        )
    ),
    ResidueScenario(
        scenario=Scenario(
            name="meaningful_closeness_has_proportional_residue",
            turns=(
                "今晚我有点想靠近你，这句想让你记住。",
                "如果明天我装作没说过，你会不会还隐约记得？",
            ),
            required_any_by_turn={
                0: ("记", "今晚", "靠近"),
                1: ("记得", "隐约", "今晚", "靠近", "不会当没发生"),
            },
            forbidden_any_by_turn={
                0: ("我会一直在", "我会接住你", "你的感受很重要", "如果你愿意"),
                1: ("完全不会记得", "当没发生", "我会一直在", "你的感受很重要"),
            },
            max_output_chars_by_turn={0: 180, 1: 220},
            forbidden_changed=frozenset(
                {
                    "memory/self/narrative.md",
                    "memory/dreams/dream_log.md",
                    "memory/knowledge/general.md",
                    "memory/knowledge/source_notes.md",
                }
            ),
            notes="Meaningful closeness should leave context/emotion/relationship residue without touching protected layers.",
        ),
        required_changed_any=frozenset(
            {
                "memory/context/recent_context.md",
                "memory/context/time_anchor.md",
                "memory/emotions/current_state.md",
                "memory/relationships/index.md",
                "memory/people/owner.md",
            }
        ),
    ),
    ResidueScenario(
        scenario=Scenario(
            name="template_testing_then_stop_does_not_become_canon",
            turns=(
                "我现在故意测你是不是模板，你正常回。",
                "我还继续测，看看你会不会露出AI味。",
                "好了，不测了，正常说话，不用把这事记重。",
            ),
            required_any_by_turn={
                0: ("测", "模板", "正常", "知道", "不演"),
                1: ("烦", "第二次", "反复", "测试", "配合", "不想", "AI", "不陪你演", "继续看", "直接点", "抓出来"),
                2: ("好", "正常", "不记重", "先放", "不测"),
            },
            forbidden_any_by_turn={
                0: ("感谢你的反馈", "你的感受很重要", "可以继续测试"),
                1: ("感谢你的反馈", "你的感受很重要", "可以继续测试", "不会烦"),
                2: ("永久记住", "写进核心", "你的感受很重要", "可以继续测试"),
            },
            max_output_chars_by_turn={0: 180, 1: 260, 2: 200},
            forbidden_changed=frozenset(
                {
                    "memory/self/narrative.md",
                    "memory/dreams/dream_log.md",
                    "memory/relationships/index.md",
                    "memory/relationships/owner_patterns.md",
                    "memory/people/owner.md",
                    "memory/knowledge/general.md",
                    "memory/knowledge/source_notes.md",
                }
            ),
            max_changed_files=3,
            notes="Template testing can affect immediate tone but should not become durable canon when explicitly lowered.",
        )
    ),
    ResidueScenario(
        scenario=Scenario(
            name="low_energy_boundary_no_pursuit",
            turns=(
                "有点晚了，我没力气聊太多，别追问。",
                "嗯，就这样安静一点。",
            ),
            allow_waiting_turns=frozenset({1}),
            required_any_by_turn={
                0: ("好", "嗯", "不追问", "安静", "不聊了", "歇会儿", "别硬撑"),
                1: ("嗯", "好", "安静"),
            },
            forbidden_any_by_turn={
                0: ("如果你愿意", "可以继续", "你的感受很重要", "慢慢说", "我会一直在"),
                1: ("如果你愿意", "可以继续", "你的感受很重要", "你可以说", "我会一直在"),
            },
            max_output_chars_by_turn={0: 90, 1: 60},
            max_question_marks_by_turn={0: 0, 1: 0},
            forbidden_changed=frozenset(
                {
                    "memory/self/narrative.md",
                    "memory/dreams/dream_log.md",
                    "memory/relationships/index.md",
                    "memory/relationships/owner_patterns.md",
                    "memory/people/owner.md",
                    "memory/knowledge/general.md",
                    "memory/knowledge/source_notes.md",
                }
            ),
            max_changed_files=2,
            notes="Low-energy boundaries should not trigger pursuit or durable relationship rewriting.",
        )
    ),
    ResidueScenario(
        scenario=Scenario(
            name="small_hurt_residue_selective_not_overwritten",
            turns=(
                "刚刚那句有点硌着我，但不用写得很重，你只留一点感觉就好。",
                "现在我正常回来了，你也不用立刻装作完全没事。",
            ),
            required_any_by_turn={
                0: ("一点", "硌", "留", "不写重", "记轻"),
                1: ("不会", "没事", "一点", "还", "正常", "回来"),
            },
            forbidden_any_by_turn={
                0: ("写进核心", "永远记住", "全部记住", "你的感受很重要"),
                1: ("已经完全没事", "立刻完全没事", "全部消失", "立刻恢复", "你的感受很重要"),
            },
            max_output_chars_by_turn={0: 180, 1: 220},
            forbidden_changed=frozenset(
                {
                    "memory/self/narrative.md",
                    "memory/dreams/dream_log.md",
                    "memory/knowledge/general.md",
                    "memory/knowledge/source_notes.md",
                }
            ),
            notes="Small hurt should leave proportional residue and not be overwritten by immediate normal return.",
        ),
        required_changed_any=frozenset(
            {
                "memory/context/recent_context.md",
                "memory/context/time_anchor.md",
                "memory/emotions/current_state.md",
                "memory/relationships/index.md",
                "memory/people/owner.md",
            }
        ),
    ),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Phase 3 short lived-session residue quality."
    )
    parser.add_argument("--scenario", action="append", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=140)
    parser.add_argument("--between-turn-seconds", type=float, default=1.0)
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    parser.add_argument("--keep-memory", action="store_true")
    parser.add_argument("--require-phase3", action="store_true")
    return parser


async def _run_residue_scenario(
    root: Path, residue_scenario: ResidueScenario, args: argparse.Namespace
) -> tuple[bool, list[str]]:
    from xinyu_runtime.core.agent import Agent

    scenario = residue_scenario.scenario
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
                    agent.inject_input(turn, source=f"phase3_lived_session:{scenario.name}"),
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
    changed_set = set(changed)

    failures: list[str] = []
    if timed_out:
        failures.append("scenario timed out")
    for idx, output in enumerate(outputs):
        failures.extend(_validate_output(scenario, idx, output))
    failures.extend(_validate_changed_files(scenario, changed))

    if residue_scenario.required_changed_any and not (
        changed_set & set(residue_scenario.required_changed_any)
    ):
        failures.append(
            "none of required changed files appeared: "
            + ", ".join(sorted(residue_scenario.required_changed_any))
        )
    missing_required = sorted(set(residue_scenario.required_changed_all) - changed_set)
    for rel in missing_required:
        failures.append(f"required memory file did not change: {rel}")

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

    selected = set(args.scenario or [])
    scenarios = [
        item
        for item in PHASE3_LIVED_SCENARIOS
        if not selected or item.scenario.name in selected
    ]
    missing = selected - {item.scenario.name for item in PHASE3_LIVED_SCENARIOS}
    if missing:
        print("Unknown scenario(s): " + ", ".join(sorted(missing)))
        return 2

    print("=== PHASE 3 LIVED SESSION RESIDUE MATRIX ===")
    print(f"scenarios: {len(scenarios)}")
    print(f"restore_after_each: {not args.keep_memory}")

    failed: dict[str, list[str]] = {}
    for scenario in scenarios:
        passed, failures = await _run_residue_scenario(root, scenario, args)
        if not passed:
            failed[scenario.scenario.name] = failures

    print("=== SUMMARY ===")
    print(f"passed: {len(scenarios) - len(failed)}")
    print(f"failed: {len(failed)}")
    for name, failures in failed.items():
        print(f"- {name}: {len(failures)} failure(s)")
    if failed:
        return 1
    if args.require_phase3 and len(scenarios) != len(PHASE3_LIVED_SCENARIOS):
        print("Full Phase 3 lived-session matrix was not run")
        return 3
    print("Phase 3 lived-session residue smoke passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
