from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SMOKE_DIR = Path(__file__).resolve().parent
if str(SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(SMOKE_DIR))

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_external_action_backend import (
    ApprovedExternalActionRequest,
    DryRunExternalActionExecutionBackend,
)
from xinyu_bridge_external_action_contract import (
    EXTERNAL_ACTION_APPROVAL_OWNER,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
    ExternalActionHarness,
    external_action_capabilities,
    external_action_execution_boundary,
)
from xinyu_bridge_http_dispatch_table import GET_ROUTE_DISPATCH, POST_ROUTE_DISPATCH
from xinyu_bridge_http_routes import (
    get_route_requires_auth,
    is_known_get_route,
    is_known_post_route,
    post_route_requires_bridge_token,
)


def _check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _run_smoke() -> None:
    failures: list[str] = []
    capabilities = external_action_capabilities()
    owner_private_routes = {
        "/desktop/private-ecosystem/pause",
        "/desktop/private-ecosystem/grant",
        "/desktop/private-ecosystem/tick",
        "/desktop/private-browser/action",
        "/desktop/private-desktop/observe",
        "/desktop/private-desktop/start",
        "/desktop/private-desktop/stop",
    }

    for capability in capabilities:
        if capability.http_method == "GET":
            _check(failures, is_known_get_route(capability.route), f"{capability.route}: GET route missing")
            _check(
                failures,
                get_route_requires_auth(capability.route) is capability.requires_bridge_token,
                f"{capability.route}: GET auth contract changed",
            )
            _check(
                failures,
                GET_ROUTE_DISPATCH[capability.route].method == capability.runtime_method,
                f"{capability.route}: GET dispatch method changed",
            )
        else:
            _check(failures, capability.http_method == "POST", f"{capability.route}: unexpected method")
            _check(failures, is_known_post_route(capability.route), f"{capability.route}: POST route missing")
            _check(
                failures,
                post_route_requires_bridge_token(capability.route) is capability.requires_bridge_token,
                f"{capability.route}: POST auth contract changed",
            )
            _check(
                failures,
                POST_ROUTE_DISPATCH[capability.route].method == capability.runtime_method,
                f"{capability.route}: POST dispatch method changed",
            )
        _check(
            failures,
            capability.requires_owner_private_context is (capability.route in owner_private_routes),
            f"{capability.route}: owner-private context contract changed",
        )

    boundary = external_action_execution_boundary()
    _check(failures, boundary.approval_owner == EXTERNAL_ACTION_APPROVAL_OWNER, "approval owner changed")
    _check(
        failures,
        boundary.execution_adapter_allowed_inputs == EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
        "allowed execution adapter inputs changed",
    )
    _check(
        failures,
        boundary.execution_adapter_denied_responsibilities == EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
        "denied execution adapter responsibilities changed",
    )
    _check(
        failures,
        "approve_or_reject_external_action_requests" in boundary.execution_adapter_denied_responsibilities,
        "execution adapter can now approve/reject requests",
    )

    calls: list[dict[str, Any]] = []

    def desktop_private_desktop_start(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(dict(payload))
        return {"started": True}

    runtime = SimpleNamespace(desktop_private_desktop_start=desktop_private_desktop_start)
    request = ApprovedExternalActionRequest(
        route="/desktop/private-desktop/start",
        http_method="POST",
        runtime_method="desktop_private_desktop_start",
        payload={"mode": "observe-only"},
        approved_by=EXTERNAL_ACTION_APPROVAL_OWNER,
        approval_id="owner-private-approval-smoke",
        bridge_token_context="verified_by_api_policy",
        owner_private_context=True,
    )
    response = asyncio.run(DryRunExternalActionExecutionBackend(enabled=True).execute(runtime, request))

    _check(failures, response["executed"] is False, "dry-run backend executed owner-private action")
    _check(failures, response["runtime_facade_present"] is True, "runtime facade presence was not detected")
    _check(failures, response["request"] == request.dry_run_shape(), "approved request shape changed")
    _check(failures, response["request"]["owner_private_context"] is True, "owner-private context not preserved")
    _check(
        failures,
        response["approved_request_inputs"] == EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
        "backend allowed-input contract changed",
    )
    _check(
        failures,
        response["denied_policy_responsibilities"] == EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
        "backend denied-responsibility contract changed",
    )
    _check(failures, calls == [], "dry-run backend invoked owner-private runtime facade")

    harness = ExternalActionHarness()
    _check(failures, harness.start().ready is True, "external action harness no longer becomes ready after start")
    _check(failures, harness.stop().ready is False, "external action harness no longer stops cleanly")

    if failures:
        raise AssertionError("\n".join(failures))


def test_external_action_execution_boundary_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("external_action_execution_boundary_smoke failed")
        for failure in str(exc).splitlines():
            print(f"- {failure}")
        return 1
    print("external_action_execution_boundary_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
