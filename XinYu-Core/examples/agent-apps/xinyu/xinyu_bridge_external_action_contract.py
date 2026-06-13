from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


EXTERNAL_ACTION_STATE_OWNER = "external_plugin_private_ecosystem_private_desktop_state"
EXTERNAL_ACTION_FALLBACK_ADAPTER = "in_process_runtime_route_methods"
EXTERNAL_ACTION_ROLLBACK = "route_external_actions_back_to_current_runtime_facades"
EXTERNAL_ACTION_APPROVAL_OWNER = "api_policy_http_route_boundary"
EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS = (
    "route_method_already_approved_by_api_policy",
    "payload_already_validated_by_route_contract",
    "bridge_token_context_already_verified_by_api_policy",
    "owner_private_context_only_when_route_requires_it",
)
EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES = (
    "approve_or_reject_external_action_requests",
    "broaden_policy_scope",
    "substitute_runtime_methods",
    "create_new_execution_paths",
    "bypass_owner_private_context",
    "mutate_public_readiness_or_worklog",
)
EXTERNAL_ACTION_FALLBACK_SEMANTICS = (
    "fallback_adapter_maps_each_capability_to_the_existing_runtime_facade_method",
    "rollback_keeps_external_action_on_current_in_process_runtime_facades",
    "no_process_split_or_new_worker_execution_path_is_introduced",
)


@dataclass(frozen=True, slots=True)
class ExternalActionCapability:
    route: str
    http_method: str
    runtime_method: str
    owner: str
    requires_bridge_token: bool
    requires_owner_private_context: bool
    execution_contract: str


@dataclass(frozen=True, slots=True)
class ExternalActionReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExternalActionExecutionBoundary:
    approval_owner: str
    execution_adapter_allowed_inputs: tuple[str, ...]
    execution_adapter_denied_responsibilities: tuple[str, ...]
    fallback_adapter: str
    rollback: str
    fallback_semantics: tuple[str, ...]


