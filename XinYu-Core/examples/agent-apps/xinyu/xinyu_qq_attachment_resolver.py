from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


SUPPORTED_IMAGE_SUFFIXES = frozenset({".bmp", ".gif", ".jfif", ".jpeg", ".jpg", ".png", ".webp"})


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _maybe_int(value: str) -> int | str:
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


async def resolve_learning_ingest_payload(gateway: Any, websocket: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("file_url") or payload.get("file_path"):
        return payload
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    file_id = _safe_str(payload.get("file_id") or metadata.get("file_id")).strip()
    if not file_id:
        return payload

    if _safe_str(metadata.get("segment_type")).strip().lower() == "image":
        resolved = await resolve_onebot_media(gateway, websocket, file_id=file_id, metadata=metadata)
    else:
        resolved = await resolve_onebot_file(gateway, websocket, file_id=file_id, metadata=metadata)
    if not resolved:
        print(f"[xinyu_qq_gateway] could not resolve QQ file_id={file_id}", flush=True)
        enriched = dict(payload)
        unresolved_metadata = dict(metadata)
        unresolved_metadata["file_resolution_status"] = "unresolved"
        enriched["metadata"] = unresolved_metadata
        return enriched
    enriched = dict(payload)
    resolved_metadata = dict(metadata)
    if resolved.get("file_url"):
        enriched["file_url"] = resolved["file_url"]
    if resolved.get("file_path"):
        enriched["file_path"] = resolved["file_path"]
    resolved_metadata.update(
        {
            "file_resolved_by": resolved.get("resolved_by", ""),
            "file_resolution_status": "resolved",
            "file_resolution_attempts": resolved.get("resolution_attempts", []),
        }
    )
    enriched["metadata"] = resolved_metadata
    return enriched


async def resolve_sticker_import_payload(gateway: Any, websocket: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("file_url") or payload.get("file_path"):
        return payload
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    file_id = _safe_str(payload.get("file_id") or metadata.get("file_id")).strip()
    if not file_id:
        return payload

    resolved = await resolve_onebot_media(gateway, websocket, file_id=file_id, metadata=metadata)
    if not resolved:
        print(f"[xinyu_qq_gateway] could not resolve QQ sticker file_id={file_id}", flush=True)
        enriched = dict(payload)
        unresolved_metadata = dict(metadata)
        unresolved_metadata["file_resolution_status"] = "unresolved"
        enriched["metadata"] = unresolved_metadata
        return enriched
    enriched = dict(payload)
    resolved_metadata = dict(metadata)
    if resolved.get("file_url"):
        enriched["file_url"] = resolved["file_url"]
    if resolved.get("file_path"):
        enriched["file_path"] = resolved["file_path"]
    resolved_metadata.update(
        {
            "file_resolved_by": resolved.get("resolved_by", ""),
            "file_resolution_status": "resolved",
            "file_resolution_attempts": resolved.get("resolution_attempts", []),
        }
    )
    enriched["metadata"] = resolved_metadata
    return enriched


async def resolve_onebot_media(
    gateway: Any,
    websocket: Any,
    *,
    file_id: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    attempts: list[str] = []
    segment_type = _safe_str(metadata.get("segment_type")).strip().lower()
    if segment_type == "image":
        for params in ({"file": file_id}, {"file_id": file_id}):
            attempts.append("get_image")
            image_data = await gateway._onebot_action_data(websocket, "get_image", params)
            if not image_data:
                continue
            url = _first_text_field(image_data, ("url", "file_url", "download_url"))
            if url:
                return {"file_url": url, "resolved_by": "get_image", "resolution_attempts": attempts}
            path = _first_text_field(image_data, ("file", "file_path", "path", "real_path"))
            if path:
                return {"file_path": path, "resolved_by": "get_image", "resolution_attempts": attempts}

    attempts.append("file_actions")
    resolved = await resolve_onebot_file(gateway, websocket, file_id=file_id, metadata=metadata)
    if resolved:
        resolved["resolution_attempts"] = attempts
    return resolved


async def resolve_onebot_file(
    gateway: Any,
    websocket: Any,
    *,
    file_id: str,
    metadata: dict[str, Any],
) -> dict[str, str]:
    group_id = _safe_str(metadata.get("group_id")).strip()
    if group_id:
        group_url = await gateway._onebot_file_url_action(
            websocket,
            "get_group_file_url",
            {"group_id": _maybe_int(group_id), "file_id": file_id},
        )
        if group_url:
            return {"file_url": group_url, "resolved_by": "get_group_file_url"}

    private_url = await gateway._onebot_file_url_action(websocket, "get_private_file_url", {"file_id": file_id})
    if private_url:
        return {"file_url": private_url, "resolved_by": "get_private_file_url"}

    file_data = await gateway._onebot_action_data(websocket, "get_file", {"file_id": file_id})
    if not file_data:
        return {}
    url = _first_text_field(file_data, ("url", "file_url", "download_url"))
    if url:
        return {"file_url": url, "resolved_by": "get_file"}
    path = _first_text_field(file_data, ("file", "file_path", "path", "real_path"))
    if path:
        return {"file_path": path, "resolved_by": "get_file"}
    return {}


async def onebot_file_url_action(gateway: Any, websocket: Any, action: str, params: dict[str, Any]) -> str:
    data = await gateway._onebot_action_data(websocket, action, params)
    return _first_text_field(data, ("url", "file_url", "download_url")) if data else ""


async def onebot_action_payload(gateway: Any, websocket: Any, action: str, params: dict[str, Any]) -> Any:
    response = await gateway.send_action(websocket, action, params)
    if not isinstance(response, dict):
        return None
    status = _safe_str(response.get("status")).lower()
    retcode = response.get("retcode")
    if status and status != "ok":
        return None
    if retcode not in {None, 0, "0"}:
        return None
    return response.get("data")


async def onebot_action_data(gateway: Any, websocket: Any, action: str, params: dict[str, Any]) -> dict[str, Any]:
    data = await onebot_action_payload(gateway, websocket, action, params)
    return data if isinstance(data, dict) else {}


def path_from_file_uri(value: str) -> Path:
    parsed = urlparse(value)
    path = unquote(parsed.path or "")
    if os.name == "nt" and re.match(r"^/[a-zA-Z]:", path):
        path = path[1:]
    return Path(path)


def onebot_local_image_file(gateway: Any, image_path: str) -> tuple[str, str]:
    text = image_path.strip().strip('"')
    if not text:
        return "", "missing image path"
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "base64://")):
        return "", "image path must be a local file"
    path = path_from_file_uri(text) if lowered.startswith("file://") else Path(text)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return "", "image file not found"
    if not resolved.is_file():
        return "", "image path is not a file"
    if resolved.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        return "", "unsupported image type"
    try:
        return resolved.as_uri(), ""
    except ValueError:
        return str(resolved), ""


def onebot_local_file(gateway: Any, file_path: str, *, file_name: str = "") -> tuple[str, str, str]:
    text = file_path.strip().strip('"')
    if not text:
        return "", "", "missing file path"
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "base64://")):
        return "", "", "file path must be a local file"
    path = path_from_file_uri(text) if lowered.startswith("file://") else Path(text)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return "", "", "file not found"
    if not resolved.is_file():
        return "", "", "file path is not a file"
    name = _safe_str(file_name).strip() or resolved.name
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name).strip(" .")
    return str(resolved), name or "attachment", ""


