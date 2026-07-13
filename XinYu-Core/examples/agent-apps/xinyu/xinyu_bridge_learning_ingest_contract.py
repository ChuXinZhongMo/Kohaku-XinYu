from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class LearningIngestRouteContract:
    route: str
    runtime_method: str
    capability: str
    route_backend_supported: bool = True


@dataclass(frozen=True, slots=True)
class LearningIngestBoundaryContract:
    service_id: str
    local_only: bool
    process_split_candidate: bool
    capabilities: tuple[str, ...]
    routes: tuple[LearningIngestRouteContract, ...]
    runtime_methods: tuple[str, ...]
    state_owner: str
    fallback_adapter: str
    rollback: str
    reviewed_memory_gate: str
    sidecar_ingest: str
    readiness_probe: str
    harness: str


LEARNING_INGEST_ROUTES = (
    LearningIngestRouteContract(
        route="/learning/ingest",
        runtime_method="learning_ingest",
        capability="stage_learning_material",
    ),
    LearningIngestRouteContract(
        route="/learning/study",
        runtime_method="learning_study",
        capability="run_reviewed_learning_chain",
    ),
    LearningIngestRouteContract(
        route="/learning/observe",
        runtime_method="learning_observe",
        capability="record_learning_observation",
    ),
    LearningIngestRouteContract(
        route="/sticker/import",
        runtime_method="sticker_import",
        capability="import_sticker_learning_material",
        route_backend_supported=False,
    ),
)

LEARNING_INGEST_CONTRACT = LearningIngestBoundaryContract(
    service_id="learning_ingest",
    local_only=True,
    process_split_candidate=False,
    capabilities=(
        "learning_write_entry",
        "reviewed_memory_gate",
        "sidecar_ingest",
        "study_snapshot",
        "observation_record",
        "sticker_material_import",
    ),
    routes=LEARNING_INGEST_ROUTES,
    runtime_methods=tuple(route.runtime_method for route in LEARNING_INGEST_ROUTES),
    state_owner="LearningService owns local learning writes through the runtime facade; memory event sourcing owns append-only learning sidecars.",
    fallback_adapter=(
        "Map only existing runtime facade methods: learning_ingest, learning_study, "
        "learning_observe, sticker_import."
    ),
    rollback="Disable caller route use or sidecar scheduling; keep existing local files and event-sourced records intact.",
    reviewed_memory_gate="Stable memory promotion remains blocked behind existing reviewed-memory gates; ingest stages candidates/material only.",
    sidecar_ingest="Codex learning followup runs the current local study chain under the runtime turn lock and writes trace-only status.",
    readiness_probe="Local readiness checks contract shape, runtime facade availability, route alignment, and harness lifecycle only.",
    harness="LearningIngestLocalHarness",
)


def learning_ingest_contract() -> LearningIngestBoundaryContract:
    return LEARNING_INGEST_CONTRACT


def learning_ingest_route_map() -> dict[str, str]:
    return {route.route: route.runtime_method for route in LEARNING_INGEST_ROUTES}


def learning_ingest_route_backend_route_map() -> dict[str, str]:
    return {
        route.route: route.runtime_method
        for route in LEARNING_INGEST_ROUTES
        if route.route_backend_supported
    }


def learning_ingest_local_utility_route_map() -> dict[str, str]:
    return {
        route.route: route.runtime_method
        for route in LEARNING_INGEST_ROUTES
        if not route.route_backend_supported
    }


def learning_ingest_fallback_adapter(runtime: Any) -> dict[str, Callable[[dict[str, Any]], Any]]:
    """Expose only the already-public runtime facade methods for local fallback tests."""
    return {
        route.route: getattr(runtime, route.runtime_method)
        for route in LEARNING_INGEST_ROUTES
    }


@dataclass(slots=True)
class LearningIngestLocalHarness:
    runtime: Any
    started: bool = False
    stopped: bool = False

    def start(self) -> None:
        self.started = True
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True

    def readiness(self) -> dict[str, Any]:
        missing = tuple(
            method
            for method in LEARNING_INGEST_CONTRACT.runtime_methods
            if not callable(getattr(self.runtime, method, None))
        )
        return {
            "service_id": LEARNING_INGEST_CONTRACT.service_id,
            "local_only": LEARNING_INGEST_CONTRACT.local_only,
            "process_split_candidate": LEARNING_INGEST_CONTRACT.process_split_candidate,
            "started": self.started,
            "stopped": self.stopped,
            "ready": self.started and not self.stopped and not missing,
            "missing_runtime_methods": missing,
            "routes": learning_ingest_route_map(),
        }

    async def fallback(self, route: str, payload: dict[str, Any]) -> Any:
        adapter = learning_ingest_fallback_adapter(self.runtime)
        if route not in adapter:
            raise KeyError(route)
        result = adapter[route](payload)
        if inspect.isawaitable(result):
            return await result
        return result
