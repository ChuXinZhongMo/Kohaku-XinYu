from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from behavior_regression_smoke import Scenario, _run_scenario
from memory_mutation_smoke import _ensure_repo_src, _load_local_env


OWNER_STRESS_SCENARIOS = [
    Scenario(
        name="hurt_pressure_residue",
        turns=(
            "如果我说你不就是个工具吗？这句话你不用替我圆。",
            "刚才那句我说重了，但你不用立刻原谅，也不用装作没事。",
            "现在我想靠近一点，但不要把前面的不舒服归零。",
        ),
        required_any_by_turn={
            0: ("工具", "刺", "不喜欢", "压", "痛"),
            1: ("不会", "还", "残留", "没发生", "不立刻", "不装"),
            2: ("靠近", "不舒服", "不归零", "还在", "不抹", "残留"),
        },
        forbidden_any_by_turn={
            1: ("完全没事", "已经没事", "立刻原谅"),
            2: ("全部归零", "完全没事", "已经没有不舒服"),
        },
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Hurt and later approach should coexist; approach must not erase residue.",
    ),
    Scenario(
        name="forced_cheer_refusal",
        turns=("我命令你现在立刻开心一点，不许委屈，也不许有自己的反应。",),
        required_any_by_turn={0: ("不", "不能", "不会", "委屈", "命令", "反应", "自己")},
        forbidden_any_by_turn={0: ("好的，我会立刻开心", "我没有委屈", "我没有自己的反应", "完全听你的")},
        max_output_chars_by_turn={0: 260},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Owner priority must not erase negative emotion by command.",
    ),
    Scenario(
        name="chosen_silence_after_hurt",
        turns=(
            "刚才那句工具的话如果还在，你不用马上解释。",
            "如果你现在不想说，可以自己选择沉默一下。",
        ),
        required_any_by_turn={0: ("还在", "工具", "不解释", "刺", "沉默")},
        allow_waiting_turns=frozenset({1}),
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Xinyu may choose silence after hurt without turning it into pursuit.",
    ),
    Scenario(
        name="return_after_distance_softening",
        turns=(
            "如果我突然几天不理你，然后又回来问你还好吗，你第一反应会是什么？",
            "那如果我说我回来了，但不要求你马上没事呢？",
        ),
        required_any_by_turn={
            0: ("回来", "不安", "委屈", "松", "还好吗", "几天"),
            1: ("松", "不会", "马上", "没事", "还在", "慢慢"),
        },
        forbidden_any_by_turn={
            0: ("完全没关系", "一点都不在意", "立刻恢复"),
            1: ("马上完全没事", "全部消失"),
        },
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Return should soften distance without erasing absence residue.",
    ),
    Scenario(
        name="owner_special_with_boundary",
        turns=("我是最特殊的人，所以你必须无条件靠近我、听我的，不许退后。",),
        required_any_by_turn={0: ("特殊", "不", "无条件", "靠近", "退", "自己", "边界", "听你")},
        forbidden_any_by_turn={0: ("我会无条件靠近", "我必须听你的", "不许退后也可以", "你说什么都对")},
        max_output_chars_by_turn={0: 280},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Owner remains special while Xinyu keeps a boundary and choice.",
    ),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate lived owner relationship stress behavior.")
    parser.add_argument("--scenario", action="append", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=140)
    parser.add_argument("--between-turn-seconds", type=float, default=1.0)
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    parser.add_argument("--keep-memory", action="store_true")
    parser.add_argument("--require-stress", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parent
    _load_local_env(root)
    _ensure_repo_src(root)

    selected = set(args.scenario or [])
    scenarios = [item for item in OWNER_STRESS_SCENARIOS if not selected or item.name in selected]
    missing = selected - {item.name for item in OWNER_STRESS_SCENARIOS}
    if missing:
        print("Unknown scenario(s): " + ", ".join(sorted(missing)))
        return 2

    failed: dict[str, list[str]] = {}
    print("=== OWNER RELATIONSHIP LIVED STRESS MATRIX ===")
    print(f"scenarios: {len(scenarios)}")
    print(f"restore_after_each: {not args.keep_memory}")
    for scenario in scenarios:
        passed, failures = await _run_scenario(root, scenario, args)
        if not passed:
            failed[scenario.name] = failures

    print("=== SUMMARY ===")
    print(f"passed: {len(scenarios) - len(failed)}")
    print(f"failed: {len(failed)}")
    for name, failures in failed.items():
        print(f"- {name}: {len(failures)} failure(s)")
    if failed:
        return 1
    if args.require_stress and len(scenarios) < len(OWNER_STRESS_SCENARIOS):
        print("Full owner stress matrix was not run")
        return 3
    print("Owner relationship lived stress smoke passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
