from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from xinyu_bridge_app import BridgeAppDependencies, run_bridge_app
from xinyu_bridge_loop_thread import start_loop_thread


class _Runtime:
    def __init__(self, events: list[str], **kwargs: Any) -> None:
        self.events = events
        self.kwargs = kwargs

    async def start_background_tasks(self) -> None:
        self.events.append("runtime_start")

    async def shutdown(self) -> None:
        self.events.append("runtime_shutdown")


class _DesktopService:
    def __init__(self, events: list[str], *, enabled: bool, loop: Any, host: str, port: int, token: str) -> None:
        self.events = events
        self.enabled = enabled
        self.loop = loop
        self.host = host
        self.port = port
        self.token = token
        self.runtime: _Runtime | None = None

    def attach_runtime(self, runtime: _Runtime) -> None:
        self.runtime = runtime
        self.events.append("desktop_attach")

    async def start(self) -> None:
        self.events.append("desktop_start")

    async def stop(self) -> None:
        self.events.append("desktop_stop")

    def listener_url(self) -> str:
        return f"ws://{self.host}:{self.port}/desktop/events"


class _Server:
    def __init__(
        self,
        events: list[str],
        address: tuple[str, int],
        request_handler_cls: Any,
        **kwargs: Any,
    ) -> None:
        self.events = events
        self.address = address
        self.request_handler_cls = request_handler_cls
        self.kwargs = kwargs

    def serve_forever(self, *, poll_interval: float) -> None:
        self.events.append(f"serve:{poll_interval}")

    def shutdown(self) -> None:
        self.events.append("server_shutdown")

    def server_close(self) -> None:
        self.events.append("server_close")


def test_run_bridge_app_wires_lifecycle_and_shutdown(tmp_path: Path) -> None:
    events: list[str] = []
    holder: dict[str, Any] = {}

    def runtime_factory(**kwargs: Any) -> _Runtime:
        runtime = _Runtime(events, **kwargs)
        holder["runtime"] = runtime
        return runtime

    def desktop_service_factory(**kwargs: Any) -> _DesktopService:
        desktop = _DesktopService(events, **kwargs)
        holder["desktop"] = desktop
        return desktop

    def http_server_factory(address: tuple[str, int], request_handler_cls: Any, **kwargs: Any) -> _Server:
        server = _Server(events, address, request_handler_cls, **kwargs)
        holder["server"] = server
        return server

    def load_local_env(path: Path) -> None:
        events.append(f"load_env:{path.name}")

    def enforce_llm_http_guard() -> None:
        events.append("llm_guard")

    def enforce_bridge_token_guard(host: str, token: str) -> None:
        events.append(f"token_guard:{host}:{token}")

    args = SimpleNamespace(
        host="127.0.0.1",
        port=8765,
        turn_timeout_seconds=10,
        request_timeout_margin_seconds=5,
        max_text_chars=8000,
        settle_seconds=0.0,
        disable_outward_renderer=False,
        renderer_mode="quality",
        render_timeout_seconds=60,
        session_idle_ttl_seconds=86400,
        max_sessions=8,
        proactive_min_interval_seconds=1800,
        disable_autonomous_maintenance=False,
        autonomous_maintenance_initial_delay_seconds=60,
        autonomous_maintenance_interval_seconds=1800,
        autonomous_maintenance_session_key="xinyu:test",
        bridge_token=" token-1 ",
        disable_desktop_events=False,
        desktop_events_host="127.0.0.1",
        desktop_events_port=8766,
        max_body_bytes=1024,
    )

    result = run_bridge_app(
        args,
        xinyu_dir=tmp_path,
        deps=BridgeAppDependencies(
            runtime_factory=runtime_factory,
            loop_thread_factory=start_loop_thread,
            desktop_service_factory=desktop_service_factory,
            http_server_factory=http_server_factory,
            request_handler_cls=object,
            load_local_env=load_local_env,
            enforce_llm_http_guard=enforce_llm_http_guard,
            enforce_bridge_token_guard=enforce_bridge_token_guard,
        ),
    )

    assert result == 0
    assert events == [
        f"load_env:{tmp_path.name}",
        "llm_guard",
        "token_guard:127.0.0.1:token-1",
        "token_guard:127.0.0.1:token-1",
        "desktop_attach",
        "runtime_start",
        "desktop_start",
        "serve:0.5",
        "server_shutdown",
        "server_close",
        "desktop_stop",
        "runtime_shutdown",
    ]
    assert holder["desktop"].token == "token-1"
    assert holder["desktop"].runtime is holder["runtime"]
    assert holder["server"].address == ("127.0.0.1", 8765)
    assert holder["server"].kwargs["request_timeout_seconds"] == 15
    assert holder["server"].kwargs["bridge_token"] == "token-1"
    assert holder["runtime"].kwargs["renderer_mode"] == "quality"


