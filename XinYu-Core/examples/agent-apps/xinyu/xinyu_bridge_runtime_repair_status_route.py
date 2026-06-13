from __future__ import annotations

import socket
import time
from collections.abc import Callable
from typing import Any

from xinyu_bridge_memory_snapshot import memory_snapshot
from xinyu_bridge_runtime_repair_status_probe import RuntimeRepairStatusProbeInput
from xinyu_bridge_runtime_repair_status_providers import (
    RuntimeRepairStatusProviders,
    runtime_repair_status_service_providers,
)
from xinyu_bridge_runtime_repair_status_response import (
    runtime_repair_status_notes,
)
from xinyu_bridge_runtime_repair_status_route_completion import complete_runtime_repair_status_turn
from xinyu_bridge_runtime_repair_status_route_diagnostics import build_runtime_repair_status_diagnostics
from xinyu_bridge_runtime_repair_status_route_payload import build_runtime_repair_status_route_payload
from xinyu_bridge_runtime_repair_status_route_visibility import (
    build_runtime_repair_status_visibility,
    looks_like_runtime_repair_status_question,
)
from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_bridge_values import safe_str
from xinyu_runtime_presence import record_turn_finished
from xinyu_runtime_security import source_file_digest
from xinyu_sent_reply_index import visible_text_hash
from xinyu_turn_coherence import finish_turn_coherence


def tcp_connect(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def maybe_handle_runtime_repair_status_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    status_question_func: Callable[[str], bool] = looks_like_runtime_repair_status_question,
    providers_func: Callable[[Any], RuntimeRepairStatusProviders] = runtime_repair_status_service_providers,
    source_digest_func: Callable[..., str] = source_file_digest,
    tcp_connect_func: Callable[..., bool] = tcp_connect,
    memory_snapshot_func: Callable[..., dict[str, Any]] = memory_snapshot,
    finish_coherence_func: Callable[..., dict[str, Any]] = finish_turn_coherence,
    clock_func: Callable[[], float] = time.perf_counter,
    record_finished_func: Callable[..., Any] = record_turn_finished,
    visible_hash_func: Callable[[str], str] = visible_text_hash,
    timestamp_func: Callable[..., str] = timestamp_or_now_iso,
    safe_str_func: Callable[..., str] = safe_str,
) -> dict[str, Any] | None:
    providers = providers_func(runtime)
    if not providers.owner_matches_func(payload):
        return None
    route_payload = build_runtime_repair_status_route_payload(
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if not status_question_func(route_payload.text):
        return None

    diagnostics = build_runtime_repair_status_diagnostics(
        RuntimeRepairStatusProbeInput(
            health=providers.health_snapshot_func(),
            source_path=providers.source_path,
        ),
        source_digest_func=source_digest_func,
        tcp_connect_func=tcp_connect_func,
        safe_str_func=safe_str_func,
    )
    visibility = build_runtime_repair_status_visibility(
        payload,
        text=route_payload.text,
        core_ok=diagnostics.core_ok,
        gateway_ok=diagnostics.gateway_ok,
        final_reply_guard_func=providers.final_reply_guard_func,
    )

    notes = runtime_repair_status_notes(
        digest_ok=diagnostics.digest_ok,
        gateway_ok=diagnostics.gateway_ok,
        event_sidecar=route_payload.event_sidecar,
        guard_flags=visibility.guard_flags,
        cleanup=route_payload.cleanup,
        safe_str_func=safe_str_func,
    )

    return await complete_runtime_repair_status_turn(
        payload,
        xinyu_dir=providers.xinyu_dir,
        memory_root=providers.memory_root,
        publish_chat_finished_func=providers.publish_chat_finished_func,
        route_payload=route_payload,
        diagnostics=diagnostics,
        visibility=visibility,
        notes=notes,
        memory_snapshot_func=memory_snapshot_func,
        finish_coherence_func=finish_coherence_func,
        clock_func=clock_func,
        record_finished_func=record_finished_func,
        visible_hash_func=visible_hash_func,
        timestamp_func=timestamp_func,
        safe_str_func=safe_str_func,
    )
