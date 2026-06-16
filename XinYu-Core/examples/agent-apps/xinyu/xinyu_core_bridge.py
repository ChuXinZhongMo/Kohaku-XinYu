from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_bridge_app import BridgeAppDependencies, configure_bridge_stdio, run_bridge_app
from xinyu_bridge_http import XinYuBridgeHTTPServer, XinYuBridgeRequestHandler
from xinyu_bridge_bootstrap import runtime_load_runtime as _runtime_load_runtime
from xinyu_bridge_bootstrap import load_local_env as _load_local_env
from xinyu_bridge_cli import build_bridge_parser as _build_parser
from xinyu_bridge_core_compat_exports import CORE_COMPAT_EXPORTS as _CORE_COMPAT_EXPORTS
from xinyu_bridge_loop_thread import start_loop_thread as _start_loop_thread
import xinyu_bridge_runtime_aliases
import xinyu_bridge_runtime_state
from xinyu_bridge_chat_turn import run_chat_payload
from xinyu_desktop_service import build_desktop_service
from xinyu_runtime_security import (
    enforce_bridge_token_guard,
    enforce_llm_http_guard,
    runtime_source_paths,
    source_file_digest,
    source_files_digest,
)
from xinyu_visible_state_hygiene import sanitize_visible_state_files

BRIDGE_VERSION = "0.9.0"
BRIDGE_SOURCE_PATH = Path(__file__).resolve()
BRIDGE_SOURCE_DIGEST = source_file_digest(BRIDGE_SOURCE_PATH)
BRIDGE_RUNTIME_SOURCE_DIGEST = source_files_digest(runtime_source_paths(BRIDGE_SOURCE_PATH.parent))

__all__ = (
    "BRIDGE_RUNTIME_SOURCE_DIGEST",
    "BRIDGE_SOURCE_DIGEST",
    "BRIDGE_SOURCE_PATH",
    "BRIDGE_VERSION",
    "BridgeAppDependencies",
    "XinYuBridgeHTTPServer",
    "XinYuBridgeRequestHandler",
    "XinYuBridgeRuntime",
    "build_desktop_service",
    "configure_bridge_stdio",
    "enforce_bridge_token_guard",
    "enforce_llm_http_guard",
    "main",
    "run_bridge_app",
    "run_chat_payload",
    "runtime_source_paths",
    "source_file_digest",
    "source_files_digest",
    *_CORE_COMPAT_EXPORTS,
)


def __getattr__(name: str) -> Any:
    if name not in _CORE_COMPAT_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import xinyu_bridge_core_compat

    value = getattr(xinyu_bridge_core_compat, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted((*globals(), *_CORE_COMPAT_EXPORTS))


class XinYuBridgeRuntime:
    def __init__(
        self,
        *,
        xinyu_dir: Path,
        turn_timeout_seconds: int,
        max_text_chars: int,
        settle_seconds: float,
        outward_renderer: bool,
        renderer_mode: str = "off",
        render_timeout_seconds: int = 60,
        session_idle_ttl_seconds: int = 86400,
        max_sessions: int = 8,
        proactive_min_interval_seconds: int = 21600,
        autonomous_maintenance_enabled: bool = True,
        autonomous_maintenance_initial_delay_seconds: int = 60,
        autonomous_maintenance_interval_seconds: int = 1800,
        autonomous_maintenance_session_key: str = "xinyu:autonomous:maintenance",
        metabolism_runner_interval_seconds: int = 30,
    ) -> None:
        xinyu_bridge_runtime_state.initialize_runtime(
            self,
            xinyu_bridge_runtime_state.RuntimeInitConfig(
                xinyu_dir=xinyu_dir,
                turn_timeout_seconds=turn_timeout_seconds,
                max_text_chars=max_text_chars,
                settle_seconds=settle_seconds,
                outward_renderer=outward_renderer,
                renderer_mode=renderer_mode,
                render_timeout_seconds=render_timeout_seconds,
                session_idle_ttl_seconds=session_idle_ttl_seconds,
                max_sessions=max_sessions,
                proactive_min_interval_seconds=proactive_min_interval_seconds,
                autonomous_maintenance_enabled=autonomous_maintenance_enabled,
                autonomous_maintenance_initial_delay_seconds=autonomous_maintenance_initial_delay_seconds,
                autonomous_maintenance_interval_seconds=autonomous_maintenance_interval_seconds,
                autonomous_maintenance_session_key=autonomous_maintenance_session_key,
                metabolism_runner_interval_seconds=metabolism_runner_interval_seconds,
            ),
            bridge_version=BRIDGE_VERSION,
            bridge_source_digest=BRIDGE_SOURCE_DIGEST,
            bridge_runtime_source_digest=BRIDGE_RUNTIME_SOURCE_DIGEST,
        )

    _load_runtime = _runtime_load_runtime

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await run_chat_payload(self, payload)


xinyu_bridge_runtime_aliases.install_runtime_aliases(
    XinYuBridgeRuntime,
    bridge_source_path=BRIDGE_SOURCE_PATH,
)


def main() -> int:
    configure_bridge_stdio()
    args = _build_parser().parse_args()
    return run_bridge_app(
        args,
        xinyu_dir=Path(__file__).resolve().parent,
        deps=BridgeAppDependencies(
            runtime_factory=XinYuBridgeRuntime,
            loop_thread_factory=_start_loop_thread,
            desktop_service_factory=build_desktop_service,
            http_server_factory=XinYuBridgeHTTPServer,
            request_handler_cls=XinYuBridgeRequestHandler,
            load_local_env=_load_local_env,
            enforce_llm_http_guard=enforce_llm_http_guard,
            enforce_bridge_token_guard=enforce_bridge_token_guard,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