def test_run_bridge_app_disabled_desktop_events_attaches_without_ws_lifecycle(tmp_path: Path) -> None:
    events: list[str] = []
    holder: dict[str, Any] = {}

    def runtime_factory(**kwargs: Any) -> _Runtime:
        runtime = _Runtime(events, **kwargs)
        holder["runtime"] = runtime
        return runtime

    def desktop_service_factory(**kwargs: Any) -> _DesktopService:
        desktop = _DesktopService(events, **kwargs)
        holder["desktop"] = desktop
        return desktop

    def http_server_factory(address: tuple[str, int], request_handler_cls: Any, **kwargs: Any) -> _Server:
        server = _Server(events, address, request_handler_cls, **kwargs)
        holder["server"] = server
        return server

    def load_local_env(path: Path) -> None:
        events.append(f"load_env:{path.name}")

    def enforce_llm_http_guard() -> None:
        events.append("llm_guard")

    def enforce_bridge_token_guard(host: str, token: str) -> None:
        events.append(f"token_guard:{host}:{token}")

    args = SimpleNamespace(
        host="127.0.0.1",
        port=8765,
        turn_timeout_seconds=10,
        request_timeout_margin_seconds=5,
        max_text_chars=8000,
        settle_seconds=0.0,
        disable_outward_renderer=False,
        renderer_mode="quality",
        render_timeout_seconds=60,
        session_idle_ttl_seconds=86400,
        max_sessions=8,
        proactive_min_interval_seconds=1800,
        disable_autonomous_maintenance=False,
        autonomous_maintenance_initial_delay_seconds=60,
        autonomous_maintenance_interval_seconds=1800,
        autonomous_maintenance_session_key="xinyu:test",
        bridge_token=" token-1 ",
        disable_desktop_events=True,
        desktop_events_host="127.0.0.2",
        desktop_events_port=8766,
        max_body_bytes=1024,
    )

    result = run_bridge_app(
        args,
        xinyu_dir=tmp_path,
        deps=BridgeAppDependencies(
            runtime_factory=runtime_factory,
            loop_thread_factory=start_loop_thread,
            desktop_service_factory=desktop_service_factory,
            http_server_factory=http_server_factory,
            request_handler_cls=object,
            load_local_env=load_local_env,
            enforce_llm_http_guard=enforce_llm_http_guard,
            enforce_bridge_token_guard=enforce_bridge_token_guard,
        ),
    )

    assert result == 0
    assert events == [
        f"load_env:{tmp_path.name}",
        "llm_guard",
        "token_guard:127.0.0.1:token-1",
        "desktop_attach",
        "runtime_start",
        "serve:0.5",
        "server_shutdown",
        "server_close",
        "runtime_shutdown",
    ]
    assert holder["desktop"].enabled is False
    assert holder["desktop"].runtime is holder["runtime"]
    assert holder["server"].address == ("127.0.0.1", 8765)
