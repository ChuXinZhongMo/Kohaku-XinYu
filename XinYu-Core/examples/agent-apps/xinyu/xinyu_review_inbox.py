from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_qq_outbox import enqueue_qq_outbox_message


CURSOR_REL = Path("memory/context/review_inbox_cursor.json")
DECISIONS_REL = Path("memory/context/review_inbox_decisions.json")
STATE_REL = Path("memory/context/review_inbox_state.md")
TRACE_REL = Path("runtime/review_inbox_trace.jsonl")
LOCK_REL = Path("memory/context/.review_inbox.lock")

VOICE_REVIEW_REL = Path("memory/self/voice_profile_review_state.md")
LEARNING_QUALITY_REL = Path("memory/knowledge/learning_quality_state.md")

CURSOR_VERSION = 1
DECISION_VERSION = 1
DEFAULT_TTL_SECONDS = 24 * 3600


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _one_line(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def _read_json(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return dict(default)
    return data if isinstance(data, dict) else dict(default)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _append_trace(root: Path, payload: dict[str, Any]) -> None:
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


@dataclass
class _FileLock:
    path: Path
    timeout_seconds: float = 3.0
    stale_seconds: float = 30.0
    _fd: int | None = None

    def __enter__(self) -> "_FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        while True:
            try:
                self._fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode("ascii", errors="ignore"))
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > self.stale_seconds:
                        self.path.unlink()
                        continue
                except OSError:
                    pass
                if time.monotonic() - started >= self.timeout_seconds:
                    raise TimeoutError(f"review inbox lock timed out: {self.path}")
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


def _field(block: str, name: str, default: str = "") -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(name)}:\s*(.*)$", block or "")
    if not match:
        return default
    return re.sub(r"\s+", " ", match.group(1).strip()) or default


def _section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text or "")
    return match.group(1) if match else ""


def _md_blocks(text: str, heading_prefix: str = "###") -> list[tuple[str, str]]:
    matches = list(re.finditer(rf"(?m)^{re.escape(heading_prefix)}\s+(.+?)\s*$", text or ""))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(1).strip(), text[start:end].strip()))
    return blocks


def _load_decisions(root: Path) -> dict[str, Any]:
    data = _read_json(
        root / DECISIONS_REL,
        default={"version": DECISION_VERSION, "updated_at": _now(), "decisions": []},
    )
    if not isinstance(data.get("decisions"), list):
        data["decisions"] = []
    data.setdefault("version", DECISION_VERSION)
    data.setdefault("updated_at", _now())
    return data


def _decision_applies(decisions: dict[str, Any], *, action_kind: str, record_key: str, content_hash: str) -> bool:
    for item in reversed([item for item in decisions.get("decisions", []) if isinstance(item, dict)]):
        if _safe_str(item.get("action_kind")) != action_kind:
            continue
        if _safe_str(item.get("record_key")) != record_key:
            continue
        if _safe_str(item.get("content_hash")) != content_hash:
            continue
        if _safe_str(item.get("decision")) in {"accepted", "rejected", "modified"}:
            return True
    return False


def _voice_items(root: Path, decisions: dict[str, Any]) -> list[dict[str, Any]]:
    rel = VOICE_REVIEW_REL.as_posix()
    text = _read_text(root / VOICE_REVIEW_REL)
    if _field(text, "review_status") != "pending_owner_review":
        return []

    items: list[dict[str, Any]] = []
    for heading, block in _md_blocks(_section(text, "## Candidates")):
        candidate_id = _field(block, "candidate_id", heading)
        if _field(block, "owner_review_status") != "pending":
            continue
        if _field(block, "accepted", "no").lower() == "yes" or _field(block, "rejected", "no").lower() == "yes":
            continue
        content = f"### {heading}\n{block}".strip()
        content_hash = _sha256_text(content)
        if _decision_applies(
            decisions,
            action_kind="voice_profile_candidate",
            record_key=candidate_id,
            content_hash=content_hash,
        ):
            continue
        cluster = _field(block, "cluster", candidate_id)
        proposed = _field(block, "proposed_profile_pressure", cluster)
        items.append(
            {
                "action_kind": "voice_profile_candidate",
                "source_kind": "voice",
                "source_path": rel,
                "item_id": candidate_id,
                "record_key": candidate_id,
                "title": cluster,
                "summary": proposed,
                "detail": _field(block, "owner_correction_examples", "none"),
                "content_hash": content_hash,
                "transaction_group": "",
            }
        )
    return items


