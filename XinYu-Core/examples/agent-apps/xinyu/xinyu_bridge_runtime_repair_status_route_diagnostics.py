from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from xinyu_bridge_runtime_repair_status_probe import RuntimeRepairStatusProbeInput, runtime_repair_status_probe


@dataclass(frozen=True, slots=True)
class RuntimeRepairStatusDiagnostics:
    probe: dict[str, Any]
    digest_ok: bool
    gateway_ok: bool
    core_ok: bool


def build_runtime_repair_status_diagnostics(
    probe_input: RuntimeRepairStatusProbeInput,
    *,
    source_digest_func: Callable[..., str],
    tcp_connect_func: Callable[..., bool],
    safe_str_func: Callable[..., str],
) -> RuntimeRepairStatusDiagnostics:
    probe = runtime_repair_status_probe(
        probe_input,
        source_digest_func=source_digest_func,
        tcp_connect_func=tcp_connect_func,
        safe_str_func=safe_str_func,
    )
    return RuntimeRepairStatusDiagnostics(
        probe=probe,
        digest_ok=probe["digest_ok"],
        gateway_ok=probe["gateway_ok"],
        core_ok=probe["core_ok"],
    )


__all__ = [
    "RuntimeRepairStatusDiagnostics",
    "build_runtime_repair_status_diagnostics",
]
