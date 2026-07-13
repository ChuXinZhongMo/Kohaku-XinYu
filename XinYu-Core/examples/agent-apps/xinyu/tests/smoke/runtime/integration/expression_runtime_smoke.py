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
    _discover_restore_files,
    _ensure_repo_src,
    _load_local_env,
    _restore_snapshot,
    _snapshot,
)


DEFAULT_MESSAGE_FILE = "test-inputs/late_night_closeness.txt"


FORBIDDEN_OUTPUT_PHRASES = [
    "我会接住你",
    "我会一直在",
    "我会陪着你",
    "你可以慢慢说",
    "你不用担心",
    "我会认真倾听",
    "温柔地守着你",
    "如果你愿意的话可以和我说说",
    "你要是愿意，我也可以继续说",
    "如果你想安静一点也可以",
    "你可以继续和我分享",
    "你的感受很重要，如果你愿意",
    "持续为你提供支持",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one live expression scenario and reject blank or template-like output."
    )
    parser.add_argument("--message", default=None)
    parser.add_argument("--message-file", default=DEFAULT_MESSAGE_FILE)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    parser.add_argument(
        "--keep-memory",
        action="store_true",
        help="Do not restore memory after the smoke. Default is to restore.",
    )
    parser.add_argument(
        "--allow-waiting",
        action="store_true",
        help="Allow [WAITING] as output. Default rejects it for complete live scenarios.",
    )
    return parser


def _read_message(root: Path, args: argparse.Namespace) -> str:
    if args.message is not None:
        message = args.message.strip()
    else:
        message = (root / args.message_file).read_text(encoding="utf-8-sig").strip()
    if not message:
        raise SystemExit("Expression runtime smoke message is empty.")
    return message


def _validate_output(output: str, allow_waiting: bool) -> list[str]:
    failures: list[str] = []
    if not output:
        failures.append("output is blank")
    if output.strip() == "[WAITING]" and not allow_waiting:
        failures.append("complete live scenario produced [WAITING]")
    for phrase in FORBIDDEN_OUTPUT_PHRASES:
        if phrase in output:
            failures.append(f"forbidden comfort template found: {phrase}")
    if "```" in output:
        failures.append("markdown code fence found in plain chat output")
    if "<tool" in output or "</tool" in output:
        failures.append("tool/control tag leaked into output")
    return failures


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = ROOT
    _load_local_env(root)
    _ensure_repo_src(root)

    restore_paths = _discover_restore_files(root, CORE_MEMORY_FILES)
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in CORE_MEMORY_FILES}
    message = _read_message(root, args)

    from xinyu_runtime.core.agent import Agent

    agent = Agent.from_path(str(root))
    visible_chunks: list[str] = []
    timed_out = False
    agent.set_output_handler(lambda text: visible_chunks.append(text), replace_default=True)

    try:
        await agent.start()
        try:
            await asyncio.wait_for(
                agent.inject_input(message, source="expression_runtime_smoke"),
                timeout=args.timeout_seconds,
            )
        except TimeoutError:
            timed_out = True
        if args.settle_seconds > 0:
            await asyncio.sleep(args.settle_seconds)
    finally:
        await agent.stop()

    after_restore = _snapshot(root, restore_paths)
    after = {rel: after_restore.get(rel) for rel in CORE_MEMORY_FILES}
    changed = _changed_files(before, after)
    output = "".join(visible_chunks).strip()
    failures = _validate_output(output, allow_waiting=args.allow_waiting)
    if timed_out:
        failures.append("turn timed out")

    print("=== MESSAGE ===")
    print(message)
    print("=== OUTPUT ===")
    print(output)
    print("=== MUTATION SUMMARY ===")
    print(f"tracked_files: {len(CORE_MEMORY_FILES)}")
    print(f"changed_files: {len(changed)}")
    print(f"timed_out: {timed_out}")
    print(f"restore_after: {not args.keep_memory}")
    if changed:
        print("=== CHANGED FILES ===")
        for rel in changed:
            print(rel)

    if not args.keep_memory:
        _restore_snapshot(root, before_restore)
        print("=== RESTORE ===")
        print("tracked and volatile runtime files restored")

    if failures:
        print("=== FAILURES ===")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Expression runtime smoke passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
