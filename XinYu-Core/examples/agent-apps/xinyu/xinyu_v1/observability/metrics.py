"""Minimal metrics sink."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class InMemoryMetrics:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    observations: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def increment(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        self.counters[_key(name, tags)] += value

    def observe(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self.observations[_key(name, tags)].append(float(value))

    def snapshot(self) -> dict[str, Any]:
        return {"counters": dict(self.counters), "observations": {k: list(v) for k, v in self.observations.items()}}


def _key(name: str, tags: dict[str, str] | None) -> str:
    if not tags:
        return name
    suffix = ",".join(f"{key}={value}" for key, value in sorted(tags.items()))
    return f"{name}|{suffix}"

