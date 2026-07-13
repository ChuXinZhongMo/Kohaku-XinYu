from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable

from xinyu_learning_library import (
    DEFAULT_MAX_BYTES,
    add_local_material,
    add_url_material,
    stage_manifest_record,
)
from xinyu_local_scope import (
    LocalScopeError,
    default_local_scope_root,
    designated_read_roots,
    resolve_read_only_scope_path,
)
from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_bridge_learning_codex_reports import stage_codex_report_material
from xinyu_bridge_learning_ingest_helpers import (
    ATTACHMENT_DIRS_ENV,
    IMAGE_SUFFIXES,
    LEGACY_ATTACHMENT_DIRS_ENV,
    LearningIngestRequest,
    _as_bool,
    _as_int,
    _attachment_kind,
    _env_roots,
    _generic_attachment_label,
    _has_traversal,
    _learning_ingest_reply,
    _payload_metadata,
    _safe_str,
    build_learning_ingest_response,
    parse_learning_ingest_request,
    payload_path,
    resolve_learning_ingest_path,
)
from xinyu_bridge_learning_runtime import (
    add_learning_request_material,
    record_learning_ingest_sidecar,
    run_learning_study_snapshot,
    stage_learning_material,
)
from xinyu_bridge_learning_routes import run_learning_ingest_route, run_learning_study_route
from xinyu_bridge_learning_sidecars import int_result as _int_result
from xinyu_bridge_learning_sidecars import run_learning_study_chain as _run_learning_study_chain
from xinyu_bridge_learning_study_reports import build_learning_study_response, learning_study_mode
from xinyu_memory_event_sourcing import record_learning_ingest_event


class LearningBridgeError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def clamp_max_bytes(value: Any, configured_max: int = DEFAULT_MAX_BYTES) -> int:
    requested = _as_int(value, configured_max)
    if requested <= 0:
        raise LearningBridgeError(HTTPStatus.BAD_REQUEST, "max_bytes must be > 0")
    return min(requested, configured_max)


def _deps() -> dict[str, Any]:
    return globals()


async def ingest(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    payload: dict[str, Any],
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
    load_local_env: Callable[[Path], None],
) -> dict[str, Any]:
    return await run_learning_ingest_route(
        xinyu_dir=xinyu_dir,
        memory_root=memory_root,
        payload=payload,
        cleanup_idle_sessions=cleanup_idle_sessions,
        session_count=session_count,
        lock=lock,
        load_local_env=load_local_env,
        deps=_deps(),
    )


async def study(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    payload: dict[str, Any],
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
    load_local_env: Callable[[Path], None],
) -> dict[str, Any]:
    return await run_learning_study_route(
        xinyu_dir=xinyu_dir,
        memory_root=memory_root,
        payload=payload,
        cleanup_idle_sessions=cleanup_idle_sessions,
        session_count=session_count,
        lock=lock,
        load_local_env=load_local_env,
        deps=_deps(),
    )

__all__ = (
    "ATTACHMENT_DIRS_ENV",
    "Any",
    "Callable",
    "DEFAULT_MAX_BYTES",
    "HTTPStatus",
    "IMAGE_SUFFIXES",
    "LEGACY_ATTACHMENT_DIRS_ENV",
    "LearningBridgeError",
    "LearningIngestRequest",
    "LocalScopeError",
    "Path",
    "_as_bool",
    "_as_int",
    "_attachment_kind",
    "_deps",
    "_env_roots",
    "_generic_attachment_label",
    "_has_traversal",
    "_int_result",
    "_learning_ingest_reply",
    "_memory_snapshot",
    "_payload_metadata",
    "_run_learning_study_chain",
    "_safe_str",
    "add_learning_request_material",
    "add_local_material",
    "add_url_material",
    "annotations",
    "build_learning_ingest_response",
    "build_learning_study_response",
    "clamp_max_bytes",
    "default_local_scope_root",
    "designated_read_roots",
    "ingest",
    "learning_study_mode",
    "parse_learning_ingest_request",
    "payload_path",
    "record_learning_ingest_event",
    "record_learning_ingest_sidecar",
    "resolve_learning_ingest_path",
    "resolve_read_only_scope_path",
    "run_learning_ingest_route",
    "run_learning_study_route",
    "run_learning_study_snapshot",
    "stage_codex_report_material",
    "stage_learning_material",
    "stage_manifest_record",
    "study",
)
