from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable


async def add_learning_request_material(
    *,
    xinyu_dir: Path,
    request: Any,
    resolve_ingest_path: Callable[[Path, str], Path],
    add_local: Callable[..., dict[str, Any]],
    add_url: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    if request.file_path:
        source = resolve_ingest_path(xinyu_dir, request.file_path)
        return await asyncio.to_thread(
            add_local,
            root=xinyu_dir,
            path=source,
            origin=request.origin,
            reason=request.reason,
            question_id=request.question_id,
            title=request.title,
            label=request.label,
            max_bytes=request.max_bytes,
        )
    return await asyncio.to_thread(
        add_url,
        root=xinyu_dir,
        url=request.file_url,
        origin=request.origin,
        reason=request.reason,
        question_id=request.question_id,
        title=request.title,
        label=request.label,
        max_bytes=request.max_bytes,
    )


async def stage_learning_material(
    *,
    xinyu_dir: Path,
    metadata: dict[str, Any],
    request: Any,
    stage_manifest: Callable[..., str],
) -> str:
    if not request.stage:
        return ""
    return await asyncio.to_thread(stage_manifest, xinyu_dir, metadata, request.curated)


def record_learning_ingest_sidecar(
    *,
    xinyu_dir: Path,
    payload: dict[str, Any],
    metadata: dict[str, Any],
    material_id: str,
    recorder: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        return recorder(
            xinyu_dir,
            payload,
            result={"material_id": material_id, "learning_item_id": metadata.get("id", "")},
        )
    except Exception as exc:
        return {"notes": [f"event_sourcing_error:{type(exc).__name__}"]}


async def run_learning_study_snapshot(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    mode: str,
    memory_snapshot: Callable[[Path], dict[str, Any]],
    study_chain: Callable[[Path, str], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    before_memory = memory_snapshot(memory_root)
    result = await asyncio.to_thread(study_chain, xinyu_dir, mode)
    after_memory = memory_snapshot(memory_root)
    return result, before_memory, after_memory
