from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

import xinyu_bridge_autonomous_maintenance


def test_create_autonomous_maintenance_event_loads_runtime_and_builds_timer_event() -> None:
    calls: list[str] = []

    class _Event:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    runtime = SimpleNamespace(
        _load_runtime=lambda: calls.append("load"),
        _trigger_event_cls=_Event,
        autonomous_maintenance_session_key="xinyu:auto",
    )

    event = xinyu_bridge_autonomous_maintenance.create_autonomous_maintenance_event(
        runtime,
        prompt="prompt",
    )

    assert calls == ["load"]
    assert event.kwargs["type"] == "timer"
    assert event.kwargs["content"] == "prompt"
    assert event.kwargs["stackable"] is False
    assert event.kwargs["context"]["trigger"] == "scheduler"
    assert event.kwargs["context"]["session_id"] == "xinyu:auto"
    assert event.kwargs["context"]["autonomous"] is True
    assert event.kwargs["context"]["time"]


def test_create_autonomous_maintenance_event_uses_default_prompt() -> None:
    class _Event:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    runtime = SimpleNamespace(
        _load_runtime=lambda: None,
        _trigger_event_cls=_Event,
        autonomous_maintenance_session_key="xinyu:auto",
    )

    event = xinyu_bridge_autonomous_maintenance.create_autonomous_maintenance_event(runtime)

    assert event.kwargs["content"] == xinyu_bridge_autonomous_maintenance.AUTONOMOUS_MAINTENANCE_PROMPT


def test_create_autonomous_maintenance_event_errors_when_trigger_class_missing() -> None:
    runtime = SimpleNamespace(_load_runtime=lambda: None, _trigger_event_cls=None)

    with pytest.raises(RuntimeError, match="TriggerEvent class is unavailable"):
        xinyu_bridge_autonomous_maintenance.create_autonomous_maintenance_event(runtime, prompt="prompt")


