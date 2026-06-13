from __future__ import annotations

from xinyu_bridge_auth import bridge_request_authorized


class Headers:
    def __init__(self, values: dict[str, str]) -> None:
        self._values = dict(values)

    def get(self, name: str, default: str = "") -> str:
        return self._values.get(name, default)


def test_bridge_request_auth_allows_empty_local_token() -> None:
    assert bridge_request_authorized(Headers({}), "") is True


def test_bridge_request_auth_accepts_bearer_or_bridge_token_header() -> None:
    assert bridge_request_authorized(
        Headers({"Authorization": "Bearer bridge-token"}),
        "bridge-token",
    )
    assert bridge_request_authorized(
        Headers({"X-XinYu-Bridge-Token": "bridge-token"}),
        "bridge-token",
    )
    assert bridge_request_authorized(
        Headers({"Authorization": "bearer  bridge-token  "}),
        "bridge-token",
    )


def test_bridge_request_auth_rejects_missing_or_wrong_token() -> None:
    assert not bridge_request_authorized(Headers({}), "bridge-token")
    assert not bridge_request_authorized(
        Headers({"Authorization": "Bearer wrong"}),
        "bridge-token",
    )
    assert not bridge_request_authorized(
        Headers({"X-XinYu-Bridge-Token": "wrong"}),
        "bridge-token",
    )
    assert not bridge_request_authorized(
        Headers({"Authorization": "Basic bridge-token"}),
        "bridge-token",
    )


def test_bridge_request_auth_tolerates_header_objects_without_get() -> None:
    assert not bridge_request_authorized(object(), "bridge-token")
