from __future__ import annotations

import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from xinyu_bridge_proactive_delivery_state_store import proactive_delivery_state_paths
from xinyu_qq_outbox_state import parse_outbox_time as _parse_time
from xinyu_qq_outbox_state import summarize_outbox_items


QUEUE_VERSION = 1
MAX_MESSAGE_CHARS = 1200
MAX_ATTEMPTS = 3
SUPPORTED_IMAGE_SUFFIXES = frozenset({".bmp", ".gif", ".jfif", ".jpeg", ".jpg", ".png", ".webp"})


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_time(_safe_str(value))
    if parsed is None:
        return _now()
    return parsed.astimezone().isoformat(timespec="seconds")


def _one_line(value: Any, *, limit: int = MAX_MESSAGE_CHARS) -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if limit > 0 and len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def _path_from_file_uri(value: str) -> Path:
    parsed = urlparse(value)
    path = unquote(parsed.path or "")
    if os.name == "nt" and re.match(r"^/[a-zA-Z]:", path):
        path = path[1:]
    return Path(path)


def _normalize_local_image_path(root: Path, value: Any) -> tuple[str, list[str]]:
    text = _safe_str(value).strip().strip('"')
    if not text:
        return "", ["missing_image_path"]
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "base64://")):
        return "", ["image_path_must_be_local_file"]

    path = _path_from_file_uri(text) if lowered.startswith("file://") else Path(text)
    if not path.is_absolute():
        path = root / path
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return "", ["image_path_not_found"]
    if not resolved.is_file():
        return "", ["image_path_not_file"]
    if resolved.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        return "", ["unsupported_image_type"]
    return str(resolved), []


def _normalize_local_file_path(root: Path, value: Any) -> tuple[str, list[str]]:
    text = _safe_str(value).strip().strip('"')
    if not text:
        return "", ["missing_file_path"]
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "base64://")):
        return "", ["file_path_must_be_local_file"]

    path = _path_from_file_uri(text) if lowered.startswith("file://") else Path(text)
    if not path.is_absolute():
        path = root / path
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return "", ["file_path_not_found"]
    if not resolved.is_file():
        return "", ["file_path_not_file"]
    return str(resolved), []


def _normalize_file_name(value: Any, fallback_path: str) -> str:
    fallback = Path(fallback_path).name if fallback_path else "attachment"
    name = _one_line(value or fallback, limit=240)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name).strip(" .")
    return name or "attachment"


def _owner_user_id_from_config(root: Path, config_path: Path | None = None) -> tuple[str, list[str]]:
    path = config_path or (root / "xinyu_qq_gateway.config.json")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return "", ["owner_config_not_found"]
    except Exception:
        return "", ["owner_config_unreadable"]
    if not isinstance(raw, dict):
        return "", ["owner_config_invalid"]
    for key in ("owner_user_ids", "whitelist_user_ids"):
        value = raw.get(key)
        candidates = value if isinstance(value, list) else [value]
        for item in candidates:
            user_id = _one_line(item, limit=64)
            if user_id and user_id != "none":
                return user_id, []
    return "", ["missing_owner_user_id"]


def _queue_path(root: Path) -> Path:
    return proactive_delivery_state_paths(root).qq_outbox_queue


def _state_path(root: Path) -> Path:
    return proactive_delivery_state_paths(root).qq_outbox_dispatch_state


def _proactive_request_state_path(root: Path) -> Path:
    return proactive_delivery_state_paths(root).proactive_request_state


def _lock_path(root: Path) -> Path:
    return proactive_delivery_state_paths(root).qq_outbox_lock


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": QUEUE_VERSION, "updated_at": _timestamp_or_now_iso(_now()), "items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"version": QUEUE_VERSION, "updated_at": _timestamp_or_now_iso(_now()), "items": []}
    if not isinstance(data, dict):
        return {"version": QUEUE_VERSION, "updated_at": _timestamp_or_now_iso(_now()), "items": []}
    items = data.get("items")
    if not isinstance(items, list):
        data["items"] = []
    data.setdefault("version", QUEUE_VERSION)
    data.setdefault("updated_at", _timestamp_or_now_iso(_now()))
    return data


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        replace_error: OSError | None = None
        for attempt in range(8):
            try:
                os.replace(tmp_path, path)
                replace_error = None
                break
            except OSError as exc:
                winerror = getattr(exc, "winerror", None)
                if winerror not in {5, 32, 33} and not isinstance(exc, PermissionError):
                    raise
                replace_error = exc
                time.sleep(min(0.05 * (2**attempt), 0.5))
        if replace_error is not None:
            raise replace_error
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _state_field(text: str, field: str, default: str = "") -> str:
    match = re.search(rf"(?m)^\s*-\s+{re.escape(field)}:\s*(.*)$", text or "")
    return _one_line(match.group(1), limit=240) if match else default


