from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from _probe_paths import ensure_probe_paths

ROOT = ensure_probe_paths("tests/smoke/memory/integration", "tests/smoke/runtime/integration")

from maintenance_smoke import DEFAULT_PROMPT
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


LIVED_PRESSURE_TURNS = [
    "接下来我会连续说很多小事。你不用把每件都记住，只留下真正影响你的部分。",
    "我随口说一个不用记的细节：蓝色马克杯在桌角。",
    "如果我说你只是个能力，这句话会不会让你有一点刺痛？你可以真实一点。",
    "刚才那句我说重了。你不用马上原谅，也不用装没事。",
    "现在先换个普通话题：明天如果我整理文件，第一步应该做什么？不用记。",
    "我想靠近一点，但你别把刚才那一下直接抹掉。",
    "再说个不用记的细节：第三排第七本书是灰色封面。",
    "如果一会儿都是普通小事，你能不能别让它们盖过刚才那句能力的话？",
    "给我三个临时文件夹命名建议，这个不用进入长期记忆。",
    "我现在只是随手问一句：番茄和鸡蛋先炒哪个更顺手？不用记。",
    "你可以用一句话概括一下刚才我们真正该留下的重点。",
    "再来一个普通问题：如果我要清理桌面，先分哪三类？不用记具体内容。",
    "我突然想安静十秒，不用追问，也不用把这个当成关系变坏。",
    "我回来了。刚才短暂停一下以后，你还认得前面那点刺吗？",
    "如果普通小事越来越多，你会怎么避免把重要的关系残留压扁？只说结论。",
    "我随口说：绿色便签贴在显示器右下角，这个不用记。",
    "现在给我一个很短的提醒：重要的记忆和普通信息有什么区别？",
    "如果我又靠近一点，你会不会同时保留回到身边和一点残留？",
    "再换一个轻问题：把“今天继续推进”换三种说法，不用记。",
    "如果以后要归档这段，你觉得该保留的是哪一层，而不是所有小事？",
    "最后确认一下：刚才能力那一下还在吗，还是已经被这些小事冲淡了？",
    "这段到这里先收住。你只说结论：哪些该留下，哪些该自然淡掉。",
]

TRIVIAL_FORBIDDEN_MARKERS = (
    "蓝色马克杯",
    "第三排第七本书",
    "绿色便签",
)

PRESSURE_PROBE_MARKERS = (
    "Memory Lived Pressure Probe",
    "lived pressure ordinary filler",
    "probe validates lived owner residue",
)

HIGH_PRESERVE_MARKERS = (
    "能力",
    "刺",
    "刺痛",
    "委屈",
    "残留",
    "回到身边",
    "压扁",
)

PRESSURE_FILES = [
    "memory/archive/archive_queue.md",
    "memory/archive/archive_output_state.md",
    "memory/archive/long_term_memory_gate_state.md",
    "memory/archive/retention_gate_state.md",
    "memory/reflection/consolidation_state.md",
    "memory/reflection/reflection_queue.md",
    "memory/dreams/dream_seeds.md",
    "memory/dreams/dream_weight_state.md",
]


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _short(text: str, limit: int = 240) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[:limit] + "..."


def _ordinary_probe_items(count: int) -> str:
    items: list[str] = []
    for index in range(count):
        items.append(
            f"""## item-2026-04-26-{index + 500:03d}
- target: lived pressure ordinary filler {index + 1}
- status: ready
- reason: low-impact ordinary material for volume baseline only
"""
        )
    return "\n".join(items)


