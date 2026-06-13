from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from xinyu_bridge_health_diagnostics_service import (
    HEALTH_DIAGNOSTICS_ROLLBACK,
    HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_IDS,
    HealthDiagnosticsServiceHealthProvider,
)
from xinyu_bridge_health_service_providers import health_diagnostics_default_service_health_providers


HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR = "_health_diagnostics_provider_registry"
HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_IN_PROCESS_MODE = "in_process_provider_registry"
HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_HTTP_MODE = "http_provider_registry"
HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_ROLLBACK = "unset_health_diagnostics_provider_registry_use_in_process"


class HealthDiagnosticsProviderRegistry(Protocol):
    mode: str

    def providers(self, runtime: Any) -> tuple[HealthDiagnosticsServiceHealthProvider, ...]:
        ...


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsProviderRegistryReadiness:
    service_id: str
    mode: str
    enabled: bool
    ready: bool
    endpoint: str
    rollback: str
    runtime_attr: str
    contract_rollback: str
    provider_count: int
    notes: tuple[str, ...] = ()


class InProcessHealthDiagnosticsProviderRegistry:
    mode = HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_IN_PROCESS_MODE

    def providers(self, runtime: Any) -> tuple[HealthDiagnosticsServiceHealthProvider, ...]:
        return health_diagnostics_default_service_health_providers(runtime)

    def readiness(self, runtime: Any) -> HealthDiagnosticsProviderRegistryReadiness:
        return HealthDiagnosticsProviderRegistryReadiness(
            service_id="health_diagnostics",
            mode=self.mode,
            enabled=True,
            ready=True,
            endpoint="",
            rollback=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_ROLLBACK,
            runtime_attr=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR,
            contract_rollback=HEALTH_DIAGNOSTICS_ROLLBACK,
            provider_count=len(self.providers(runtime)),
            notes=("in_process_provider_registry_fallback",),
        )


HealthRegistryTransport = Callable[[str, str, int], dict[str, Any]]


class HttpHealthDiagnosticsProviderRegistry:
    mode = HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_HTTP_MODE

    def __init__(
        self,
        *,
        endpoint: str,
        enabled: bool = False,
        provider_ids: tuple[str, ...] = HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_IDS,
        timeout_seconds: int = 5,
        transport: HealthRegistryTransport | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.enabled = bool(enabled)
        self.provider_ids = tuple(provider_ids)
        self.timeout_seconds = timeout_seconds
        self._transport = _default_json_transport if transport is None else transport

    def providers(self, runtime: Any) -> tuple[HealthDiagnosticsServiceHealthProvider, ...]:
        del runtime
        return tuple(
            HealthDiagnosticsServiceHealthProvider(
                service_id,
                lambda received_runtime, bound_service_id=service_id: self._provider_health(bound_service_id),
            )
            for service_id in self.provider_ids
        )

    def readiness(self, runtime: Any) -> HealthDiagnosticsProviderRegistryReadiness:
        del runtime
        return HealthDiagnosticsProviderRegistryReadiness(
            service_id="health_diagnostics",
            mode=self.mode,
            enabled=self.enabled,
            ready=self.enabled and bool(self.endpoint) and bool(self.provider_ids),
            endpoint=self.endpoint,
            rollback=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_ROLLBACK,
            runtime_attr=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR,
            contract_rollback=HEALTH_DIAGNOSTICS_ROLLBACK,
            provider_count=len(self.provider_ids),
            notes=("http_provider_registry",),
        )

    def _provider_health(self, service_id: str) -> dict[str, Any]:
        if not self.readiness(None).ready:
            return {
                "service_id": service_id,
                "ok": False,
                "ready": False,
                "status": "degraded",
                "payload": {},
                "notes": ("http_provider_registry_not_ready",),
            }
        response = self._transport(
            "GET",
            f"{self.endpoint}/health/services/{service_id}",
            self.timeout_seconds,
        )
        return response if response else {
            "service_id": service_id,
            "ok": False,
            "ready": False,
            "status": "unknown",
            "payload": {},
            "notes": ("empty_http_provider_response",),
        }


IN_PROCESS_HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY = InProcessHealthDiagnosticsProviderRegistry()


def health_diagnostics_provider_registry_for_runtime(
    runtime: Any,
    *,
    explicit_registry: HealthDiagnosticsProviderRegistry | None = None,
) -> HealthDiagnosticsProviderRegistry:
    if explicit_registry is not None:
        return explicit_registry
    runtime_registry = getattr(runtime, HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR, None)
    if runtime_registry is not None:
        return runtime_registry
    return IN_PROCESS_HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY


def health_diagnostics_provider_registry_readiness(
    runtime: Any,
    *,
    explicit_registry: HealthDiagnosticsProviderRegistry | None = None,
) -> HealthDiagnosticsProviderRegistryReadiness:
    registry = health_diagnostics_provider_registry_for_runtime(runtime, explicit_registry=explicit_registry)
    readiness = getattr(registry, "readiness", None)
    if callable(readiness):
        return readiness(runtime)
    providers = tuple(registry.providers(runtime))
    return HealthDiagnosticsProviderRegistryReadiness(
        service_id="health_diagnostics",
        mode=getattr(registry, "mode", type(registry).__name__),
        enabled=True,
        ready=bool(providers),
        endpoint="",
        rollback=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_ROLLBACK,
        runtime_attr=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR,
        contract_rollback=HEALTH_DIAGNOSTICS_ROLLBACK,
        provider_count=len(providers),
        notes=("runtime_provider_registry",),
    )


def health_diagnostics_provider_registry_providers(
    runtime: Any,
) -> tuple[HealthDiagnosticsServiceHealthProvider, ...]:
    registry = health_diagnostics_provider_registry_for_runtime(runtime)
    return tuple(registry.providers(runtime))


def _default_json_transport(method: str, url: str, timeout_seconds: int) -> dict[str, Any]:
    request = Request(url, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except URLError as exc:
        return {
            "service_id": "unknown_service",
            "ok": False,
            "ready": False,
            "status": "transport_error",
            "payload": {"error": str(exc)},
            "notes": ("http_provider_registry_transport_error",),
        }
    if not body.strip():
        return {}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {
            "service_id": "unknown_service",
            "ok": False,
            "ready": False,
            "status": "invalid_worker_response",
            "payload": {},
            "notes": ("http_provider_registry_invalid_json",),
        }
    return parsed if isinstance(parsed, dict) else {}


__all__ = [
    "HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_HTTP_MODE",
    "HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_IN_PROCESS_MODE",
    "HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_ROLLBACK",
    "HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR",
    "HealthDiagnosticsProviderRegistry",
    "HealthDiagnosticsProviderRegistryReadiness",
    "HttpHealthDiagnosticsProviderRegistry",
    "InProcessHealthDiagnosticsProviderRegistry",
    "health_diagnostics_provider_registry_for_runtime",
    "health_diagnostics_provider_registry_providers",
    "health_diagnostics_provider_registry_readiness",
]
