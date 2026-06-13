from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_learning_ingest_request import LearningIngestRequest
from xinyu_bridge_values import safe_str as _safe_str


IMAGE_SUFFIXES = {".bmp", ".gif", ".jfif", ".jpeg", ".jpg", ".png", ".webp"}


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


def learning_ingest_notes(
    *,
    cleanup: dict[str, Any],
    max_bytes: int,
    stage: bool,
    material_id: str,
    sidecar_result: dict[str, Any],
    safe_str: Callable[[Any, str], str] = _safe_str,
) -> list[str]:
    notes = ["learning_ingest", "no_agent_turn", "session_not_created", f"max_bytes:{max_bytes}"]
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    notes.append(f"stage:{material_id}" if stage else "stage:skipped")
    notes.extend(safe_str(note, "") for note in sidecar_result.get("notes", [])[:4])
    return notes


def build_learning_ingest_response(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    *,
    request: LearningIngestRequest,
    cleanup: dict[str, Any],
    sidecar_result: dict[str, Any],
    material_id: str,
    before_memory: Any,
    after_memory: Any,
    sessions: int,
    reply_factory: Callable[..., str] = _learning_ingest_reply,
    safe_str: Callable[[Any, str], str] = _safe_str,
) -> dict[str, Any]:
    extracted_text_path = safe_str(metadata.get("extracted_text_path"), "").strip()
    return {
        "accepted": True,
        "reply": reply_factory(
            payload,
            metadata,
            file_name=request.file_name,
            stage=request.stage,
            extracted_text_path=extracted_text_path,
        ),
        "memory_changed": before_memory != after_memory,
        "library_changed": True,
        "session_created": False,
        "sessions": sessions,
        "learning_item_id": metadata.get("id", ""),
        "material_id": material_id,
        "origin": metadata.get("origin", request.origin),
        "item_dir": metadata.get("item_dir", ""),
        "stored_paths": metadata.get("stored_paths", []),
        "extracted_text": bool(extracted_text_path),
        "extracted_text_path": extracted_text_path,
        "stage_status": material_id or "not_staged",
        "notes": learning_ingest_notes(
            cleanup=cleanup,
            max_bytes=request.max_bytes,
            stage=request.stage,
            material_id=material_id,
            sidecar_result=sidecar_result,
            safe_str=safe_str,
        ),
    }
