from __future__ import annotations

import asyncio
import json
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ASTRBOT_ROOT = Path("D:/XinYu/AstrBot")
sys.path.insert(0, str(ASTRBOT_ROOT))
sys.path.insert(0, str(ROOT / "plugins/xinyu_bridge"))

from main import XinYuBridgePlugin  # noqa: E402


class SmokeBridgeHandler(BaseHTTPRequestHandler):
    server: "SmokeBridgeServer"

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        self.server.requests.append((self.path, payload))
        if self.path == "/proactive":
            self._send(
                {
                    "accepted": True,
                    "reply": "smoke proactive message",
                    "claim_id": payload.get("claim_id", "smoke-claim"),
                    "candidate_claimed": True,
                    "notes": ["smoke_claimed"],
                }
            )
            return
        if self.path == "/proactive/ack":
            self.server.acks.append(payload)
            self._send({"accepted": True, "ack_recorded": True, "notes": ["smoke_ack"]})
            return
        self._send({"accepted": False, "reply": "", "notes": ["not_found"]}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class SmokeBridgeServer(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), SmokeBridgeHandler)
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self.acks: list[dict[str, Any]] = []


class FakeMeta:
    id = "smoke-platform"


class FakePlatform:
    def meta(self) -> FakeMeta:
        return FakeMeta()


class FakePlatformManager:
    platform_insts = [FakePlatform()]


class FakeContext:
    def __init__(self, *, send_ok: bool = True) -> None:
        self.platform_manager = FakePlatformManager()
        self.send_ok = send_ok
        self.sent: list[tuple[str, Any]] = []

    def get_config(self, umo: str | None = None) -> dict[str, Any]:
        return {}

    async def send_message(self, session: str, message_chain: Any) -> bool:
        self.sent.append((session, message_chain))
        return self.send_ok


async def run_case(*, send_ok: bool) -> tuple[bool, FakeContext, SmokeBridgeServer]:
    server = SmokeBridgeServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    ctx = FakeContext(send_ok=send_ok)
    plugin = XinYuBridgePlugin(
        ctx,  # type: ignore[arg-type]
        {
            "enabled": True,
            "bridge_url": f"{base_url}/chat",
            "proactive_enabled": True,
            "proactive_target_session": "",
            "proactive_platform_id": "",
            "owner_user_ids": ["owner-id"],
            "proactive_min_interval_seconds": 0,
        },
    )
    try:
        result = await plugin._poll_proactive_once(reason="smoke")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return result, ctx, server


def main() -> int:
    failures: list[str] = []

    sent, sent_ctx, sent_server = asyncio.run(run_case(send_ok=True))
    if not sent:
        failures.append("successful proactive poll did not report sent")
    if not sent_ctx.sent:
        failures.append("successful proactive poll did not call context.send_message")
    if not sent_server.acks or sent_server.acks[-1].get("status") != "sent":
        failures.append(f"successful proactive poll did not ack sent: {sent_server.acks}")

    failed, failed_ctx, failed_server = asyncio.run(run_case(send_ok=False))
    if failed:
        failures.append("failed proactive poll should not report sent")
    if not failed_ctx.sent:
        failures.append("failed proactive poll did not attempt context.send_message")
    if not failed_server.acks or failed_server.acks[-1].get("status") != "failed":
        failures.append(f"failed proactive poll did not ack failed: {failed_server.acks}")

    if failures:
        print("XinYu bridge proactive smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge proactive smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
