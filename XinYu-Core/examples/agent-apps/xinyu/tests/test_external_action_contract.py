from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_external_action_contract import (
    EXTERNAL_ACTION_APPROVAL_OWNER,
    EXTERNAL_ACTION_FALLBACK_ADAPTER,
    EXTERNAL_ACTION_ROLLBACK,
    EXTERNAL_ACTION_STATE_OWNER,
    ExternalActionHarness,
    external_action_capabilities,
    external_action_execution_boundary,
    external_action_routes,
)
from xinyu_bridge_http_dispatch_table import GET_ROUTE_DISPATCH, POST_ROUTE_DISPATCH
from xinyu_bridge_http_routes import (
    get_route_requires_auth,
    is_known_get_route,
    is_known_post_route,
    post_route_requires_bridge_token,
)
from xinyu_serviceization_contracts import service_contract_by_id


def test_external_action_contract_matches_service_boundary_manifest() -> None:
    contract = service_contract_by_id("external_action")
    capabilities = external_action_capabilities()

    assert external_action_routes() == contract.api_routes
    assert tuple(capability.runtime_method for capability in capabilities) == contract.runtime_facade_methods


def test_external_action_contract_matches_http_dispatch_table() -> None:
    for capability in external_action_capabilities():
        if capability.http_method == "GET":
            assert is_known_get_route(capability.route)
            assert get_route_requires_auth(capability.route) is capability.requires_bridge_token
            assert GET_ROUTE_DISPATCH[capability.route].method == capability.runtime_method
            continue

        assert capability.http_method == "POST"
        assert is_known_post_route(capability.route)
        assert post_route_requires_bridge_token(capability.route) is capability.requires_bridge_token
        assert POST_ROUTE_DISPATCH[capability.route].method == capability.runtime_method


def test_external_action_contract_marks_private_desktop_owner_context() -> None:
    owner_context_routes = {
        capability.route
        for capability in external_action_capabilities()
        if capability.requires_owner_private_context
    }

    assert owner_context_routes == {
        "/desktop/private-ecosystem/pause",
        "/desktop/private-ecosystem/grant",
        "/desktop/private-ecosystem/tick",
        "/desktop/private-browser/action",
        "/desktop/private-desktop/observe",
        "/desktop/private-desktop/start",
        "/desktop/private-desktop/stop",
    }


def test_external_action_boundary_keeps_approval_outside_execution_adapter() -> None:
    boundary = external_action_execution_boundary()

    assert boundary.approval_owner == EXTERNAL_ACTION_APPROVAL_OWNER
    assert "route_method_already_approved_by_api_policy" in boundary.execution_adapter_allowed_inputs
    assert "payload_already_validated_by_route_contract" in boundary.execution_adapter_allowed_inputs
    assert "owner_private_context_only_when_route_requires_it" in boundary.execution_adapter_allowed_inputs
    assert "approve_or_reject_external_action_requests" in boundary.execution_adapter_denied_responsibilities
    assert "broaden_policy_scope" in boundary.execution_adapter_denied_responsibilities
    assert "create_new_execution_paths" in boundary.execution_adapter_denied_responsibilities
    assert "mutate_public_readiness_or_worklog" in boundary.execution_adapter_denied_responsibilities


def test_external_action_boundary_preserves_fallback_and_rollback_semantics() -> None:
    boundary = external_action_execution_boundary()

    assert boundary.fallback_adapter == EXTERNAL_ACTION_FALLBACK_ADAPTER
    assert boundary.rollback == EXTERNAL_ACTION_ROLLBACK
    assert boundary.fallback_semantics == (
        "fallback_adapter_maps_each_capability_to_the_existing_runtime_facade_method",
        "rollback_keeps_external_action_on_current_in_process_runtime_facades",
        "no_process_split_or_new_worker_execution_path_is_introduced",
    )


def test_external_action_harness_lifecycle_readiness_and_fallback() -> None:
    harness = ExternalActionHarness()

    initial = harness.readiness()
    assert initial.service_id == "external_action"
    assert initial.mode == "in_process"
    assert initial.started is False
    assert initial.ready is False
    assert initial.state_owner == EXTERNAL_ACTION_STATE_OWNER
    assert initial.fallback_adapter == EXTERNAL_ACTION_FALLBACK_ADAPTER
    assert initial.rollback == EXTERNAL_ACTION_ROLLBACK

    started = harness.start()
    assert started.started is True
    assert started.ready is True

    calls: list[str] = []

    def _method(name: str):
        def call(*args, **kwargs):
            calls.append(name)
            return {"method": name, "args": args, "kwargs": kwargs}

        return call

    runtime = SimpleNamespace(
        **{capability.runtime_method: _method(capability.runtime_method) for capability in external_action_capabilities()}
    )
    fallback = harness.fallback_adapter(runtime)

    assert set(fallback) == {capability.runtime_method for capability in external_action_capabilities()}
    for capability in external_action_capabilities():
        assert fallback[capability.runtime_method] is getattr(runtime, capability.runtime_method)

    assert fallback["external_plugin_manifest"]({"limit": 1})["method"] == "external_plugin_manifest"
    assert calls == ["external_plugin_manifest"]

    stopped = harness.stop()
    assert stopped.started is False
    assert stopped.ready is False