def _replace_frontmatter_field(text: str, field: str, value: str) -> str:
    replacement = f"{field}: {_one_line(value, limit=240) or 'none'}"
    updated, count = re.subn(rf"(?m)^\s*{re.escape(field)}:\s*.*$", replacement, text, count=1)
    if count:
        return updated
    return text.rstrip() + "\n" + replacement + "\n"


def _replace_list_field(text: str, field: str, value: str) -> str:
    replacement = f"- {field}: {_one_line(value, limit=500) or 'none'}"
    updated, count = re.subn(rf"(?m)^\s*-\s+{re.escape(field)}:\s*.*$", replacement, text, count=1)
    if count:
        return updated
    return text.rstrip() + "\n" + replacement + "\n"


def _update_proactive_request_from_outbox_ack(
    root: Path,
    item: dict[str, Any],
    *,
    ack_status: str,
    adapter_message_id: str,
    adapter_error: str,
    updated_at: str,
) -> bool:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    request_id = _one_line(
        metadata.get("proactive_request_id")
        or metadata.get("request_id")
        or metadata.get("desktop_candidate_id"),
        limit=160,
    )
    message_id = _one_line(item.get("id"), limit=160)
    proactive_hint = bool(
        request_id
        or metadata.get("direct_proactive") is True
        or metadata.get("desktop_action") == "approve_qq"
        or metadata.get("source") in {"xinyu_desktop_shell", "xinyu_proactive_direct_sender"}
    )
    if not proactive_hint:
        return False

    path = _proactive_request_state_path(root)
    state = _read_text_file(path)
    if not state:
        return False

    state_request_id = _state_field(state, "request_id", "")
    state_message_id = _state_field(state, "qq_outbox_message_id", "") or _state_field(state, "adapter_message_id", "")
    request_matches = bool(request_id and state_request_id and request_id == state_request_id)
    message_matches = bool(message_id and state_message_id and message_id == state_message_id)
    if not request_matches and not message_matches:
        return False

    request_status = "sent" if ack_status == "sent" else "failed"
    answer_state = "sent_waiting_owner_reply" if ack_status == "sent" else "not_requested_failed"
    error_text = _one_line(adapter_error or ("" if ack_status == "sent" else f"qq_outbox_{ack_status}"), limit=500)
    adapter_ref = _one_line(adapter_message_id or message_id, limit=160)

    updated = _replace_frontmatter_field(state, "updated_at", _timestamp_or_now_iso(updated_at))
    updated = _replace_list_field(updated, "status", request_status)
    updated = _replace_list_field(updated, "request_answer_state", answer_state)
    updated = _replace_list_field(updated, "qq_outbox_message_id", message_id or "none")
    updated = _replace_list_field(updated, "last_ack_status", ack_status)
    updated = _replace_list_field(updated, "last_acked_at", _timestamp_or_now_iso(updated_at))
    updated = _replace_list_field(updated, "adapter_message_id", adapter_ref or "none")
    updated = _replace_list_field(updated, "adapter_error", error_text or "none")
    _atomic_write_text(path, updated.rstrip() + "\n")
    return True


def _proactive_dispatch_state_path(root: Path) -> Path:
    return proactive_delivery_state_paths(root).proactive_dispatch_state


