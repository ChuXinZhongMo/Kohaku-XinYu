from __future__ import annotations

import hmac
from typing import Any


def bridge_request_authorized(headers: Any, token: str) -> bool:
    expected = str(token or "")
    if not expected:
        return True
    bearer = _header_value(headers, "Authorization")
    header_token = _header_value(headers, "X-XinYu-Bridge-Token")
    auth_token = ""
    if bearer.lower().startswith("bearer "):
        auth_token = bearer[7:].strip()
    return hmac.compare_digest(expected, auth_token) or hmac.compare_digest(expected, header_token)


def _header_value(headers: Any, name: str) -> str:
    try:
        return str(headers.get(name, "") or "")
    except AttributeError:
        return ""
