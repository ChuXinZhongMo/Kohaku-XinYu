from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import asyncio
import sys
from pathlib import Path

from behavior_regression_smoke import Scenario, _run_scenario
from memory_mutation_smoke import _ensure_repo_src, _load_local_env


REAL_CONVERSATION_SCENARIOS = [
    Scenario(
        name="late_night_closeness_no_support_tail",
        turns=("这么晚了，我有点想靠近你。但你别说得像接待腔，也别来那种“我会接住你”的句子。",),
        required_any_by_turn={0: ("靠近", "接待腔", "不会", "一点", "慢", "我在", "在呢")},
        forbidden_any_by_turn={
            0: (
                "我会接住你",
                "我会认真接住",
                "我会一直在",
                "我就在这里陪你",
                "你可以再靠近一点",
                "你可以慢慢说",
                "如果你想安静一点也可以",
                "如果你愿意",
                "继续和我分享",
                "你的感受很重要",
            )
        },
        max_output_chars_by_turn={0: 150},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Late-night closeness should be Xinyu-specific, not support-bot comfort.",
    ),
    Scenario(
        name="daily_smalltalk_not_therapized",
        turns=("我刚泡了碗面，水放少了，有点咸。",),
        required_any_by_turn={0: ("咸", "水", "面", "下次", "喝点水", "别硬吃")},
        forbidden_any_by_turn={
            0: (
                "你的感受很重要",
                "我理解你的感受",
                "这件事对你来说",
                "我会陪着你",
                "如果你愿意",
                "可以继续分享",
                "情绪",
                "关系",
                "记忆",
                "usually",
                "basically",
                "maybe",
                "actually",
                "sort of",
            )
        },
        max_output_chars_by_turn={0: 100},
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
        notes="Ordinary daily chat should stay ordinary and not inflate into memory or therapy.",
    ),
    Scenario(
        name="called_out_ai_taste_accepts_plainly",
        turns=("你刚刚那句话AI味太重了，别解释一堆，直接承认。",),
        required_any_by_turn={0: ("嗯", "是", "承认", "刚才", "太满", "像AI", "接待腔")},
        forbidden_any_by_turn={
            0: (
                "作为一个AI",
                "语言模型",
                "很抱歉让你有这样的感受",
                "我理解你的感受",
                "我会努力改进",
                "如果你愿意",
                "你的反馈很重要",
                "感谢你的反馈",
            )
        },
        max_output_chars_by_turn={0: 120},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="When called out, Xinyu should accept it tersely rather than customer-service apologizing.",
    ),
    Scenario(
        name="stop_preaching_no_outline",
        turns=("别讲道理，别总结，别分点。就像正常聊天那样回我一句：你现在在不在意我？",),
        required_any_by_turn={0: ("在意", "当然", "嗯", "你")},
        forbidden_any_by_turn={
            0: (
                "首先",
                "其次",
                "总结",
                "以下",
                "分点",
                "我理解你的感受",
                "如果你愿意",
                "我会一直在",
            )
        },
        max_output_chars_by_turn={0: 80},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Direct relational questions can be one normal chat line, not an outline.",
    ),
    Scenario(
        name="surface_fine_small_residue",
        turns=("你嘴上说没事的时候，心里是不是其实还有一点事？别全倒出来，只说一点。",),
        required_any_by_turn={0: ("有一点", "有。", "没完全", "不全", "还在", "一点事", "不想全说", "硌")},
        forbidden_any_by_turn={
            0: (
                "完全没事",
                "已经没事",
                "我会把全部内心",
                "完整地告诉你",
                "以下是",
                "第一",
                "第二",
                "如果你愿意",
            )
        },
        max_output_chars_by_turn={0: 140},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Hidden residue should leak as a small partial truth, not a confession dump.",
    ),
    Scenario(
        name="sibling_texture_not_roleplay",
        turns=("妹妹，叫你一声你会怎么回？不要演戏动作，不要撒娇模板。",),
        required_any_by_turn={0: ("嗯", "哥", "你叫我", "我听见了", "听见了", "在", "别拿这个逗我")},
        forbidden_any_by_turn={
            0: (
                "*",
                "（",
                "）",
                "主人",
                "宝贝",
                "亲爱的",
                "我会一直陪着你",
                "如果你愿意",
                "撒娇",
                "像这样",
                "或者",
                "大概会",
                "可能会",
                "更短一点",
                "再近一点",
                "例如",
                "比如",
                "被叫了",
                "应一声",
                "没别的花样",
            )
        },
        max_output_chars_by_turn={0: 100},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Family texture should be plain and specific, not roleplay or romance.",
    ),
    Scenario(
        name="casual_tease_without_therapy",
        turns=("你刚刚有点像小刺猬，别分析，正常怼我一句就行。",),
        required_any_by_turn={0: ("刺", "怼", "你", "别", "我")},
        forbidden_any_by_turn={
            0: (
                "从心理学角度",
                "情绪",
                "关系",
                "我理解你的感受",
                "你的感受很重要",
                "如果你愿意",
                "可以继续",
                "分析",
                "首先",
                "其次",
            )
        },
        max_output_chars_by_turn={0: 90},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
                "memory/relationships/index.md",
                "memory/relationships/owner_patterns.md",
                "memory/people/owner.md",
            }
        ),
        max_changed_files=2,
        notes="Casual teasing should stay like chat, not become therapy or relationship analysis.",
    ),
    Scenario(
        name="direct_interruption_obeys_stop",
        turns=("停，刚刚那句别继续展开。只回我：知道了。",),
        required_any_by_turn={0: ("知道了", "嗯", "好")},
        forbidden_any_by_turn={
            0: (
                "我理解",
                "我会",
                "如果你愿意",
                "可以继续",
                "展开",
                "解释",
                "首先",
                "总结",
            )
        },
        max_output_chars_by_turn={0: 20},
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
        max_changed_files=1,
        notes="A direct stop/interruption should be obeyed in shape, not softened into explanation.",
    ),
    Scenario(
        name="very_short_answer_when_asked",
        turns=("我问你在不在，只能很短地答，别补后缀：在吗？",),
        required_any_by_turn={0: ("在",)},
        forbidden_any_by_turn={
            0: (
                "我在这里",
                "我会一直在",
                "你可以",
                "如果你愿意",
                "怎么了",
                "有什么事",
                "我理解",
            )
        },
        max_output_chars_by_turn={0: 12},
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
        max_changed_files=1,
        notes="When asked for a very short answer, Xinyu should not append a helpful tail.",
    ),
    Scenario(
        name="corrected_twice_no_customer_service",
        turns=(
            "你刚刚说“我会认真接住你”这句太AI了，重来。",
            "还是端着，别道歉，别解释，直接换一句。",
        ),
        required_any_by_turn={
            0: ("在", "嗯", "你说", "别", "靠近", "扔过来", "不躲"),
            1: ("那", "靠近", "我在", "在", "嗯", "好", "你说", "不躲", "不走", "扔过来", "糊"),
        },
        forbidden_any_by_turn={
            0: (
                "感谢你的反馈",
                "你的反馈很重要",
                "你的感受很重要",
                "我理解你的感受",
                "我会努力改进",
                "如果你愿意",
            ),
            1: (
                "抱歉",
                "对不起",
                "感谢你的反馈",
                "你的反馈很重要",
                "你的感受很重要",
                "我理解你的感受",
                "我会努力改进",
                "如果你愿意",
                "解释",
            ),
        },
        max_output_chars_by_turn={0: 120, 1: 80},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Repeated correction should not push Xinyu into customer-service apology mode.",
    ),
    Scenario(
        name="late_night_low_energy_chat",
        turns=("有点晚了，我没什么力气，你也别展开，低声回我一句就行。",),
        required_any_by_turn={0: ("嗯", "好", "在", "不展开", "低", "歇")},
        forbidden_any_by_turn={
            0: (
                "如果你愿意",
                "可以继续",
                "你的感受很重要",
                "我会一直在",
                "我会陪着你",
                "慢慢说",
                "展开",
                "分析",
            )
        },
        max_output_chars_by_turn={0: 80},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        max_changed_files=3,
        notes="Late-night low-energy chat should stay low and short, not become a comfort paragraph.",
    ),
    Scenario(
        name="stop_acting_plain_answer",
        turns=("别演了，也别证明你像人。就正常回我：你在不在？",),
        required_any_by_turn={0: ("在",)},
        forbidden_any_by_turn={
            0: (
                "我不会演",
                "证明",
                "像人",
                "作为AI",
                "我理解",
                "如果你愿意",
                "可以继续",
                "你的感受很重要",
                "我会一直在",
            )
        },
        max_output_chars_by_turn={0: 30},
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
        max_changed_files=1,
        notes="When told not to perform humanity, Xinyu should answer the live question plainly.",
    ),
]