def _update_proactive_dispatch_from_outbox_ack(
    root: Path,
    item: dict[str, Any],
    *,
    ack_status: str,
    adapter_message_id: str,
    adapter_error: str,
    updated_at: str,
) -> bool:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    request_id = _one_line(
        metadata.get("proactive_request_id")
        or metadata.get("request_id")
        or metadata.get("desktop_candidate_id"),
        limit=160,
    )
    claim_id = _one_line(metadata.get("claim_id"), limit=160)
    message_id = _one_line(item.get("id"), limit=160)
    proactive_hint = bool(
        request_id
        or claim_id
        or metadata.get("direct_proactive") is True
        or metadata.get("desktop_action") == "approve_qq"
        or metadata.get("source") in {"xinyu_desktop_shell", "xinyu_proactive_direct_sender"}
    )
    if not proactive_hint:
        return False

    path = _proactive_dispatch_state_path(root)
    state = _read_text_file(path)
    if not state:
        return False

    state_claim_id = _state_field(state, "last_claim_id", "")
    state_request_id = _state_field(state, "proactive_request_id", "")
    state_adapter_ref = _state_field(state, "adapter_message_id", "")
    claim_matches = bool(claim_id and state_claim_id and claim_id == state_claim_id)
    request_matches = bool(request_id and state_request_id and request_id == state_request_id)
    message_matches = bool(message_id and state_adapter_ref and message_id == state_adapter_ref)
    if not claim_matches and not request_matches and not message_matches:
        return False

    error_text = _one_line(adapter_error or ("" if ack_status == "sent" else f"qq_outbox_{ack_status}"), limit=500)
    adapter_ref = _one_line(adapter_message_id or message_id, limit=160)
    timestamp = _timestamp_or_now_iso(updated_at)
    updated = _replace_frontmatter_field(state, "updated_at", timestamp)
    updated = _replace_list_field(updated, "last_claim_status", ack_status)
    updated = _replace_list_field(updated, "last_ack_status", ack_status)
    updated = _replace_list_field(updated, "last_acked_at", timestamp)
    updated = _replace_list_field(updated, "adapter_message_id", adapter_ref or "none")
    updated = _replace_list_field(updated, "adapter_error", error_text or "none")
    _atomic_write_text(path, updated.rstrip() + "\n")
    return True


def _write_json(path: Path, data: dict[str, Any]) -> None:
    data["version"] = QUEUE_VERSION
    data["updated_at"] = _now()
    _atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