def _parse_warning_line(line: str) -> dict[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("- ") or stripped == "- none":
        return None
    body = stripped[2:].strip()
    if ":" not in body:
        return None
    kind, rest = body.split(":", 1)
    values: dict[str, str] = {"kind": kind.strip(), "raw": stripped}
    for part in rest.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key.strip()] = value.strip()
    if not values.get("kind") or not values.get("target"):
        return None
    return values


def _learning_items(root: Path, decisions: dict[str, Any]) -> list[dict[str, Any]]:
    rel = LEARNING_QUALITY_REL.as_posix()
    text = _read_text(root / LEARNING_QUALITY_REL)
    if _field(text, "quality_grade") != "review_needed":
        return []

    items: list[dict[str, Any]] = []
    for line in _section(text, "## Warnings").splitlines():
        parsed = _parse_warning_line(line)
        if parsed is None:
            continue
        content_hash = _sha256_text(parsed["raw"])
        record_key = f"{parsed['kind']}::{parsed['target']}"
        if _decision_applies(
            decisions,
            action_kind="learning_quality_warning",
            record_key=record_key,
            content_hash=content_hash,
        ):
            continue
        detail = parsed.get("detail", "none")
        items.append(
            {
                "action_kind": "learning_quality_warning",
                "source_kind": "learning",
                "source_path": rel,
                "item_id": record_key,
                "record_key": record_key,
                "title": f"{parsed['kind']} {parsed['target']}",
                "summary": detail,
                "detail": f"severity={parsed.get('severity', 'unknown')}",
                "content_hash": content_hash,
                "transaction_group": "",
            }
        )
    return items


