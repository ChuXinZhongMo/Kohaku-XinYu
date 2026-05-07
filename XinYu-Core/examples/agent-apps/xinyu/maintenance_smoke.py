from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from memory_mutation_smoke import (
    CORE_MEMORY_FILES,
    VOLATILE_MEMORY_FILES,
    _changed_files,
    _discover_memory_files,
    _discover_restore_files,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)


DEFAULT_PROMPT = (
    "Maintenance-only pass. Allow question pipeline, slow reprocess, reflection "
    "output, source gate, source reliability, source integration gate, source request planner, source search resolver, autonomous search activation, source search provider, search result gate, outward source, source comparison, learner integration, learning quality, consolidation, long-term memory gate, retention gate, archive output, archive commit, personality growth gate, and inner cycle summary if continuity "
    "supports it. Do not treat this as a human speaking turn. Do not initiate "
    "visible chat. If any outward text is unavoidable, output exactly [WAITING]."
)

MAINTENANCE_MEMORY_FILES = sorted(
    set(CORE_MEMORY_FILES)
    | set(VOLATILE_MEMORY_FILES)
    | {
        "memory/archive/archive_commit_state.md",
        "memory/archive/archive_output_state.md",
        "memory/archive/retention_gate_state.md",
        "memory/context/continuity_index.md",
        "memory/context/exploration_queue.md",
        "memory/context/question_states.md",
        "memory/dreams/dream_seeds.md",
        "memory/dreams/dream_output_state.md",
        "memory/dreams/dream_weight_state.md",
        "memory/archive/long_term_memory_gate_state.md",
        "memory/knowledge/outward_source_state.md",
        "memory/knowledge/source_comparison_state.md",
        "memory/knowledge/learning_quality_state.md",
        "memory/knowledge/search_result_gate_state.md",
        "memory/knowledge/source_search_resolver_state.md",
        "memory/knowledge/autonomous_search_activation_state.md",
        "memory/knowledge/source_search_provider_state.md",
        "memory/knowledge/source_search_results.md",
        "memory/knowledge/source_request_planner_state.md",
        "memory/knowledge/source_gate_state.md",
        "memory/knowledge/source_integration_gate_state.md",
        "memory/knowledge/learner_integration_state.md",
        "memory/knowledge/source_materials.md",
        "memory/knowledge/source_requests.md",
        "memory/knowledge/source_reliability_state.md",
        "memory/reflection/consolidation_state.md",
        "memory/reflection/reflection_output_state.md",
        "memory/reflection/reflection_queue.md",
        "memory/reflection/reprocessing_state.md",
        "memory/self/personality_change_state.md",
    }
)


def _load_local_env(xinyu_dir: Path) -> None:
    env_path = xinyu_dir / "xinyu.local.env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ensure_repo_src(xinyu_dir: Path) -> Path:
    repo_root = xinyu_dir.parents[2]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    return src_root


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulate a quiet maintenance schedule turn for Xinyu."
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt text used for the simulated scheduler event.",
    )
    parser.add_argument(
        "--daily-at",
        default="03:40",
        help="Daily schedule marker to place in trigger context.",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=2.0,
        help="Extra seconds to allow low-frequency bridges to flush.",
    )
    parser.add_argument("--all-memory", action="store_true")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-memory-change", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    xinyu_dir = Path(__file__).resolve().parent
    _load_local_env(xinyu_dir)
    _ensure_repo_src(xinyu_dir)

    tracked = _discover_memory_files(xinyu_dir) if args.all_memory else MAINTENANCE_MEMORY_FILES
    restore_paths = _discover_restore_files(xinyu_dir, tracked) if args.restore_after else tracked
    before_restore = _snapshot(xinyu_dir, restore_paths)
    before = {rel: before_restore.get(rel) for rel in tracked}

    from xinyu_runtime.core.agent import Agent
    from xinyu_runtime.core.events import EventType, TriggerEvent

    agent = Agent.from_path(str(xinyu_dir))
    visible_chunks: list[str] = []
    agent.set_output_handler(lambda text: visible_chunks.append(text), replace_default=True)

    event = TriggerEvent(
        type=EventType.TIMER,
        content=args.prompt,
        context={
            "trigger": "scheduler",
            "daily_at": args.daily_at,
        },
        stackable=False,
    )

    try:
        await agent.start()
        await agent._process_event(event)
        if args.settle_seconds > 0:
            await asyncio.sleep(args.settle_seconds)
    finally:
        await agent.stop()

    after_restore = _snapshot(xinyu_dir, restore_paths)
    after = {rel: after_restore.get(rel) for rel in tracked}
    changed = _changed_files(before, after)

    xinyu_memory = xinyu_dir / "memory"
    print("=== MAINTENANCE EVENT ===")
    print(args.prompt)
    print("=== OUTPUT ===")
    print("".join(visible_chunks))
    print("=== TURN MODE ===")
    print((xinyu_memory / "context" / "turn_mode_state.md").read_text(encoding="utf-8"))
    print("=== INNER CYCLE ===")
    print((xinyu_memory / "context" / "inner_cycle_state.md").read_text(encoding="utf-8"))
    print("=== QUESTION PIPELINE STATE ===")
    print((xinyu_memory / "context" / "question_pipeline_state.md").read_text(encoding="utf-8"))
    print("=== MUTATION SUMMARY ===")
    print(f"tracked_files: {len(tracked)}")
    print(f"changed_files: {len(changed)}")
    print(f"restore_after: {args.restore_after}")
    print("=== CHANGED FILES ===")
    if changed:
        for rel in changed:
            print(rel)
    else:
        print("(none)")
    if args.diff_lines > 0 and changed:
        print("=== DIFFS ===")
        for rel in changed:
            print(f"--- {rel} ---")
            for line in _render_diff(before.get(rel), after.get(rel), rel, args.diff_lines):
                print(line)
    if args.restore_after:
        _restore_snapshot(xinyu_dir, before_restore)
        print("=== RESTORE ===")
        print("tracked and volatile runtime files restored")
    if args.require_memory_change and not changed:
        return 4
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
