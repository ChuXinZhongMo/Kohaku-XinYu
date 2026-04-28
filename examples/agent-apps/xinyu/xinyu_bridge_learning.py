from __future__ import annotations

import asyncio
import os
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from xinyu_learning_library import DEFAULT_MAX_BYTES, add_local_material, add_url_material, stage_manifest_record
from xinyu_local_scope import (
    LocalScopeError,
    default_local_scope_root,
    designated_read_roots,
    resolve_read_only_scope_path,
)
from xinyu_memory_event_sourcing import record_learning_ingest_event


ATTACHMENT_DIRS_ENV = "XINYU_QQ_ATTACHMENT_DIRS"
LEGACY_ATTACHMENT_DIRS_ENV = "XINYU_ASTRBOT_ATTACHMENT_DIRS"


class LearningBridgeError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _memory_snapshot(memory_root: Path) -> dict[str, tuple[int, int]]:
    if not memory_root.exists():
        return {}
    snapshot: dict[str, tuple[int, int]] = {}
    for path in memory_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshot[path.relative_to(memory_root).as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def payload_path(value: str) -> Path:
    text = value.strip()
    if text.lower().startswith("file://"):
        parsed = urlparse(text)
        path_text = parsed.path
        if os.name == "nt" and len(path_text) > 2 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
        return Path(unquote(path_text))
    return Path(text)


def _env_roots(name: str) -> tuple[Path, ...]:
    configured = os.environ.get(name, "").strip()
    if not configured:
        return ()
    roots: list[Path] = []
    for part in configured.split(os.pathsep):
        text = part.strip()
        if text:
            roots.append(Path(text).expanduser().resolve())
    return tuple(roots)


def _has_traversal(raw: str) -> bool:
    return any(part == ".." for part in Path(raw).parts)


def resolve_learning_ingest_path(xinyu_dir: Path, raw_path: str) -> Path:
    if _has_traversal(raw_path):
        raise LocalScopeError("path traversal is not allowed for learning ingest")
    parsed = payload_path(raw_path)
    read_roots = (
        designated_read_roots()
        + (default_local_scope_root(xinyu_dir),)
        + _env_roots(ATTACHMENT_DIRS_ENV)
        + _env_roots(LEGACY_ATTACHMENT_DIRS_ENV)
    )
    return resolve_read_only_scope_path(read_roots, parsed)


def clamp_max_bytes(value: Any, configured_max: int = DEFAULT_MAX_BYTES) -> int:
    requested = _as_int(value, configured_max)
    if requested <= 0:
        raise LearningBridgeError(HTTPStatus.BAD_REQUEST, "max_bytes must be > 0")
    return min(requested, configured_max)


def _run_learning_study_chain(root: Path, mode: str) -> dict[str, object]:
    custom_dir = Path(__file__).resolve().parent / "custom"
    import sys

    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    from learner_integration_engine import run_learner_integration
    from learning_quality_engine import run_learning_quality
    from source_integration_gate_engine import run_source_integration_gate

    gate = run_source_integration_gate(root, mode=f"{mode}_source_gate")
    learner = run_learner_integration(root, mode=f"{mode}_learner")
    quality = run_learning_quality(root, mode=f"{mode}_quality")
    return {
        "source_integration_gate": gate,
        "learner_integration": learner,
        "learning_quality": quality,
    }


def _int_result(mapping: dict[str, object], key: str) -> int:
    try:
        return int(mapping.get(key, 0))
    except (TypeError, ValueError):
        return 0


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
    file_path = _safe_str(payload.get("file_path") or payload.get("path")).strip()
    file_url = _safe_str(payload.get("file_url") or payload.get("url")).strip()
    file_name = _safe_str(payload.get("file_name") or payload.get("name")).strip()
    if not file_path and not file_url:
        raise LearningBridgeError(HTTPStatus.BAD_REQUEST, "file_path or file_url is required")

    origin = _safe_str(payload.get("origin"), "owner_supplied").strip() or "owner_supplied"
    reason = _safe_str(payload.get("reason"), "owner supplied QQ file").strip() or "owner supplied QQ file"
    question_id = _safe_str(payload.get("question_id"), "qq-file-learning").strip() or "qq-file-learning"
    title = _safe_str(payload.get("title") or file_name).strip()
    label = _safe_str(payload.get("label") or file_name).strip()
    stage = _as_bool(payload.get("stage"), default=True)
    curated = _as_bool(payload.get("curated"), default=(origin == "owner_supplied"))
    max_bytes = clamp_max_bytes(payload.get("max_bytes"))

    async with lock:
        load_local_env(xinyu_dir)
        cleanup = await cleanup_idle_sessions()
        before_memory = _memory_snapshot(memory_root)
        try:
            if file_path:
                source = resolve_learning_ingest_path(xinyu_dir, file_path)
                metadata = await asyncio.to_thread(
                    add_local_material,
                    root=xinyu_dir,
                    path=source,
                    origin=origin,
                    reason=reason,
                    question_id=question_id,
                    title=title,
                    label=label,
                    max_bytes=max_bytes,
                )
            else:
                metadata = await asyncio.to_thread(
                    add_url_material,
                    root=xinyu_dir,
                    url=file_url,
                    origin=origin,
                    reason=reason,
                    question_id=question_id,
                    title=title,
                    label=label,
                    max_bytes=max_bytes,
                )
        except LocalScopeError as exc:
            raise LearningBridgeError(HTTPStatus.FORBIDDEN, str(exc)) from exc
        except RuntimeError as exc:
            raise LearningBridgeError(HTTPStatus.BAD_REQUEST, str(exc)) from exc
        material_id = ""
        if stage:
            material_id = await asyncio.to_thread(stage_manifest_record, xinyu_dir, metadata, curated)
        sidecar_result: dict[str, Any] = {"notes": ["event_sourcing_not_run"]}
        try:
            sidecar_result = record_learning_ingest_event(
                xinyu_dir,
                payload,
                result={"material_id": material_id, "learning_item_id": metadata.get("id", "")},
            )
        except Exception as exc:
            sidecar_result = {"notes": [f"event_sourcing_error:{type(exc).__name__}"]}
        after_memory = _memory_snapshot(memory_root)

    notes = ["learning_ingest", "no_agent_turn", "session_not_created", f"max_bytes:{max_bytes}"]
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    notes.append(f"stage:{material_id}" if stage else "stage:skipped")
    notes.extend(_safe_str(note) for note in sidecar_result.get("notes", [])[:4])

    title_for_reply = _safe_str(metadata.get("title") or file_name or metadata.get("id")).strip()
    extracted_text_path = _safe_str(metadata.get("extracted_text_path")).strip()
    staged_text = ", staged" if stage else ""
    extracted_text = ", readable text extracted" if extracted_text_path else ", no readable text extracted"
    return {
        "accepted": True,
        "reply": f"received: {title_for_reply}. learning library updated{staged_text}{extracted_text}.",
        "memory_changed": before_memory != after_memory,
        "library_changed": True,
        "session_created": False,
        "sessions": session_count(),
        "learning_item_id": metadata.get("id", ""),
        "material_id": material_id,
        "origin": metadata.get("origin", origin),
        "item_dir": metadata.get("item_dir", ""),
        "stored_paths": metadata.get("stored_paths", []),
        "extracted_text": bool(extracted_text_path),
        "extracted_text_path": extracted_text_path,
        "stage_status": material_id or "not_staged",
        "notes": notes,
    }


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
    mode = _safe_str(payload.get("mode"), "bridge_learning_study").strip() or "bridge_learning_study"

    async with lock:
        load_local_env(xinyu_dir)
        cleanup = await cleanup_idle_sessions()
        before_memory = _memory_snapshot(memory_root)
        result = await asyncio.to_thread(_run_learning_study_chain, xinyu_dir, mode)
        after_memory = _memory_snapshot(memory_root)

    learner = result.get("learner_integration", {})
    quality = result.get("learning_quality", {})
    gate = result.get("source_integration_gate", {})
    learner_map = learner if isinstance(learner, dict) else {}
    quality_map = quality if isinstance(quality, dict) else {}
    gate_map = gate if isinstance(gate, dict) else {}

    integrated = _int_result(learner_map, "newly_integrated_materials")
    ready = _int_result(learner_map, "ready_materials")
    blocked_unreadable = _int_result(learner_map, "blocked_unreadable_materials")
    held_unreadable = _int_result(learner_map, "held_unreadable_materials")
    pending = _int_result(learner_map, "pending_ready_materials")
    already = _int_result(learner_map, "already_integrated_ready_materials")
    quality_grade = _safe_str(quality_map.get("quality_grade"), "unknown")
    warning_count = _int_result(quality_map, "warning_count")
    gate_reason = _safe_str(gate_map.get("gate_reason"), "unknown")

    if integrated > 0:
        reply = f"learning integrated {integrated} material(s); quality={quality_grade}; warnings={warning_count}."
    elif blocked_unreadable > 0:
        reply = f"learning checked; {blocked_unreadable} material(s) were blocked as unreadable."
    elif held_unreadable > 0:
        reply = f"learning checked; {held_unreadable} unreadable material(s) were held."
    elif ready > 0 and already >= ready and pending == 0:
        reply = "learning checked; ready materials were already integrated."
    else:
        reply = f"learning checked; no new ready material. gate={gate_reason}"

    notes = ["learning_study", "no_agent_turn", "session_not_created"]
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": before_memory != after_memory,
        "library_changed": False,
        "session_created": False,
        "sessions": session_count(),
        "source_integration_gate": gate_map,
        "learner_integration": learner_map,
        "learning_quality": quality_map,
        "integrated_materials": integrated,
        "ready_materials": ready,
        "blocked_unreadable_materials": blocked_unreadable,
        "held_unreadable_materials": held_unreadable,
        "quality_grade": quality_grade,
        "warning_count": warning_count,
        "notes": notes,
    }
