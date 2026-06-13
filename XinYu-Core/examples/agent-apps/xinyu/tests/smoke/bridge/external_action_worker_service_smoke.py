from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
ROOT_TEXT = str(ROOT)
if ROOT_TEXT not in sys.path:
    sys.path.insert(0, ROOT_TEXT)

from xinyu_bridge_external_action_backend import ApprovedExternalActionRequest, HttpExternalActionExecutionBackend
from xinyu_bridge_external_action_worker_service import (
    EXTERNAL_ACTION_WORKER_SERVICE_MODE,
    ExternalActionWorkerService,
    external_action_worker_service_transport,
)


def _run_smoke() -> None:
    service = ExternalActionWorkerService()
    health = service.handle_request("GET", "/health")
    assert health["ok"] is True, "external action worker service health is not ready"
    assert health["mode"] == EXTERNAL_ACTION_WORKER_SERVICE_MODE, "worker service mode changed"
    assert health["executes_runtime"] is False, "dry-run worker service must not execute runtime actions"

    backend = HttpExternalActionExecutionBackend(
        endpoint="http://127.0.0.1:8788",
        enabled=True,
        transport=external_action_worker_service_transport(service),
    )
    request = ApprovedExternalActionRequest(
        route="/external/call",
        http_method="POST",
        runtime_method="external_plugin_call",
        payload={"plugin": "status"},
        approval_id="smoke-approval",
    )
    result = asyncio.run(
        backend.execute(
            SimpleNamespace(external_plugin_call=lambda payload: {"executed": payload}),
            request,
        )
    )

    assert result["status"] == "dry_run_accepted", "worker service did not accept approved request shape"
    assert result["executed"] is False, "dry-run worker service must not execute external actions"
    assert result["worker_response"]["dry_run"] is True, "worker response lost dry-run marker"
    assert result["request"]["approval_id"] == "smoke-approval", "approval id changed"


def test_external_action_worker_service_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("external_action_worker_service_smoke failed")
        if str(exc):
            print(f"- {exc}")
        return 1
    print("external_action_worker_service_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
