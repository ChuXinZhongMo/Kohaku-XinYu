from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kernel import decide
from compose import compose_shadow


ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = ROOT / "state" / "feedback.jsonl"


class TinyKernelHandler(BaseHTTPRequestHandler):
    server_version = "XinYuTinyKernel/0.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length > 0 else b"{}"
        value = json.loads(raw.decode("utf-8"))
        return value if isinstance(value, dict) else {}

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"ok": True, "kernel": "rule", "model_loaded": False, "adapter": "none"})
            return
        if self.path == "/version":
            self._send_json(200, {"version": "0.1.0", "project": "XinYu-TinyKernel"})
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
        except Exception as exc:
            self._send_json(400, {"ok": False, "error": f"invalid_json:{type(exc).__name__}"})
            return
        if self.path == "/decide":
            self._send_json(200, decide(payload))
            return
        if self.path == "/compose_shadow":
            self._send_json(200, compose_shadow(payload))
            return
        if self.path == "/feedback":
            payload["received_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
            with FEEDBACK_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            self._send_json(202, {"ok": True, "stored": True, "path": "state/feedback.jsonl"})
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8877)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), TinyKernelHandler)
    print(f"TinyKernel server listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
