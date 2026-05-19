from __future__ import annotations

import contextlib
import io
import os

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_cli import build_bridge_parser
from xinyu_core_bridge import _build_parser


def main() -> int:
    failures: list[str] = []
    old_env = {
        key: os.environ.get(key)
        for key in (
            "XINYU_RENDERER_MODE",
            "XINYU_DIALOGUE_SESSION_IDLE_TTL_SECONDS",
            "XINYU_BRIDGE_TOKEN",
            "XINYU_DESKTOP_EVENTS_HOST",
            "XINYU_DESKTOP_EVENTS_PORT",
            "XINYU_DISABLE_DESKTOP_EVENTS",
        )
    }
    try:
        os.environ["XINYU_RENDERER_MODE"] = "quality"
        os.environ["XINYU_DIALOGUE_SESSION_IDLE_TTL_SECONDS"] = "123"
        os.environ["XINYU_BRIDGE_TOKEN"] = "token-from-env"
        os.environ["XINYU_DESKTOP_EVENTS_HOST"] = "127.0.0.2"
        os.environ["XINYU_DESKTOP_EVENTS_PORT"] = "9876"
        os.environ["XINYU_DISABLE_DESKTOP_EVENTS"] = "true"

        args = build_bridge_parser().parse_args([])
        if args.renderer_mode != "quality":
            failures.append("bridge parser renderer env default changed")
        if args.session_idle_ttl_seconds != 123:
            failures.append("bridge parser session ttl env default changed")
        if args.bridge_token != "token-from-env":
            failures.append("bridge parser token env default changed")
        if args.desktop_events_host != "127.0.0.2" or args.desktop_events_port != 9876:
            failures.append("bridge parser desktop event env defaults changed")
        if args.disable_desktop_events is not True:
            failures.append("bridge parser desktop event disable env default changed")

        with contextlib.redirect_stderr(io.StringIO()):
            explicit = build_bridge_parser().parse_args(
                ["--host", "0.0.0.0", "--port", "9999", "--renderer-mode", "off", "--enable-invalid"]
            )
        failures.append(f"bridge parser accepted unknown argument unexpectedly: {explicit}")
    except SystemExit as exc:
        if exc.code == 0:
            failures.append("bridge parser exited successfully on invalid argument")
    finally:
        for key, old_value in old_env.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value

    explicit = build_bridge_parser().parse_args(["--host", "0.0.0.0", "--port", "9999", "--renderer-mode", "off"])
    if explicit.host != "0.0.0.0" or explicit.port != 9999 or explicit.renderer_mode != "off":
        failures.append("bridge parser explicit arguments changed")

    if _build_parser is not build_bridge_parser:
        failures.append("core bridge parser alias no longer delegates")

    if failures:
        print("XinYu bridge CLI smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge CLI smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