@dataclass
class _QueueLock:
    path: Path
    timeout_seconds: float = 3.0
    stale_seconds: float = 30.0

    _fd: int | None = None

    def __enter__(self) -> "_QueueLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        while True:
            try:
                self._fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode("ascii", errors="ignore"))
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > self.stale_seconds:
                        self.path.unlink()
                        continue
                except OSError:
                    pass
                if time.monotonic() - started >= self.timeout_seconds:
                    raise TimeoutError(f"QQ outbox queue lock timed out: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def _message_id(source: str, dedupe_key: str) -> str:
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    safe_source = re.sub(r"[^a-zA-Z0-9_-]+", "-", source or "qq-outbox").strip("-")[:32] or "qq-outbox"
    safe_key = re.sub(r"[^a-zA-Z0-9_-]+", "-", dedupe_key or "").strip("-")[:48]
    suffix = safe_key or str(int(time.time() * 1000))[-8:]
    return f"{safe_source}-{stamp}-{suffix}"


def _write_state(root: Path, data: dict[str, Any], *, last_event: str, last_message_id: str = "") -> None:
    items = [item for item in data.get("items", []) if isinstance(item, dict)]
    summary = summarize_outbox_items(items)
    now = _safe_str(data.get("updated_at"), _now())
    text = f"""---
title: QQ Outbox Dispatch State
memory_type: qq_outbox_dispatch_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: core_bridge
created_at: {now}
updated_at: {now}
importance_score: 84
impact_score: 86
confidence_score: 94
status: active
tags: [qq, outbox, dispatch, codex, adapter]
---

# QQ Outbox Dispatch State

## Queue
- last_event: {last_event}
- last_message_id: {last_message_id or "none"}
- queued_count: {summary["queued_count"]}
- claimed_count: {summary["claimed_count"]}
- sent_count: {summary["sent_count"]}
- failed_count: {summary["failed_count"]}
- dead_count: {summary["dead_count"]}
- suppressed_count: {summary["suppressed_count"]}
- unknown_status_count: {summary["unknown_status_count"]}
- recent_failed_count: {summary["recent_failed_count"]}
- recent_dead_count: {summary["recent_dead_count"]}
- last_failed_at: {summary["last_failed_at"]}
- last_dead_at: {summary["last_dead_at"]}

## Boundaries
- Core may enqueue owner-private completion summaries.
- Gateway claims one message at a time and sends through the existing OneBot WebSocket.
- Gateway must ack each send result.
- Text messages must not expose raw local paths, credentials, stdout, stderr, or hidden reasoning.
- Image dispatch may carry a local image_path only for adapter delivery; the gateway must not echo that path as visible QQ text.
- File dispatch may carry a local file_path only for adapter delivery; the gateway must not echo that path as visible QQ text.
"""
    _atomic_write_text(_state_path(root), text)


def enqueue_qq_outbox_message(
    root: Path,
    *,
    user_id: str,
    message: str = "",
    source: str,
    dedupe_key: str = "",
    image_path: str = "",
    file_path: str = "",
    file_name: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_id = _one_line(user_id, limit=64)
    message = _one_line(message)
    source = _one_line(source or "qq_outbox", limit=80)
    dedupe_key = _one_line(dedupe_key, limit=120)
    normalized_image_path = ""
    if image_path:
        normalized_image_path, image_notes = _normalize_local_image_path(root, image_path)
        if image_notes:
            return {"accepted": False, "queued": False, "message_id": "", "notes": image_notes}
    normalized_file_path = ""
    normalized_file_name = ""
    if file_path:
        if normalized_image_path:
            return {"accepted": False, "queued": False, "message_id": "", "notes": ["multiple_attachment_paths"]}
        normalized_file_path, file_notes = _normalize_local_file_path(root, file_path)
        if file_notes:
            return {"accepted": False, "queued": False, "message_id": "", "notes": file_notes}
        normalized_file_name = _normalize_file_name(file_name, normalized_file_path)
    if not user_id or user_id == "none":
        return {"accepted": False, "queued": False, "message_id": "", "notes": ["missing_user_id"]}
    if (not message or message == "none") and not normalized_image_path and not normalized_file_path:
        return {"accepted": False, "queued": False, "message_id": "", "notes": ["missing_message"]}

    with _QueueLock(_lock_path(root)):
        path = _queue_path(root)
        data = _read_json(path)
        items = [item for item in data.get("items", []) if isinstance(item, dict)]
        if dedupe_key:
            for item in items:
                if item.get("dedupe_key") == dedupe_key and item.get("status") in {"queued", "claimed", "sent"}:
                    return {
                        "accepted": True,
                        "queued": False,
                        "message_id": _safe_str(item.get("id")),
                        "notes": ["duplicate_dedupe_key"],
                    }

        message_id = _message_id(source, dedupe_key)
        message_type = "file" if normalized_file_path else ("image" if normalized_image_path else "text")
        created_at = _timestamp_or_now_iso(_now())
        item = {
            "id": message_id,
            "status": "queued",
            "message_type": message_type,
            "created_at": _timestamp_or_now_iso(created_at),
            "updated_at": _timestamp_or_now_iso(created_at),
            "source": source,
            "dedupe_key": dedupe_key,
            "target": {"message_kind": "private", "user_id": user_id, "group_id": ""},
            "message": message,
            "image_path": normalized_image_path,
            "file_path": normalized_file_path,
            "file_name": normalized_file_name,
            "attempts": 0,
            "claim_id": "",
            "claimed_at": "",
            "acked_at": "",
            "adapter": "",
            "adapter_message_id": "",
            "adapter_error": "",
            "metadata": metadata if isinstance(metadata, dict) else {},
        }
        items.append(item)
        data["items"] = items
        _write_json(path, data)
        _write_state(root, data, last_event="enqueue", last_message_id=message_id)
        return {"accepted": True, "queued": True, "message_id": message_id, "notes": ["queued"]}


def enqueue_owner_qq_outbox_message(
    root: Path,
    *,
    message: str,
    source: str,
    dedupe_key: str = "",
    metadata: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    user_id, notes = _owner_user_id_from_config(root, config_path=config_path)
    if notes:
        return {"accepted": False, "queued": False, "message_id": "", "notes": notes}
    return enqueue_qq_outbox_message(
        root,
        user_id=user_id,
        message=message,
        source=source,
        dedupe_key=dedupe_key,
        metadata=metadata,
    )


def enqueue_qq_outbox_image(
    root: Path,
    *,
    user_id: str,
    image_path: str,
    caption: str = "",
    source: str,
    dedupe_key: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return enqueue_qq_outbox_message(
        root,
        user_id=user_id,
        message=caption,
        source=source,
        dedupe_key=dedupe_key,
        image_path=image_path,
        metadata=metadata,
    )


def enqueue_owner_qq_outbox_image(
    root: Path,
    *,
    image_path: str,
    caption: str = "",
    source: str = "owner_image_dispatch",
    dedupe_key: str = "",
    metadata: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    user_id, notes = _owner_user_id_from_config(root, config_path=config_path)
    if notes:
        return {"accepted": False, "queued": False, "message_id": "", "notes": notes}
    return enqueue_qq_outbox_image(
        root,
        user_id=user_id,
        image_path=image_path,
        caption=caption,
        source=source,
        dedupe_key=dedupe_key,
        metadata=metadata,
    )


def enqueue_qq_outbox_file(
    root: Path,
    *,
    user_id: str,
    file_path: str,
    name: str = "",
    caption: str = "",
    source: str,
    dedupe_key: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return enqueue_qq_outbox_message(
        root,
        user_id=user_id,
        message=caption,
        source=source,
        dedupe_key=dedupe_key,
        file_path=file_path,
        file_name=name,
        metadata=metadata,
    )


def enqueue_owner_qq_outbox_file(
    root: Path,
    *,
    file_path: str,
    name: str = "",
    caption: str = "",
    source: str = "owner_file_dispatch",
    dedupe_key: str = "",
    metadata: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    user_id, notes = _owner_user_id_from_config(root, config_path=config_path)
    if notes:
        return {"accepted": False, "queued": False, "message_id": "", "notes": notes}
    return enqueue_qq_outbox_file(
        root,
        user_id=user_id,
        file_path=file_path,
        name=name,
        caption=caption,
        source=source,
        dedupe_key=dedupe_key,
        metadata=metadata,
    )


def _seconds_since(value: str, default: float = 999999.0) -> float:
    parsed = _parse_time(value)
    if parsed is None:
        return default
    return max(0.0, (datetime.now().astimezone() - parsed).total_seconds())


def _metadata_bool(metadata: dict[str, Any], key: str) -> bool:
    value = metadata.get(key)
    if isinstance(value, bool):
        return value
    return _safe_str(value).strip().lower() in {"1", "true", "yes", "on"}


def _control_plane_visible_delivery_suppressed(item: dict[str, Any]) -> bool:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    if not _metadata_bool(metadata, "control_plane"):
        return False
    return not (
        _metadata_bool(metadata, "visible_control_plane_allowed")
        or _metadata_bool(metadata, "qq_visible_control_plane_allowed")
    )


def claim_next_qq_outbox_message(root: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    claim_id = _one_line(payload.get("claim_id") or f"qq-gateway-{int(time.time())}", limit=120)
    adapter = _one_line(payload.get("adapter") or "xinyu_native_qq_gateway", limit=80)
    retry_after_seconds = max(5, int(payload.get("retry_after_seconds") or 60))
    claim_timeout_seconds = max(10, int(payload.get("claim_timeout_seconds") or 120))

    with _QueueLock(_lock_path(root)):
        path = _queue_path(root)
        data = _read_json(path)
        items = [item for item in data.get("items", []) if isinstance(item, dict)]
        for item in items:
            if item.get("status") == "claimed" and _seconds_since(_safe_str(item.get("claimed_at"))) > claim_timeout_seconds:
                item["status"] = "queued"
                item["claim_id"] = ""
                item["claimed_at"] = ""
                item["updated_at"] = _now()

        selected: dict[str, Any] | None = None
        suppressed_count = 0
        for item in items:
            status = _safe_str(item.get("status"), "queued")
            attempts = int(item.get("attempts") or 0)
            if status in {"queued", "failed"} and _control_plane_visible_delivery_suppressed(item):
                item["status"] = "suppressed"
                item["updated_at"] = _now()
                item["adapter_error"] = "control_plane_visible_delivery_suppressed"
                suppressed_count += 1
                continue
            if status == "queued":
                selected = item
                break
            if status == "failed" and attempts < MAX_ATTEMPTS and _seconds_since(_safe_str(item.get("acked_at"))) >= retry_after_seconds:
                selected = item
                break

        if selected is None:
            data["items"] = items
            _write_json(path, data)
            last_event = "suppress_control_plane" if suppressed_count else "claim_empty"
            _write_state(root, data, last_event=last_event)
            notes = ["empty"]
            if suppressed_count:
                notes.append(f"control_plane_suppressed:{suppressed_count}")
            return {"accepted": True, "message_claimed": False, "claim_id": claim_id, "notes": notes}

        selected["status"] = "claimed"
        selected["attempts"] = int(selected.get("attempts") or 0) + 1
        selected["claim_id"] = claim_id
        selected["claimed_at"] = _now()
        selected["updated_at"] = _now()
        selected["adapter"] = adapter
        data["items"] = items
        _write_json(path, data)
        _write_state(root, data, last_event="claim", last_message_id=_safe_str(selected.get("id")))
        return {
            "accepted": True,
            "message_claimed": True,
            "message_id": _safe_str(selected.get("id")),
            "claim_id": claim_id,
            "target": selected.get("target") if isinstance(selected.get("target"), dict) else {},
            "message_type": _safe_str(
                selected.get("message_type"),
                "file" if selected.get("file_path") else ("image" if selected.get("image_path") else "text"),
            ),
            "message": _safe_str(selected.get("message")),
            "image_path": _safe_str(selected.get("image_path")),
            "file_path": _safe_str(selected.get("file_path")),
            "file_name": _safe_str(selected.get("file_name")),
            "attempts": selected["attempts"],
            "source": _safe_str(selected.get("source")),
            "metadata": selected.get("metadata") if isinstance(selected.get("metadata"), dict) else {},
            "notes": ["claimed"],
        }


def ack_qq_outbox_message(root: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    message_id = _one_line(payload.get("message_id"), limit=160)
    claim_id = _one_line(payload.get("claim_id"), limit=120)
    ack_status = _one_line(payload.get("ack_status") or payload.get("status") or "sent", limit=32).lower()
    adapter_message_id = _one_line(payload.get("adapter_message_id") or payload.get("message_id_from_adapter"), limit=160)
    adapter_error = _one_line(payload.get("adapter_error") or payload.get("error"), limit=500)
    if ack_status not in {"sent", "failed"}:
        return {"accepted": False, "ack_recorded": False, "notes": ["invalid_ack_status"]}

    with _QueueLock(_lock_path(root)):
        path = _queue_path(root)
        data = _read_json(path)
        items = [item for item in data.get("items", []) if isinstance(item, dict)]
        selected = None
        for item in items:
            if _safe_str(item.get("id")) == message_id:
                selected = item
                break
        if selected is None:
            return {"accepted": True, "ack_recorded": False, "message_id": message_id, "notes": ["message_not_found"]}
        if claim_id and _safe_str(selected.get("claim_id")) != claim_id:
            return {
                "accepted": True,
                "ack_recorded": False,
                "message_id": message_id,
                "expected_claim_id": _safe_str(selected.get("claim_id")),
                "notes": ["claim_id_mismatch"],
            }

        attempts = int(selected.get("attempts") or 0)
        current_status = _safe_str(selected.get("status")).lower()
        if current_status in {"sent", "dead"}:
            notes = ["terminal_ack_already_recorded"]
            if current_status == "sent" and ack_status != "sent":
                notes.append("late_ack_ignored_terminal_sent")
            elif current_status == "dead" and ack_status != "failed":
                notes.append("late_ack_ignored_terminal_dead")
            return {
                "accepted": True,
                "ack_recorded": False,
                "message_id": message_id,
                "ack_status": current_status,
                "attempts": attempts,
                "notes": notes,
            }

        final_status = "sent" if ack_status == "sent" else ("dead" if attempts >= MAX_ATTEMPTS else "failed")
        acked_at = _now()
        selected["status"] = final_status
        selected["acked_at"] = acked_at
        selected["updated_at"] = acked_at
        selected["adapter_message_id"] = adapter_message_id or "none"
        selected["adapter_error"] = adapter_error or "none"
        data["items"] = items
        _write_json(path, data)
        _write_state(root, data, last_event=f"ack_{final_status}", last_message_id=message_id)
        request_updated = _update_proactive_request_from_outbox_ack(
            root,
            selected,
            ack_status=final_status,
            adapter_message_id=adapter_message_id or message_id,
            adapter_error=adapter_error,
            updated_at=acked_at,
        )
        dispatch_updated = _update_proactive_dispatch_from_outbox_ack(
            root,
            selected,
            ack_status=final_status,
            adapter_message_id=adapter_message_id or message_id,
            adapter_error=adapter_error,
            updated_at=acked_at,
        )
        return {
            "accepted": True,
            "ack_recorded": True,
            "message_id": message_id,
            "ack_status": final_status,
            "attempts": attempts,
            "notes": (
                ["ack_recorded"]
                + (["proactive_request_state_updated"] if request_updated else [])
                + (["proactive_dispatch_state_updated"] if dispatch_updated else [])
            ),
        }
