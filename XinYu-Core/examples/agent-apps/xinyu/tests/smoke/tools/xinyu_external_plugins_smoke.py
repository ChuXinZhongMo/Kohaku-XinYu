from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from xinyu_external_plugins import (
    PROTOCOL_VERSION,
    TRANSPORT_HTTP,
    TRANSPORT_MCP,
    TRANSPORT_NATIVE_BRIDGE,
    TRANSPORT_WEBSOCKET,
    ExternalCallContext,
    default_external_plugins,
    external_plugin_runtime_allowed,
    execute_http_prepared_call,
    external_plugin_manifest,
    external_plugin_status,
    install_external_plugin,
    load_external_plugin_control,
    prepare_external_call,
    save_external_plugin_control_patch,
)


class _KohakuStubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b""
        body = json.loads(raw.decode("utf-8")) if raw else {}
        if self.path != "/api/sessions/session%20one/creatures/kohaku/chat":
            payload = {"error": "unexpected_path", "path": self.path}
            data = json.dumps(payload).encode("utf-8")
            self.send_response(404)
        else:
            payload = {"response": "kohaku-ok", "echo": body}
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _format: str, *_args) -> None:
        return


def _run_kohaku_stub() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _KohakuStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def _plugin_by_id(status: dict[str, object], plugin_id: str) -> dict[str, object]:
    for item in status.get("plugins", []):
        if isinstance(item, dict) and item.get("plugin_id") == plugin_id:
            return item
    return {}


