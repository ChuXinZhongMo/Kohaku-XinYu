from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import asyncio
import os
import sys
from pathlib import Path


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


def _read_message(args: argparse.Namespace) -> str:
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8").strip()
        if not message:
            raise SystemExit(f"Message file is empty: {args.message_file}")
        return message
    return args.message


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Programmatic smoke test for Xinyu without terminal stdout noise."
    )
    parser.add_argument("--message", default="你好，心玉。")
    parser.add_argument("--message-file", default=None)
    parser.add_argument(
        "--show-memory",
        action="store_true",
        help="Print key memory files after the run.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=150,
        help="Maximum seconds to wait for a single injected turn.",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=2.0,
        help="Extra seconds to allow follow-up tasks to flush before agent stop.",
    )
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

    message = _read_message(args)
    agent = Agent.from_path(str(xinyu_dir))
    visible_chunks: list[str] = []
    agent.set_output_handler(lambda text: visible_chunks.append(text), replace_default=True)

    try:
        await agent.start()
        try:
            await asyncio.wait_for(
                agent.inject_input(message, source="programmatic_smoke"),
                timeout=args.timeout_seconds,
            )
        except TimeoutError:
            print("=== TIMEOUT ===")
            print(f"Turn exceeded {args.timeout_seconds} seconds.")
        if args.settle_seconds > 0:
            await asyncio.sleep(args.settle_seconds)
    finally:
        await agent.stop()

    print("=== MESSAGE ===")
    print(message)
    print("=== OUTPUT ===")
    print("".join(visible_chunks))
    print("=== CONVERSATION TAIL ===")
    for msg in agent.conversation_history[-6:]:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        print(f"[{role}] {content}")

    if args.show_memory:
        print("=== MEMORY ===")
        for rel in [
            "memory/context/time_anchor.md",
            "memory/context/recent_context.md",
            "memory/self/narrative.md",
            "memory/emotions/current_state.md",
            "memory/people/owner.md",
        ]:
            path = xinyu_dir / rel
            print(f"\n--- {rel} ---")
            print(path.read_text(encoding="utf-8"))

    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
