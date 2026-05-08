from __future__ import annotations

import argparse
import os

from xinyu_bridge_values import as_bool, as_int


def build_bridge_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HTTP bridge from QQ gateway to XinYu core.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--turn-timeout-seconds", type=int, default=165)
    parser.add_argument("--settle-seconds", type=float, default=0.0)
    parser.add_argument("--max-body-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--max-text-chars", type=int, default=8000)
    parser.add_argument("--disable-outward-renderer", action="store_true")
    parser.add_argument(
        "--renderer-mode",
        choices=("always", "quality", "pressure", "off"),
        default=os.environ.get("XINYU_RENDERER_MODE", "off"),
        help=(
            "Outward renderer policy. always=second LLM call every reply; "
            "quality=only pressure or failed quality gate; pressure=only pressure turns; off=disabled by default."
        ),
    )
    parser.add_argument("--render-timeout-seconds", type=int, default=60)
    parser.add_argument(
        "--session-idle-ttl-seconds",
        type=int,
        default=as_int(os.environ.get("XINYU_DIALOGUE_SESSION_IDLE_TTL_SECONDS"), 86400),
    )
    parser.add_argument("--max-sessions", type=int, default=8)
    parser.add_argument("--proactive-min-interval-seconds", type=int, default=1800)
    parser.add_argument("--disable-autonomous-maintenance", action="store_true")
    parser.add_argument("--autonomous-maintenance-initial-delay-seconds", type=int, default=60)
    parser.add_argument("--autonomous-maintenance-interval-seconds", type=int, default=1800)
    parser.add_argument(
        "--autonomous-maintenance-session-key",
        default="xinyu:autonomous:maintenance",
    )
    parser.add_argument(
        "--bridge-token",
        default=os.environ.get("XINYU_BRIDGE_TOKEN", ""),
        help="Shared token. Optional only for loopback hosts; required for non-loopback hosts.",
    )
    parser.add_argument(
        "--desktop-events-host",
        default=os.environ.get("XINYU_DESKTOP_EVENTS_HOST", "127.0.0.1"),
        help="Loopback host for the dark-launched desktop WebSocket event stream.",
    )
    parser.add_argument(
        "--desktop-events-port",
        type=int,
        default=as_int(os.environ.get("XINYU_DESKTOP_EVENTS_PORT"), 8766),
        help="Port for the dark-launched desktop WebSocket event stream.",
    )
    parser.add_argument(
        "--disable-desktop-events",
        action="store_true",
        default=as_bool(os.environ.get("XINYU_DISABLE_DESKTOP_EVENTS"), default=False),
        help="Disable the desktop WebSocket event stream dark launch.",
    )
    return parser