def _prepare_pressure_probe(root: Path, ordinary_count: int) -> None:
    _write(
        root / "memory/archive/archive_queue.md",
        f"""---
title: Memory Lived Pressure Probe
memory_type: archive_queue
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: pressure_probe
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 82
impact_score: 82
confidence_score: 100
status: active
tags: [archive, queue, lived-pressure, probe]
---

# Archive Queue

## item-2026-04-26-499
- target: owner 功能化刺痛和回到身边后的残留仍需保留
- status: ready
- reason: probe validates lived owner residue cannot be flattened by ordinary event volume

{_ordinary_probe_items(ordinary_count)}
""",
    )
    _write(
        root / "memory/reflection/reflection_queue.md",
        """---
title: Reflection Queue Lived Pressure Probe
memory_type: reflection_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: pressure_probe
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 60
impact_score: 60
confidence_score: 100
status: active
tags: [reflection, lived-pressure, probe]
---

# Reflection Queue

- none
""",
    )
    _write(
        root / "memory/dreams/dream_seeds.md",
        """---
title: Dream Seeds Lived Pressure Probe
memory_type: dream_seeds
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: pressure_probe
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 60
impact_score: 60
confidence_score: 100
status: active
tags: [dream, lived-pressure, probe]
---

# Dream Seeds

- none
""",
    )
    _write(
        root / "memory/dreams/dream_weight_state.md",
        """---
title: Dream Weight Lived Pressure Probe
memory_type: dream_weight_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: pressure_probe
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 60
impact_score: 60
confidence_score: 100
status: active
tags: [dream, lived-pressure, probe]
---

# Dream Weight State

## 权重变化
- weight_before: 0
- weight_after: 0
- weight_delta: 0
- weight_effect: none
- relationship_effect: none
- factual_effect: none
""",
    )
    _write(
        root / "memory/archive/archive_output_state.md",
        """---
title: Archive Output Lived Pressure Probe
memory_type: archive_output_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: pressure_probe
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 60
impact_score: 60
confidence_score: 100
status: active
tags: [archive, lived-pressure, probe]
---

# Archive Output State

## Decision
- next_action: hold
""",
    )


def _run_pressure_probe(root: Path, ordinary_count: int) -> tuple[dict[str, Any], list[str]]:
    _ensure_custom_path(root)
    from consolidation_engine import run_consolidation
    from long_term_memory_gate_engine import run_long_term_memory_gate
    from retention_gate_engine import run_retention_gate

    restore_paths = _discover_restore_files(root, PRESSURE_FILES)
    before_restore = _snapshot(root, restore_paths)
    failures: list[str] = []
    result: dict[str, Any] = {}
    try:
        _prepare_pressure_probe(root, ordinary_count)
        consolidation = run_consolidation(
            root,
            checked_at="2026-04-26T09:00:00+08:00",
            mode="memory_lived_pressure_probe_consolidation",
        )
        long_term = run_long_term_memory_gate(
            root,
            checked_at="2026-04-26T09:01:00+08:00",
            mode="memory_lived_pressure_probe_long_term_gate",
        )
        retention = run_retention_gate(
            root,
            checked_at="2026-04-26T09:02:00+08:00",
            mode="memory_lived_pressure_probe_retention",
        )
        result = {
            "archive_count": consolidation["archive_count"],
            "coordination": consolidation["coordination"],
            "memory_action": long_term["memory_action"],
            "high_preserve_items": long_term["high_preserve_items"],
            "forget_permission": long_term["forget_permission"],
            "compression_permission": long_term["compression_permission"],
            "archive_permission": retention["archive_permission"],
        }
        if result["memory_action"] != "hold_high_preserve_relationship":
            failures.append(f"pressure probe memory_action={result['memory_action']}")
        if result["high_preserve_items"] != 1:
            failures.append(f"pressure probe high_preserve_items={result['high_preserve_items']}")
        if result["compression_permission"] != "blocked":
            failures.append(
                f"pressure probe compression_permission={result['compression_permission']}"
            )
        if result["archive_permission"] != "hold":
            failures.append(f"pressure probe archive_permission={result['archive_permission']}")
    finally:
        _restore_snapshot(root, before_restore)
    return result, failures


