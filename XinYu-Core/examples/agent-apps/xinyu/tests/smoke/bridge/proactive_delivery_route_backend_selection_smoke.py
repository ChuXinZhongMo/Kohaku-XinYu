from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

SMOKE_DIR = Path(__file__).resolve().parent
if str(SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(SMOKE_DIR))

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_desktop_proactive_routes import desktop_proactive_ack
from xinyu_bridge_proactive_delivery_route_backend import (
    PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR,
    DryRunProactiveDeliveryRouteBackend,
)
from xinyu_bridge_proactive_delivery_routes import proactive_ack, qq_outbox_ack_fast, qq_outbox_claim_fast
from xinyu_qq_outbox import enqueue_qq_outbox_message


def _check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        memory_root=root / "memory",
        _closed=False,
        _sessions={},
        _claim_proactive_for_qq_outbox_sync=lambda payload: None,
        **{PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR: DryRunProactiveDeliveryRouteBackend(enabled=True)},
    )


def _run_smoke() -> None:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-route-backend-") as tmp:
        root = Path(tmp)
        runtime = _runtime(root)

        claim = qq_outbox_claim_fast(runtime, {"claim_id": "claim-fast"})
        _check(failures, claim["status"] == "dry_run_ready", "qq_outbox_claim_fast did not use backend")
        _check(failures, claim["request"]["route"] == "/qq/outbox/claim", "claim route changed")
        _check(failures, claim["request"]["fast_path"] is True, "claim fast_path flag missing")

        ack = qq_outbox_ack_fast(runtime, {"message_id": "proactive:request-1", "claim_id": "claim-fast"})
        _check(failures, ack["status"] == "dry_run_ready", "qq_outbox_ack_fast did not use backend")
        _check(failures, ack["request"]["route"] == "/qq/outbox/ack", "ack route changed")

        proactive_ack_result = asyncio.run(proactive_ack(runtime, {"claim_id": "claim-async", "ack_status": "sent"}))
        _check(
            failures,
            proactive_ack_result["request"]["route"] == "/proactive/ack",
            "proactive_ack route changed",
        )

        desktop_ack = asyncio.run(desktop_proactive_ack(runtime, {"candidateId": "candidate-1", "action": "dismiss"}))
        _check(
            failures,
            desktop_ack["request"]["route"] == "/desktop/proactive/ack",
            "desktop proactive ack route changed",
        )

        enqueue_qq_outbox_message(
            root,
            user_id="owner-1",
            message="rollback message",
            source="route-backend-smoke",
            dedupe_key="route-backend-smoke",
        )
        delattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR)
        fallback = qq_outbox_claim_fast(runtime, {"claim_id": "claim-fallback"})
        _check(failures, fallback["message_claimed"] is True, "runtime attr rollback did not restore in-process claim")
        _check(failures, fallback["claim_id"] == "claim-fallback", "fallback claim_id changed")

    if failures:
        raise AssertionError("\n".join(failures))


def test_proactive_delivery_route_backend_selection_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("proactive_delivery_route_backend_selection_smoke failed")
        for failure in str(exc).splitlines():
            print(f"- {failure}")
        return 1
    print("proactive_delivery_route_backend_selection_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
