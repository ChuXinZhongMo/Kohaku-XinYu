from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class BridgeAppDependencies:
    runtime_factory: Callable[..., Any]
    loop_thread_factory: Callable[[], tuple[Any, Any]]
    desktop_service_factory: Callable[..., Any]
    http_server_factory: Callable[..., Any]
    request_handler_cls: Any
    load_local_env: Callable[[Path], None]
    enforce_llm_http_guard: Callable[[], None]
    enforce_bridge_token_guard: Callable[[str, str], None]
    log_prefix: str = "[xinyu_core_bridge]"


def configure_bridge_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_bridge_app(args: Any, *, xinyu_dir: Path, deps: BridgeAppDependencies) -> int:
    deps.load_local_env(xinyu_dir)
    deps.enforce_llm_http_guard()

    bridge_token = args.bridge_token.strip()
    deps.enforce_bridge_token_guard(args.host, bridge_token)
    if not args.disable_desktop_events:
        deps.enforce_bridge_token_guard(args.desktop_events_host, bridge_token)

    runtime = deps.runtime_factory(
        xinyu_dir=xinyu_dir,
        turn_timeout_seconds=args.turn_timeout_seconds,
        max_text_chars=args.max_text_chars,
        settle_seconds=args.settle_seconds,
        outward_renderer=not args.disable_outward_renderer and args.renderer_mode != "off",
        renderer_mode=args.renderer_mode,
        render_timeout_seconds=args.render_timeout_seconds,
        session_idle_ttl_seconds=args.session_idle_ttl_seconds,
        max_sessions=args.max_sessions,
        proactive_min_interval_seconds=args.proactive_min_interval_seconds,
        autonomous_maintenance_enabled=not args.disable_autonomous_maintenance,
        autonomous_maintenance_initial_delay_seconds=args.autonomous_maintenance_initial_delay_seconds,
        autonomous_maintenance_interval_seconds=args.autonomous_maintenance_interval_seconds,
        autonomous_maintenance_session_key=args.autonomous_maintenance_session_key,
    )
    loop, loop_thread = deps.loop_thread_factory()
    desktop_service = deps.desktop_service_factory(
        enabled=not args.disable_desktop_events,
        loop=loop,
        host=args.desktop_events_host,
        port=args.desktop_events_port,
        token=bridge_token,
    )
    desktop_service.attach_runtime(runtime)

    request_timeout_margin_seconds = max(0, args.request_timeout_margin_seconds)
    request_timeout_seconds = args.turn_timeout_seconds + request_timeout_margin_seconds
    server = deps.http_server_factory(
        (args.host, args.port),
        deps.request_handler_cls,
        runtime=runtime,
        loop=loop,
        bridge_token=bridge_token,
        max_body_bytes=args.max_body_bytes,
        request_timeout_seconds=request_timeout_seconds,
    )

    try:
        future = asyncio.run_coroutine_threadsafe(runtime.start_background_tasks(), loop)
        future.result(timeout=10)
    except Exception as exc:
        print(f"{deps.log_prefix} background startup warning: {exc}", flush=True)

    if desktop_service.enabled:
        try:
            future = asyncio.run_coroutine_threadsafe(desktop_service.start(), loop)
            future.result(timeout=10)
            print(
                f"{deps.log_prefix} desktop event stream dark launch listening on "
                f"{desktop_service.listener_url()}",
                flush=True,
            )
        except Exception as exc:
            print(f"{deps.log_prefix} desktop event stream startup warning: {exc}", flush=True)

    print(
        f"{deps.log_prefix} listening on http://{args.host}:{args.port} "
        f"(turn_timeout={args.turn_timeout_seconds}s, "
        f"request_timeout={request_timeout_seconds}s, "
        f"session_ttl={args.session_idle_ttl_seconds}s, max_sessions={args.max_sessions}, "
        f"renderer_mode={args.renderer_mode}, autonomous_maintenance={not args.disable_autonomous_maintenance})",
        flush=True,
    )

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print(f"{deps.log_prefix} interrupted", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        if desktop_service.enabled:
            try:
                future = asyncio.run_coroutine_threadsafe(desktop_service.stop(), loop)
                future.result(timeout=10)
                print(f"{deps.log_prefix} desktop event stream stopped", flush=True)
            except Exception as exc:
                print(f"{deps.log_prefix} desktop event stream shutdown warning: {exc}", flush=True)
        try:
            future = asyncio.run_coroutine_threadsafe(runtime.shutdown(), loop)
            future.result(timeout=60)
        except Exception as exc:
            print(f"{deps.log_prefix} shutdown warning: {exc}", flush=True)
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=10)
        print(f"{deps.log_prefix} stopped", flush=True)
    return 0