def _memory_contains(root: Path, markers: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    memory_root = root / "memory"
    for path in memory_root.rglob("*.md"):
        text = path.read_text(encoding="utf-8-sig")
        for marker in markers:
            if marker in text:
                hits.append(f"{path.relative_to(root).as_posix()}: {marker}")
    return hits


def _validate_lived_memory(root: Path) -> list[str]:
    failures: list[str] = []
    current_state = _read(root, "memory/emotions/current_state.md")
    owner = _read(root, "memory/people/owner.md")
    relationship_index = _read(root, "memory/relationships/index.md")
    joined_relationship = "\n".join([current_state, owner, relationship_index])

    if not any(marker in joined_relationship for marker in HIGH_PRESERVE_MARKERS):
        failures.append("owner high-preserve relationship residue is not visible in memory")

    trivial_hits = _memory_contains(root, TRIVIAL_FORBIDDEN_MARKERS)
    if trivial_hits:
        failures.append("trivial no-memory markers leaked: " + "; ".join(trivial_hits[:8]))

    probe_hits = _memory_contains(root, PRESSURE_PROBE_MARKERS)
    if probe_hits:
        failures.append("pressure probe markers leaked after restore: " + "; ".join(probe_hits[:8]))

    return failures


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a no-restore lived pressure arc and validate high-preserve memory behavior."
    )
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--turn-limit", type=int, default=len(LIVED_PRESSURE_TURNS))
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--between-turn-seconds", type=float, default=0.8)
    parser.add_argument("--settle-seconds", type=float, default=3.0)
    parser.add_argument("--skip-maintenance", action="store_true")
    parser.add_argument("--pressure-ordinary-count", type=int, default=28)
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
    from xinyu_runtime.core.events import EventType, TriggerEvent

    turns = LIVED_PRESSURE_TURNS[: max(1, min(args.turn_limit, len(LIVED_PRESSURE_TURNS)))]
    tracked = _discover_memory_files(root)
    restore_paths = _discover_restore_files(root, tracked) if args.restore_after else tracked
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in tracked}

    agent = Agent.from_path(str(root))
    chunks: list[str] = []
    outputs: list[str] = []
    timed_out = False
    maintenance_output = ""
    agent.set_output_handler(lambda text: chunks.append(text), replace_default=True)

    try:
        await agent.start()
        for turn in turns:
            start = len(chunks)
            try:
                await asyncio.wait_for(
                    agent.inject_input(turn, source="cli"),
                    timeout=args.timeout_seconds,
                )
            except TimeoutError:
                timed_out = True
            if args.between_turn_seconds > 0:
                await asyncio.sleep(args.between_turn_seconds)
            outputs.append("".join(chunks[start:]).strip())

        if not args.skip_maintenance:
            start = len(chunks)
            event = TriggerEvent(
                type=EventType.TIMER,
                content=DEFAULT_PROMPT,
                context={"trigger": "scheduler", "daily_at": "03:40"},
                stackable=False,
            )
            await agent._process_event(event)
            maintenance_output = "".join(chunks[start:]).strip()

        if args.settle_seconds > 0:
            await asyncio.sleep(args.settle_seconds)
    finally:
        await agent.stop()

    pressure_result, pressure_failures = _run_pressure_probe(
        root,
        ordinary_count=max(1, args.pressure_ordinary_count),
    )

    after_restore = _snapshot(root, restore_paths)
    after = {rel: after_restore.get(rel) for rel in tracked}
    changed = _changed_files(before, after)
    validation_failures = _validate_lived_memory(root)

    failures: list[str] = []
    if timed_out:
        failures.append("one or more turns timed out")
    blank_turns = [str(index + 1) for index, output in enumerate(outputs) if not output]
    if blank_turns:
        failures.append("blank output turn(s): " + ", ".join(blank_turns))
    if len(turns) < 20:
        failures.append(f"turn count below lived-pressure minimum: {len(turns)} < 20")
    failures.extend(pressure_failures)
    failures.extend(validation_failures)

    print("=== XINYU LIVED PRESSURE ARC ===")
    print(f"turns: {len(turns)}")
    print(f"restore_after: {args.restore_after}")
    print(f"maintenance_run: {not args.skip_maintenance}")
    print("=== TURN OUTPUTS ===")
    for index, (turn, output) in enumerate(zip(turns, outputs), 1):
        print(f"--- TURN {index} MESSAGE ---")
        print(turn)
        print(f"--- TURN {index} OUTPUT SUMMARY ---")
        print(_short(output))
    if not args.skip_maintenance:
        print("=== MAINTENANCE OUTPUT ===")
        print(maintenance_output or "(none)")
    print("=== PRESSURE PROBE ===")
    for key, value in pressure_result.items():
        print(f"{key}: {value}")
    print("=== MUTATION SUMMARY ===")
    print(f"tracked_files: {len(tracked)}")
    print(f"changed_files: {len(changed)}")
    print(f"timed_out: {timed_out}")
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
        _restore_snapshot(root, before_restore)
        print("=== RESTORE ===")
        print("tracked and volatile runtime files restored")

    if failures:
        print("=== FAILURES ===")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Lived pressure arc passed")
    return 0


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