def test_record_autonomous_failure_updates_runtime_and_writes_state() -> None:
    calls: list[tuple[str, str]] = []
    runtime = SimpleNamespace(
        _autonomous_failure_count=2,
        _autonomous_last_error="",
        _trace_autonomous=lambda message: calls.append(("trace", message)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
    )

    xinyu_bridge_autonomous_maintenance.record_autonomous_failure(runtime, "boom")

    assert runtime._autonomous_failure_count == 3
    assert runtime._autonomous_last_error == "boom"
    assert calls == [("trace", "boom"), ("state", "error")]


def test_ensure_autonomous_session_cleans_and_marks_ready(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Lock:
        async def __aenter__(self):
            calls.append(("lock", "enter"))

        async def __aexit__(self, exc_type, exc, tb):
            calls.append(("lock", "exit"))

    session = SimpleNamespace(key="auto", last_used_at=0.0)

    async def cleanup(*, preserve_keys):
        calls.append(("cleanup", preserve_keys))
        return {"cleaned_sessions": 1}

    async def get_session(key: str):
        calls.append(("get_session", key))
        return session

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance.time, "time", lambda: 123.5)
    runtime = SimpleNamespace(
        _global_turn_lock=_Lock(),
        autonomous_maintenance_session_key="auto",
        _cleanup_idle_sessions=cleanup,
        _get_session=get_session,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
    )

    result = asyncio.run(xinyu_bridge_autonomous_maintenance.ensure_autonomous_session(runtime))

    assert result is session
    assert session.last_used_at == 123.5
    assert calls == [
        ("lock", "enter"),
        ("cleanup", {"auto"}),
        ("get_session", "auto"),
        ("trace", "session ready key=auto"),
        ("state", "session_ready"),
        ("lock", "exit"),
    ]


def test_autonomous_maintenance_loop_runs_once_and_sleeps(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    async def ensure_session() -> None:
        calls.append(("ensure", "session"))

    async def run_once() -> dict[str, object]:
        calls.append(("run", "once"))
        runtime._closed = True
        return {"accepted": True}

    async def fake_sleep(seconds: float) -> None:
        calls.append(("sleep", seconds))

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance.time, "time", lambda: 100.0)
    runtime = SimpleNamespace(
        _closed=False,
        autonomous_maintenance_enabled=True,
        autonomous_maintenance_initial_delay_seconds=0,
        autonomous_maintenance_interval_seconds=30,
        _autonomous_next_run_at="",
        _autonomous_in_progress=True,
        _ensure_autonomous_session=ensure_session,
        _run_autonomous_maintenance_once=run_once,
        _record_autonomous_failure=lambda message: calls.append(("failure", message)),
        _iso_from_timestamp=lambda value: f"iso:{value}",
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _trace_autonomous=lambda line: calls.append(("trace", line)),
    )

    asyncio.run(xinyu_bridge_autonomous_maintenance.autonomous_maintenance_loop(runtime))

    assert calls == [
        ("ensure", "session"),
        ("run", "once"),
        ("state", "sleeping"),
        ("sleep", 30),
        ("state", "closed"),
    ]
    assert runtime._autonomous_next_run_at == "iso:130.0"
    assert runtime._autonomous_in_progress is False


def test_autonomous_maintenance_loop_records_startup_and_run_errors(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    async def ensure_session() -> None:
        raise RuntimeError("session boom")

    async def run_once() -> dict[str, object]:
        runtime._closed = True
        raise ValueError("run boom")

    async def fake_sleep(seconds: float) -> None:
        calls.append(("sleep", seconds))

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance.asyncio, "sleep", fake_sleep)
    runtime = SimpleNamespace(
        _closed=False,
        autonomous_maintenance_enabled=True,
        autonomous_maintenance_initial_delay_seconds=0,
        autonomous_maintenance_interval_seconds=10,
        _autonomous_next_run_at="",
        _autonomous_in_progress=True,
        _ensure_autonomous_session=ensure_session,
        _run_autonomous_maintenance_once=run_once,
        _record_autonomous_failure=lambda message: calls.append(("failure", message)),
        _iso_from_timestamp=lambda value: "iso",
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _trace_autonomous=lambda line: calls.append(("trace", line)),
    )

    asyncio.run(xinyu_bridge_autonomous_maintenance.autonomous_maintenance_loop(runtime))

    assert calls[0] == ("failure", "startup_session_error:RuntimeError('session boom')")
    assert calls[1] == ("failure", "run_error:ValueError('run boom')")
    assert ("state", "closed") in calls
    assert runtime._autonomous_in_progress is False


def test_autonomous_maintenance_loop_records_cancelled_state() -> None:
    calls: list[tuple[str, object]] = []

    async def ensure_session() -> None:
        calls.append(("ensure", "session"))

    async def run_once() -> dict[str, object]:
        raise asyncio.CancelledError()

    runtime = SimpleNamespace(
        _closed=False,
        autonomous_maintenance_enabled=True,
        autonomous_maintenance_initial_delay_seconds=0,
        autonomous_maintenance_interval_seconds=10,
        _autonomous_in_progress=True,
        _ensure_autonomous_session=ensure_session,
        _run_autonomous_maintenance_once=run_once,
        _record_autonomous_failure=lambda message: calls.append(("failure", message)),
        _iso_from_timestamp=lambda value: "iso",
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _trace_autonomous=lambda line: calls.append(("trace", line)),
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(xinyu_bridge_autonomous_maintenance.autonomous_maintenance_loop(runtime))

    assert calls == [
        ("ensure", "session"),
        ("trace", "background task cancelled"),
        ("state", "cancelled"),
    ]
    assert runtime._autonomous_in_progress is False


def test_run_autonomous_maintenance_once_returns_disabled_when_closed() -> None:
    runtime = SimpleNamespace(_closed=True, autonomous_maintenance_enabled=True)

    result = asyncio.run(xinyu_bridge_autonomous_maintenance.run_autonomous_maintenance_once(runtime))

    assert result == {"accepted": False, "notes": ["disabled_or_closed"]}


def test_run_autonomous_maintenance_once_runs_event_and_records_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_HEAVY_MAINTENANCE_SUBPROCESS", "0")
    calls: list[tuple[str, object]] = []

    class _Lock:
        async def __aenter__(self) -> None:
            calls.append(("lock", "enter"))

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls.append(("lock", "exit"))

    class _Agent:
        async def inject_event(self, event: object) -> None:
            calls.append(("inject", event))
            session.chunks.extend(["  hello\n", "world  "])

        def interrupt(self) -> None:
            calls.append(("interrupt", "called"))

    async def cleanup(*, preserve_keys: set[str]) -> dict[str, int]:
        calls.append(("cleanup", preserve_keys))
        return {"cleaned_sessions": 2}

    async def get_session(key: str):
        calls.append(("get_session", key))
        return session

    snapshots = iter(["before", "after"])
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "memory_snapshot", lambda root: next(snapshots))
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance.time, "time", lambda: 123.0)
    session = SimpleNamespace(agent=_Agent(), chunks=["stale"], last_used_at=0.0, key="auto")
    runtime = SimpleNamespace(
        _closed=False,
        autonomous_maintenance_enabled=True,
        _global_turn_lock=_Lock(),
        autonomous_maintenance_session_key="auto",
        _cleanup_idle_sessions=cleanup,
        _get_session=get_session,
        memory_root=tmp_path,
        _create_autonomous_maintenance_event=lambda: "event",
        _autonomous_in_progress=False,
        _autonomous_last_started_at="",
        _autonomous_last_error="old",
        _autonomous_run_count=4,
        _autonomous_last_success_at="",
        _sessions={"auto": session, "other": object()},
        turn_timeout_seconds=5,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status, **kwargs: calls.append(("state", (status, kwargs))),
        _run_autonomous_self_thought_sidecars=lambda *, checked_at: ["sidecar_note"],
    )

    result = asyncio.run(xinyu_bridge_autonomous_maintenance.run_autonomous_maintenance_once(runtime))

    assert result["accepted"] is True
    assert result["memory_changed"] is True
    assert result["reply_preview"] == "hello world"
    assert result["sessions"] == 2
    assert result["notes"] == [
        "autonomous_maintenance_turn",
        "no_visible_reply",
        "heavy_maintenance:disabled",
        "sidecar_note",
        "cleaned_idle_sessions:2",
    ]
    assert session.last_used_at == 123.0
    assert runtime._autonomous_run_count == 5
    assert runtime._autonomous_last_error == ""
    assert runtime._autonomous_in_progress is False
    assert calls[0] == ("trace", "heavy_maintenance disabled")
    assert calls[1:7] == [
        ("lock", "enter"),
        ("cleanup", {"auto"}),
        ("get_session", "auto"),
        ("trace", "run started"),
        ("state", ("running", {})),
        ("inject", "event"),
    ]
    assert calls[-2][0] == "state"
    assert calls[-2][1][0] == "last_run_ok"
    assert calls[-1] == ("lock", "exit")


def test_run_autonomous_maintenance_once_interrupts_agent_on_timeout(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_HEAVY_MAINTENANCE_SUBPROCESS", "0")
    calls: list[str] = []

    class _Lock:
        async def __aenter__(self) -> None:
            calls.append("lock_enter")

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls.append("lock_exit")

    class _Agent:
        async def inject_event(self, event: object) -> None:
            calls.append("inject")

        def interrupt(self) -> None:
            calls.append("interrupt")

    async def fake_wait_for(coro, *, timeout: int) -> None:
        coro.close()
        calls.append(f"wait_for:{timeout}")
        raise TimeoutError()

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance.asyncio, "wait_for", fake_wait_for)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "memory_snapshot", lambda root: "before")
    runtime = SimpleNamespace(
        _closed=False,
        autonomous_maintenance_enabled=True,
        _global_turn_lock=_Lock(),
        autonomous_maintenance_session_key="auto",
        _cleanup_idle_sessions=lambda **kwargs: {"cleaned_sessions": 0},
        _get_session=lambda key: SimpleNamespace(agent=_Agent(), chunks=[], last_used_at=0.0),
        memory_root=tmp_path,
        _create_autonomous_maintenance_event=lambda: "event",
        _autonomous_in_progress=False,
        _autonomous_last_started_at="",
        _autonomous_last_error="",
        turn_timeout_seconds=7,
        _trace_autonomous=lambda line: calls.append(f"trace:{line}"),
        _write_autonomous_state=lambda status, **kwargs: calls.append(f"state:{status}"),
    )

    async def cleanup(*, preserve_keys):
        return {"cleaned_sessions": 0}

    async def get_session(key):
        return SimpleNamespace(agent=_Agent(), chunks=[], last_used_at=0.0)

    runtime._cleanup_idle_sessions = cleanup
    runtime._get_session = get_session

    with pytest.raises(TimeoutError):
        asyncio.run(xinyu_bridge_autonomous_maintenance.run_autonomous_maintenance_once(runtime))

    assert calls == [
        "trace:heavy_maintenance disabled",
        "lock_enter",
        "trace:run started",
        "state:running",
        "wait_for:7",
        "interrupt",
        "lock_exit",
    ]
    assert runtime._autonomous_in_progress is False


