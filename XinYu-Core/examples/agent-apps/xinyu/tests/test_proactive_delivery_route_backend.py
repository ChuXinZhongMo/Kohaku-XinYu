from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_desktop_proactive_routes import desktop_proactive_ack
from xinyu_bridge_proactive_delivery_route_backend import (
    PROACTIVE_DELIVERY_BACKEND_HTTP_MODE,
    PROACTIVE_DELIVERY_ROUTE_BACKEND_ROLLBACK,
    PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR,
    DryRunProactiveDeliveryRouteBackend,
    HttpProactiveDeliveryRouteBackend,
    build_proactive_delivery_route_backend,
    maybe_execute_proactive_delivery_backend,
    maybe_execute_proactive_delivery_backend_sync,
    proactive_delivery_route_backend_readiness,
)
from xinyu_bridge_proactive_delivery_contract import PROACTIVE_DELIVERY_ROLLBACK
from xinyu_bridge_proactive_delivery_routes import (
    proactive,
    proactive_ack,
    qq_outbox_ack_fast,
    qq_outbox_claim,
    qq_outbox_claim_fast,
)
from xinyu_qq_outbox import enqueue_qq_outbox_message


def _runtime(root: Path, **extra: object) -> SimpleNamespace:
    values = {
        "xinyu_dir": root,
        "memory_root": root / "memory",
        "_closed": False,
        "_sessions": {},
    }
    values.update(extra)
    return SimpleNamespace(**values)


def test_proactive_delivery_route_backend_default_does_not_intercept(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    result = asyncio.run(
        maybe_execute_proactive_delivery_backend(
            runtime,
            {"claim": True},
            route="/proactive",
            http_method="GET_OR_POST",
            runtime_method="proactive",
        )
    )
    sync_result = maybe_execute_proactive_delivery_backend_sync(
        runtime,
        {"claim_id": "claim-1"},
        route="/qq/outbox/claim",
        http_method="POST",
        runtime_method="qq_outbox_claim_fast",
    )
    readiness = proactive_delivery_route_backend_readiness(runtime)

    assert result is None
    assert sync_result is None
    assert readiness.service_id == "proactive_delivery"
    assert readiness.ready is False
    assert readiness.runtime_attr == PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.rollback == PROACTIVE_DELIVERY_ROUTE_BACKEND_ROLLBACK
    assert readiness.contract_rollback == PROACTIVE_DELIVERY_ROLLBACK
    assert "disabled_by_default_contract_only" in readiness.notes


def test_proactive_delivery_route_backend_enabled_returns_dry_run_response(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR: DryRunProactiveDeliveryRouteBackend(enabled=True)},
    )

    result = asyncio.run(
        maybe_execute_proactive_delivery_backend(
            runtime,
            {"claim_id": "claim-1", "query": {"trace": "route-backend"}},
            route="/qq/outbox/claim",
            http_method="POST",
            runtime_method="qq_outbox_claim",
        )
    )

    assert result is not None
    assert result["service_id"] == "proactive_delivery"
    assert result["status"] == "dry_run_ready"
    assert result["executed"] is False
    assert result["request"]["route"] == "/qq/outbox/claim"
    assert result["request"]["runtime_method"] == "qq_outbox_claim"
    assert result["request"]["payload"]["claim_id"] == "claim-1"
    assert result["request"]["query"] == {"trace": "route-backend"}
    assert result["request"]["fast_path"] is False


def test_proactive_delivery_route_backend_factory_selects_http_backend() -> None:
    backend = build_proactive_delivery_route_backend(
        mode=PROACTIVE_DELIVERY_BACKEND_HTTP_MODE,
        enabled=True,
        endpoint="http://127.0.0.1:8787",
    )

    assert isinstance(backend, HttpProactiveDeliveryRouteBackend)
    assert backend.mode == PROACTIVE_DELIVERY_BACKEND_HTTP_MODE
    assert backend.enabled is True


