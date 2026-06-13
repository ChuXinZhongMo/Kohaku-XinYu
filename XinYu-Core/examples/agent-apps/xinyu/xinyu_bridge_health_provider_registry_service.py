from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

from xinyu_bridge_health_diagnostics_service import HEALTH_DIAGNOSTICS_ROLLBACK
from xinyu_bridge_health_provider_registry import (
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_IN_PROCESS_MODE,
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR,
    HealthRegistryTransport,
)
from xinyu_bridge_health_service_providers import service_health_provider_ids


HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE = "health_diagnostics_provider_registry_service_dry_run"
HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROUTES = (
    "/health",
    "/health/services/{service_id}",
)
HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROLLBACK = (
    "stop_health_provider_registry_service_and_unset_provider_registry"
)


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsProviderRegistryServiceReadiness:
    service_id: str
    mode: str
    ready: bool
    dry_run: bool
    mutates_state: bool
    routes: tuple[str, ...]
    provider_ids: tuple[str, ...]
    provider_count: int
    fallback_registry: str
    rollback: str
    contract_rollback: str
    runtime_attr: str
    notes: tuple[str, ...] = ()


class HealthDiagnosticsProviderRegistryService:
    def __init__(
        self,
        *,
        ready: bool = True,
        provider_ids: tuple[str, ...] | None = None,
        service_payloads: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.ready = bool(ready)
        self.provider_ids = tuple(provider_ids or service_health_provider_ids())
        self._service_payloads = {
            str(service_id): dict(payload)
            for service_id, payload in dict(service_payloads or {}).items()
        }

    def readiness(self) -> HealthDiagnosticsProviderRegistryServiceReadiness:
        return HealthDiagnosticsProviderRegistryServiceReadiness(
            service_id="health_diagnostics",
            mode=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE,
            ready=self.ready and bool(self.provider_ids),
            dry_run=True,
            mutates_state=False,
            routes=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROUTES,
            provider_ids=self.provider_ids,
            provider_count=len(self.provider_ids),
            fallback_registry=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_IN_PROCESS_MODE,
            rollback=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROLLBACK,
            contract_rollback=HEALTH_DIAGNOSTICS_ROLLBACK,
            runtime_attr=HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR,
            notes=("dry_run_provider_registry_service", "does_not_read_or_write_runtime_state"),
        )

    def handle_request(self, method: str, path: str) -> dict[str, Any]:
        normalized_method = str(method or "").upper()
        normalized_path = _normalize_path(path)

        if normalized_method == "GET" and normalized_path == "/health":
            readiness = self.readiness()
            return {"ok": readiness.ready, **asdict(readiness)}

        service_id = _service_id_from_path(normalized_path)
        if normalized_method == "GET" and service_id:
            return self._service_health(service_id)

        if normalized_path == "/health" or normalized_path.startswith("/health/services/"):
            return _error_response("method_not_allowed", http_status=405)
        return _error_response("not_found", http_status=404)

    def _service_health(self, service_id: str) -> dict[str, Any]:
        if service_id not in self.provider_ids:
            return {
                "service_id": service_id,
                "ok": False,
                "ready": False,
                "status": "missing_provider",
                "payload": {},
                "http_status": 404,
                "notes": ("provider_registry_service_unknown_service",),
            }
        if not self.readiness().ready:
            return {
                "service_id": service_id,
                "ok": False,
                "ready": False,
                "status": "degraded",
                "payload": {
                    "fallback_registry": HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_IN_PROCESS_MODE,
                    "dry_run": True,
                },
                "http_status": 503,
                "notes": ("provider_registry_service_not_ready",),
            }

        payload = dict(self._service_payloads.get(service_id, {}))
        payload.setdefault("source", HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE)
        payload.setdefault("dry_run", True)
        payload.setdefault("provider_registry_service", True)
        return {
            "service_id": service_id,
            "ok": True,
            "ready": True,
            "status": "ok",
            "payload": payload,
            "notes": (
                "dry_run_provider_registry_service",
                "runtime_state_not_read",
                "runtime_state_not_written",
            ),
        }


def health_provider_registry_service_transport(
    service: HealthDiagnosticsProviderRegistryService,
) -> HealthRegistryTransport:
    def transport(method: str, url: str, timeout_seconds: int) -> dict[str, Any]:
        del timeout_seconds
        return service.handle_request(method, urlparse(url).path)

    return transport


def _normalize_path(path: str) -> str:
    parsed = urlparse(str(path or ""))
    normalized = unquote(parsed.path or "/")
    if normalized != "/" and normalized.endswith("/"):
        return normalized[:-1]
    return normalized


def _service_id_from_path(path: str) -> str:
    prefix = "/health/services/"
    if not path.startswith(prefix):
        return ""
    return path[len(prefix) :].strip()


def _error_response(status: str, *, http_status: int) -> dict[str, Any]:
    return {
        "ok": False,
        "ready": False,
        "service_id": "health_diagnostics",
        "status": status,
        "http_status": http_status,
    }


__all__ = [
    "HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE",
    "HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROUTES",
    "HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROLLBACK",
    "HealthDiagnosticsProviderRegistryService",
    "HealthDiagnosticsProviderRegistryServiceReadiness",
    "health_provider_registry_service_transport",
]
