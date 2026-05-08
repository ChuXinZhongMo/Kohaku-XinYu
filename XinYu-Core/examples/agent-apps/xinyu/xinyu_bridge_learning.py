from __future__ import annotations

import asyncio
import hashlib
import os
import re
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from xinyu_learning_library import (
    DEFAULT_MAX_BYTES,
    claim_from_text,
    ensure_source_materials_file,
    next_material_id,
    pdf_text_looks_garbled,
    sanitize_field,
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
from xinyu_memory_event_sourcing import record_learning_ingest_event


ATTACHMENT_DIRS_ENV = "XINYU_QQ_ATTACHMENT_DIRS"
LEGACY_ATTACHMENT_DIRS_ENV = "XINYU_ASTRBOT_ATTACHMENT_DIRS"
IMAGE_SUFFIXES = {".bmp", ".gif", ".jfif", ".jpeg", ".jpg", ".png", ".webp"}


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


def _resolve_report_path(root: Path, report_path: str) -> Path:
    path = Path(_safe_str(report_path).strip())
    if not path:
        return path
    return path if path.is_absolute() else root / path


def _codex_report_key(report_path: Path) -> str:
    return hashlib.sha256(str(report_path.resolve()).encode("utf-8", errors="replace")).hexdigest()[:16]


def _existing_codex_report_material_id(source_materials: str, report_key: str) -> str:
    marker = f"- codex_report_key: {report_key}"
    marker_index = source_materials.find(marker)
    if marker_index < 0:
        return ""
    preceding = source_materials[:marker_index]
    matches = re.findall(r"(?m)^## (material-\d{4}-\d{2}-\d{2}-\d{3})\n", preceding)
    return matches[-1] if matches else ""


def _append_report_learning_registration(report_path: Path, material_id: str, registered_at: str) -> None:
    try:
        text = report_path.read_text(encoding="utf-8-sig", errors="replace").rstrip()
    except OSError:
        return
    if "## XinYu Learning Registration" in text:
        return
    addition = (
        "\n\n## XinYu Learning Registration\n\n"
        f"- material_id: {material_id}\n"
        f"- registered_at: {registered_at}\n"
        "- learning_followup: queued_through_existing_gates\n"
    )
    try:
        report_path.write_text(text + addition + "\n", encoding="utf-8")
    except OSError:
        return


def stage_codex_report_material(
    root: Path,
    *,
    report_path: str,
    task_text: str = "",
    job_id: str = "",
    registered_at: str | None = None,
) -> dict[str, object]:
    registered_at = registered_at or datetime.now().astimezone().isoformat()
    path = _resolve_report_path(root, report_path)
    if not path or not path.is_file():
        return {
            "material_id": "",
            "registered": False,
            "status": "missing_report",
            "notes": ["codex_report_material_missing"],
        }

    source_path = ensure_source_materials_file(root)
    source_text = source_path.read_text(encoding="utf-8-sig", errors="replace").rstrip()
    report_key = _codex_report_key(path)
    existing = _existing_codex_report_material_id(source_text, report_key)
    if existing:
        _append_report_learning_registration(path, existing, registered_at)
        return {
            "material_id": existing,
            "registered": False,
            "status": "already_staged",
            "notes": ["codex_report_material_already_staged"],
        }

    report_text = path.read_text(encoding="utf-8-sig", errors="replace")
    readable = bool(report_text.strip()) and not pdf_text_looks_garbled(report_text)
    stat = path.stat()
    fetched_at = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat()
    date_part = fetched_at[:10]
    material_id = next_material_id(source_text, date_part)
    fallback = f"Codex report for owner-delegated task: {task_text[:240] or path.name}"
    claim = claim_from_text(report_text, fallback)
    status = "ready" if readable else "hold"
    extraction_status = "readable_text" if readable else "unreadable"
    addition = (
        f"\n\n## {material_id}\n"
        "- question_id: qq-codex-delegation\n"
        f"- source_question: {sanitize_field(task_text or path.name)}\n"
        f"- url: codex-report://{sanitize_field(job_id or report_key, 120)}\n"
        "- source_type: codex_search_report\n"
        "- reliability: curated\n"
        "- integration_scope: knowledge_only\n"
        f"- status: {status}\n"
        f"- fetched_at: {fetched_at}\n"
        "- comparison_status: curated\n"
        "- evidence_hosts: 1\n"
        "- learning_origin: codex_report\n"
        "- learning_item_id: none\n"
        f"- local_path: {sanitize_field(str(path))}\n"
        f"- extracted_text_path: {sanitize_field(str(path))}\n"
        f"- extraction_status: {extraction_status}\n"
        f"- codex_job_id: {sanitize_field(job_id or 'none', 120)}\n"
        f"- codex_report_key: {report_key}\n"
        f"- claim: {sanitize_field(claim)}\n"
    )
    source_path.write_text(source_text + addition + "\n", encoding="utf-8")
    _append_report_learning_registration(path, material_id, registered_at)
    return {
        "material_id": material_id,
        "registered": True,
        "status": status,
        "notes": ["codex_report_material_staged"],
    }


def _int_result(mapping: dict[str, object], key: str) -> int:
    try:
        return int(mapping.get(key, 0))
    except (TypeError, ValueError):
        return 0


def _payload_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _attachment_kind(payload: dict[str, Any], metadata: dict[str, Any], file_name: str) -> str:
    payload_metadata = _payload_metadata(payload)
    segment_type = _safe_str(payload_metadata.get("segment_type")).strip().lower()
    if segment_type in {"image", "file", "record", "video"}:
        return segment_type
    content_type = _safe_str(metadata.get("content_type")).strip().lower()
    if content_type.startswith("image/"):
        return "image"
    suffix = Path(_safe_str(metadata.get("title") or file_name)).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    return "file"


def _generic_attachment_label(kind: str) -> str:
    if kind == "image":
        return "这张图片"
    if kind == "record":
        return "这段语音"
    if kind == "video":
        return "这个视频"
    return "这个文件"


def _learning_ingest_reply(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    *,
    file_name: str,
    stage: bool,
    extracted_text_path: str,
) -> str:
    kind = _attachment_kind(payload, metadata, file_name)
    label = _generic_attachment_label(kind)
    stored = "已经先存进学习资料库" if stage else "已经先收下"
    if extracted_text_path:
        return f"收到{label}了，{stored}，也提取到了可阅读文字。"
    if kind == "image":
        return f"收到{label}了，{stored}；里面暂时没读出文字。"
    return f"收到{label}了，{stored}；暂时没提取到可阅读文本。"


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

    extracted_text_path = _safe_str(metadata.get("extracted_text_path")).strip()
    return {
        "accepted": True,
        "reply": _learning_ingest_reply(
            payload,
            metadata,
            file_name=file_name,
            stage=stage,
            extracted_text_path=extracted_text_path,
        ),
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
