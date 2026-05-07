from __future__ import annotations

from http import HTTPStatus

from xinyu_v1.errors import BridgeProtocolError
from xinyu_v1.gateway.compatibility import bridge_error, bridge_success


def test_bridge_success_preserves_v08_fields() -> None:
    data = bridge_success("ok", memory_changed=False, notes=("n1",), route="fast_path", trace_id="tr-1")

    assert data["accepted"] is True
    assert data["reply"] == "ok"
    assert data["memory_changed"] is False
    assert data["route"] == "fast_path"
    assert data["trace_id"] == "tr-1"


def test_bridge_error_preserves_http_status() -> None:
    status, data = bridge_error(BridgeProtocolError("bad payload"))

    assert status is HTTPStatus.BAD_REQUEST
    assert data["accepted"] is False
    assert data["error"]["code"] == "bridge_protocol_error"

