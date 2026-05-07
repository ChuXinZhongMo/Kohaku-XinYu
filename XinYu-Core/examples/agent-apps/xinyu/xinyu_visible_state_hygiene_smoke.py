from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_visible_state_hygiene import sanitize_visible_state_files, visible_state_marker_hits


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-visible-state-") as tmp:
        root = Path(tmp)
        _write(
            root / "memory/reflection/reflection_queue.md",
            """# Reflection Queue

## item-2026-05-06-001
- topic: action residue after local action pressure after log_scan:minecraft_server
- waking_residue: log_scan:minecraft_server ended as failure; pressure=medium
""",
        )
        _write(
            root / "memory/context/proactive_request_state.md",
            "- evidence_label: reflection queue strong topic: action residue after local action pressure after codex_delegate:none\n",
        )
        _write(
            root / "memory/dreams/dream_output_trace.log",
            "2026-05-06 runtime_dream_output theme=local action pressure after codex_delegate:none\n",
        )
        _write(
            root / "runtime/dialogue_working_memory/session.jsonl",
            '{"role":"assistant","content":"local action pressure after codex_delegate:none codex_delegate:n","recorded_at":"2026-05-06T00:00:00+08:00"}\n',
        )
        _write(
            root / "runtime/gateway_ack_spool.jsonl",
            '{"event":"pending","key":"a|b|c","payload":{"visible_text":"local action pressure after codex_delegate:none","message":"codex_delegate:n"}}\n',
        )
        _write(
            root / "runtime/sent_reply_index.json",
            '{"version":1,"entries":[{"visible_text_preview":"local action pressure after codex_delegate:none codex_delegate:n"}]}\n',
        )
        _write(
            root / "memory/context/continuity_index.md",
            "- owner 留下了一次有轻微留痕意义的互动：[Tool batch completed] ## read_9601cfa6 - OK 1→-\n",
        )
        _write(
            root / "memory/context/proactive_presence_state.md",
            "- candidate_message: 有个梦醒来还留着：[Tool batch completed] ## read_9601cfa6 - OK 1→-\n",
        )
        result = sanitize_visible_state_files(root)
        if int(result.get("changed_count") or 0) != 8:
            failures.append(f"expected eight files to be sanitized: {result}")
        hits = visible_state_marker_hits(root)
        if hits:
            failures.append(f"visible state hygiene left marker hits: {hits}")
        reflection = _read(root / "memory/reflection/reflection_queue.md")
        proactive = _read(root / "memory/context/proactive_request_state.md")
        if "minecraft_server 日志扫描" not in reflection or "执行失败" not in reflection or "中负载" not in reflection:
            failures.append("reflection state did not get readable action wording")
        if "反思队列" not in proactive or "Codex 委派" not in proactive:
            failures.append("proactive state did not get readable reflection wording")

    if failures:
        print("XinYu visible state hygiene smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu visible state hygiene smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
