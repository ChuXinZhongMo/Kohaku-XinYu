from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeRepairStatusProbeInput:
    health: dict[str, Any]
    source_path: Path


def runtime_repair_status_probe(
    probe_input: RuntimeRepairStatusProbeInput,
    *,
    source_digest_func: Callable[..., str],
    tcp_connect_func: Callable[..., bool],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    health = dict(probe_input.health)
    source_digest = source_digest_func(probe_input.source_path)
    running_digest = safe_str_func(health.get("source_digest"), "unknown")
    digest_ok = bool(running_digest and running_digest == source_digest)
    gateway_ok = tcp_connect_func("127.0.0.1", 6199)
    return {
        "health": health,
        "source_digest": source_digest,
        "running_digest": running_digest,
        "digest_ok": digest_ok,
        "gateway_ok": gateway_ok,
        "core_ok": bool(health.get("ok")) and digest_ok,
    }


__all__ = [
    "RuntimeRepairStatusProbeInput",
    "runtime_repair_status_probe",
]
