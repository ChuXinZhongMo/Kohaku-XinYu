from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any


@dataclass(frozen=True)
class BridgeHTTPDispatchResult:
    data: dict[str, Any]
    status: HTTPStatus = HTTPStatus.OK


def status_from_result_http_status(
    result: dict[str, Any],
    *,
    status_cls: Any = HTTPStatus,
) -> HTTPStatus:
    return status_cls(int(result.get("http_status") or status_cls.OK.value))