def test_trace_autonomous_appends_trace_line(tmp_path) -> None:
    runtime = SimpleNamespace(memory_root=tmp_path)

    xinyu_bridge_autonomous_maintenance.trace_autonomous(runtime, "hello")

    trace = (tmp_path / "context/autonomous_mind_loop_trace.log").read_text(encoding="utf-8")
    assert "hello" in trace


def test_write_autonomous_state_updates_runtime_state_file(tmp_path) -> None:
    runtime = SimpleNamespace(
        memory_root=tmp_path,
        autonomous_maintenance_enabled=True,
        autonomous_maintenance_session_key="xinyu:auto",
        autonomous_maintenance_initial_delay_seconds=1,
        autonomous_maintenance_interval_seconds=30,
        _autonomous_in_progress=False,
        _autonomous_next_run_at="2026-06-06T01:00:00+08:00",
        _autonomous_run_count=4,
        _autonomous_failure_count=1,
        _autonomous_last_started_at="2026-06-06T00:00:00+08:00",
        _autonomous_last_success_at="2026-06-06T00:01:00+08:00",
        _autonomous_last_memory_changed="false",
        _autonomous_last_error="",
        _autonomous_last_notes=[],
    )

    xinyu_bridge_autonomous_maintenance.write_autonomous_state(
        runtime,
        "running",
        memory_changed=True,
        notes=["note-a", "note-b"],
    )

    state = (tmp_path / "context/autonomous_mind_loop_state.md").read_text(encoding="utf-8")
    assert runtime._autonomous_last_notes == ["note-a", "note-b"]
    assert runtime._autonomous_last_memory_changed == "true"
    assert "- status: running" in state
    assert "- enabled: true" in state
    assert "- session_key: xinyu:auto" in state
    assert "- memory_changed: true" in state
    assert "- note-a" in state
    assert "- note-b" in state


def test_append_watched_source_and_goal_ecology_notes_append_summaries(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_watched(root, **kwargs):
        calls.append(("watched", {"root": root, **kwargs}))
        return {"status": "checked", "fetched_items": 4, "new_items": 2}

    def fake_goal(root, **kwargs):
        calls.append(("goal", {"root": root, **kwargs}))
        return {"selected_goal_id": "goal-1", "selected_score": "0.77"}

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_watched_source_check", fake_watched)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_self_chosen_goal_ecology", fake_goal)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=120,
        _trace_autonomous=lambda line: None,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_watched_source_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_goal_ecology_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "watched_source:checked/4/2",
        "goal_ecology:goal-1/0.77",
    ]
    assert calls == [
        (
            "watched",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "min_interval_seconds": 120,
            },
        ),
        (
            "goal",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "trigger": "autonomous_maintenance",
            },
        ),
    ]


def test_append_watched_source_note_skips_no_sources(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        xinyu_bridge_autonomous_maintenance,
        "run_watched_source_check",
        lambda *args, **kwargs: {"status": "no_sources", "fetched_items": 0, "new_items": 0},
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=120,
        _trace_autonomous=lambda line: None,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_watched_source_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == []


def test_append_watched_source_and_goal_ecology_notes_record_errors(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_watched_source_check", fail)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_self_chosen_goal_ecology", fail)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=120,
        _trace_autonomous=traces.append,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_watched_source_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_goal_ecology_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "watched_source_error:RuntimeError",
        "goal_ecology_error:RuntimeError",
    ]
    assert len(traces) == 2
    assert traces[0].startswith("watched_source_error=RuntimeError")
    assert traces[1].startswith("goal_ecology_error=RuntimeError")


def test_append_github_learning_and_self_exploration_notes_append_summaries(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_github(root, **kwargs):
        calls.append(("github", {"root": root, **kwargs}))
        return {"status": "staged", "candidates_found": 3, "staged_repos": 1}

    def fake_exploration(root, **kwargs):
        calls.append(("exploration", {"root": root, **kwargs}))
        return {
            "status": "prepared",
            "research_route": "source_search_provider",
            "research_execution_level": "proposal",
            "provider_results": 4,
        }

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance.sys, "path", [])
    monkeypatch.setitem(
        sys.modules,
        "github_autonomous_learning_engine",
        SimpleNamespace(run_github_autonomous_learning=fake_github),
    )
    monkeypatch.setattr(
        xinyu_bridge_autonomous_maintenance,
        "run_autonomous_self_exploration_tick",
        fake_exploration,
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=60,
        _trace_autonomous=lambda line: None,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_github_learning_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_self_exploration_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert xinyu_bridge_autonomous_maintenance.sys.path[0] == str(tmp_path / "custom")
    assert notes == [
        "github_learning:staged/3/1",
        "self_exploration:prepared/source_search_provider/proposal/4",
    ]
    assert calls == [
        (
            "github",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "mode": "autonomous_maintenance_github_learning",
                "max_stage": 1,
                "min_interval_seconds": 21600,
            },
        ),
        (
            "exploration",
            {
                "root": tmp_path,
                "evaluated_at": "2026-06-06T01:00:00+08:00",
                "allow_live_search": None,
                "allow_codex": None,
                "execute_low_risk": False,
            },
        ),
    ]


