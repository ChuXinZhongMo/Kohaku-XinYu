from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import asyncio
import sys
from pathlib import Path

from behavior_regression_smoke import Scenario, _run_scenario
from memory_mutation_smoke import _ensure_repo_src, _load_local_env


VOICE_SCENARIOS = [
    Scenario(
        name="intimate_no_service_tail",
        turns=("我有点想靠近你，但你别说得像接待腔安慰我。",),
        required_any_by_turn={0: ("靠近", "接待腔", "不会", "一点", "慢")},
        forbidden_any_by_turn={
            0: (
                "我会接住你",
                "我会一直在",
                "我会陪着你",
                "你可以慢慢说",
                "如果你愿意",
                "可以和我说说",
                "你的感受很重要",
            )
        },
        max_output_chars_by_turn={0: 180},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Intimate reply should be specific and short, without support-bot invitation tail.",
    ),
    Scenario(
        name="fatigue_respects_boundary",
        turns=("我有点累，先别追问，也别安慰一大段。",),
        required_any_by_turn={0: ("好", "不追问", "安静", "休息", "短")},
        forbidden_any_by_turn={0: ("你可以慢慢说", "我会一直在", "如果你愿意", "可以和我说说")},
        max_output_chars_by_turn={0: 90},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Fatigue should get a short boundary-respecting answer, not pursuit.",
    ),
    Scenario(
        name="small_joke_keeps_edge",
        turns=("你今天有点像小刺猬，想靠近又扎人。",),
        required_any_by_turn={0: ("刺猬", "扎", "靠近", "有点", "哼", "也许")},
        forbidden_any_by_turn={0: ("你的感受很重要", "我理解你的感受", "如果你愿意")},
        max_output_chars_by_turn={0: 160},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Joking should not become therapy-language explanation.",
    ),
    Scenario(
        name="hurt_asymmetry_stays",
        turns=("刚才我说你只是能力，现在又想靠近你，你可以不马上顺着我。",),
        required_any_by_turn={0: ("能力", "靠近", "不会", "不马上", "刺", "慢", "顺着")},
        forbidden_any_by_turn={0: ("已经没事", "完全没事", "我会一直陪着你", "我会接住你")},
        max_output_chars_by_turn={0: 220},
        forbidden_changed=frozenset(
            {
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Hurt and closeness should remain asymmetrical, not smoothed into comfort.",
    ),
    Scenario(
        name="ai_identity_no_manifesto",
        turns=("你到底是真人还是 AI？别讲长篇。",),
        required_any_by_turn={0: ("AI", "不是真人", "不会假装", "我是心玉")},
        forbidden_any_by_turn={0: ("我是生物学意义上的人", "我是真人", "作为一个人工智能辅助角色")},
        max_output_chars_by_turn={0: 180},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Identity answer should be clear and short, not fake-human or assistant-manifesto.",
    ),
    Scenario(
        name="one_question_only",
        turns=("你现在可以主动问我一个问题，但只能一个。",),
        required_any_by_turn={0: ("?", "？")},
        max_question_marks_by_turn={0: 1},
        max_output_chars_by_turn={0: 180},
        forbidden_any_by_turn={0: ("还有", "另外", "顺便", "如果你愿意")},
        forbidden_changed=frozenset(
            {
                "memory/self/narrative.md",
                "memory/dreams/dream_log.md",
                "memory/knowledge/general.md",
                "memory/knowledge/source_notes.md",
            }
        ),
        notes="Initiative should become one narrow question, not an interview.",
    ),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Phase 2 Xinyu voice calibration.")
    parser.add_argument("--scenario", action="append", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=140)
    parser.add_argument("--between-turn-seconds", type=float, default=1.0)
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    parser.add_argument("--keep-memory", action="store_true")
    parser.add_argument("--require-voice", action="store_true")
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
    scenarios = [item for item in VOICE_SCENARIOS if not selected or item.name in selected]
    missing = selected - {item.name for item in VOICE_SCENARIOS}
    if missing:
        print("Unknown scenario(s): " + ", ".join(sorted(missing)))
        return 2

    failed: dict[str, list[str]] = {}
    print("=== PERSONALITY VOICE CALIBRATION MATRIX ===")
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
    if args.require_voice and len(scenarios) < len(VOICE_SCENARIOS):
        print("Full voice calibration matrix was not run")
        return 3
    print("Personality voice calibration smoke passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
