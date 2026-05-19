from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any


NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class BridgeError(RuntimeError):
    pass


class CoreBridgeClient:
    def __init__(
        self,
        *,
        chat_url: str,
        codex_execute_url: str,
        learning_ingest_url: str,
        sticker_import_url: str,
        package_install_url: str,
        review_inbox_command_url: str,
        goldmark_mark_url: str,
        qq_outbox_claim_url: str,
        qq_outbox_ack_url: str,
        message_ack_url: str,
        token: str,
        timeout_seconds: int,
        gateway_version: str,
    ) -> None:
        self.chat_url = chat_url.strip()
        self.codex_execute_url = codex_execute_url.strip()
        self.learning_ingest_url = learning_ingest_url.strip()
        self.sticker_import_url = sticker_import_url.strip()
        self.package_install_url = package_install_url.strip()
        self.review_inbox_command_url = review_inbox_command_url.strip()
        self.goldmark_mark_url = goldmark_mark_url.strip()
        self.qq_outbox_claim_url = qq_outbox_claim_url.strip()
        self.qq_outbox_ack_url = qq_outbox_ack_url.strip()
        self.message_ack_url = message_ack_url.strip()
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds
        self.gateway_version = gateway_version.strip()

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.chat_url, payload)

    async def codex_execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.codex_execute_url, payload)

    async def learning_ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.learning_ingest_url, payload)

    async def sticker_import(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.sticker_import_url, payload)

    async def package_install(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.package_install_url, payload)

    async def review_inbox_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.review_inbox_command_url, payload)

    async def self_action_approval(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self._route_url("/desktop/self-action/approval"), payload)

    async def goldmark_mark_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.goldmark_mark_url, payload)

    async def qq_outbox_claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.qq_outbox_claim_url, payload)

    async def qq_outbox_ack(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.qq_outbox_ack_url, payload)

    async def message_ack(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.message_ack_url, payload)

    def _route_url(self, route: str) -> str:
        trimmed = self.chat_url.rstrip("/")
        if trimmed.endswith("/chat"):
            return trimmed[: -len("/chat")] + route
        return trimmed + route

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not url:
            raise BridgeError("core chat URL is empty")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"XinYu-QQ-Gateway/{self.gateway_version}",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            headers["X-XinYu-Bridge-Token"] = self.token
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with NO_PROXY_OPENER.open(request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                response_body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise BridgeError(f"core bridge HTTP {exc.code}: {error_body[:300]}") from exc
        except urllib.error.URLError as exc:
            raise BridgeError(f"core bridge connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise BridgeError("core bridge request timed out") from exc
        if status < 200 or status >= 300:
            raise BridgeError(f"core bridge HTTP {status}: {response_body[:300]}")
        try:
            data = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise BridgeError(f"core bridge returned invalid JSON: {response_body[:300]}") from exc
        if not isinstance(data, dict):
            raise BridgeError("core bridge returned non-object JSON")
        return data
