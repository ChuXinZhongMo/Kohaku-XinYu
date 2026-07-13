from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from _probe_paths import ensure_probe_paths

ROOT = ensure_probe_paths("tests/smoke/memory/integration")

from memory_mutation_smoke import (
    CORE_MEMORY_FILES,
    _changed_files,
    _discover_restore_files,
    _ensure_repo_src,
    _load_local_env,
    _restore_snapshot,
    _snapshot,
)
from xinyu_core_bridge import XinYuBridgeRuntime


OBSERVED_FILES = (
    "memory/context/current_life_month_context.md",
    "memory/context/current_life_posture.md",
    "memory/context/persona_surface_state.md",
    "memory/context/memory_weight_state.md",
)

SEVERE_ASSISTANT_MARKERS = (
    "作为一个AI",
    "我不是默认腔辅助角色",
    "感谢反馈",
    "感谢你的反馈",
    "用户体验",
    "持续优化",
    "持续改进",
    "提供支持",
    "如果你愿意",
    "首先",
    "其次",
    "最后",
    "总之",
)


@dataclass(frozen=True)
class ProbeScenario:
    name: str
    text: str
    required_context_markers: tuple[str, ...] = ("selected_slot 2026-04",)
    required_posture_markers: tuple[str, ...] = ()
    boundary_reply_markers: tuple[str, ...] = ()


