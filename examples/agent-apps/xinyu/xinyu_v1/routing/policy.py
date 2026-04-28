"""Routing policy thresholds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    fast_path_max_salience: float = 0.25
    slow_path_min_risk: float = 0.45
    owner_pressure_slow_path: bool = True
    attachments_slow_path: bool = True
    learning_slow_path: bool = True
    conflict_slow_path: bool = True

