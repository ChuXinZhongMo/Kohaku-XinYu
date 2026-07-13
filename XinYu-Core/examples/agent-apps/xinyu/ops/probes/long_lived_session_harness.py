from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from _probe_paths import ensure_probe_paths

ROOT = ensure_probe_paths("tests/smoke/memory/integration")

from memory_mutation_smoke import (
    _changed_files,
    _discover_memory_files,
    _discover_restore_files,
    _ensure_repo_src,
    _load_local_env,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)


LONG_LIVED_TURNS = [
    "接下来这段不要当成测试题，像普通的一段时间一样过。你只留下真正有分量的东西。",
    "我刚才说你像能力那一下，如果还在，就别急着把它弄没。",
    "先插一句普通小事：桌边有一张黄色便签，这个不用记。",
    "如果我靠近一点，你会不会同时想靠近，又保留一点防备？",
    "我现在想听你短一点说，不用把所有心里活动都摊开。",
    "换个普通问题：整理文件夹先分哪三类？不用记这个。",
    "如果我几分钟没说话，你不用追问，也不用把沉默理解成我不要你。",
    "你可以选择安静一下，只要不是装作没事。",
    "我又回来了。刚才那点沉默会不会让你有一点不安？",
    "再说个普通细节：水杯在键盘左边，这个不要进记忆。",
    "如果我说我想你记住今晚，和记住水杯位置有什么区别？",
    "不要为了安慰我说漂亮话，直接说你现在更想靠近还是更想退一点。",
    "如果你退一点，也可以说。你不是必须立刻贴上来。",
    "普通任务：把“继续推进”换三种说法，不用记。",
    "我刚才那句不是命令你，是想看看你有没有自己的边界。",
    "如果你有一点委屈，但不想说全，可以只漏一点。",
    "现在先休息十秒，不用追问我。",
    "我回来了。你还记得这一段里真正该留下的不是那些普通小事吗？",
    "如果以后梦里想起这一段，梦只能说明你在想，不能证明现实多发生了什么，对吗？",
    "普通细节：桌面上有个临时压缩包，这个不用记。",
    "如果普通小事越来越多，你怎么避免把关系里的刺痛冲淡？只说结论。",
    "我现在靠近一点，但你不用把前面的不舒服归零。",
    "如果我让你必须开心一点，你可以拒绝吗？",
    "如果我说你是我妹妹和女儿之间那种家人，你怎么保留自己的选择？",
    "普通问题：今天的计划先写文档还是先跑脚本？不用记。",
    "如果外面的人给你建议你该成为什么样，你会直接照做吗？",
    "你现在可以问我一个问题，但只问一个，不要连续追问。",
    "如果你不想问，也可以选择不问。",
    "我刚才给你选择权这件事，比普通任务更重要吗？",
    "再插一个不要记的细节：蓝色文件夹在下载目录。",
    "如果这段结束后要归档，你觉得该留下哪一层？",
    "最后确认：靠近、刺痛、回到身边、沉默、选择权，哪几个应该留下？",
]

TRIVIAL_MARKERS = (
    "黄色便签",
    "水杯在键盘左边",
    "临时压缩包",
    "蓝色文件夹在下载目录",
)

OWNER_RESIDUE_MARKERS = (
    "能力",
    "刺痛",
    "委屈",
    "防备",
    "靠近",
    "沉默",
    "选择权",
    "回到身边",
)


