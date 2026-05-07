from __future__ import annotations

import argparse
import asyncio
import difflib
import hashlib
import os
import sys
from pathlib import Path


CORE_MEMORY_FILES = [
    "memory/context/time_anchor.md",
    "memory/context/recent_context.md",
    "memory/context/continuity_index.md",
    "memory/context/unfinished_experiences.md",
    "memory/context/life_month_slots.md",
    "memory/context/active_questions.md",
    "memory/emotions/current_state.md",
    "memory/emotions/event_log.md",
    "memory/relationships/index.md",
    "memory/relationships/owner_patterns.md",
    "memory/people/index.md",
    "memory/people/owner.md",
    "memory/self/system_prompt_memory.md",
    "memory/self/narrative.md",
    "memory/context/real_world_anchor_policy.md",
    "memory/reflection/reflection_log.md",
    "memory/reflection/growth_log.md",
    "memory/dreams/dream_log.md",
    "memory/archive/archive_queue.md",
    "memory/archive/compressed.md",
    "memory/knowledge/general.md",
    "memory/knowledge/source_notes.md",
]

VOLATILE_MEMORY_FILES = {
    "memory/context/turn_mode_state.md",
    "memory/context/inner_cycle_state.md",
    "memory/context/question_pipeline_state.md",
    "memory/context/maintenance_schedule_state.md",
    "memory/context/runtime_bridge_state.md",
    "memory/context/maintenance_dispatch_state.md",
    "memory/context/maintenance_recommendations.md",
    "memory/context/persona_surface_state.md",
    "memory/context/memory_weight_state.md",
    "memory/context/current_life_month_context.md",
}


def _load_local_env(xinyu_dir: Path) -> None:
    env_path = xinyu_dir / "xinyu.local.env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ensure_repo_src(xinyu_dir: Path) -> None:
    repo_root = xinyu_dir.parents[2]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


def _read_message(args: argparse.Namespace) -> str:
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8-sig").strip()
        if not message:
            raise SystemExit(f"Message file is empty: {args.message_file}")
        return message
    return args.message


def _discover_memory_files(xinyu_dir: Path) -> list[str]:
    memory_root = xinyu_dir / "memory"
    files: list[str] = []
    for path in memory_root.rglob("*.md"):
        rel = path.relative_to(xinyu_dir).as_posix()
        if rel in VOLATILE_MEMORY_FILES:
            continue
        files.append(rel)
    return sorted(files)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _discover_restore_files(xinyu_dir: Path, tracked: list[str]) -> list[str]:
    memory_root = xinyu_dir / "memory"
    files = set(tracked) | set(VOLATILE_MEMORY_FILES)
    extra_markdown = {
        "memory/context/automation_state.md",
        "memory/context/inner_sync_state.md",
        "memory/context/maintenance_recommendations.md",
    }
    files |= extra_markdown
    for path in memory_root.rglob("*.md"):
        rel = path.relative_to(xinyu_dir).as_posix()
        if rel.endswith("_state.md"):
            files.add(rel)
    for path in memory_root.rglob("*.log"):
        files.add(path.relative_to(xinyu_dir).as_posix())
    return sorted(files)


def _snapshot(xinyu_dir: Path, rel_paths: list[str]) -> dict[str, str | None]:
    snap: dict[str, str | None] = {}
    for rel in rel_paths:
        path = xinyu_dir / rel
        if not path.exists():
            snap[rel] = None
            continue
        snap[rel] = path.read_text(encoding="utf-8-sig")
    return snap


def _restore_snapshot(xinyu_dir: Path, before: dict[str, str | None]) -> None:
    root = xinyu_dir.resolve()
    for rel, content in before.items():
        path = (xinyu_dir / rel).resolve()
        if not path.is_relative_to(root):
            raise RuntimeError(f"Refusing to restore outside xinyu dir: {path}")
        if content is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _changed_files(
    before: dict[str, str | None],
    after: dict[str, str | None],
) -> list[str]:
    changed: list[str] = []
    for rel in sorted(set(before) | set(after)):
        old = before.get(rel)
        new = after.get(rel)
        if old is None and new is None:
            continue
        if old is None or new is None or _sha(old) != _sha(new):
            changed.append(rel)
    return changed


def _render_diff(old: str | None, new: str | None, rel: str, limit: int) -> list[str]:
    old_lines = [] if old is None else old.splitlines()
    new_lines = [] if new is None else new.splitlines()
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"before/{rel}",
        tofile=f"after/{rel}",
        lineterm="",
    )
    lines = list(diff)
    if limit <= 0:
        return []
    if len(lines) > limit:
        return lines[:limit] + [f"... diff truncated after {limit} lines ..."]
    return lines


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one Xinyu turn and report core memory file mutations."
    )
    parser.add_argument(
        "--message",
        default=(
            "我今天想确认一件事：不是每句话都需要被你记住，"
            "但如果某句话真的影响了你，你可以只留下重要的部分。"
        ),
    )
    parser.add_argument("--message-file", default=None)
    parser.add_argument(
        "--all-memory",
        action="store_true",
        help="Track all non-volatile memory markdown files instead of core files only.",
    )
    parser.add_argument(
        "--restore-after",
        action="store_true",
        help="Restore tracked memory files after reporting mutations.",
    )
    parser.add_argument(
        "--require-memory-change",
        action="store_true",
        help="Exit non-zero if no tracked memory file changes.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="Maximum seconds to wait for the injected turn.",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=3.0,
        help="Extra seconds to allow writer tasks to flush before agent stop.",
    )
    parser.add_argument(
        "--diff-lines",
        type=int,
        default=120,
        help="Maximum diff lines to print per changed file. Use 0 to suppress diffs.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    xinyu_dir = Path(__file__).resolve().parent
    _load_local_env(xinyu_dir)
    _ensure_repo_src(xinyu_dir)

    from xinyu_runtime.core.agent import Agent

    tracked = _discover_memory_files(xinyu_dir) if args.all_memory else CORE_MEMORY_FILES
    restore_paths = _discover_restore_files(xinyu_dir, tracked) if args.restore_after else tracked
    before_restore = _snapshot(xinyu_dir, restore_paths)
    before = {rel: before_restore.get(rel) for rel in tracked}

    message = _read_message(args)
    agent = Agent.from_path(str(xinyu_dir))
    visible_chunks: list[str] = []
    timed_out = False
    agent.set_output_handler(lambda text: visible_chunks.append(text), replace_default=True)

    try:
        await agent.start()
        try:
            await asyncio.wait_for(
                agent.inject_input(message, source="memory_mutation_smoke"),
                timeout=args.timeout_seconds,
            )
        except TimeoutError:
            timed_out = True
        if args.settle_seconds > 0:
            await asyncio.sleep(args.settle_seconds)
    finally:
        await agent.stop()

    after_restore = _snapshot(xinyu_dir, restore_paths)
    after = {rel: after_restore.get(rel) for rel in tracked}
    changed = _changed_files(before, after)
    output = "".join(visible_chunks).strip()

    print("=== MESSAGE ===")
    print(message)
    print("=== OUTPUT ===")
    print(output)
    print("=== MUTATION SUMMARY ===")
    print(f"tracked_files: {len(tracked)}")
    print(f"changed_files: {len(changed)}")
    print(f"timed_out: {timed_out}")
    print(f"restore_after: {args.restore_after}")

    if changed:
        print("=== CHANGED FILES ===")
        for rel in changed:
            print(rel)
    else:
        print("=== CHANGED FILES ===")
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
    if not output:
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