def test_proactive_delivery_http_backend_uses_transport_for_async_and_fast_paths(tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object], int]] = []

    def transport(method: str, url: str, payload: dict[str, object], timeout_seconds: int) -> dict[str, object]:
        calls.append((method, url, payload, timeout_seconds))
        return {"accepted": True, "executed": True, "status": "accepted"}

    backend = HttpProactiveDeliveryRouteBackend(
        endpoint="http://127.0.0.1:8787/",
        enabled=True,
        timeout_seconds=6,
        transport=transport,
    )
    runtime = _runtime(
        tmp_path,
        qq_outbox_claim=lambda payload: {"claimed": payload},
        qq_outbox_claim_fast=lambda payload: {"claimed": payload},
        **{PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR: backend},
    )

    async_result = asyncio.run(
        maybe_execute_proactive_delivery_backend(
            runtime,
            {"claim_id": "claim-async"},
            route="/qq/outbox/claim",
            http_method="POST",
            runtime_method="qq_outbox_claim",
        )
    )
    sync_result = maybe_execute_proactive_delivery_backend_sync(
        runtime,
        {"claim_id": "claim-fast"},
        route="/qq/outbox/claim",
        http_method="POST",
        runtime_method="qq_outbox_claim_fast",
    )

    assert async_result is not None
    assert async_result["mode"] == PROACTIVE_DELIVERY_BACKEND_HTTP_MODE
    assert async_result["dry_run"] is False
    assert async_result["executed"] is True
    assert sync_result is not None
    assert sync_result["request"]["fast_path"] is True
    assert [call[1] for call in calls] == [
        "http://127.0.0.1:8787/proactive-delivery/execute",
        "http://127.0.0.1:8787/proactive-delivery/execute",
    ]
    assert all(call[3] == 6 for call in calls)


def test_proactive_and_ack_routes_use_enabled_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR: DryRunProactiveDeliveryRouteBackend(enabled=True)},
    )

    preview = asyncio.run(proactive(runtime, {"query": {"source": "get-or-post"}}))
    ack = asyncio.run(proactive_ack(runtime, {"claim_id": "claim-1", "ack_status": "sent"}))

    assert preview["status"] == "dry_run_ready"
    assert preview["request"]["route"] == "/proactive"
    assert preview["request"]["http_method"] == "GET_OR_POST"
    assert preview["request"]["runtime_method"] == "proactive"
    assert ack["status"] == "dry_run_ready"
    assert ack["request"]["route"] == "/proactive/ack"
    assert ack["request"]["runtime_method"] == "proactive_ack"


def test_qq_outbox_claim_and_fast_ack_use_enabled_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR: DryRunProactiveDeliveryRouteBackend(enabled=True)},
    )

    claim = asyncio.run(qq_outbox_claim(runtime, {"claim_id": "claim-async"}))
    fast_claim = qq_outbox_claim_fast(runtime, {"claim_id": "claim-fast"})
    fast_ack = qq_outbox_ack_fast(
        runtime,
        {"message_id": "ordinary-1", "claim_id": "claim-fast", "ack_status": "sent"},
    )

    assert claim["status"] == "dry_run_ready"
    assert claim["request"]["runtime_method"] == "qq_outbox_claim"
    assert claim["request"]["fast_path"] is False
    assert fast_claim["status"] == "dry_run_ready"
    assert fast_claim["request"]["runtime_method"] == "qq_outbox_claim_fast"
    assert fast_claim["request"]["fast_path"] is True
    assert fast_ack["status"] == "dry_run_ready"
    assert fast_ack["request"]["route"] == "/qq/outbox/ack"
    assert fast_ack["request"]["runtime_method"] == "qq_outbox_ack_fast"
    assert fast_ack["request"]["fast_path"] is True


def test_desktop_proactive_ack_uses_enabled_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR: DryRunProactiveDeliveryRouteBackend(enabled=True)},
    )

    result = asyncio.run(desktop_proactive_ack(runtime, {"candidateId": "candidate-1", "action": "dismiss"}))

    assert result["status"] == "dry_run_ready"
    assert result["request"]["route"] == "/desktop/proactive/ack"
    assert result["request"]["runtime_method"] == "desktop_proactive_ack"
    assert result["request"]["payload"]["candidateId"] == "candidate-1"


def test_proactive_delivery_route_backend_rollback_restores_in_process_fast_claim(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        _claim_proactive_for_qq_outbox_sync=lambda payload: None,
        **{PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR: DryRunProactiveDeliveryRouteBackend(enabled=True)},
    )
    enqueue_qq_outbox_message(
        tmp_path,
        user_id="owner-1",
        message="hello",
        source="test",
        dedupe_key="rollback-fast-claim",
    )

    intercepted = qq_outbox_claim_fast(runtime, {"claim_id": "claim-intercepted"})
    delattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR)
    fallback = qq_outbox_claim_fast(runtime, {"claim_id": "claim-fallback"})

    assert intercepted["status"] == "dry_run_ready"
    assert fallback["message_claimed"] is True
    assert fallback["claim_id"] == "claim-fallback"
    assert fallback["notes"] == ["claimed"]