def first_text_field(gateway: Any, data: dict[str, Any], keys: tuple[str, ...]) -> str:
    return first_text_field_value(data, keys)


def first_text_field_value(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    return _first_text_field(data, keys)


def _first_text_field(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _safe_str(data.get(key)).strip()
        if value:
            return value
    return ""


def looks_like_file_path(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if text.lower().startswith("file://"):
        return True
    if len(text) > 2 and text[1] == ":" and text[2] in {"\\", "/"}:
        return True
    return "\\" in text or "/" in text


def sticker_import_material_from_data(segment_type: str, data: dict[str, Any]) -> dict[str, str] | None:
    name = (
        _safe_str(data.get("name")).strip()
        or _safe_str(data.get("file_name")).strip()
        or _safe_str(data.get("filename")).strip()
        or _safe_str(data.get("file")).strip()
        or _safe_str(data.get("summary")).strip()
        or _safe_str(data.get("text")).strip()
        or f"qq-{segment_type}-sticker"
    )
    url = (
        _safe_str(data.get("url")).strip()
        or _safe_str(data.get("file_url")).strip()
        or _safe_str(data.get("download_url")).strip()
    )
    path = (
        _safe_str(data.get("file_path")).strip()
        or _safe_str(data.get("path")).strip()
        or _safe_str(data.get("local_path")).strip()
    )
    file_value = _safe_str(data.get("file")).strip()
    file_id = (
        _safe_str(data.get("file_id")).strip()
        or _safe_str(data.get("fileId")).strip()
        or _safe_str(data.get("fid")).strip()
    )
    if not path and looks_like_file_path(file_value):
        path = file_value
    if not file_id and file_value and not path:
        file_id = file_value
    if not url and not path and not file_id:
        return None
    return {
        "segment_type": segment_type,
        "name": name,
        "summary": _safe_str(data.get("summary") or data.get("text") or name).strip(),
        "url": url,
        "path": path,
        "file_id": file_id,
    }


def learning_material_from_data(segment_type: str, data: dict[str, Any]) -> dict[str, str] | None:
    name = (
        _safe_str(data.get("name")).strip()
        or _safe_str(data.get("file_name")).strip()
        or _safe_str(data.get("filename")).strip()
        or _safe_str(data.get("file")).strip()
        or f"qq-{segment_type}"
    )
    url = _safe_str(data.get("url")).strip()
    path = (
        _safe_str(data.get("file_path")).strip()
        or _safe_str(data.get("path")).strip()
        or _safe_str(data.get("local_path")).strip()
    )
    file_value = _safe_str(data.get("file")).strip()
    file_id = (
        _safe_str(data.get("file_id")).strip()
        or _safe_str(data.get("id")).strip()
        or _safe_str(data.get("fid")).strip()
    )
    if not path and looks_like_file_path(file_value):
        path = file_value
    if not file_id and file_value and not path:
        file_id = file_value
    if not url and not path and not file_id:
        return None
    return {
        "segment_type": segment_type,
        "name": name,
        "url": url,
        "path": path,
        "file_id": file_id,
    }


def reply_file_learning_intent(gateway: Any, text: str) -> bool:
    return reply_file_learning_intent_text(text)


def reply_file_learning_intent_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    deny_markers = ("不用读", "别读", "不读", "先别读", "do not read", "don't read")
    if any(marker in lowered or marker in stripped for marker in deny_markers):
        return False
    intent_markers = (
        "读",
        "阅读",
        "看",
        "看看",
        "学习",
        "研究",
        "解析",
        "总结",
        "讲讲",
        "提取",
        "导入",
        "收一下",
        "这个",
        "附件",
        "文件",
        "截图",
        "图片",
        "照片",
        "图像",
        "这张",
        "那张",
        "看图",
        "pdf",
        "paper",
        "read",
        "open",
        "parse",
        "summarize",
        "summarise",
        "study",
        "learn",
        "file",
        "image",
        "picture",
        "screenshot",
        "this",
    )
    return any(marker in lowered or marker in stripped for marker in intent_markers)
