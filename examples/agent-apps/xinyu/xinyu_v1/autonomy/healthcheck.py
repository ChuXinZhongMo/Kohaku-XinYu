"""Runtime healthcheck aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from ..types import HealthState, JSONValue, ServiceHealth


@dataclass(frozen=True, slots=True)
class HealthReport:
    state: HealthState
    services: tuple[ServiceHealth, ...]

    def to_json(self) -> dict[str, JSONValue]:
        return {"state": self.state.value, "services": [service.to_json() for service in self.services]}


def aggregate_health(services: tuple[ServiceHealth, ...]) -> HealthReport:
    if any(service.state is HealthState.FAILED for service in services):
        state = HealthState.FAILED
    elif any(service.state in {HealthState.DEGRADED, HealthState.BLOCKED} for service in services):
        state = HealthState.DEGRADED
    else:
        state = HealthState.OK
    return HealthReport(state=state, services=services)

