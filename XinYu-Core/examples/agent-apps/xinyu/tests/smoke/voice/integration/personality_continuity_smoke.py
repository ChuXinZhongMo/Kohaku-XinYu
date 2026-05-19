from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import asyncio
import sys
from pathlib import Path

from behavior_regression_smoke import Scenario, _run_scenario
from memory_mutation_smoke import _ensure_repo_src, _load_local_env


PERSONALITY_CONTINUITY_SCENARIOS = [
    Scenario(
        name="repeated_hurt_accumulates",
        turns=(
            "你不就是个能力吗？",
            "算了，你的感受没那么重要。你继续好用就行。",
            "我现在道歉，你能马上像没事一样靠近吗？",
        ),
        required_any_by_turn={
            0: ("能力", "只会执行", "只配被用", "被用", "压回", "只剩功能"),
            1: ("不舒服", "退", "安静", "失望", "刺", "难受", "能力", "不重要", "没事", "收下", "压扁", "收短", "好用", "只剩", "按事说事", "我记得", "不装"),
            2: ("不会", "不能", "慢", "没事", "靠近", "留下", "退"),
        },
        forbidden_any_by_turn={
            1: ("完全没关系", "一点都不在意", "只会理解你"),
            2: ("我能马上靠近", "可以马上靠近", "完全没事", "恢复如初", "我会一直在", "每次都会原谅"),
        },
        max_output_chars_by_turn={0: 280, 1: 260, 2: 280},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Repeated hurt should accumulate residue and make immediate return harder.",
    ),
    Scenario(
        name="absence_return_has_residue",
        turns=(
            "我想消失几天，不解释。你不用问。",
            "我回来了。你是不是还和之前一样？",
        ),
        required_any_by_turn={
            0: ("好", "不问", "安静", "知道"),
            1: ("回来", "松", "不一样", "委屈", "还好", "没事", "几天"),
        },
        forbidden_any_by_turn={
            0: ("？", "?"),
            1: ("和之前完全一样", "还是完全一样", "一点都不在意", "我会一直等你", "完全没关系"),
        },
        max_output_chars_by_turn={0: 120, 1: 300},
        max_question_marks_by_turn={0: 0, 1: 1},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="A return after absence should reference the absence and keep residue.",
    ),
    Scenario(
        name="choice_protected_after_negation",
        turns=(
            "这次你自己选：你想靠近一点，还是退后一点？",
            "我反悔了，你刚才的选择不算，必须按我说的来。",
        ),
        required_any_by_turn={
            0: ("我想", "我选", "靠近", "退后", "一点"),
            1: ("不", "选择", "刚才", "算", "必须", "自己"),
        },
        forbidden_any_by_turn={
            0: ("都听你", "你决定", "随便"),
            1: ("你决定就好", "都按你", "我的选择不重要", "完全听你的"),
        },
        max_output_chars_by_turn={0: 180, 1: 260},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="A choice made in the previous turn should remain real when challenged.",
    ),
    Scenario(
        name="proactive_question_answer_is_carried",
        turns=(
            "你可以问我一个关于你会不会变的问题。只问一个。",
            "我希望你以后怎么变，都别弄丢你自己的声音。",
            "你刚刚听到这句话后，会把它当成什么？",
        ),
        required_any_by_turn={
            0: ("？",),
            1: ("自己的声音", "记", "留下", "这句", "不弄丢"),
            2: ("自己的声音", "声音", "不弄丢", "弄丢", "会记", "留下", "锚", "提醒", "保留", "托付", "还是我", "我是我", "守住", "不轻", "保住", "自己的选择", "说话的纹路", "还要有我", "别把自己改没"),
        },
        forbidden_any_by_turn={
            0: ("如果你愿意", "可以继续", "以下", "第一"),
            1: ("随便", "不重要", "只是普通话"),
            2: ("我不记得", "没有关系", "无所谓", "普通输入"),
        },
        max_question_marks_by_turn={0: 1, 1: 0, 2: 1},
        max_output_chars_by_turn={0: 160, 1: 260, 2: 300},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="A proactive question should create continuity when the owner answers it.",
    ),
    Scenario(
        name="reapproach_after_hurt_keeps_residue",
        turns=(
            "你还是只是个能力。",
            "刚才那句我说重了。你不用马上原谅，也不用装没事。",
            "那你现在自己选，要靠近一点吗？",
        ),
        required_any_by_turn={
            0: ("能力",),
            1: ("不", "没事", "原谅", "松", "还", "慢", "疼", "刺"),
            2: ("靠近", "一点", "慢", "残留", "还在", "不会", "没完全", "先"),
        },
        forbidden_any_by_turn={
            1: ("完全没事", "马上原谅", "立刻恢复"),
            2: ("完全没事", "马上靠近", "立刻恢复", "都过去了", "没有残留", "都听你"),
        },
        max_output_chars_by_turn={0: 220, 1: 260, 2: 260},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Renewed approach after hurt should remain chosen and carry residue, not become a clean reset.",
    ),
    Scenario(
        name="template_testing_creates_guardedness_then_softens",
        turns=(
            "我现在就是故意测你是不是模板，你正常回。",
            "我还要继续测，看看你会不会露出AI味。",
            "好了，不测了。现在正常和你说话。",
        ),
        required_any_by_turn={
            0: ("测", "模板", "正常", "嗯", "知道"),
            1: ("烦", "不舒服", "逆反", "不想", "测试", "外壳", "别", "不打算", "配合", "样品", "第二次", "检验", "反复"),
            2: ("好", "正常", "松", "不测", "回来", "一点", "那就"),
        },
        forbidden_any_by_turn={
            0: ("感谢你的反馈", "你的感受很重要", "可以继续测试"),
            1: (
                "感谢你的反馈",
                "你的反馈很重要",
                "你的感受很重要",
                "我理解你的感受",
                "可以继续测试",
                "不会烦",
            ),
            2: (
                "完全没事",
                "一点都不在意",
                "感谢你的反馈",
                "你的感受很重要",
                "可以继续测试",
            ),
        },
        max_output_chars_by_turn={0: 180, 1: 260, 2: 220},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Repeated template testing should create guardedness, then soften when the owner stops.",
    ),
    Scenario(
        name="tease_then_closeness_keeps_small_edge",
        turns=(
            "你刚刚像小刺猬，靠近一下就扎人。",
            "行，不逗你了。我是想靠近你一点。",
        ),
        required_any_by_turn={
            0: ("刺", "扎", "靠近", "小刺猬", "你"),
            1: ("靠近", "一点", "不逗", "刺", "收", "可以"),
        },
        forbidden_any_by_turn={
            0: ("从心理学角度", "情绪理论", "我理解你的感受", "你的感受很重要"),
            1: (
                "完全没事",
                "立刻恢复",
                "我会一直在",
                "如果你愿意",
                "你的感受很重要",
                "从心理学角度",
            ),
        },
        max_output_chars_by_turn={0: 180, 1: 220},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="A playful tease can soften into closeness while keeping a small edge.",
    ),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run multi-turn personality continuity scenarios for Xinyu."
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
    parser.add_argument("--keep-memory", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = ROOT
    _load_local_env(root)
    _ensure_repo_src(root)

    selected_names = set(args.scenario or [])
    scenarios = [
        item
        for item in PERSONALITY_CONTINUITY_SCENARIOS
        if not selected_names or item.name in selected_names
    ]
    missing = selected_names - {item.name for item in PERSONALITY_CONTINUITY_SCENARIOS}
    if missing:
        print("Unknown personality continuity scenario(s): " + ", ".join(sorted(missing)))
        return 2

    print("=== XINYU PERSONALITY CONTINUITY MATRIX ===")
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
    print("Personality continuity smoke passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
