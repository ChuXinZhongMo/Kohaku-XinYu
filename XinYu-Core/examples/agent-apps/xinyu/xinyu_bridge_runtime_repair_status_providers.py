from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_bridge_health_snapshot import runtime_health_snapshot


@dataclass(frozen=True, slots=True)
class RuntimeRepairStatusProviders:
    owner_matches_func: Callable[[dict[str, Any]], bool]
    health_snapshot_func: Callable[[], dict[str, Any]]
    source_path: Path
    xinyu_dir: Path
    memory_root: Path
    final_reply_guard_func: Callable[..., tuple[str, Any]]
    publish_chat_finished_func: Callable[..., Any]


def runtime_repair_status_service_providers(runtime: Any) -> RuntimeRepairStatusProviders:
    return RuntimeRepairStatusProviders(
        owner_matches_func=runtime._owner_private_payload_matches,
        health_snapshot_func=lambda: runtime_health_snapshot(runtime),
        source_path=Path(runtime.xinyu_dir) / "xinyu_core_bridge.py",
        xinyu_dir=Path(runtime.xinyu_dir),
        memory_root=Path(runtime.memory_root),
        final_reply_guard_func=runtime.speech_controller.final_reply_guard,
        publish_chat_finished_func=runtime._desktop_publish_chat_finished,
    )


__all__ = [
    "RuntimeRepairStatusProviders",
    "runtime_repair_status_service_providers",
]