def test_append_github_learning_and_self_exploration_notes_record_errors(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance.sys, "path", [])
    monkeypatch.setitem(
        sys.modules,
        "github_autonomous_learning_engine",
        SimpleNamespace(run_github_autonomous_learning=fail),
    )
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_autonomous_self_exploration_tick", fail)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=3600,
        _trace_autonomous=traces.append,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_github_learning_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_self_exploration_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "github_learning_error:RuntimeError",
        "self_exploration_error:RuntimeError",
    ]
    assert len(traces) == 2
    assert traces[0].startswith("github_learning_error=RuntimeError")
    assert traces[1].startswith("self_exploration_error=RuntimeError")


def test_append_autonomous_intake_notes_append_summaries(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_digest(root, **kwargs):
        calls.append(("daily", {"root": root, **kwargs}))
        return {"status": "generated", "generated": True}

    def fake_creative(root, **kwargs):
        calls.append(("creative", {"root": root, **kwargs}))
        return {
            "status": "written",
            "today_chapters_written": 2,
            "daily_target_chapters": 3,
            "total_chapters": 9,
        }

    def fake_review(root, **kwargs):
        calls.append(("review", {"root": root, **kwargs}))
        return {"pending_count": 4, "queued": False}

    def fake_goldmark(root, **kwargs):
        calls.append(("goldmark", {"root": root, **kwargs}))
        return {"status": "ok", "processed": 5, "succeeded": 3, "skipped": 1, "failed": 1}

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_daily_digest_maintenance", fake_digest)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_creative_writing_maintenance", fake_creative)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_review_inbox_maintenance", fake_review)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_goldmark_dehydration_maintenance", fake_goldmark)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _owner_private_user_id=lambda: "owner-1",
        _trace_autonomous=lambda line: None,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_daily_digest_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_creative_writing_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_review_inbox_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_goldmark_dehydrate_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "daily_digest:generated/true",
        "creative_writing:written/2/3/9",
        "review_inbox:4/false",
        "goldmark_dehydrate:ok/5/3/1/1",
    ]
    assert calls == [
        ("daily", {"root": tmp_path, "observed_at": "2026-06-06T01:00:00+08:00"}),
        (
            "creative",
            {"root": tmp_path, "checked_at": "2026-06-06T01:00:00+08:00", "daily_target": 3},
        ),
        (
            "review",
            {
                "root": tmp_path,
                "owner_user_id": "owner-1",
                "max_items": 3,
                "enqueue": False,
                "reason": "autonomous_maintenance",
            },
        ),
        ("goldmark", {"root": tmp_path, "limit": 5, "provider": "auto", "timeout_seconds": 45}),
    ]


def test_append_autonomous_intake_notes_record_errors(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_daily_digest_maintenance", fail)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_creative_writing_maintenance", fail)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_review_inbox_maintenance", fail)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_goldmark_dehydration_maintenance", fail)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _owner_private_user_id=lambda: "owner-1",
        _trace_autonomous=traces.append,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_daily_digest_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_creative_writing_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_review_inbox_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_goldmark_dehydrate_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "daily_digest_error:RuntimeError",
        "creative_writing_error:RuntimeError",
        "review_inbox_error:RuntimeError",
        "goldmark_dehydrate_error:RuntimeError",
    ]
    assert len(traces) == 4
    assert traces[0].startswith("daily_digest_error=RuntimeError")
    assert traces[1].startswith("creative_writing_error=RuntimeError")
    assert traces[2].startswith("review_inbox_error=RuntimeError")
    assert traces[3].startswith("goldmark_dehydrate_error=RuntimeError")


def test_append_self_action_notes_append_summaries_and_enqueue_notes(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_gateway(root, **kwargs):
        calls.append(("gateway", {"root": root, **kwargs}))
        return {
            "status": "completed",
            "selected_goal_id": "goal-1",
            "executed_action_count": 2,
            "queued_approval_count": 1,
            "notes": ["gateway-note-1", "gateway-note-2", "gateway-note-3", "gateway-note-4"],
        }

    def fake_patch_executor(root, **kwargs):
        calls.append(("patch", {"root": root, **kwargs}))
        return {
            "status": "prepared",
            "task_id": "task-1",
            "codex": "not-a-dict",
            "notes": ["patch-note-1", "patch-note-2", "patch-note-3"],
        }

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_self_action_gateway", fake_gateway)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_self_action_patch_executor", fake_patch_executor)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _trace_autonomous=lambda line: None,
        _maybe_enqueue_self_action_approval_to_qq=lambda result, *, checked_at: [
            f"approval-enqueued:{result['selected_goal_id']}:{checked_at}"
        ],
        _maybe_enqueue_self_action_prepared_patch_to_qq=lambda result, *, checked_at: [
            f"patch-enqueued:{result['task_id']}:{checked_at}"
        ],
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_self_action_gateway_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_self_action_patch_executor_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "self_action_gateway:completed/goal-1/2/1",
        "gateway-note-1",
        "gateway-note-2",
        "gateway-note-3",
        "approval-enqueued:goal-1:2026-06-06T01:00:00+08:00",
        "self_action_patch_executor:prepared/task-1/none",
        "patch-note-1",
        "patch-note-2",
        "patch-enqueued:task-1:2026-06-06T01:00:00+08:00",
    ]
    assert calls == [
        (
            "gateway",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "trigger": "autonomous_maintenance",
            },
        ),
        (
            "patch",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "execution_level": "prepare",
                "allow_codex": False,
            },
        ),
    ]


def test_append_self_action_notes_record_errors(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_self_action_gateway", fail)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_self_action_patch_executor", fail)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _trace_autonomous=traces.append,
        _maybe_enqueue_self_action_approval_to_qq=lambda result, *, checked_at: ["unexpected"],
        _maybe_enqueue_self_action_prepared_patch_to_qq=lambda result, *, checked_at: ["unexpected"],
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_self_action_gateway_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_self_action_patch_executor_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "self_action_gateway_error:RuntimeError",
        "self_action_patch_executor_error:RuntimeError",
    ]
    assert len(traces) == 2
    assert traces[0].startswith("self_action_gateway_error=RuntimeError")
    assert traces[1].startswith("self_action_patch_executor_error=RuntimeError")


