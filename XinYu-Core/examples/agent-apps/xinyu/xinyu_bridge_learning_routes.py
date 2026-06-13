from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable, Mapping

from xinyu_local_scope import LocalScopeError


async def run_learning_ingest_route(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    payload: dict[str, Any],
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
    load_local_env: Callable[[Path], None],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    max_bytes = deps["clamp_max_bytes"](payload.get("max_bytes"))
    request = deps["parse_learning_ingest_request"](
        payload,
        max_bytes=max_bytes,
        safe_str=deps["_safe_str"],
        as_bool=deps["_as_bool"],
    )
    if not request.file_path and not request.file_url:
        raise deps["LearningBridgeError"](HTTPStatus.BAD_REQUEST, "file_path or file_url is required")

    async with lock:
        load_local_env(xinyu_dir)
        cleanup = await cleanup_idle_sessions()
        before_memory = deps["_memory_snapshot"](memory_root)
        try:
            metadata = await deps["add_learning_request_material"](
                xinyu_dir=xinyu_dir,
                request=request,
                resolve_ingest_path=deps["resolve_learning_ingest_path"],
                add_local=deps["add_local_material"],
                add_url=deps["add_url_material"],
            )
        except LocalScopeError as exc:
            raise deps["LearningBridgeError"](HTTPStatus.FORBIDDEN, str(exc)) from exc
        except RuntimeError as exc:
            raise deps["LearningBridgeError"](HTTPStatus.BAD_REQUEST, str(exc)) from exc
        material_id = await deps["stage_learning_material"](
            xinyu_dir=xinyu_dir,
            metadata=metadata,
            request=request,
            stage_manifest=deps["stage_manifest_record"],
        )
        sidecar_result = deps["record_learning_ingest_sidecar"](
            xinyu_dir=xinyu_dir,
            payload=payload,
            metadata=metadata,
            material_id=material_id,
            recorder=deps["record_learning_ingest_event"],
        )
        after_memory = deps["_memory_snapshot"](memory_root)

    return deps["build_learning_ingest_response"](
        payload,
        metadata,
        request=request,
        cleanup=cleanup,
        sidecar_result=sidecar_result,
        material_id=material_id,
        before_memory=before_memory,
        after_memory=after_memory,
        sessions=session_count(),
        reply_factory=deps["_learning_ingest_reply"],
        safe_str=deps["_safe_str"],
    )


async def run_learning_study_route(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    payload: dict[str, Any],
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
    load_local_env: Callable[[Path], None],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    mode = deps["learning_study_mode"](payload, safe_str=deps["_safe_str"])

    async with lock:
        load_local_env(xinyu_dir)
        cleanup = await cleanup_idle_sessions()
        result, before_memory, after_memory = await deps["run_learning_study_snapshot"](
            xinyu_dir=xinyu_dir,
            memory_root=memory_root,
            mode=mode,
            memory_snapshot=deps["_memory_snapshot"],
            study_chain=deps["_run_learning_study_chain"],
        )

    return deps["build_learning_study_response"](
        result,
        cleanup,
        before_memory=before_memory,
        after_memory=after_memory,
        sessions=session_count(),
        safe_str=deps["_safe_str"],
        int_result=deps["_int_result"],
    )
