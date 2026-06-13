from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_desktop_proactive_routes import desktop_proactive_inbox
from xinyu_bridge_desktop_recent_routes import (
    desktop_chat_recent,
    desktop_memory_growth_candidates,
    desktop_memory_recent,
)
from xinyu_bridge_desktop_self_action_routes import desktop_self_action_approval
from xinyu_bridge_desktop_snapshot import desktop_snapshot
from xinyu_bridge_desktop_surface_route_backend import (
    DESKTOP_SURFACE_BACKEND_HTTP_MODE,
    DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK,
    DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR,
    DryRunDesktopSurfaceRouteBackend,
    HttpDesktopSurfaceRouteBackend,
    build_desktop_surface_route_backend,
    desktop_surface_route_backend_readiness,
    maybe_execute_desktop_surface_backend,
)
from xinyu_bridge_desktop_surface_contract import DESKTOP_SURFACE_ROLLBACK


def _runtime(root: Path, **extra: object) -> SimpleNamespace:
    values = {
        "xinyu_dir": root,
        "_closed": False,
        "_desktop_recent_turns": [],
        "_desktop_recent_memory_events": [],
    }
    values.update(extra)
    return SimpleNamespace(**values)


def test_desktop_surface_route_backend_default_does_not_intercept(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    result = asyncio.run(
        maybe_execute_desktop_surface_backend(
            runtime,
            {"query": {"limit": "1"}},
            route="/desktop/snapshot",
            http_method="GET",
            runtime_method="desktop_snapshot",
        )
    )
    readiness = desktop_surface_route_backend_readiness(runtime)

    assert result is None
    assert readiness.service_id == "desktop_surface"
    assert readiness.ready is False
    assert readiness.runtime_attr == DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.rollback == DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK
    assert readiness.contract_rollback == DESKTOP_SURFACE_ROLLBACK
    assert "disabled_by_default_contract_only" in readiness.notes


def test_desktop_surface_route_backend_enabled_returns_dry_run_response(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR: DryRunDesktopSurfaceRouteBackend(enabled=True)},
    )

    result = asyncio.run(
        maybe_execute_desktop_surface_backend(
            runtime,
            {"query": {"trace": "desktop-surface"}},
            route="/desktop/snapshot",
            http_method="GET",
            runtime_method="desktop_snapshot",
        )
    )

    assert result is not None
    assert result["service_id"] == "desktop_surface"
    assert result["status"] == "dry_run_ready"
    assert result["executed"] is False
    assert result["request"]["route"] == "/desktop/snapshot"
    assert result["request"]["runtime_method"] == "desktop_snapshot"
    assert result["request"]["query"] == {"trace": "desktop-surface"}


def test_desktop_surface_route_backend_factory_selects_http_backend() -> None:
    backend = build_desktop_surface_route_backend(
        mode=DESKTOP_SURFACE_BACKEND_HTTP_MODE,
        enabled=True,
        endpoint="http://127.0.0.1:8787",
    )

    assert isinstance(backend, HttpDesktopSurfaceRouteBackend)
    assert backend.mode == DESKTOP_SURFACE_BACKEND_HTTP_MODE
    assert backend.enabled is True


def test_desktop_surface_http_backend_uses_transport(tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object], int]] = []

    def transport(method: str, url: str, payload: dict[str, object], timeout_seconds: int) -> dict[str, object]:
        calls.append((method, url, payload, timeout_seconds))
        return {"accepted": True, "executed": True, "status": "accepted"}

    backend = HttpDesktopSurfaceRouteBackend(
        endpoint="http://127.0.0.1:8787/",
        enabled=True,
        timeout_seconds=6,
        transport=transport,
    )
    runtime = _runtime(
        tmp_path,
        desktop_snapshot=lambda payload: {"snapshot": payload},
        **{DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR: backend},
    )

    result = asyncio.run(
        maybe_execute_desktop_surface_backend(
            runtime,
            {"query": {"trace": "desktop-surface"}},
            route="/desktop/snapshot",
            http_method="GET",
            runtime_method="desktop_snapshot",
        )
    )

    assert result is not None
    assert result["mode"] == DESKTOP_SURFACE_BACKEND_HTTP_MODE
    assert result["dry_run"] is False
    assert result["executed"] is True
    assert result["request"]["route"] == "/desktop/snapshot"
    assert calls == [
        (
            "POST",
            "http://127.0.0.1:8787/desktop-surface/execute",
            {
                "route": "/desktop/snapshot",
                "http_method": "GET",
                "runtime_method": "desktop_snapshot",
                "payload": {"query": {"trace": "desktop-surface"}},
                "query": {"trace": "desktop-surface"},
            },
            6,
        )
    ]


def test_desktop_snapshot_and_recent_routes_use_enabled_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR: DryRunDesktopSurfaceRouteBackend(enabled=True)},
    )

    snapshot = asyncio.run(desktop_snapshot(runtime, {"query": {"view": "full"}}))
    chat = asyncio.run(desktop_chat_recent(runtime, {"limit": 1}))
    memory = asyncio.run(desktop_memory_recent(runtime, {"limit": 1}))
    growth = asyncio.run(desktop_memory_growth_candidates(runtime, {"limit": 1}))

    assert snapshot["request"]["route"] == "/desktop/snapshot"
    assert snapshot["request"]["runtime_method"] == "desktop_snapshot"
    assert chat["request"]["route"] == "/desktop/chat/recent"
    assert chat["request"]["runtime_method"] == "desktop_chat_recent"
    assert memory["request"]["route"] == "/desktop/memory/recent"
    assert memory["request"]["runtime_method"] == "desktop_memory_recent"
    assert growth["request"]["route"] == "/desktop/memory/growth-candidates"
    assert growth["request"]["runtime_method"] == "desktop_memory_growth_candidates"


def test_desktop_proactive_inbox_and_self_action_routes_use_enabled_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR: DryRunDesktopSurfaceRouteBackend(enabled=True)},
    )

    inbox = asyncio.run(desktop_proactive_inbox(runtime, {"query": {"limit": "5"}}))
    approval = asyncio.run(
        desktop_self_action_approval(
            runtime,
            {"queueId": "approval-1", "decision": "deny", "reason": "test"},
        )
    )

    assert inbox["request"]["route"] == "/desktop/proactive/inbox"
    assert inbox["request"]["runtime_method"] == "desktop_proactive_inbox"
    assert approval["request"]["route"] == "/desktop/self-action/approval"
    assert approval["request"]["runtime_method"] == "desktop_self_action_approval"


def test_desktop_surface_route_backend_rollback_restores_in_process_recent_route(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        _desktop_recent_turns=[{"id": "turn-1", "text": "hello"}],
        **{DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR: DryRunDesktopSurfaceRouteBackend(enabled=True)},
    )

    intercepted = asyncio.run(desktop_chat_recent(runtime, {"limit": 1}))
    delattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR)
    fallback = asyncio.run(desktop_chat_recent(runtime, {"limit": 1}))

    assert intercepted["status"] == "dry_run_ready"
    assert fallback["items"] == [{"id": "turn-1", "text": "hello"}]
    assert fallback["notes"] == ["desktop_chat_recent_v0_runtime_buffer"]
