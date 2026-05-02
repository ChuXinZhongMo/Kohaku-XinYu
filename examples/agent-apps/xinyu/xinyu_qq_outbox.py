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


QUEUE_VERSION = 1
MAX_MESSAGE_CHARS = 1200
MAX_ATTEMPTS = 3


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _one_line(value: Any, *, limit: int = MAX_MESSAGE_CHARS) -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if limit > 0 and len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def _queue_path(root: Path) -> Path:
    return root / "memory/context/qq_outbox_queue.json"


def _state_path(root: Path) -> Path:
    return root / "memory/context/qq_outbox_dispatch_state.md"


def _lock_path(root: Path) -> Path:
    return root / "memory/context/.qq_outbox_queue.lock"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": QUEUE_VERSION, "updated_at": _now(), "items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"version": QUEUE_VERSION, "updated_at": _now(), "items": []}
    if not isinstance(data, dict):
        return {"version": QUEUE_VERSION, "updated_at": _now(), "items": []}
    items = data.get("items")
    if not isinstance(items, list):
        data["items"] = []
    data.setdefault("version", QUEUE_VERSION)
    data.setdefault("updated_at", _now())
    return data


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


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


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    result = {"queued": 0, "claimed": 0, "sent": 0, "failed": 0, "dead": 0}
    for item in items:
        status = _safe_str(item.get("status"), "queued")
        if status in result:
            result[status] += 1
    return result


def _write_state(root: Path, data: dict[str, Any], *, last_event: str, last_message_id: str = "") -> None:
    items = [item for item in data.get("items", []) if isinstance(item, dict)]
    counts = _counts(items)
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
- queued_count: {counts["queued"]}
- claimed_count: {counts["claimed"]}
- sent_count: {counts["sent"]}
- failed_count: {counts["failed"]}
- dead_count: {counts["dead"]}

## Boundaries
- Core may enqueue owner-private completion summaries.
- Gateway claims one message at a time and sends through the existing OneBot WebSocket.
- Gateway must ack each send result.
- This queue must not expose raw local paths, credentials, stdout, stderr, or hidden reasoning.
"""
    _atomic_write_text(_state_path(root), text)


def enqueue_qq_outbox_message(
    root: Path,
    *,
    user_id: str,
    message: str,
    source: str,
    dedupe_key: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_id = _one_line(user_id, limit=64)
    message = _one_line(message)
    source = _one_line(source or "qq_outbox", limit=80)
    dedupe_key = _one_line(dedupe_key, limit=120)
    if not user_id or user_id == "none":
        return {"accepted": False, "queued": False, "message_id": "", "notes": ["missing_user_id"]}
    if not message or message == "none":
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
        item = {
            "id": message_id,
            "status": "queued",
            "created_at": _now(),
            "updated_at": _now(),
            "source": source,
            "dedupe_key": dedupe_key,
            "target": {"message_kind": "private", "user_id": user_id, "group_id": ""},
            "message": message,
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


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _seconds_since(value: str, default: float = 999999.0) -> float:
    parsed = _parse_time(value)
    if parsed is None:
        return default
    return max(0.0, (datetime.now().astimezone() - parsed).total_seconds())


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
        for item in items:
            status = _safe_str(item.get("status"), "queued")
            attempts = int(item.get("attempts") or 0)
            if status == "queued":
                selected = item
                break
            if status == "failed" and attempts < MAX_ATTEMPTS and _seconds_since(_safe_str(item.get("acked_at"))) >= retry_after_seconds:
                selected = item
                break

        if selected is None:
            data["items"] = items
            _write_json(path, data)
            _write_state(root, data, last_event="claim_empty")
            return {"accepted": True, "message_claimed": False, "claim_id": claim_id, "notes": ["empty"]}

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
            "message": _safe_str(selected.get("message")),
            "attempts": selected["attempts"],
            "source": _safe_str(selected.get("source")),
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
        final_status = "sent" if ack_status == "sent" else ("dead" if attempts >= MAX_ATTEMPTS else "failed")
        selected["status"] = final_status
        selected["acked_at"] = _now()
        selected["updated_at"] = _now()
        selected["adapter_message_id"] = adapter_message_id or "none"
        selected["adapter_error"] = adapter_error or "none"
        data["items"] = items
        _write_json(path, data)
        _write_state(root, data, last_event=f"ack_{final_status}", last_message_id=message_id)
        return {
            "accepted": True,
            "ack_recorded": True,
            "message_id": message_id,
            "ack_status": final_status,
            "attempts": attempts,
            "notes": ["ack_recorded"],
        }