def _interleave(groups: list[list[dict[str, Any]]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    offset = 0
    while len(selected) < limit:
        progressed = False
        for group in groups:
            if offset < len(group):
                selected.append(group[offset])
                progressed = True
                if len(selected) >= limit:
                    break
        if not progressed:
            break
        offset += 1
    return selected


def _discover_items(root: Path, *, limit: int) -> list[dict[str, Any]]:
    decisions = _load_decisions(root)
    return _interleave(
        [
            _voice_items(root, decisions),
            _learning_items(root, decisions),
        ],
        limit=max(1, limit),
    )


def _batch_hash(items: list[dict[str, Any]]) -> str:
    lines = [
        "|".join(
            [
                _safe_str(item.get("action_kind")),
                _safe_str(item.get("source_path")),
                _safe_str(item.get("record_key")),
                _safe_str(item.get("content_hash")),
            ]
        )
        for item in items
    ]
    return _sha256_text("\n".join(lines))


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _cursor_expired(cursor: dict[str, Any], *, now: str | None = None) -> bool:
    expires_at = _parse_iso(_safe_str(cursor.get("expires_at")))
    if expires_at is None:
        return True
    current = _parse_iso(now or _now()) or datetime.now().astimezone()
    return current >= expires_at


def _render_card(cursor: dict[str, Any]) -> str:
    items = [item for item in cursor.get("items", []) if isinstance(item, dict)]
    lines = [
        f"[Review Inbox] {len(items)} item(s) need owner review. batch={_safe_str(cursor.get('batch_id'), 'unknown')}",
    ]
    for item in items:
        lines.append(
            f"{item.get('index')}. {_one_line(item.get('source_kind'), limit=32)}: "
            f"{_one_line(item.get('title'), limit=80)} - {_one_line(item.get('summary'), limit=150)}"
        )
    lines.append("Reply: !ok all | !rej 1 | !mod 2 <rewrite>")
    return " ".join(lines)


def _write_state(
    root: Path,
    *,
    status: str,
    batch_id: str = "none",
    pending_count: int = 0,
    queued: bool = False,
    processed: int = 0,
    stale: int = 0,
    note: str = "none",
) -> None:
    observed_at = _now()
    text = f"""---
title: Review Inbox State
memory_type: review_inbox_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_review_inbox
updated_at: {observed_at}
status: active
tags: [review, qq, control-plane]
---

# Review Inbox State

## Latest
- observed_at: {observed_at}
- status: {_one_line(status)}
- batch_id: {_one_line(batch_id, limit=120)}
- pending_count: {pending_count}
- queued: {str(queued).lower()}
- processed: {processed}
- stale: {stale}
- note: {_one_line(note, limit=300)}

## Boundaries
- QQ review commands are control-plane input, not dialogue memory.
- Cursor indices are batch-local aliases backed by content hashes.
- Decisions are recorded in an overlay instead of rewriting source warnings directly.
"""
    _atomic_write_text(root / STATE_REL, text)


def _cursor_for_items(
    items: list[dict[str, Any]],
    *,
    observed_at: str,
    ttl_seconds: int,
) -> dict[str, Any]:
    digest = _batch_hash(items)
    expires_at = (datetime.now().astimezone() + timedelta(seconds=max(60, ttl_seconds))).isoformat(timespec="seconds")
    cursor_items = []
    for index, item in enumerate(items, start=1):
        cursor_items.append({**item, "index": index})
    return {
        "version": CURSOR_VERSION,
        "batch_id": f"rev-{_stamp()}-{digest[:8]}",
        "batch_hash": digest,
        "created_at": observed_at,
        "expires_at": expires_at,
        "items": cursor_items,
    }


def _generate_locked(
    root: Path,
    *,
    owner_user_id: str = "",
    max_items: int = 3,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    enqueue: bool = True,
    reason: str = "maintenance",
) -> dict[str, Any]:
    observed = _now()
    items = _discover_items(root, limit=max_items)
    if not items:
        _write_state(root, status="no_pending", pending_count=0, note=reason)
        _append_trace(
            root,
            {
                "event_kind": "review_inbox_no_pending",
                "observed_at": observed,
                "reason": reason,
            },
        )
        return {
            "accepted": True,
            "pending_count": 0,
            "batch_id": "",
            "queued": False,
            "notes": ["no_pending_review_items"],
        }

    new_hash = _batch_hash(items)
    cursor_path = root / CURSOR_REL
    existing = _read_json(cursor_path, default={})
    if (
        existing.get("version") == CURSOR_VERSION
        and _safe_str(existing.get("batch_hash")) == new_hash
        and not _cursor_expired(existing, now=observed)
    ):
        cursor = existing
        cursor_status = "cursor_reused"
    else:
        cursor = _cursor_for_items(items, observed_at=observed, ttl_seconds=ttl_seconds)
        _write_json(cursor_path, cursor)
        cursor_status = "cursor_created"

    queued = {"queued": False, "message_id": "", "notes": ["enqueue_skipped"]}
    owner = _one_line(owner_user_id, limit=64, default="")
    if enqueue and owner:
        queued = enqueue_qq_outbox_message(
            root,
            user_id=owner,
            message=_render_card(cursor),
            source="review_inbox",
            dedupe_key=f"review-inbox:{cursor.get('batch_hash')}",
            metadata={
                "batch_id": cursor.get("batch_id"),
                "batch_hash": cursor.get("batch_hash"),
                "control_plane": True,
            },
        )

    _write_state(
        root,
        status=cursor_status,
        batch_id=_safe_str(cursor.get("batch_id"), "unknown"),
        pending_count=len(cursor.get("items", [])),
        queued=bool(queued.get("queued")),
        note=",".join(_safe_str(note) for note in queued.get("notes", [])[:3]) or reason,
    )
    _append_trace(
        root,
        {
            "event_kind": cursor_status,
            "observed_at": observed,
            "batch_id": cursor.get("batch_id"),
            "batch_hash": cursor.get("batch_hash"),
            "pending_count": len(cursor.get("items", [])),
            "queued": bool(queued.get("queued")),
            "message_id": queued.get("message_id", ""),
            "reason": reason,
        },
    )
    return {
        "accepted": True,
        "pending_count": len(cursor.get("items", [])),
        "batch_id": _safe_str(cursor.get("batch_id")),
        "batch_hash": _safe_str(cursor.get("batch_hash")),
        "queued": bool(queued.get("queued")),
        "message_id": _safe_str(queued.get("message_id")),
        "notes": [cursor_status] + list(queued.get("notes", [])),
    }


def run_review_inbox_maintenance(
    root: Path,
    *,
    owner_user_id: str = "",
    max_items: int = 3,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    enqueue: bool = True,
    reason: str = "maintenance",
) -> dict[str, Any]:
    root = root.resolve()
    with _FileLock(root / LOCK_REL):
        return _generate_locked(
            root,
            owner_user_id=owner_user_id,
            max_items=max_items,
            ttl_seconds=ttl_seconds,
            enqueue=enqueue,
            reason=reason,
        )


def _resolve_current_item(root: Path, cursor_item: dict[str, Any]) -> dict[str, Any] | None:
    action_kind = _safe_str(cursor_item.get("action_kind"))
    record_key = _safe_str(cursor_item.get("record_key"))
    decisions = {"decisions": []}
    if action_kind == "voice_profile_candidate":
        for item in _voice_items(root, decisions):
            if item.get("record_key") == record_key:
                return item
    if action_kind == "learning_quality_warning":
        for item in _learning_items(root, decisions):
            if item.get("record_key") == record_key:
                return item
    return None


def _normalize_command(value: Any) -> str:
    command = _safe_str(value).strip().lower()
    if command in {"ok", "accept", "approve", "y", "yes"}:
        return "ok"
    if command in {"rej", "reject", "deny", "n", "no"}:
        return "rej"
    if command in {"mod", "modify", "rewrite"}:
        return "mod"
    return command


def _selected_items(cursor: dict[str, Any], payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    items = [item for item in cursor.get("items", []) if isinstance(item, dict)]
    by_index = {int(item.get("index")): item for item in items if str(item.get("index")).isdigit()}
    raw_indices = payload.get("indices")
    if raw_indices is None:
        raw_indices = payload.get("selectors")
    if raw_indices is None:
        raw_indices = payload.get("index")
    if isinstance(raw_indices, str):
        parts = [part.strip() for part in re.split(r"[\s,]+", raw_indices) if part.strip()]
    elif isinstance(raw_indices, (list, tuple, set)):
        parts = [str(part).strip() for part in raw_indices if str(part).strip()]
    elif raw_indices is None:
        parts = []
    else:
        parts = [str(raw_indices).strip()]
    if not parts:
        return [], "missing_index"
    if any(part.lower() == "all" for part in parts):
        return items, ""
    selected: list[dict[str, Any]] = []
    for part in parts:
        if not part.isdigit():
            return [], f"invalid_index:{part}"
        item = by_index.get(int(part))
        if item is None:
            return [], f"unknown_index:{part}"
        selected.append(item)
    return selected, ""


def _append_decision(
    decisions: dict[str, Any],
    *,
    cursor: dict[str, Any],
    item: dict[str, Any],
    command: str,
    user_id: str,
    message_id: str,
    mod_text: str = "",
) -> dict[str, Any]:
    decided_at = _now()
    decision = {
        "decision_id": f"review-decision-{_stamp()}-{len(decisions.get('decisions', [])) + 1}",
        "decided_at": decided_at,
        "batch_id": _safe_str(cursor.get("batch_id")),
        "batch_hash": _safe_str(cursor.get("batch_hash")),
        "index": item.get("index"),
        "item_id": _safe_str(item.get("item_id")),
        "record_key": _safe_str(item.get("record_key")),
        "source_path": _safe_str(item.get("source_path")),
        "action_kind": _safe_str(item.get("action_kind")),
        "content_hash": _safe_str(item.get("content_hash")),
        "command": command,
        "decision": {"ok": "accepted", "rej": "rejected", "mod": "modified"}.get(command, command),
        "mod_text": _one_line(mod_text, limit=1000, default=""),
        "user_id": _one_line(user_id, limit=80, default="unknown"),
        "message_id": _one_line(message_id, limit=120, default="unknown"),
    }
    decisions.setdefault("decisions", []).append(decision)
    decisions["version"] = DECISION_VERSION
    decisions["updated_at"] = decided_at
    return decision


def handle_review_inbox_command(root: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    payload = payload or {}
    with _FileLock(root / LOCK_REL):
        cursor = _read_json(root / CURSOR_REL, default={})
        if cursor.get("version") != CURSOR_VERSION or not cursor.get("items"):
            refreshed = _generate_locked(
                root,
                owner_user_id=_safe_str(payload.get("user_id")),
                reason="command_without_cursor",
            )
            return {
                "accepted": False,
                "reply": "Review command rejected: no active review card. I refreshed the inbox.",
                "processed_count": 0,
                "stale_count": 0,
                "notes": ["missing_cursor"] + list(refreshed.get("notes", [])),
            }
        if _cursor_expired(cursor):
            refreshed = _generate_locked(
                root,
                owner_user_id=_safe_str(payload.get("user_id")),
                reason="expired_cursor",
            )
            return {
                "accepted": False,
                "reply": "Review command rejected: this review card expired. I refreshed the inbox.",
                "processed_count": 0,
                "stale_count": 0,
                "notes": ["expired_cursor"] + list(refreshed.get("notes", [])),
            }

        command = _normalize_command(payload.get("command"))
        if command not in {"ok", "rej", "mod"}:
            return {
                "accepted": False,
                "reply": "Review command rejected: unknown command.",
                "processed_count": 0,
                "stale_count": 0,
                "notes": [f"unknown_command:{command or 'empty'}"],
            }

        selected, error = _selected_items(cursor, payload)
        if error:
            return {
                "accepted": False,
                "reply": f"Review command rejected: {error}.",
                "processed_count": 0,
                "stale_count": 0,
                "notes": [error],
            }
        if command == "mod":
            if len(selected) != 1:
                return {
                    "accepted": False,
                    "reply": "Review command rejected: !mod only accepts one index.",
                    "processed_count": 0,
                    "stale_count": 0,
                    "notes": ["mod_requires_single_item"],
                }
            if not _safe_str(payload.get("mod_text")).strip():
                return {
                    "accepted": False,
                    "reply": "Review command rejected: !mod needs rewrite text.",
                    "processed_count": 0,
                    "stale_count": 0,
                    "notes": ["missing_mod_text"],
                }

        decisions = _load_decisions(root)
        processed: list[dict[str, Any]] = []
        stale: list[dict[str, Any]] = []
        for item in selected:
            current = _resolve_current_item(root, item)
            if current is None or _safe_str(current.get("content_hash")) != _safe_str(item.get("content_hash")):
                stale.append(item)
                continue
            processed.append(
                _append_decision(
                    decisions,
                    cursor=cursor,
                    item=item,
                    command=command,
                    user_id=_safe_str(payload.get("user_id")),
                    message_id=_safe_str(payload.get("message_id")),
                    mod_text=_safe_str(payload.get("mod_text")),
                )
            )

        if processed:
            _write_json(root / DECISIONS_REL, decisions)

        refreshed = _generate_locked(
            root,
            owner_user_id=_safe_str(payload.get("user_id")),
            reason="command_after_decision" if processed else "command_stale_refresh",
        )
        processed_count = len(processed)
        stale_count = len(stale)
        reply = f"Review processed: {processed_count} applied"
        if stale_count:
            reply += f", {stale_count} stale"
        if refreshed.get("pending_count"):
            reply += "; refreshed card queued."
        else:
            reply += "; inbox is clear."

        _write_state(
            root,
            status="command_processed",
            batch_id=_safe_str(cursor.get("batch_id"), "unknown"),
            pending_count=int(refreshed.get("pending_count") or 0),
            queued=bool(refreshed.get("queued")),
            processed=processed_count,
            stale=stale_count,
            note=command,
        )
        _append_trace(
            root,
            {
                "event_kind": "command_processed",
                "observed_at": _now(),
                "batch_id": cursor.get("batch_id"),
                "command": command,
                "processed_count": processed_count,
                "stale_count": stale_count,
                "refreshed_batch_id": refreshed.get("batch_id", ""),
            },
        )
        return {
            "accepted": True,
            "reply": reply,
            "processed_count": processed_count,
            "stale_count": stale_count,
            "refreshed": refreshed,
            "notes": ["review_command_processed"],
        }

