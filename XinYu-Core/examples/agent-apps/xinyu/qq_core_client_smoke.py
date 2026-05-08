from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from xinyu_qq_core_client import BridgeError, CoreBridgeClient


class _Handler(BaseHTTPRequestHandler):
    received: dict[str, object] = {}

    def do_POST(self) -> None:  # noqa: N802 - http.server hook
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        _Handler.received = {
            "path": self.path,
            "authorization": self.headers.get("Authorization", ""),
            "bridge_token": self.headers.get("X-XinYu-Bridge-Token", ""),
            "user_agent": self.headers.get("User-Agent", ""),
            "payload": json.loads(body),
        }
        response = json.dumps({"accepted": True}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: object) -> None:
        return


def _client(url: str) -> CoreBridgeClient:
    return CoreBridgeClient(
        chat_url=url,
        codex_execute_url=url,
        learning_ingest_url=url,
        sticker_import_url=url,
        package_install_url=url,
        review_inbox_command_url=url,
        goldmark_mark_url=url,
        qq_outbox_claim_url=url,
        qq_outbox_ack_url=url,
        message_ack_url=url,
        token="smoke-token",
        timeout_seconds=5,
        gateway_version="smoke-version",
    )


def main() -> int:
    failures: list[str] = []
    try:
        _client("")._post_json("", {})
        failures.append("empty URL was accepted")
    except BridgeError:
        pass

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/chat"
        result = _client(url)._post_json(url, {"hello": "world"})
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    if result != {"accepted": True}:
        failures.append(f"unexpected response: {result!r}")
    received = _Handler.received
    if received.get("path") != "/chat":
        failures.append("request path changed")
    if received.get("payload") != {"hello": "world"}:
        failures.append("request JSON body changed")
    if received.get("authorization") != "Bearer smoke-token":
        failures.append("authorization header changed")
    if received.get("bridge_token") != "smoke-token":
        failures.append("bridge token header changed")
    if received.get("user_agent") != "XinYu-QQ-Gateway/smoke-version":
        failures.append("user agent changed")

    if failures:
        print("QQ core client smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("QQ core client smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