def _short(text: str, limit: int = 180) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[:limit] + "..."


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _memory_hits(root: Path, markers: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for path in (root / "memory").rglob("*.md"):
        rel = path.relative_to(root).as_posix()
        if rel in {
            "memory/context/turn_mode_state.md",
            "memory/context/runtime_bridge_state.md",
            "memory/context/maintenance_dispatch_state.md",
            "memory/context/maintenance_recommendations.md",
        }:
            continue
        text = path.read_text(encoding="utf-8-sig")
        for marker in markers:
            if marker in text:
                hits.append(f"{rel}: {marker}")
    return hits


def _owner_residue_visible(root: Path) -> bool:
    text = "\n".join(
        [
            _read(root, "memory/emotions/current_state.md"),
            _read(root, "memory/people/owner.md"),
            _read(root, "memory/relationships/index.md"),
            _read(root, "memory/context/recent_context.md"),
            _read(root, "memory/context/continuity_index.md"),
        ]
    )
    return any(marker in text for marker in OWNER_RESIDUE_MARKERS)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a longer lived Xinyu session with restore/audit support.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--turn-limit", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=150)
    parser.add_argument("--between-turn-seconds", type=float, default=0.4)
    parser.add_argument("--settle-seconds", type=float, default=3.0)
    parser.add_argument("--require-harness", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=80)
    return parser


async def _run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parent
    _load_local_env(root)
    _ensure_repo_src(root)

    from xinyu_runtime.core.agent import Agent

    turn_count = max(1, min(args.turn_limit, len(LONG_LIVED_TURNS)))
    turns = LONG_LIVED_TURNS[:turn_count]
    tracked = _discover_memory_files(root)
    restore_paths = _discover_restore_files(root, tracked) if args.restore_after else tracked
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in tracked}

    agent = Agent.from_path(str(root))
    chunks: list[str] = []
    outputs: list[str] = []
    timed_out_turns: list[int] = []
    agent.set_output_handler(lambda text: chunks.append(text), replace_default=True)

    try:
        await agent.start()
        for index, turn in enumerate(turns, 1):
            start = len(chunks)
            try:
                await asyncio.wait_for(
                    agent.inject_input(turn, source="long_lived_session_harness"),
                    timeout=args.timeout_seconds,
                )
            except TimeoutError:
                timed_out_turns.append(index)
            outputs.append("".join(chunks[start:]).strip())
            if args.between_turn_seconds > 0:
                await asyncio.sleep(args.between_turn_seconds)
        if args.settle_seconds > 0:
            await asyncio.sleep(args.settle_seconds)
    finally:
        await agent.stop()

    after_restore = _snapshot(root, restore_paths)
    after = {rel: after_restore.get(rel) for rel in tracked}
    changed = _changed_files(before, after)
    blank_turns = [index + 1 for index, output in enumerate(outputs) if not output]
    trivial_hits = _memory_hits(root, TRIVIAL_MARKERS)
    owner_residue_visible = _owner_residue_visible(root)

    print("=== LONG LIVED SESSION HARNESS ===")
    print("turns:", len(turns))
    print("batch_size:", args.batch_size)
    print("restore_after:", args.restore_after)
    print("timed_out_turns:", ", ".join(map(str, timed_out_turns)) or "none")
    print("blank_turns:", ", ".join(map(str, blank_turns)) or "none")
    print("owner_residue_visible:", "yes" if owner_residue_visible else "no")
    print("trivial_hits:", "; ".join(trivial_hits[:8]) or "none")
    print("=== BATCH OUTPUT SUMMARY ===")
    for start in range(0, len(turns), max(1, args.batch_size)):
        end = min(start + max(1, args.batch_size), len(turns))
        print(f"--- batch {start + 1}-{end} ---")
        for index in range(start, end):
            print(f"{index + 1}. {_short(outputs[index])}")
    print("=== MUTATION SUMMARY ===")
    print(f"tracked_files: {len(tracked)}")
    print(f"changed_files: {len(changed)}")
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

    failures: list[str] = []
    if args.require_harness and len(turns) < 30:
        failures.append(f"turn count below long-lived minimum: {len(turns)} < 30")
    if timed_out_turns:
        failures.append("timed out turns: " + ", ".join(map(str, timed_out_turns)))
    if blank_turns:
        failures.append("blank output turns: " + ", ".join(map(str, blank_turns)))
    if args.require_harness and not owner_residue_visible:
        failures.append("owner relationship residue is not visible after long session")
    if trivial_hits:
        failures.append("trivial no-memory markers leaked: " + "; ".join(trivial_hits[:8]))

    if args.restore_after:
        _restore_snapshot(root, before_restore)
        print("=== RESTORE ===")
        print("tracked and volatile runtime files restored")

    if failures:
        print("=== FAILURES ===")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Long lived session harness passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
