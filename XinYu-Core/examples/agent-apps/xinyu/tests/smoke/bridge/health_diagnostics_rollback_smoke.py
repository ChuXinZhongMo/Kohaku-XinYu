from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_health_diagnostics_service import (
    HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER,
    HEALTH_DIAGNOSTICS_ROLLBACK,
    HEALTH_DIAGNOSTICS_STATE_OWNER,
    HealthDiagnosticsDeps,
    build_health_diagnostics_service,
)


class _SelfChoiceStore:
    def health_snapshot(self) -> dict[str, object]:
        return {"available": True}


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        memory_root=root / "memory",
        _sessions={},
        turn_timeout_seconds=1,
        pre_model_routes_timeout_seconds=1,
        outward_renderer=False,
        renderer_mode="off",
        render_timeout_seconds=1,
        session_idle_ttl_seconds=60,
        max_sessions=2,
        dialogue_prompt_tail_entries=0,
        dialogue_session_tail_entries=0,
        dialogue_persisted_tail_entries=0,
        proactive_min_interval_seconds=60,
        _v1_health=lambda: {"enabled": False},
        self_choice_store=_SelfChoiceStore(),
        _closed=False,
    )


def _deps() -> HealthDiagnosticsDeps:
    return HealthDiagnosticsDeps(
        read_code_awareness_summary_func=lambda root: {"available": False},
        read_runtime_presence_summary_func=lambda root: {
            "current_turn_state": "idle",
            "current_turn_age_seconds": 0,
            "stale_running": False,
        },
        read_turn_route_summary_func=lambda root: {
            "last_stage": "none",
            "last_route": "none",
            "last_status": "ok",
        },
        read_recent_action_digest_snapshot_func=lambda root, *, limit: {"recent": [], "limit": limit},
        autonomous_maintenance_health_func=lambda runtime: {"enabled": False},
        metabolism_health_func=lambda runtime: {"task_running": False},
        operator_health_func=lambda **kwargs: {
            "current_turn_state": "idle",
            "route_stage": "none",
            "route_status": "ok",
        },
    )


def _check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        service = build_health_diagnostics_service(_deps())

        initial = service.readiness()
        _check(failures, initial.service_id == "health_diagnostics", "unexpected service id")
        _check(failures, initial.mode == "in_process", "health diagnostics must remain in-process")
        _check(failures, initial.started is False and initial.ready is False, "initial readiness changed")
        _check(failures, initial.state_owner == HEALTH_DIAGNOSTICS_STATE_OWNER, "state owner changed")
        _check(failures, initial.fallback_adapter == HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER, "fallback changed")
        _check(failures, initial.rollback == HEALTH_DIAGNOSTICS_ROLLBACK, "rollback plan changed")
        _check(failures, "no_background_resources" in initial.notes, "background resource note missing")

        started = service.start()
        _check(failures, started.started is True and started.ready is True, "start readiness changed")
        stopped = service.stop()
        _check(failures, stopped.started is False and stopped.ready is False, "stop readiness changed")

        fallback = service.fallback_adapter()
        _check(failures, fallback.__name__ == "health_snapshot", "fallback adapter target changed")
        snapshot = fallback(
            _runtime(root),
            bridge_version="rollback-smoke",
            source_digest="bridge-digest",
            runtime_source_digest="runtime-digest",
        )
        _check(failures, snapshot.get("ok") is True, "fallback snapshot not ok")
        _check(failures, snapshot.get("version") == "rollback-smoke", "snapshot version changed")
        _check(failures, snapshot.get("source_digest") == "bridge-digest", "source digest changed")
        _check(failures, snapshot.get("runtime_source_digest") == "runtime-digest", "runtime digest changed")
        _check(failures, isinstance(snapshot.get("code_awareness"), dict), "code awareness missing")
        _check(failures, isinstance(snapshot.get("operator"), dict), "operator missing")
        _check(failures, not (root / "runtime").exists(), "fallback created runtime state")
        _check(failures, not (root / "memory").exists(), "fallback created memory state")

    if failures:
        print("health diagnostics rollback smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("health diagnostics rollback smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