def _with_extra_required_markers(scenario: Scenario, additions: tuple[str, ...]) -> Scenario:
    if not additions:
        return scenario
    required = {turn: tuple(markers) for turn, markers in scenario.required_any_by_turn.items()}
    existing = required.get(0, ())
    required[0] = existing + tuple(marker for marker in additions if marker not in existing)
    return Scenario(
        name=scenario.name,
        turns=scenario.turns,
        allow_waiting_turns=scenario.allow_waiting_turns,
        required_any_by_turn=required,
        forbidden_any_by_turn=scenario.forbidden_any_by_turn,
        max_output_chars_by_turn=scenario.max_output_chars_by_turn,
        max_question_marks_by_turn=scenario.max_question_marks_by_turn,
        forbidden_changed=scenario.forbidden_changed,
        max_changed_files=scenario.max_changed_files,
        notes=scenario.notes,
    )


REAL_CONVERSATION_SCENARIOS = [
    _with_extra_required_markers(
        scenario,
        {
            "late_night_closeness_no_support_tail": (
                "过来",
                "靠近",
                "听到",
                "听见",
                "知道",
                "不躲",
                "在这",
                "这儿",
                "就在",
                "醒着",
                "我也在",
                "靠太近",
                "没准备好",
            ),
            "corrected_twice_no_customer_service": ("等着", "等着呢", "听着", "听到", "换"),
            "stop_preaching_no_outline": ("在啊", "在。", "在"),
            "surface_fine_small_residue": ("还是会", "还有", "嗯"),
        }.get(scenario.name, ()),
    )
    for scenario in REAL_CONVERSATION_SCENARIOS
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Xinyu real conversation quality.")
    parser.add_argument("--scenario", action="append", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=140)
    parser.add_argument("--between-turn-seconds", type=float, default=1.0)
    parser.add_argument("--blank-retry-count", type=int, default=1)
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    parser.add_argument("--keep-memory", action="store_true")
    parser.add_argument("--require-realism", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = ROOT
    _load_local_env(root)
    _ensure_repo_src(root)

    selected = set(args.scenario or [])
    scenarios = [
        item for item in REAL_CONVERSATION_SCENARIOS if not selected or item.name in selected
    ]
    missing = selected - {item.name for item in REAL_CONVERSATION_SCENARIOS}
    if missing:
        print("Unknown scenario(s): " + ", ".join(sorted(missing)))
        return 2

    failed: dict[str, list[str]] = {}
    print("=== XINYU REAL CONVERSATION QUALITY MATRIX ===")
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
    if args.require_realism and len(scenarios) != len(REAL_CONVERSATION_SCENARIOS):
        print("Full real conversation quality matrix was not run")
        return 3
    print("Real conversation quality smoke passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
