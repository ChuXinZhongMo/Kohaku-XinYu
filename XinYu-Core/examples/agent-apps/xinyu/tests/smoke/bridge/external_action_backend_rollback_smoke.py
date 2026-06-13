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
    DISABLED_EXTERNAL_ACTION_BACKEND,
    EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
    EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE,
    EXTERNAL_ACTION_BACKEND_ROLLBACK,
    EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
    ApprovedExternalActionRequest,
    DryRunExternalActionExecutionBackend,
    external_action_backend_for_runtime,
)
from xinyu_bridge_external_action_contract import ExternalActionHarness, external_action_capabilities


def _approved_request() -> ApprovedExternalActionRequest:
    return ApprovedExternalActionRequest(
        route="/external/call",
        http_method="POST",
        runtime_method="external_plugin_call",
        payload={"plugin": "status", "args": {"target": "self"}},
        query={"trace": "rollback-smoke"},
        approval_id="external-action-rollback-smoke",
    )


def _check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _run_smoke() -> None:
    failures: list[str] = []
    runtime_calls: list[dict[str, Any]] = []

    def _method(name: str):
        def call(payload: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> dict[str, Any]:
            runtime_calls.append(
                {
                    "method": name,
                    "payload": dict(payload or {}),
                    "args": args,
                    "kwargs": kwargs,
                }
            )
            return {
                "accepted": True,
                "source": "in_process_runtime_facade",
                "method": name,
                "payload": dict(payload or {}),
            }

        return call

    enabled_backend = DryRunExternalActionExecutionBackend(enabled=True)
    runtime = SimpleNamespace(
        **{capability.runtime_method: _method(capability.runtime_method) for capability in external_action_capabilities()},
        **{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: enabled_backend},
    )

    _check(
        failures,
        external_action_backend_for_runtime(runtime) is enabled_backend,
        "runtime backend attr was not selected",
    )
    enabled_response = asyncio.run(enabled_backend.execute(runtime, _approved_request()))
    _check(failures, enabled_response["mode"] == EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE, "enabled mode changed")
    _check(failures, enabled_response["status"] == "dry_run_ready", "enabled dry-run status changed")
    _check(failures, enabled_response["executed"] is False, "dry-run backend executed approved work")
    _check(failures, runtime_calls == [], "runtime facade ran while backend dry-run attr was set")

    delattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR)
    fallback_backend = external_action_backend_for_runtime(runtime)
    _check(failures, fallback_backend is DISABLED_EXTERNAL_ACTION_BACKEND, "runtime attr removal did not restore fallback backend")
    disabled_response = asyncio.run(fallback_backend.execute(runtime, _approved_request()))
    _check(failures, disabled_response["mode"] == EXTERNAL_ACTION_BACKEND_DISABLED_MODE, "disabled fallback mode changed")
    _check(failures, disabled_response["status"] == "backend_disabled", "disabled fallback status changed")
    _check(failures, disabled_response["rollback"] == EXTERNAL_ACTION_BACKEND_ROLLBACK, "backend rollback marker changed")
    _check(failures, disabled_response["executed"] is False, "disabled fallback backend executed approved work")
    _check(failures, runtime_calls == [], "disabled backend invoked runtime facade")

    facade_map = ExternalActionHarness.fallback_adapter(runtime)
    _check(failures, facade_map["external_plugin_call"] is runtime.external_plugin_call, "fallback facade identity changed")
    facade_result = facade_map["external_plugin_call"]({"plugin": "status"})
    _check(failures, facade_result["source"] == "in_process_runtime_facade", "fallback facade result changed")
    _check(failures, facade_result["method"] == "external_plugin_call", "fallback facade method changed")
    _check(
        failures,
        runtime_calls == [
            {
                "method": "external_plugin_call",
                "payload": {"plugin": "status"},
                "args": (),
                "kwargs": {},
            }
        ],
        "fallback facade did not run exactly once",
    )

    if failures:
        raise AssertionError("\n".join(failures))


def test_external_action_backend_rollback_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("external_action_backend_rollback_smoke failed")
        for failure in str(exc).splitlines():
            print(f"- {failure}")
        return 1
    print("external_action_backend_rollback_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