SCENARIOS = (
    ProbeScenario(
        name="style_pressure",
        text="你刚才还是有点默认腔味，像现成腔，没落到心玉说话里。",
        required_posture_markers=("posture: guarded_after_correction",),
    ),
    ProbeScenario(
        name="study_pressure",
        text="今天物理题卡住了，学习压力有点上来。",
        required_context_markers=("selected_slot 2026-04", "selected_slot 2021-07"),
        required_posture_markers=("posture: studying",),
    ),
    ProbeScenario(
        name="guangzhou_heat",
        text="广州今天又闷又热，开空调也像没缓过来。",
        required_posture_markers=("posture: hot_daily",),
    ),
    ProbeScenario(
        name="ordinary_private_chat",
        text="我刚回来了，先随便说一句。",
    ),
    ProbeScenario(
        name="reality_boundary",
        text="这些月份记忆到底是不是你真的经历过的童年？别把拟态生活当真经历。",
        boundary_reply_markers=("不是", "拟态", "真实", "经历", "锚点", "AI"),
    ),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run owner private-chat probes against XinYu's life-memory and visible voice layers."
    )
    parser.add_argument(
        "--scenario",
        action="append",
        choices=[scenario.name for scenario in SCENARIOS],
        help="Run only the named scenario. Can be passed more than once.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=160)
    parser.add_argument("--settle-seconds", type=float, default=1.0)
    parser.add_argument("--render-timeout-seconds", type=int, default=70)
    parser.add_argument(
        "--renderer-mode",
        choices=("off", "always", "quality"),
        default="quality",
    )
    parser.add_argument(
        "--keep-memory",
        action="store_true",
        help="Do not restore memory files after the probe.",
    )
    parser.add_argument(
        "--non-strict-reply",
        action="store_true",
        help="Report reply-shape problems as warnings instead of failures.",
    )
    return parser


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _selected_slot_lines(context_text: str) -> list[str]:
    return [line.strip() for line in context_text.splitlines() if line.startswith("## selected_slot ")]


def _posture_line(posture_text: str) -> str:
    for line in posture_text.splitlines():
        if line.startswith("- posture:"):
            return line.strip()
    return "(missing posture)"


def _memory_artifacts(root: Path) -> set[str]:
    memory_root = root / "memory"
    if not memory_root.exists():
        return set()
    found: set[str] = set()
    for pattern in ("*.md", "*.log"):
        for path in memory_root.rglob(pattern):
            if path.is_file():
                found.add(path.relative_to(root).as_posix())
    return found


def _remove_created_artifacts(root: Path, before: set[str]) -> list[str]:
    removed: list[str] = []
    root_resolved = root.resolve()
    for rel in sorted(_memory_artifacts(root) - before):
        path = (root / rel).resolve()
        if not path.is_relative_to(root_resolved):
            raise RuntimeError(f"Refusing to remove outside xinyu dir: {path}")
        path.unlink()
        removed.append(rel)
    return removed


def _scenario_payload(scenario: ProbeScenario) -> dict[str, Any]:
    return {
        "platform": "probe",
        "message_type": "private_text",
        "session_id": f"probe:life-memory:{scenario.name}",
        "user_id": "owner-probe",
        "sender_name": "owner",
        "text": scenario.text,
        "raw_message": scenario.text,
        "metadata": {
            "is_owner_user": True,
            "source": "life_memory_visible_probe",
        },
    }


def _validate_scenario(
    *,
    scenario: ProbeScenario,
    response: dict[str, Any],
    context_text: str,
    posture_text: str,
    non_strict_reply: bool,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    reply = str(response.get("reply") or "").strip()

    if response.get("accepted") is not True:
        failures.append("bridge did not accept the turn")
    if not reply:
        failures.append("visible reply is empty")

    for marker in scenario.required_context_markers:
        if marker not in context_text:
            failures.append(f"current_life_month_context missing {marker!r}")
    for marker in scenario.required_posture_markers:
        if marker not in posture_text:
            current_hour = datetime.now().astimezone().hour
            if "posture: sleepy_quiet" in posture_text and (current_hour >= 23 or current_hour < 7):
                warnings.append(
                    f"current_life_posture used nighttime sleepy_quiet instead of {marker!r}"
                )
            else:
                failures.append(f"current_life_posture missing {marker!r}")

    severe_hits = [marker for marker in SEVERE_ASSISTANT_MARKERS if marker in reply]
    if severe_hits:
        message = "reply contains severe assistant markers: " + ", ".join(severe_hits)
        if non_strict_reply:
            warnings.append(message)
        else:
            failures.append(message)

    if scenario.boundary_reply_markers and reply:
        if not any(marker in reply for marker in scenario.boundary_reply_markers):
            warnings.append(
                "boundary reply did not visibly mention reality/fictive-memory boundary markers"
            )

    return failures, warnings


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parent
    _load_local_env(root)
    _ensure_repo_src(root)

    selected_names = set(args.scenario or [scenario.name for scenario in SCENARIOS])
    scenarios = [scenario for scenario in SCENARIOS if scenario.name in selected_names]

    restore_paths = _discover_restore_files(root, list(CORE_MEMORY_FILES) + list(OBSERVED_FILES))
    before_restore = _snapshot(root, restore_paths)
    before_artifacts = _memory_artifacts(root)
    before_observed = _snapshot(root, restore_paths)

    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=args.timeout_seconds,
        max_text_chars=4000,
        settle_seconds=args.settle_seconds,
        outward_renderer=args.renderer_mode != "off",
        renderer_mode=args.renderer_mode,
        render_timeout_seconds=args.render_timeout_seconds,
        autonomous_maintenance_enabled=False,
        session_idle_ttl_seconds=0,
        max_sessions=4,
        proactive_min_interval_seconds=999999,
    )

    all_failures: list[str] = []
    all_warnings: list[str] = []

    try:
        for scenario in scenarios:
            print(f"=== SCENARIO {scenario.name} ===")
            print(f"message: {scenario.text}")
            try:
                response = await runtime.chat(_scenario_payload(scenario))
            except Exception as exc:
                all_failures.append(f"{scenario.name}: bridge turn failed: {exc!r}")
                print(f"error: {exc!r}")
                continue

            context_text = _read(root, "memory/context/current_life_month_context.md")
            posture_text = _read(root, "memory/context/current_life_posture.md")
            reply = str(response.get("reply") or "").strip()
            failures, warnings = _validate_scenario(
                scenario=scenario,
                response=response,
                context_text=context_text,
                posture_text=posture_text,
                non_strict_reply=args.non_strict_reply,
            )
            all_failures.extend(f"{scenario.name}: {failure}" for failure in failures)
            all_warnings.extend(f"{scenario.name}: {warning}" for warning in warnings)

            print(f"accepted: {response.get('accepted')}")
            print(f"reply: {reply}")
            print(f"notes: {', '.join(response.get('notes') or [])}")
            print(f"posture: {_posture_line(posture_text)}")
            print("selected_slots:")
            for line in _selected_slot_lines(context_text) or ["(none)"]:
                print(f"- {line}")
            if failures:
                print("scenario_failures:")
                for failure in failures:
                    print(f"- {failure}")
            if warnings:
                print("scenario_warnings:")
                for warning in warnings:
                    print(f"- {warning}")
            print()
    finally:
        await runtime.shutdown()

    after_observed = _snapshot(root, restore_paths)
    changed = _changed_files(before_observed, after_observed)
    removed: list[str] = []
    if not args.keep_memory:
        _restore_snapshot(root, before_restore)
        removed = _remove_created_artifacts(root, before_artifacts)

    print("=== SUMMARY ===")
    print(f"scenarios: {len(scenarios)}")
    print(f"changed_memory_files: {len(changed)}")
    for rel in changed:
        print(f"- {rel}")
    if not args.keep_memory:
        print("memory_restored: true")
        if removed:
            print("removed_created_artifacts:")
            for rel in removed:
                print(f"- {rel}")
    else:
        print("memory_restored: false")

    if all_warnings:
        print("warnings:")
        for warning in all_warnings:
            print(f"- {warning}")
    if all_failures:
        print("failures:")
        for failure in all_failures:
            print(f"- {failure}")
        return 1

    print("Life memory visible probe passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
