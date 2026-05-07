"""Bridge-facing gateway boundary."""

from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from ..config import BridgeConfig
from ..errors import AuthenticationError, BridgeProtocolError
from ..types import Headers, TurnKind
from .compatibility import bridge_error
from .models import BridgeReply, InboundTurn
from .normalizer import TurnNormalizer


TurnHandler = Callable[[InboundTurn], Awaitable[BridgeReply]]


class BridgeGateway:
    def __init__(self, config: BridgeConfig, normalizer: TurnNormalizer | None = None) -> None:
        self._config = config
        self._normalizer = normalizer or TurnNormalizer()

    def authenticate(self, headers: Headers | None) -> None:
        token = self._config.token.strip()
        if not token:
            return
        header_map = {key.lower(): value for key, value in (headers or {}).items()}
        auth_header = header_map.get("authorization", "")
        bearer = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
        supplied = header_map.get("x-xinyu-bridge-token", "").strip() or bearer
        if not supplied or not hmac.compare_digest(supplied, token):
            raise AuthenticationError("invalid XinYu bridge token")

    async def handle_payload(
        self,
        payload: Mapping[str, Any],
        *,
        headers: Headers | None = None,
        handler: TurnHandler,
        default_kind: TurnKind = TurnKind.HUMAN_CHAT,
    ) -> tuple[int, dict[str, Any]]:
        try:
            self.authenticate(headers)
            if not isinstance(payload, Mapping):
                raise BridgeProtocolError("bridge payload must be a JSON object")
            turn = self._normalizer.normalize(payload, default_kind=default_kind)
            reply = await handler(turn)
            return 200, reply.to_json()
        except BaseException as exc:
            status, data = bridge_error(exc)
            return int(status), data

