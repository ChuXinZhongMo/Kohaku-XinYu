from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class MockBridgeHandler(BaseHTTPRequestHandler):
    server_version = "XinYuMockBridge/0.1"

    def do_POST(self) -> None:
        if self.path not in {"/chat", "/learning/ingest"}:
            self._send_json({"accepted": False, "reply": "", "notes": ["not_found"]}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"accepted": False, "reply": "", "notes": ["invalid_json"]}, status=400)
            return

        if self.path == "/learning/ingest":
            file_name = str(payload.get("file_name") or "file")
            self._send_json(
                {
                    "accepted": True,
                    "reply": f"[mock XinYu bridge] learned file: {file_name}",
                    "learning_item_id": "learn-mock",
                    "material_id": "material-mock",
                    "extracted_text": True,
                    "notes": ["mock_learning_ingest_only"],
                }
            )
            return

        user_id = str(payload.get("user_id") or "unknown")
        message_type = str(payload.get("message_type") or "unknown")
        text = str(payload.get("text") or "")
        reply = f"[mock XinYu bridge] accepted {message_type} from {user_id}: {text[:80]}"
        self._send_json(
            {
                "accepted": True,
                "reply": reply,
                "memory_changed": False,
                "notes": ["mock_bridge_only"],
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local echo bridge for AstrBot shell testing.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MockBridgeHandler)
    print(f"Mock XinYu bridge listening on http://{args.host}:{args.port}/chat and /learning/ingest")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping mock bridge")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
