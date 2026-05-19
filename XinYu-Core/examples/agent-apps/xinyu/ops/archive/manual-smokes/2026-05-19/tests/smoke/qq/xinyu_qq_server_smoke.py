from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from types import SimpleNamespace

from xinyu_qq_server import connection_id, websocket_path, websocket_path_allowed


def main() -> int:
    failures: list[str] = []

    request_websocket = SimpleNamespace(request=SimpleNamespace(path="/ws"), path="/legacy")
    if websocket_path(request_websocket) != "/ws":
        failures.append("request.path should win over legacy websocket.path")

    legacy_websocket = SimpleNamespace(path="/legacy")
    if websocket_path(legacy_websocket) != "/legacy":
        failures.append("legacy websocket.path fallback changed")

    if not websocket_path_allowed("", "/ws") or not websocket_path_allowed("/ws", "/ws"):
        failures.append("allowed websocket path changed")
    if websocket_path_allowed("/other", "/ws"):
        failures.append("invalid websocket path was accepted")
    if not websocket_path_allowed("/other", ""):
        failures.append("empty configured path should allow all paths")

    if connection_id("napcat", 123, 4) != "napcat-123-4":
        failures.append("connection id format changed")

    if failures:
        print("XinYu QQ server smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ server smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