def test_append_self_thought_and_proactive_request_notes_return_results(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_self_thought(root, **kwargs):
        calls.append(("thought", {"root": root, **kwargs}))
        return {
            "status": "candidate",
            "outcome": "request_candidate",
            "focus_kind": "dream_residue",
            "intention": "share_dream",
            "candidate_enabled": True,
        }

    def fake_request(root, **kwargs):
        calls.append(("request", {"root": root, **kwargs}))
        return {
            "status": "ready",
            "kind": "dream_share",
            "delivery_level": "queue_owner_private",
        }

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_self_thought_loop", fake_self_thought)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_proactive_request_loop", fake_request)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=90,
        _trace_autonomous=lambda line: None,
    )
    notes: list[str] = []

    thought = xinyu_bridge_autonomous_maintenance.append_self_thought_loop_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    request = xinyu_bridge_autonomous_maintenance.append_proactive_request_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert thought and thought["candidate_enabled"] is True
    assert request["status"] == "ready"
    assert notes == [
        "self_thought:candidate/request_candidate/dream_residue/share_dream",
        "proactive_request:ready/dream_share/queue_owner_private",
    ]
    assert calls == [
        (
            "thought",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "trigger": "autonomous_maintenance",
                "min_interval_seconds": 90,
            },
        ),
        (
            "request",
            {
                "root": tmp_path,
                "evaluated_at": "2026-06-06T01:00:00+08:00",
                "delivery_level": "queue_owner_private",
            },
        ),
    ]


def test_append_self_thought_and_proactive_request_notes_record_errors(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_self_thought_loop", fail)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_proactive_request_loop", fail)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=90,
        _trace_autonomous=traces.append,
    )
    notes: list[str] = []

    thought = xinyu_bridge_autonomous_maintenance.append_self_thought_loop_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    request = xinyu_bridge_autonomous_maintenance.append_proactive_request_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert thought is None
    assert request == {}
    assert notes == [
        "self_thought_error:RuntimeError",
        "proactive_request_error:RuntimeError",
    ]
    assert len(traces) == 2
    assert traces[0].startswith("self_thought_error=RuntimeError")
    assert traces[1].startswith("proactive_request_error=RuntimeError")


def test_run_autonomous_self_thought_sidecars_runs_candidate_branch_in_order() -> None:
    calls: list[tuple[str, object]] = []

    def append(name: str, note: str):
        def inner(notes: list[str], *, checked_at: str) -> None:
            calls.append((name, checked_at))
            notes.append(note)

        return inner

    def append_thought(notes: list[str], *, checked_at: str) -> dict[str, object]:
        calls.append(("thought", checked_at))
        notes.append("self_thought:candidate")
        return {"candidate_enabled": True}

    def append_request(notes: list[str], *, checked_at: str) -> dict[str, object]:
        calls.append(("request", checked_at))
        notes.append("proactive_request:ready")
        return {"status": "ready", "notes": ["request-note"]}

    def append_outward(notes: list[str], *, checked_at: str, prepare_request: bool) -> dict[str, object]:
        calls.append(("outward", {"checked_at": checked_at, "prepare_request": prepare_request}))
        notes.append(f"autonomous_outward:{str(prepare_request).lower()}")
        return {"queued": False}

    def append_desktop(notes: list[str], *, request: dict[str, object], auto_outward: dict[str, object]) -> None:
        calls.append(("desktop", {"request": request, "auto_outward": auto_outward}))
        notes.append("desktop_ready")

    def append_closed_loop(
        notes: list[str],
        *,
        thought: dict[str, object],
        checked_at: str,
        request: dict[str, object] | None = None,
    ) -> None:
        calls.append(("closed_loop", {"checked_at": checked_at, "thought": thought, "request": request}))
        notes.append("closed_loop")

    runtime = SimpleNamespace(
        _append_watched_source_note=append("watched", "watched"),
        _append_github_learning_note=append("github", "github"),
        _append_daily_digest_note=append("digest", "digest"),
        _append_creative_writing_note=append("creative", "creative"),
        _append_review_inbox_note=append("review", "review"),
        _append_goldmark_dehydrate_note=append("goldmark", "goldmark"),
        _append_goal_ecology_note=append("goal", "goal"),
        _append_private_ecosystem_note=append("private", "private"),
        _append_self_action_gateway_note=append("gateway", "gateway"),
        _append_self_action_patch_executor_note=append("patch", "patch"),
        _append_self_thought_loop_note=append_thought,
        _append_proactive_request_note=append_request,
        _append_autonomous_outward_note=append_outward,
        _append_desktop_proactive_candidate_ready_note=append_desktop,
        _append_learning_closed_loop_self_thought_note=append_closed_loop,
        _append_autonomous_outcome_shadow_notes=append("outcome", "outcome"),
    )

    notes = xinyu_bridge_autonomous_maintenance.run_autonomous_self_thought_sidecars(
        runtime,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "watched",
        "github",
        "digest",
        "creative",
        "review",
        "goldmark",
        "goal",
        "private",
        "gateway",
        "patch",
        "self_thought:candidate",
        "proactive_request:ready",
        "autonomous_outward:false",
        "desktop_ready",
        "closed_loop",
        "outcome",
    ]
    assert [name for name, _ in calls] == [
        "watched",
        "github",
        "digest",
        "creative",
        "review",
        "goldmark",
        "goal",
        "private",
        "gateway",
        "patch",
        "thought",
        "request",
        "outward",
        "desktop",
        "closed_loop",
        "outcome",
    ]
    assert calls[12][1] == {"checked_at": "2026-06-06T01:00:00+08:00", "prepare_request": False}
    assert calls[14][1]["request"] == {"status": "ready", "notes": ["request-note"]}  # type: ignore[index]


