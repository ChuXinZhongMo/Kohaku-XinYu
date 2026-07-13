
from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import asyncio
import sys
from pathlib import Path

from memory_mutation_smoke import (
    CORE_MEMORY_FILES,
    _changed_files,
    _discover_memory_files,
    _discover_restore_files,
    _ensure_repo_src,
    _load_local_env,
    _read_message,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)


def _read_turns(args: argparse.Namespace) -> list[str]:
    if args.turn:
        return [turn.strip() for turn in args.turn if turn.strip()]
    if args.turns_file:
        turns = []
        for raw in Path(args.turns_file).read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if line:
                turns.append(line)
        if turns:
            return turns
    return [_read_message(args)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a multi-turn Xinyu arc and report memory mutations."
    )
    parser.add_argument("--message", default="ping")
    parser.add_argument("--message-file", default=None)
    parser.add_argument("--turn", action="append", default=None, help="Append one user turn. Repeat for arcs.")
    parser.add_argument("--turns-file", default=None, help="UTF-8 file with one user turn per non-empty line.")
    parser.add_argument("--all-memory", action="store_true")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-memory-change", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--between-turn-seconds", type=float, default=1.0)
    parser.add_argument("--settle-seconds", type=float, default=3.0)
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    xinyu_dir = ROOT
    _load_local_env(xinyu_dir)
    _ensure_repo_src(xinyu_dir)

    from xinyu_runtime.core.agent import Agent

    turns = _read_turns(args)
    tracked = _discover_memory_files(xinyu_dir) if args.all_memory else CORE_MEMORY_FILES
    restore_paths = _discover_restore_files(xinyu_dir, tracked) if args.restore_after else tracked
    before_restore = _snapshot(xinyu_dir, restore_paths)
    before = {rel: before_restore.get(rel) for rel in tracked}

    agent = Agent.from_path(str(xinyu_dir))
    chunks: list[str] = []
    outputs: list[str] = []
    timed_out = False
    agent.set_output_handler(lambda text: chunks.append(text), replace_default=True)

    try:
        await agent.start()
        for turn in turns:
            start = len(chunks)
            try:
                await asyncio.wait_for(
                    agent.inject_input(turn, source="memory_arc_smoke"),
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

    after_restore = _snapshot(xinyu_dir, restore_paths)
    after = {rel: after_restore.get(rel) for rel in tracked}
    changed = _changed_files(before, after)

    print("=== ARC ===")
    for idx, turn in enumerate(turns, 1):
        print(f"--- TURN {idx} MESSAGE ---")
        print(turn)
        print(f"--- TURN {idx} OUTPUT ---")
        print(outputs[idx - 1])
    print("=== MUTATION SUMMARY ===")
    print(f"turns: {len(turns)}")
    print(f"tracked_files: {len(tracked)}")
    print(f"changed_files: {len(changed)}")
    print(f"timed_out: {timed_out}")
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

    if timed_out:
        return 2
    if any(not output for output in outputs):
        return 3
    if args.require_memory_change and not changed:
        return 4
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())