def main() -> int:
    failures: list[str] = []
    env = {"XINYU_KOHAKU_BASE_URL": "http://127.0.0.1:8123"}
    registry = default_external_plugins(
        env
    )

    codex = registry.get("codex")
    kohaku = registry.get("kohaku_terrarium")
    mcp = registry.get("mcp_gateway")
    if not codex or codex.transport != TRANSPORT_NATIVE_BRIDGE:
        failures.append("Codex should be registered as a native bridge plugin")
    if not kohaku or kohaku.transport != "http_ws":
        failures.append("Kohaku should be registered as an HTTP/WS runtime plugin")
    if not mcp or mcp.transport != TRANSPORT_MCP:
        failures.append("MCP gateway should be registered as a protocol adapter")

    owner_proactive = ExternalCallContext(
        source="self_thought_loop",
        owner_private=True,
        reason="needs external runtime perspective",
        proactive=True,
    )
    chat = prepare_external_call(
        "kohaku_terrarium",
        "chat_creature",
        {"session_id": "session one", "creature_id": "kohaku", "message": "hello"},
        owner_proactive,
        registry=registry,
    )
    if chat.protocol != PROTOCOL_VERSION or not chat.decision.ok:
        failures.append(f"Kohaku chat should be allowed: {chat}")
    if chat.request.get("transport") != TRANSPORT_HTTP:
        failures.append("Kohaku chat should use HTTP transport")
    expected_chat_url = (
        "http://127.0.0.1:8123/api/sessions/session%20one/creatures/kohaku/chat"
    )
    if chat.request.get("url") != expected_chat_url:
        failures.append(f"Kohaku chat URL mismatch: {chat.request.get('url')}")
    if chat.request.get("json") != {"message": "hello"}:
        failures.append("Kohaku chat body should use AgentChat.message")

    server, base_url = _run_kohaku_stub()
    try:
        live_chat = prepare_external_call(
            "kohaku_terrarium",
            "chat_creature",
            {"base_url": base_url, "session_id": "session one", "creature_id": "kohaku", "message": "hello"},
            owner_proactive,
            registry=registry,
        )
        execution = execute_http_prepared_call(live_chat, timeout_seconds=5)
        if not execution.get("ok") or execution.get("status_code") != 200:
            failures.append(f"Kohaku HTTP execution should succeed: {execution}")
        data = execution.get("json") if isinstance(execution.get("json"), dict) else {}
        if data.get("response") != "kohaku-ok" or data.get("echo") != {"message": "hello"}:
            failures.append(f"Kohaku HTTP execution response mismatch: {data}")
    finally:
        server.shutdown()
        server.server_close()

    ws = prepare_external_call(
        "kohaku_terrarium",
        "ws_chat",
        {
            "session_id": "s1",
            "creature_id": "c1",
            "message": "stream me",
            "target": "c1",
        },
        owner_proactive,
        registry=registry,
    )
    if not ws.decision.ok or ws.request.get("transport") != TRANSPORT_WEBSOCKET:
        failures.append(f"Kohaku websocket should be allowed: {ws}")
    if ws.request.get("url") != "ws://127.0.0.1:8123/ws/sessions/s1/creatures/c1/chat":
        failures.append(f"Kohaku websocket URL mismatch: {ws.request.get('url')}")
    if ws.request.get("send_frame") != {
        "type": "input",
        "message": "stream me",
        "target": "c1",
    }:
        failures.append("Kohaku websocket frame should match attach_io input")

    command = prepare_external_call(
        "kohaku_terrarium",
        "command",
        {"session_id": "s1", "creature_id": "c1", "command": "status"},
        owner_proactive,
        registry=registry,
    )
    if command.decision.ok or command.decision.reason != "proactive_not_allowed_for_capability":
        failures.append("Kohaku commands should not be proactive by default")

    manual_approved = ExternalCallContext(
        source="owner_private_manual",
        owner_private=True,
        reason="owner asked for a Kohaku command",
        proactive=False,
        approved=True,
    )
    approved_command = prepare_external_call(
        "kohaku_terrarium",
        "command",
        {"session_id": "s1", "creature_id": "c1", "command": "status", "args": "--short"},
        manual_approved,
        registry=registry,
    )
    if not approved_command.decision.ok:
        failures.append(f"Approved Kohaku command should be allowed: {approved_command}")
    if approved_command.request.get("json") != {"command": "status", "args": "--short"}:
        failures.append("Approved Kohaku command body mismatch")

    codex_call = prepare_external_call(
        "codex",
        "delegate_task",
        {"task_text": "inspect D:\\XinYu for the plugin gateway"},
        owner_proactive,
        registry=registry,
    )
    if not codex_call.decision.ok:
        failures.append(f"Codex delegate should be allowed in owner-private context: {codex_call}")
    if codex_call.request.get("transport") != TRANSPORT_NATIVE_BRIDGE:
        failures.append("Codex delegate should prepare a native bridge request")
    if codex_call.request.get("bridge_method") != "codex_execute":
        failures.append("Codex delegate should target runtime.codex_execute")

    non_owner = ExternalCallContext(
        source="group_chat",
        owner_private=False,
        reason="group asked for local code",
        proactive=False,
    )
    blocked_codex = prepare_external_call(
        "codex",
        "delegate_task",
        {"task_text": "inspect local files"},
        non_owner,
        registry=registry,
    )
    if blocked_codex.decision.ok or blocked_codex.decision.reason != "owner_private_required":
        failures.append("Codex delegate should require owner-private context")

    empty_reason = ExternalCallContext(
        source="self_thought_loop",
        owner_private=True,
        proactive=True,
    )
    blocked_reason = prepare_external_call(
        "kohaku_terrarium",
        "history",
        {"session_id": "s1", "creature_id": "c1"},
        empty_reason,
        registry=registry,
    )
    if blocked_reason.decision.ok or blocked_reason.decision.reason != "concrete_reason_required":
        failures.append("Proactive external calls should require a concrete reason")

    manifest = external_plugin_manifest({"XINYU_KOHAKU_BASE_URL": "http://127.0.0.1:8123"})
    if manifest.get("protocol") != PROTOCOL_VERSION:
        failures.append("Manifest protocol mismatch")
    if TRANSPORT_MCP not in manifest.get("supported_transports", []):
        failures.append("Manifest should expose MCP as a supported transport")
    plugin_ids = {item.get("plugin_id") for item in manifest.get("plugins", [])}
    if {"codex", "kohaku_terrarium", "mcp_gateway"} - plugin_ids:
        failures.append(f"Manifest missing plugin ids: {plugin_ids}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        control = load_external_plugin_control(temp_root, env)
        if not control.get("plugins") or "kohaku_terrarium" not in control.get("plugins", {}):
            failures.append("Default plugin control should include Kohaku")

        saved = save_external_plugin_control_patch(
            temp_root,
            {
                "plugin_id": "kohaku_terrarium",
                "enabled": True,
                "proactive_enabled": True,
                "config": {
                    "base_url": "http://127.0.0.1:8123",
                    "install_path": str(temp_root / "missing" / "kohaku"),
                    "session_id": "session-one",
                    "creature_id": "kohaku",
                },
            },
            env,
        )
        kohaku_saved = _plugin_by_id(saved, "kohaku_terrarium")
        if kohaku_saved.get("config", {}).get("install_path") != str(temp_root / "missing" / "kohaku"):
            failures.append("Plugin control patch should persist install_path")

        blocked_allowed, blocked_reason, _ = external_plugin_runtime_allowed(
            temp_root,
            "kohaku_terrarium",
            proactive=True,
            env=env,
        )
        if blocked_allowed or blocked_reason != "plugin_not_installed":
            failures.append("Missing Kohaku install should be blocked")

        source_dir = temp_root / "kohaku-source"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "KohakuTerrarium.exe").write_text("stub", encoding="utf-8")
        install_path = temp_root / "runtime" / "kohaku"
        install_result = install_external_plugin(
            temp_root,
            "kohaku_terrarium",
            {
                "source_path": str(source_dir),
                "install_path": str(install_path),
            },
        )
        if not install_result.get("ok") or not install_result.get("installed"):
            failures.append(f"Kohaku source install should succeed: {install_result}")

        installed_status = external_plugin_status(temp_root, env)
        installed_kohaku = _plugin_by_id(installed_status, "kohaku_terrarium")
        if not installed_kohaku.get("installed") or installed_kohaku.get("install", {}).get("path") != str(install_path):
            failures.append("Kohaku install status should point at the installed path")

        allowed_after, reason_after, _ = external_plugin_runtime_allowed(
            temp_root,
            "kohaku_terrarium",
            proactive=True,
            env=env,
        )
        if not allowed_after or reason_after != "allowed":
            failures.append(f"Installed Kohaku should be allowed: {reason_after}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("xinyu_external_plugins_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