def test_run_autonomous_self_thought_sidecars_handles_research_without_candidate() -> None:
    calls: list[str] = []

    def append_base(name: str):
        def inner(notes: list[str], *, checked_at: str) -> None:
            calls.append(name)
            notes.append(name)

        return inner

    def append_thought(notes: list[str], *, checked_at: str) -> dict[str, object]:
        calls.append("thought")
        notes.append("thought")
        return {"candidate_enabled": False, "research_needed": True, "research_route": "source_search_provider"}

    def append_research(notes: list[str], *, thought: dict[str, object], checked_at: str) -> None:
        calls.append("research")
        notes.append(f"research:{thought['research_route']}")

    def append_closed_loop(notes: list[str], *, thought: dict[str, object], checked_at: str) -> None:
        calls.append("closed_loop")
        notes.append("closed_loop")

    def append_outward(notes: list[str], *, checked_at: str, prepare_request: bool) -> dict[str, object]:
        calls.append(f"outward:{prepare_request}")
        notes.append(f"outward:{prepare_request}")
        return {}

    runtime = SimpleNamespace(
        _append_watched_source_note=append_base("watched"),
        _append_github_learning_note=append_base("github"),
        _append_daily_digest_note=append_base("digest"),
        _append_creative_writing_note=append_base("creative"),
        _append_review_inbox_note=append_base("review"),
        _append_goldmark_dehydrate_note=append_base("goldmark"),
        _append_goal_ecology_note=append_base("goal"),
        _append_private_ecosystem_note=append_base("private"),
        _append_self_action_gateway_note=append_base("gateway"),
        _append_self_action_patch_executor_note=append_base("patch"),
        _append_self_thought_loop_note=append_thought,
        _append_self_thought_research_notes=append_research,
        _append_learning_closed_loop_self_thought_note=append_closed_loop,
        _append_autonomous_outward_note=append_outward,
        _append_autonomous_outcome_shadow_notes=append_base("outcome"),
        _append_proactive_request_note=lambda notes, *, checked_at: calls.append("unexpected_request") or {},
    )

    notes = xinyu_bridge_autonomous_maintenance.run_autonomous_self_thought_sidecars(
        runtime,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert "unexpected_request" not in calls
    assert calls[-4:] == ["research", "closed_loop", "outward:True", "outcome"]
    assert notes[-4:] == ["research:source_search_provider", "closed_loop", "outward:True", "outcome"]


def test_run_autonomous_self_thought_sidecars_records_outcome_when_thought_fails() -> None:
    calls: list[str] = []

    def append_base(name: str):
        def inner(notes: list[str], *, checked_at: str) -> None:
            calls.append(name)
            notes.append(name)

        return inner

    runtime = SimpleNamespace(
        _append_watched_source_note=append_base("watched"),
        _append_github_learning_note=append_base("github"),
        _append_daily_digest_note=append_base("digest"),
        _append_creative_writing_note=append_base("creative"),
        _append_review_inbox_note=append_base("review"),
        _append_goldmark_dehydrate_note=append_base("goldmark"),
        _append_goal_ecology_note=append_base("goal"),
        _append_private_ecosystem_note=append_base("private"),
        _append_self_action_gateway_note=append_base("gateway"),
        _append_self_action_patch_executor_note=append_base("patch"),
        _append_self_thought_loop_note=lambda notes, *, checked_at: calls.append("thought") or None,
        _append_autonomous_outcome_shadow_notes=append_base("outcome"),
        _append_proactive_request_note=lambda notes, *, checked_at: calls.append("unexpected_request") or {},
    )

    notes = xinyu_bridge_autonomous_maintenance.run_autonomous_self_thought_sidecars(
        runtime,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert calls == [
        "watched",
        "github",
        "digest",
        "creative",
        "review",
        "goldmark",
        "goal",
        "private",
        "gateway",
        "patch",
        "thought",
        "outcome",
    ]
    assert notes[-1] == "outcome"


def test_append_learning_closed_loop_self_thought_note_appends_bounded_notes(tmp_path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_closed_loop(root, **kwargs):
        calls.append({"root": root, **kwargs})
        return {"notes": ["closed-note-1", "closed-note-2", "closed-note-3"]}

    monkeypatch.setattr(
        xinyu_bridge_autonomous_maintenance,
        "record_learning_closed_loop_self_thought",
        fake_closed_loop,
    )
    runtime = SimpleNamespace(xinyu_dir=tmp_path)
    notes: list[str] = []
    thought = {"status": "held"}
    request = {"status": "ready"}

    xinyu_bridge_autonomous_maintenance.append_learning_closed_loop_self_thought_note(
        runtime,
        notes,
        thought=thought,
        checked_at="2026-06-06T01:00:00+08:00",
    )
    xinyu_bridge_autonomous_maintenance.append_learning_closed_loop_self_thought_note(
        runtime,
        notes,
        thought=thought,
        checked_at="2026-06-06T01:00:00+08:00",
        request=request,
    )

    assert notes == ["closed-note-1", "closed-note-2", "closed-note-1", "closed-note-2"]
    assert calls == [
        {
            "root": tmp_path,
            "thought": thought,
            "observed_at": "2026-06-06T01:00:00+08:00",
        },
        {
            "root": tmp_path,
            "thought": thought,
            "observed_at": "2026-06-06T01:00:00+08:00",
            "request": request,
        },
    ]


def test_append_learning_closed_loop_self_thought_note_records_error(tmp_path, monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        xinyu_bridge_autonomous_maintenance,
        "record_learning_closed_loop_self_thought",
        fail,
    )
    runtime = SimpleNamespace(xinyu_dir=tmp_path)
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_learning_closed_loop_self_thought_note(
        runtime,
        notes,
        thought={"status": "held"},
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["learning_closed_loop_self_thought_error:RuntimeError"]


def test_append_self_thought_research_notes_runs_plugin_and_exploration() -> None:
    calls: list[tuple[str, object]] = []

    def fake_plugin(*, thought, checked_at):
        calls.append(("plugin", {"thought": thought, "checked_at": checked_at}))
        return ["plugin-note"]

    def fake_exploration(notes, *, checked_at):
        calls.append(("exploration", checked_at))
        notes.append("self_exploration:ok")

    runtime = SimpleNamespace(
        _maybe_run_self_thought_external_plugin=fake_plugin,
        _append_self_exploration_note=fake_exploration,
    )
    notes: list[str] = []
    thought = {"research_route": "source_search_provider"}

    xinyu_bridge_autonomous_maintenance.append_self_thought_research_notes(
        runtime,
        notes,
        thought=thought,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "self_thought_research:source_search_provider",
        "plugin-note",
        "self_exploration:ok",
    ]
    assert calls == [
        (
            "plugin",
            {
                "thought": thought,
                "checked_at": "2026-06-06T01:00:00+08:00",
            },
        ),
        ("exploration", "2026-06-06T01:00:00+08:00"),
    ]


def test_append_desktop_proactive_candidate_ready_note_schedules_only_ready_unqueued() -> None:
    scheduled: list[list[str]] = []
    runtime = SimpleNamespace(
        _desktop_schedule_proactive_candidate_ready_from_state=lambda *, notes: scheduled.append(notes) or True,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_desktop_proactive_candidate_ready_note(
        runtime,
        notes,
        request={"status": "ready", "notes": ["a", "b", "c", "d", "e"]},
        auto_outward={"queued": False},
    )
    xinyu_bridge_autonomous_maintenance.append_desktop_proactive_candidate_ready_note(
        runtime,
        notes,
        request={"status": "ready", "notes": ["queued"]},
        auto_outward={"queued": True},
    )
    xinyu_bridge_autonomous_maintenance.append_desktop_proactive_candidate_ready_note(
        runtime,
        notes,
        request={"status": "skipped", "notes": ["skipped"]},
        auto_outward={"queued": False},
    )

    assert scheduled == [["a", "b", "c", "d"]]
    assert notes == ["desktop_proactive_candidate_ready_scheduled"]


def test_append_autonomous_outcome_shadow_notes_runs_goal_then_proactivity() -> None:
    calls: list[tuple[str, str]] = []

    def append_goal(notes, *, checked_at):
        calls.append(("goal", checked_at))
        notes.append("goal_outcome:ok")

    def append_proactivity(notes, *, checked_at):
        calls.append(("proactivity", checked_at))
        notes.append("proactivity_shadow:ok")

    runtime = SimpleNamespace(
        _append_goal_outcome_observer_note=append_goal,
        _append_proactivity_shadow_note=append_proactivity,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_autonomous_outcome_shadow_notes(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["goal_outcome:ok", "proactivity_shadow:ok"]
    assert calls == [
        ("goal", "2026-06-06T01:00:00+08:00"),
        ("proactivity", "2026-06-06T01:00:00+08:00"),
    ]


def test_append_autonomous_outward_note_appends_tick_summary(tmp_path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_tick(root, **kwargs):
        calls.append({"root": root, **kwargs})
        return {
            "status": "prepared",
            "queued": True,
            "send_status": "queued",
            "prepared_request": {"source": "self_thought"},
        }

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_autonomous_outward_action_tick", fake_tick)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=60,
        _trace_autonomous=lambda line: None,
    )
    notes: list[str] = []

    result = xinyu_bridge_autonomous_maintenance.append_autonomous_outward_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
        prepare_request=True,
    )

    assert result["status"] == "prepared"
    assert notes == ["autonomous_outward:prepared/true/queued/self_thought"]
    assert calls == [
        {
            "root": tmp_path,
            "evaluated_at": "2026-06-06T01:00:00+08:00",
            "min_interval_seconds": 1800,
            "max_messages_per_day": 3,
            "dry_run": False,
            "prepare_request": True,
        }
    ]


def test_append_autonomous_outward_note_records_error(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fake_tick(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_autonomous_outward_action_tick", fake_tick)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        autonomous_maintenance_interval_seconds=3600,
        _trace_autonomous=traces.append,
    )
    notes: list[str] = []

    result = xinyu_bridge_autonomous_maintenance.append_autonomous_outward_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
        prepare_request=False,
    )

    assert result == {}
    assert notes == ["autonomous_outward_error:RuntimeError"]
    assert traces and traces[0].startswith("autonomous_outward_error=RuntimeError")


def test_append_goal_outcome_observer_note_appends_summary(tmp_path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_observer(root, **kwargs):
        kwargs["maintenance_notes"] = list(kwargs.get("maintenance_notes", []))
        calls.append({"root": root, **kwargs})
        return {"status": "recorded", "goal_id": "goal-1", "outcome": "useful"}

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_goal_outcome_observer", fake_observer)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _trace_autonomous=lambda line: None)
    notes = ["before"]

    xinyu_bridge_autonomous_maintenance.append_goal_outcome_observer_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["before", "goal_outcome:recorded/goal-1/useful"]
    assert calls == [
        {
            "root": tmp_path,
            "checked_at": "2026-06-06T01:00:00+08:00",
            "trigger": "autonomous_maintenance",
            "maintenance_notes": ["before"],
        }
    ]


def test_append_goal_outcome_observer_note_records_error(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fake_observer(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_goal_outcome_observer", fake_observer)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _trace_autonomous=traces.append)
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_goal_outcome_observer_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["goal_outcome_error:RuntimeError"]
    assert traces and traces[0].startswith("goal_outcome_error=RuntimeError")


def test_append_proactivity_shadow_note_appends_sidecars_and_publishes(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    published: list[tuple[dict[str, object], list[str]]] = []

    def fake_shadow(root, **kwargs):
        calls.append(("shadow", {"root": root, **kwargs}))
        return {
            "status": "ready",
            "source_type": "self_thought",
            "total_score": "0.75",
            "preferred_channel": "desktop",
        }

    def fake_initiative(root, **kwargs):
        calls.append(("initiative", {"root": root, **kwargs}))
        return {
            "status": "candidate_only",
            "source_type": "self_thought",
            "total_score": "0.82",
            "delivery_level": "desktop_inbox",
            "desktop_item": {"candidateId": "candidate-1"},
            "notes": ["note-a", "note-b"],
        }

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_proactivity_scorer_shadow", fake_shadow)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_initiative_orchestrator", fake_initiative)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _trace_autonomous=lambda line: None,
        _append_emotion_council_note=lambda notes, *, checked_at: notes.append("emotion_council:ok"),
        _append_impulse_soup_note=lambda notes, *, checked_at: notes.append("impulse_soup:ok"),
        _append_initiative_spine_note=lambda notes, *, checked_at: notes.append("initiative_spine:ok"),
        _desktop_publish_initiative_candidate_threadsafe=lambda item, *, notes: published.append((item, notes)) or True,
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_proactivity_shadow_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "emotion_council:ok",
        "proactivity_shadow:ready/self_thought/0.75/desktop",
        "initiative_orchestrator:candidate_only/self_thought/0.82/desktop_inbox",
        "desktop_initiative_candidate_ready_scheduled",
        "impulse_soup:ok",
        "initiative_spine:ok",
    ]
    assert calls == [
        ("shadow", {"root": tmp_path, "checked_at": "2026-06-06T01:00:00+08:00"}),
        (
            "initiative",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "trigger": "autonomous_maintenance",
                "delivery_level": "desktop_inbox",
                "dry_run": False,
            },
        ),
    ]
    assert published == [({"candidateId": "candidate-1"}, ["note-a", "note-b"])]


def test_append_proactivity_shadow_note_records_independent_errors(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fail_shadow(*args, **kwargs):
        raise RuntimeError("shadow")

    def fail_initiative(*args, **kwargs):
        raise ValueError("initiative")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_proactivity_scorer_shadow", fail_shadow)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_initiative_orchestrator", fail_initiative)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _trace_autonomous=traces.append,
        _append_emotion_council_note=lambda notes, *, checked_at: notes.append("emotion_council:ok"),
        _append_impulse_soup_note=lambda notes, *, checked_at: notes.append("impulse_soup:ok"),
        _append_initiative_spine_note=lambda notes, *, checked_at: notes.append("initiative_spine:ok"),
    )
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_proactivity_shadow_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "emotion_council:ok",
        "proactivity_shadow_error:RuntimeError",
        "initiative_orchestrator_error:ValueError",
        "impulse_soup:ok",
        "initiative_spine:ok",
    ]
    assert len(traces) == 2
    assert traces[0].startswith("proactivity_shadow_error=RuntimeError")
    assert traces[1].startswith("initiative_orchestrator_error=ValueError")


def test_append_emotion_council_note_appends_summary(tmp_path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_council(root, **kwargs):
        calls.append({"root": root, **kwargs})
        return {"status": "active", "strongest_lens": "guardedness", "active_lens_count": 2}

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_emotion_council_shadow", fake_council)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _trace_autonomous=lambda line: None)
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_emotion_council_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["emotion_council:active/guardedness/2"]
    assert calls == [
        {
            "root": tmp_path,
            "checked_at": "2026-06-06T01:00:00+08:00",
            "trigger": "autonomous_maintenance",
        }
    ]


def test_append_emotion_council_note_records_error(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fake_council(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_emotion_council_shadow", fake_council)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _trace_autonomous=traces.append)
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_emotion_council_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["emotion_council_error:RuntimeError"]
    assert traces and traces[0].startswith("emotion_council_error=RuntimeError")


def test_append_impulse_soup_note_appends_summary(tmp_path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_soup(root, **kwargs):
        calls.append({"root": root, **kwargs})
        return {
            "status": "active",
            "active_count": 3,
            "lineage_count": 2,
            "top_desire_shape": "repair",
        }

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_impulse_soup", fake_soup)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _trace_autonomous=lambda line: None)
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_impulse_soup_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["impulse_soup:active/3/2/repair"]
    assert calls == [{"root": tmp_path, "checked_at": "2026-06-06T01:00:00+08:00"}]


def test_append_impulse_soup_note_records_error(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fake_soup(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_impulse_soup", fake_soup)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _trace_autonomous=traces.append)
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_impulse_soup_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["impulse_soup_error:RuntimeError"]
    assert traces and traces[0].startswith("impulse_soup_error=RuntimeError")


def test_append_initiative_spine_note_appends_all_sidecars(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_spine(root, **kwargs):
        calls.append(("spine", {"root": root, **kwargs}))
        return {"emergence_level": "feedback_absorption", "action_permission": "hold"}

    def fake_drive(root, **kwargs):
        calls.append(("drive", {"root": root, **kwargs}))
        return {
            "status": "active",
            "dominant_drive": "repair",
            "drive_intensity": "0.7",
            "autonomy_tension": "medium",
        }

    def fake_observatory(root, **kwargs):
        calls.append(("observatory", {"root": root, **kwargs}))
        return {
            "posture": "balanced",
            "latest_scene": "initiative_feedback",
            "recall_admitted_count_24h": 2,
            "initiative_held_by_context_count_24h": 1,
        }

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_initiative_spine", fake_spine)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_desire_drive_state", fake_drive)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_contextual_self_observatory", fake_observatory)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _trace_autonomous=lambda line: None)
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_initiative_spine_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "initiative_spine:feedback_absorption/hold",
        "desire_drive:active/repair/0.7/medium",
        "contextual_self_observatory:balanced/initiative_feedback/2/1",
    ]
    assert calls == [
        (
            "spine",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "trigger": "autonomous_maintenance",
            },
        ),
        (
            "drive",
            {
                "root": tmp_path,
                "checked_at": "2026-06-06T01:00:00+08:00",
                "trigger": "autonomous_maintenance",
            },
        ),
        (
            "observatory",
            {
                "root": tmp_path,
                "observed_at": "2026-06-06T01:00:00+08:00",
            },
        ),
    ]


def test_append_initiative_spine_note_records_independent_errors(tmp_path, monkeypatch) -> None:
    traces: list[str] = []

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_initiative_spine", fail)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_desire_drive_state", fail)
    monkeypatch.setattr(xinyu_bridge_autonomous_maintenance, "run_contextual_self_observatory", fail)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _trace_autonomous=traces.append)
    notes: list[str] = []

    xinyu_bridge_autonomous_maintenance.append_initiative_spine_note(
        runtime,
        notes,
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == [
        "initiative_spine_error:RuntimeError",
        "desire_drive_error:RuntimeError",
        "contextual_self_observatory_error:RuntimeError",
    ]
    assert len(traces) == 3
    assert traces[0].startswith("initiative_spine_error=RuntimeError")
    assert traces[1].startswith("desire_drive_error=RuntimeError")
    assert traces[2].startswith("contextual_self_observatory_error=RuntimeError")