EXTERNAL_ACTION_CAPABILITIES = (
    ExternalActionCapability(
        route="/external/plugins",
        http_method="GET",
        runtime_method="external_plugin_manifest",
        owner="ExternalPluginService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="read plugin manifest/status only",
    ),
    ExternalActionCapability(
        route="/external/call",
        http_method="POST",
        runtime_method="external_plugin_call",
        owner="ExternalPluginService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="perform an approved external plugin call",
    ),
    ExternalActionCapability(
        route="/external/plugins/config",
        http_method="POST",
        runtime_method="external_plugin_config",
        owner="ExternalPluginService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="update plugin runtime control config",
    ),
    ExternalActionCapability(
        route="/external/plugins/install",
        http_method="POST",
        runtime_method="external_plugin_install",
        owner="ExternalPluginService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="install an approved external plugin package",
    ),
    ExternalActionCapability(
        route="/package/install",
        http_method="POST",
        runtime_method="package_install",
        owner="PackageExecutionService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="install approved Python packages",
    ),
    ExternalActionCapability(
        route="/desktop/private-ecosystem/snapshot",
        http_method="GET",
        runtime_method="desktop_private_ecosystem_snapshot",
        owner="PrivateEcosystemService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="read sanitized private ecosystem snapshot",
    ),
    ExternalActionCapability(
        route="/desktop/private-ecosystem/pause",
        http_method="POST",
        runtime_method="desktop_private_ecosystem_pause",
        owner="PrivateEcosystemService",
        requires_bridge_token=True,
        requires_owner_private_context=True,
        execution_contract="update owner-private autonomous share pause state",
    ),
    ExternalActionCapability(
        route="/desktop/private-ecosystem/grant",
        http_method="POST",
        runtime_method="desktop_private_ecosystem_grant",
        owner="PrivateEcosystemService",
        requires_bridge_token=True,
        requires_owner_private_context=True,
        execution_contract="sanitize and persist private ecosystem grant patch",
    ),
    ExternalActionCapability(
        route="/desktop/private-ecosystem/tick",
        http_method="POST",
        runtime_method="desktop_private_ecosystem_tick",
        owner="PrivateEcosystemService",
        requires_bridge_token=True,
        requires_owner_private_context=True,
        execution_contract="run one approved private ecosystem tick",
    ),
    ExternalActionCapability(
        route="/desktop/private-browser/snapshot",
        http_method="GET",
        runtime_method="desktop_private_browser_snapshot",
        owner="PrivateBrowserService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="read sanitized private browser snapshot",
    ),
    ExternalActionCapability(
        route="/desktop/private-browser/action",
        http_method="POST",
        runtime_method="desktop_private_browser_action",
        owner="PrivateBrowserService",
        requires_bridge_token=True,
        requires_owner_private_context=True,
        execution_contract="perform an approved private browser action through plugin adapter",
    ),
    ExternalActionCapability(
        route="/desktop/private-desktop/snapshot",
        http_method="GET",
        runtime_method="desktop_private_desktop_snapshot",
        owner="PrivateDesktopService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="read sanitized isolated desktop snapshot",
    ),
    ExternalActionCapability(
        route="/desktop/private-desktop/live-state",
        http_method="GET",
        runtime_method="desktop_private_desktop_live_state",
        owner="PrivateDesktopService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="read isolated desktop backend live state",
    ),
    ExternalActionCapability(
        route="/desktop/private-desktop/frame",
        http_method="GET",
        runtime_method="desktop_private_desktop_frame",
        owner="PrivateDesktopService",
        requires_bridge_token=True,
        requires_owner_private_context=False,
        execution_contract="read a bounded isolated desktop frame reference",
    ),
    ExternalActionCapability(
        route="/desktop/private-desktop/observe",
        http_method="POST",
        runtime_method="desktop_private_desktop_observe",
        owner="PrivateDesktopService",
        requires_bridge_token=True,
        requires_owner_private_context=True,
        execution_contract="perform owner-private isolated desktop observation",
    ),
    ExternalActionCapability(
        route="/desktop/private-desktop/start",
        http_method="POST",
        runtime_method="desktop_private_desktop_start",
        owner="PrivateDesktopService",
        requires_bridge_token=True,
        requires_owner_private_context=True,
        execution_contract="start owner-private isolated desktop backend",
    ),
    ExternalActionCapability(
        route="/desktop/private-desktop/stop",
        http_method="POST",
        runtime_method="desktop_private_desktop_stop",
        owner="PrivateDesktopService",
        requires_bridge_token=True,
        requires_owner_private_context=True,
        execution_contract="stop owner-private isolated desktop backend",
    ),
)


class ExternalActionHarness:
    def __init__(self) -> None:
        self._started = False

    def start(self) -> ExternalActionReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> ExternalActionReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> ExternalActionReadiness:
        return ExternalActionReadiness(
            service_id="external_action",
            mode="in_process",
            started=self._started,
            ready=self._started,
            state_owner=EXTERNAL_ACTION_STATE_OWNER,
            fallback_adapter=EXTERNAL_ACTION_FALLBACK_ADAPTER,
            rollback=EXTERNAL_ACTION_ROLLBACK,
            notes=(
                "approval_policy_remains_outside_execution_worker",
                "execution_adapter_performs_only_api_policy_approved_work",
            ),
        )

    @staticmethod
    def fallback_adapter(runtime: Any) -> dict[str, Callable[..., Any]]:
        return {
            capability.runtime_method: getattr(runtime, capability.runtime_method)
            for capability in EXTERNAL_ACTION_CAPABILITIES
        }


def external_action_capabilities() -> tuple[ExternalActionCapability, ...]:
    return EXTERNAL_ACTION_CAPABILITIES


def external_action_routes() -> tuple[str, ...]:
    return tuple(capability.route for capability in EXTERNAL_ACTION_CAPABILITIES)


def external_action_execution_boundary() -> ExternalActionExecutionBoundary:
    return ExternalActionExecutionBoundary(
        approval_owner=EXTERNAL_ACTION_APPROVAL_OWNER,
        execution_adapter_allowed_inputs=EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
        execution_adapter_denied_responsibilities=EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
        fallback_adapter=EXTERNAL_ACTION_FALLBACK_ADAPTER,
        rollback=EXTERNAL_ACTION_ROLLBACK,
        fallback_semantics=EXTERNAL_ACTION_FALLBACK_SEMANTICS,
    )
