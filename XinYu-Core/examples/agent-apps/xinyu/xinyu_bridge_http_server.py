from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class XinYuBridgeHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        *,
        runtime: Any,
        loop: asyncio.AbstractEventLoop,
        bridge_token: str,
        max_body_bytes: int,
        request_timeout_seconds: int,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.runtime = runtime
        self.loop = loop
        self.bridge_token = bridge_token
        self.max_body_bytes = max_body_bytes
        self.request_timeout_seconds = request_timeout_seconds
