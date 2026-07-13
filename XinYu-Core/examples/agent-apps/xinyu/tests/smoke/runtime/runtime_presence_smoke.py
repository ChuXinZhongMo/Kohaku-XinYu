from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path

from xinyu_runtime_presence import (
    build_runtime_presence_prompt_block,
    record_bridge_heartbeat,
    record_codex_presence,
    record_turn_finished,
    record_turn_started,
    read_runtime_presence_summary,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-runtime-presence-") as tmp:
        root = Path(tmp)
        stable_self = root / "memory/self/core.md"
        bridge_state = root / "memory/context/runtime_bridge_state.md"
        _write(stable_self, "# Core\n\nstable self")
        _write(bridge_state, "# Runtime Bridge\n\nmust not change")
        stable_before = _read(stable_self)
        bridge_before = _read(bridge_state)

        heartbeat = record_bridge_heartbeat(
            root,
            reason="bridge_init",
            bridge_snapshot={
                "active_sessions": 0,
                "autonomous_maintenance": "idle",
                "qq_outbox": "idle",
            },
        )
        if not heartbeat.get("ok"):
            failures.append("bridge heartbeat returned failure")

        secret_text = (
            "please check Authorization: Bearer sk-testsecret000000 "
            "XINYU_API_KEY=abc123456789012345 at D:\\XinYu\\secret\\notes.md "
            "for user 123456789"
        )
        started = record_turn_started(
            root,
            payload={
                "platform": "qq",
                "message_type": "private",
                "user_id": "123456789",
                "metadata": {"is_owner_user": True},
            },
            text=secret_text,
            session_key="qq:private:123456789",
            active_sessions=1,
        )
        if not started.get("ok") or not started.get("turn_id"):
            failures.append("turn start did not return a turn id")

        block = build_runtime_presence_prompt_block(root, limit=360)
        if not block:
            failures.append("prompt block was empty after turn start")
        if len(block) > 360:
            failures.append("prompt block exceeded configured limit")
        for forbidden in ("sk-testsecret", "XINYU_API_KEY", "abc123456789012345", "D:\\XinYu", "123456789"):
            if forbidden in block:
                failures.append(f"prompt block leaked sensitive marker: {forbidden}")
        if "runtime facts only" not in block:
            failures.append("prompt block missing factual boundary note")
        summary = read_runtime_presence_summary(root)
        if summary.get("current_turn_state") != "running":
            failures.append("health-safe summary did not report running turn")
        if not summary.get("updated_at"):
            failures.append("health-safe summary lost runtime updated_at")
        for forbidden_key in ("current_user_preview", "last_user_preview", "last_reply_preview"):
            if forbidden_key in summary:
                failures.append(f"health-safe summary leaked prompt text field: {forbidden_key}")

        md_path = root / "memory/context/runtime_self_presence.md"
        md_text = _read(md_path)
        md_text = md_text.replace(
            "current_turn_started_at: " + str(started.get("observed_at")),
            "current_turn_started_at: 2000-01-01T00:00:00+00:00",
        )
        _write(md_path, md_text)
        stale_block = build_runtime_presence_prompt_block(root, limit=420)
        stale_summary = read_runtime_presence_summary(root)
        if "current_turn_state: stale_running" not in stale_block:
            failures.append("stale running turn was not marked in prompt block")
        if stale_summary.get("current_turn_state") != "stale_running":
            failures.append("stale running turn was not marked in health summary")

        finished = record_turn_finished(
            root,
            turn_id=str(started.get("turn_id", "")),
            reply="done, no Bearer abcdefghijklmnop in visible prompt",
            elapsed_ms=1842,
            status="ok",
            notes=["dialogue_working_memory_active"],
            memory_changed=False,
        )
        if not finished.get("ok"):
            failures.append("turn finish returned failure")

        codex = record_codex_presence(
            root,
            job_id="codex-qq-20260501T120000",
            status="running",
            request_path=r"D:\XinYu\Codex\Requests\codex-qq-20260501T120000.md",
            report_path=r"D:\XinYu\Codex\Outbox\codex-qq-20260501T120000-report.md",
            visible_window_title="Xinyu codex",
        )
        if not codex.get("ok"):
            failures.append("codex presence returned failure")
        codex_state = json.loads(_read(root / "runtime/codex_presence_state.json"))
        if codex_state.get("request_label") != "codex-qq-20260501T120000.md":
            failures.append("codex request label was not reduced to basename")
        if "\\" in codex_state.get("request_label", "") or ":\\\\" in json.dumps(codex_state):
            failures.append("codex presence state leaked a full local path")

        md = _read(root / "memory/context/runtime_self_presence.md")
        trace = _read(root / "runtime/self_presence_trace.jsonl")
        if "Runtime Self Presence" not in md:
            failures.append("runtime presence markdown shape is wrong")
        if "current_turn_state: finished" not in md:
            failures.append("turn finish did not update markdown state")
        if "last_turn_elapsed_ms: 1842" not in md:
            failures.append("last turn elapsed time missing")
        for forbidden in ("sk-testsecret", "XINYU_API_KEY", "abc123456789012345", "D:\\XinYu", "123456789"):
            if forbidden in md or forbidden in trace:
                failures.append(f"presence files leaked sensitive marker: {forbidden}")
        if _read(stable_self) != stable_before:
            failures.append("runtime presence wrote under memory/self")
        if _read(bridge_state) != bridge_before:
            failures.append("runtime presence rewrote runtime_bridge_state")

        _write(root / "runtime/codex_presence_state.json", "{not-json")
        malformed_block = build_runtime_presence_prompt_block(root, limit=220)
        if len(malformed_block) > 220:
            failures.append("prompt block exceeded limit with malformed codex json")

    source_root = ROOT
    core_text = _read(source_root / "xinyu_core_bridge.py")
    context_text = _read(source_root / "xinyu_runtime_context.py")
    required_core_markers = (
        "record_bridge_heartbeat(",
        "record_turn_started(",
        "build_runtime_presence_prompt_block",
        "runtime presence sidecar:",
        "record_turn_finished(",
        "record_codex_presence(",
    )
    for marker in required_core_markers:
        if marker not in core_text:
            failures.append(f"xinyu_core_bridge.py missing runtime presence marker: {marker}")
    if "memory/context/runtime_self_presence.md" not in context_text:
        failures.append("renderer context does not include runtime_self_presence.md")

    if failures:
        print("Runtime presence smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Runtime presence smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
