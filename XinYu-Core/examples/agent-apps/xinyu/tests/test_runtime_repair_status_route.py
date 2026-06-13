from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import xinyu_bridge_runtime_repair_status_route as route
from xinyu_bridge_runtime_repair_status_probe import RuntimeRepairStatusProbeInput, runtime_repair_status_probe
from xinyu_bridge_runtime_repair_status_providers import RuntimeRepairStatusProviders


def _runtime(root: Path, publish_calls: list[tuple[dict[str, object], dict[str, object]]]) -> SimpleNamespace:
    del root, publish_calls
    return SimpleNamespace()


async def _publish(
    publish_calls: list[tuple[dict[str, object], dict[str, object]]],
    payload: dict[str, object],
    **kwargs: object,
) -> None:
    publish_calls.append((payload, kwargs))


def _route_deps(
    tmp_path: Path,
    publish_calls: list[tuple[dict[str, object], dict[str, object]]] | None = None,
) -> dict[str, object]:
    calls = [] if publish_calls is None else publish_calls
    return {
        "providers_func": lambda runtime: RuntimeRepairStatusProviders(
            owner_matches_func=lambda payload: True,
            health_snapshot_func=lambda: {"ok": True, "source_digest": "digest"},
            source_path=tmp_path / "xinyu_core_bridge.py",
            xinyu_dir=tmp_path,
            memory_root=tmp_path / "memory",
            final_reply_guard_func=lambda **kwargs: (kwargs["reply"], []),
            publish_chat_finished_func=lambda payload, **kwargs: _publish(calls, payload, **kwargs),
        ),
    }


def test_runtime_repair_status_probe_uses_explicit_input_dto(tmp_path: Path) -> None:
    probe = runtime_repair_status_probe(
        RuntimeRepairStatusProbeInput(
            health={"ok": True, "source_digest": "digest"},
            source_path=tmp_path / "xinyu_core_bridge.py",
        ),
        source_digest_func=lambda path: "digest",
        tcp_connect_func=lambda *args, **kwargs: True,
        safe_str_func=lambda value, default="": str(value or default),
    )

    assert probe["digest_ok"] is True
    assert probe["gateway_ok"] is True
    assert probe["core_ok"] is True
    assert probe["health"] == {"ok": True, "source_digest": "digest"}


def test_runtime_repair_status_route_returns_none_before_status_match(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, [])

    assert (
        asyncio.run(
            route.maybe_handle_runtime_repair_status_turn(
                runtime,
                {},
                text="普通聊天",
                session_key="s",
                turn_id="t",
                turn_started_wall="2026-06-08T00:00:00+08:00",
                turn_started_at=1.0,
                before_memory={},
                cleanup={},
                event_sidecar={},
                status_question_func=lambda text: False,
                **_route_deps(tmp_path),
            )
        )
        is None
    )


def test_runtime_repair_status_completion_records_and_publishes(tmp_path: Path) -> None:
    publish_calls: list[tuple[dict[str, object], dict[str, object]]] = []
    record_calls: list[dict[str, object]] = []
    runtime = _runtime(tmp_path, publish_calls)

    def memory_snapshot(root: Path) -> dict[str, object]:
        return {"after": True}

    def record_finished(root: Path, **kwargs: object) -> None:
        record_calls.append({"root": root, **kwargs})

    result = asyncio.run(
        route.maybe_handle_runtime_repair_status_turn(
            runtime,
            {"platform": "qq"},
            text="status?",
            session_key="session-1",
            turn_id="turn-1",
            turn_started_wall="2026-06-08T00:00:00+08:00",
            turn_started_at=10.0,
            before_memory={"before": True},
            cleanup={"cleaned_sessions": 1},
            event_sidecar={"notes": ["event-note"]},
            status_question_func=lambda text: True,
            **_route_deps(tmp_path, publish_calls),
            source_digest_func=lambda path: "digest",
            tcp_connect_func=lambda *args, **kwargs: True,
            memory_snapshot_func=memory_snapshot,
            finish_coherence_func=lambda *args, **kwargs: {"notes": ["coherence-a", "coherence-b"]},
            clock_func=lambda: 12.5,
            record_finished_func=record_finished,
            visible_hash_func=lambda reply: f"hash:{reply[:4]}",
            timestamp_func=lambda value: f"ts:{value}",
        )
    )

    assert result is not None
    assert result["memory_changed"] is True
    assert result["reply_hash"].startswith("hash:")
    assert "coherence-a" in result["notes"]
    assert record_calls[0]["elapsed_ms"] == 2500
    assert record_calls[0]["memory_changed"] is True
    assert publish_calls[0][1]["reply_hash"] == result["reply_hash"]
    assert publish_calls[0][1]["started_at"] == "ts:2026-06-08T00:00:00+08:00"


def test_runtime_repair_status_completion_records_coherence_error(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, [])

    def fail_coherence(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("boom")

    result = asyncio.run(
        route.maybe_handle_runtime_repair_status_turn(
            runtime,
            {},
            text="status?",
            session_key="session-1",
            turn_id="turn-1",
            turn_started_wall="wall",
            turn_started_at=10.0,
            before_memory={},
            cleanup={},
            event_sidecar={},
            status_question_func=lambda text: True,
            **_route_deps(tmp_path),
            source_digest_func=lambda path: "digest",
            tcp_connect_func=lambda *args, **kwargs: False,
            memory_snapshot_func=lambda root: {},
            finish_coherence_func=fail_coherence,
            clock_func=lambda: 10.1,
            record_finished_func=lambda *args, **kwargs: None,
            visible_hash_func=lambda reply: "hash",
            timestamp_func=lambda value: value,
        )
    )

    assert result is not None
    assert "turn_coherence_error:RuntimeError" in result["notes"]
