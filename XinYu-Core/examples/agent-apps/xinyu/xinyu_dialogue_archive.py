from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ARCHIVE_REL_PATH = Path("runtime") / "dialogue_archive" / "dialogue.sqlite3"
SCHEMA_VERSION = 2

OWNER_PRIVATE_SCOPE = "owner_private"
GROUP_SCOPE = "qq_group"
NON_OWNER_PRIVATE_SCOPE = "qq_private_non_owner"
SYSTEM_SCOPE = "system_maintenance"
CODEX_CALLBACK_SCOPE = "codex_callback"
SEMANTIC_MODEL = "local_hash_v1"
LOCAL_CONTEXT_PATH_RE = re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\|file://)[^\s<>'\"]+")

SEMANTIC_SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("search", "lookup", "find", "搜索", "搜", "检索", "查找", "找资料"),
    ("blocked", "failed", "denied", "不能", "不行", "失败", "拦住", "权限", "受限"),
    ("codex", "Codex", "辅助脑", "委托"),
    ("voice", "style", "语气", "说话", "接待腔", "AI味", "GPT味", "机械"),
    ("memory", "context", "记忆", "上下文", "连续性", "召回"),
    ("project", "runtime", "smoke", "项目", "运行时", "修复", "验证"),
)


@dataclass(frozen=True)
class DialogueScope:
    session_key: str
    session_key_hash: str
    scope: str
    channel: str
    privacy_scope: str
    owner_user_hash: str
    group_id_hash: str


@dataclass(frozen=True)
class DialogueArchiveRecord:
    message_id: int
    session_key_hash: str
    scope: str
    channel: str
    role: str
    text: str
    created_at: str
    message_type: str
    privacy_scope: str
    source_event_id: str
    reply_to_id: int | None
    codex_task_id: str
    quality_flags: dict[str, Any]
    metadata: dict[str, Any]
    rank_score: float = 0.0
    retrieval_source: str = ""


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


def _env_bool(name: str, default: bool) -> bool:
    return _as_bool(os.environ.get(name), default=default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(_safe_str(os.environ.get(name)).strip() or default)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_safe_str(os.environ.get(name)).strip() or default)
    except (TypeError, ValueError):
        return default


def archive_enabled() -> bool:
    return _env_bool("XINYU_DIALOGUE_ARCHIVE_ENABLED", True)


def archive_owner_private_only() -> bool:
    return _env_bool("XINYU_DIALOGUE_ARCHIVE_OWNER_PRIVATE_ONLY", False)


def archive_group_scope_enabled() -> bool:
    return _env_bool("XINYU_DIALOGUE_ARCHIVE_GROUP_SCOPE_ENABLED", True)


def semantic_retrieval_enabled() -> bool:
    return _env_bool("XINYU_DIALOGUE_SEMANTIC_RETRIEVAL_ENABLED", False)


def semantic_embedding_dimensions() -> int:
    return max(32, _env_int("XINYU_DIALOGUE_SEMANTIC_EMBEDDING_DIMENSIONS", 128))


def semantic_min_score() -> float:
    return max(0.0, _env_float("XINYU_DIALOGUE_SEMANTIC_MIN_SCORE", 0.18))


def semantic_max_scan() -> int:
    return max(50, _env_int("XINYU_DIALOGUE_SEMANTIC_MAX_SCAN", 500))


def temporal_traces_enabled() -> bool:
    return _env_bool("XINYU_DIALOGUE_TEMPORAL_TRACES_ENABLED", True)


def dialogue_archive_path(root: Path) -> Path:
    return root / ARCHIVE_REL_PATH


def _hash_id(value: Any, *, length: int = 24) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {_safe_str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _safe_str(value)


def _json_loads(value: str, default: Any) -> Any:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default
    return parsed


def _scrub_context_text(value: Any, *, limit: int = 300) -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return ""
    text = LOCAL_CONTEXT_PATH_RE.sub("[local-path]", text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _safe_rich_segments(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    safe: list[dict[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        safe.append(
            {
                "kind": _scrub_context_text(item.get("kind"), limit=40),
                "segment_type": _scrub_context_text(item.get("segment_type"), limit=40),
                "summary": _scrub_context_text(item.get("summary") or item.get("name") or item.get("id"), limit=240),
                "mood": _scrub_context_text(item.get("mood"), limit=80),
                "meaning": _scrub_context_text(item.get("meaning"), limit=240),
                "confidence": _scrub_context_text(item.get("confidence"), limit=40),
            }
        )
    return safe


def _safe_image_context(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    notes = value.get("notes")
    if not isinstance(notes, list):
        notes = []
    return {
        "available": _as_bool(value.get("available"), default=False),
        "kind": _scrub_context_text(value.get("kind"), limit=40),
        "notes": [_scrub_context_text(note, limit=120) for note in notes[:8]],
        "ocr_chars": len(_safe_str(value.get("ocr_text")).strip()),
        "vision_chars": len(_safe_str(value.get("vision_summary")).strip()),
    }


def _semantic_tokens(text: str) -> list[str]:
    lowered = _safe_str(text).lower()
    tokens = [token for token in re.findall(r"[a-z0-9_+#./-]+", lowered) if token]
    cjk_chars = [char for char in lowered if "\u4e00" <= char <= "\u9fff"]
    tokens.extend(cjk_chars)
    tokens.extend("".join(cjk_chars[index : index + 2]) for index in range(max(0, len(cjk_chars) - 1)))
    tokens.extend("".join(cjk_chars[index : index + 3]) for index in range(max(0, len(cjk_chars) - 2)))
    token_set = set(tokens)
    for group in SEMANTIC_SYNONYM_GROUPS:
        normalized = {item.lower() for item in group}
        if token_set & normalized:
            tokens.extend(normalized)
    return list(dict.fromkeys(token for token in tokens if token))


def _hash_embedding(text: str, *, dimensions: int | None = None) -> list[float]:
    dims = max(32, int(dimensions or semantic_embedding_dimensions()))
    values = [0.0 for _ in range(dims)]
    tokens = _semantic_tokens(text) or [_safe_str(text).lower()]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8", errors="replace")).digest()
        index = int.from_bytes(digest[:4], "big") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.25 if len(token) >= 3 else 1.0
        values[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    limit = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(limit))
    left_norm = math.sqrt(sum(value * value for value in left[:limit]))
    right_norm = math.sqrt(sum(value * value for value in right[:limit]))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _created_at_from_payload(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return _now_iso()
    raw = payload.get("timestamp") or payload.get("observed_at")
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(float(raw)).astimezone().isoformat()
        except (OSError, OverflowError, ValueError):
            return _now_iso()
    text = _safe_str(raw).strip()
    return text or _now_iso()


def _metadata(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw = payload.get("metadata") if isinstance(payload, dict) else {}
    return raw if isinstance(raw, dict) else {}


def _payload_value(payload: dict[str, Any] | None, key: str) -> str:
    if not isinstance(payload, dict):
        return ""
    metadata = _metadata(payload)
    return _safe_str(payload.get(key) if payload.get(key) is not None else metadata.get(key)).strip()


def resolve_dialogue_scope(payload: dict[str, Any] | None) -> DialogueScope:
    payload = payload if isinstance(payload, dict) else {}
    metadata = _metadata(payload)
    session_key = _payload_value(payload, "session_id")
    user_id = _payload_value(payload, "user_id")
    group_id = _payload_value(payload, "group_id")
    message_type = (_payload_value(payload, "message_type") or _safe_str(metadata.get("onebot_message_type"))).lower()
    platform = _safe_str(payload.get("platform") or metadata.get("platform") or "qq").strip() or "qq"
    source = _safe_str(payload.get("source") or metadata.get("source")).strip()
    is_owner = _as_bool(metadata.get("is_owner_user") if "is_owner_user" in metadata else payload.get("is_owner_user"))

    if not session_key:
        if group_id:
            session_key = f"{platform}:group:{group_id}:{user_id or 'unknown'}"
        elif user_id:
            session_key = f"{platform}:private:{user_id}"
        else:
            session_key = f"{platform}:default"

    if source == "codex_completion" or message_type.startswith("private_codex"):
        scope = CODEX_CALLBACK_SCOPE if not is_owner else OWNER_PRIVATE_SCOPE
    elif message_type.startswith("group") or group_id:
        scope = GROUP_SCOPE
    elif message_type.startswith("system") or source.startswith("maintenance"):
        scope = SYSTEM_SCOPE
    elif is_owner:
        scope = OWNER_PRIVATE_SCOPE
    else:
        scope = NON_OWNER_PRIVATE_SCOPE

    privacy_scope = {
        OWNER_PRIVATE_SCOPE: "owner_private",
        GROUP_SCOPE: "group_context",
        NON_OWNER_PRIVATE_SCOPE: "external_private",
        SYSTEM_SCOPE: "system_internal",
        CODEX_CALLBACK_SCOPE: "owner_private" if is_owner else "system_internal",
    }.get(scope, "unknown")

    return DialogueScope(
        session_key=session_key,
        session_key_hash=_hash_id(session_key),
        scope=scope,
        channel=platform,
        privacy_scope=privacy_scope,
        owner_user_hash=_hash_id(user_id) if is_owner else "",
        group_id_hash=_hash_id(group_id),
    )


def _should_archive_scope(scope: DialogueScope) -> bool:
    if not archive_enabled():
        return False
    if archive_owner_private_only() and scope.scope != OWNER_PRIVATE_SCOPE:
        return False
    if scope.scope == GROUP_SCOPE and not archive_group_scope_enabled():
        return False
    return scope.scope in {
        OWNER_PRIVATE_SCOPE,
        GROUP_SCOPE,
        NON_OWNER_PRIVATE_SCOPE,
        SYSTEM_SCOPE,
        CODEX_CALLBACK_SCOPE,
    }


def _connect(root: Path) -> sqlite3.Connection:
    path = dialogue_archive_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _connection(root: Path) -> Iterable[sqlite3.Connection]:
    conn = _connect(root)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_dialogue_archive(root: Path) -> dict[str, Any]:
    with _connection(root) as conn:
        _ensure_schema(conn)
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    return {"path": str(dialogue_archive_path(root)), "schema_version": version}


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS dialogue_sessions (
            id INTEGER PRIMARY KEY,
            session_key_hash TEXT NOT NULL,
            scope TEXT NOT NULL,
            channel TEXT NOT NULL,
            owner_user_hash TEXT,
            group_id_hash TEXT,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            summary_short TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            UNIQUE(session_key_hash, scope)
        );

        CREATE TABLE IF NOT EXISTS dialogue_messages (
            id INTEGER PRIMARY KEY,
            session_key_hash TEXT NOT NULL,
            scope TEXT NOT NULL,
            channel TEXT NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            message_type TEXT NOT NULL DEFAULT '',
            privacy_scope TEXT NOT NULL DEFAULT '',
            source_event_id TEXT NOT NULL DEFAULT '',
            reply_to_id INTEGER,
            codex_task_id TEXT NOT NULL DEFAULT '',
            quality_flags_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS recalled_context_log (
            id INTEGER PRIMARY KEY,
            turn_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            query_text TEXT NOT NULL,
            selected_message_ids_json TEXT NOT NULL,
            selected_memory_refs_json TEXT NOT NULL,
            notes_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS memory_candidates (
            id INTEGER PRIMARY KEY,
            candidate_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            candidate_type TEXT NOT NULL,
            source_message_ids_json TEXT NOT NULL,
            candidate_text TEXT NOT NULL,
            confidence_score INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            target_gate TEXT NOT NULL,
            target_memory_layer TEXT NOT NULL,
            reason TEXT NOT NULL,
            review_notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS dialogue_semantic_index (
            message_id INTEGER PRIMARY KEY,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            embedding_json TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            FOREIGN KEY(message_id) REFERENCES dialogue_messages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS temporal_traces (
            id INTEGER PRIMARY KEY,
            trace_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source_candidate_id TEXT NOT NULL,
            candidate_type TEXT NOT NULL,
            trace_type TEXT NOT NULL,
            relation TEXT NOT NULL,
            scope TEXT NOT NULL,
            confidence_score INTEGER NOT NULL,
            source_message_ids_json TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_text TEXT NOT NULL,
            target_gate TEXT NOT NULL,
            target_memory_layer TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            boundary TEXT NOT NULL DEFAULT 'temporal trace only; not stable memory unless an existing gate approves it'
        );

        CREATE INDEX IF NOT EXISTS idx_dialogue_messages_scope_time
            ON dialogue_messages(scope, created_at);
        CREATE INDEX IF NOT EXISTS idx_dialogue_messages_session_time
            ON dialogue_messages(session_key_hash, created_at);
        CREATE INDEX IF NOT EXISTS idx_dialogue_messages_text_hash
            ON dialogue_messages(text_hash);
        CREATE INDEX IF NOT EXISTS idx_dialogue_semantic_model
            ON dialogue_semantic_index(model, dimensions);
        CREATE INDEX IF NOT EXISTS idx_memory_candidates_status
            ON memory_candidates(status, candidate_type, created_at);
        CREATE INDEX IF NOT EXISTS idx_temporal_traces_status
            ON temporal_traces(status, candidate_type, created_at);
        CREATE INDEX IF NOT EXISTS idx_temporal_traces_candidate
            ON temporal_traces(source_candidate_id);
        """
    )
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS dialogue_fts USING fts5(message_id UNINDEXED, text)")
    except sqlite3.OperationalError:
        pass
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def _fts_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dialogue_fts'"
    ).fetchone()
    return row is not None


def _index_semantic_message(conn: sqlite3.Connection, *, message_id: int, text: str, text_hash: str) -> None:
    if not semantic_retrieval_enabled():
        return
    dimensions = semantic_embedding_dimensions()
    embedding = _hash_embedding(text, dimensions=dimensions)
    conn.execute(
        """
        INSERT INTO dialogue_semantic_index (
            message_id, model, dimensions, embedding_json, text_hash, indexed_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            model = excluded.model,
            dimensions = excluded.dimensions,
            embedding_json = excluded.embedding_json,
            text_hash = excluded.text_hash,
            indexed_at = excluded.indexed_at
        """,
        (
            message_id,
            SEMANTIC_MODEL,
            dimensions,
            _json_dumps(embedding),
            text_hash,
            _now_iso(),
        ),
    )


def ensure_dialogue_semantic_index(root: Path, *, limit: int | None = None) -> dict[str, Any]:
    if not archive_enabled():
        return {"indexed": 0, "notes": ["dialogue_archive_disabled"]}
    safe_limit = semantic_max_scan() if limit is None else max(1, int(limit))
    dimensions = semantic_embedding_dimensions()
    indexed = 0
    with _connection(root) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT m.id, m.text, m.text_hash
            FROM dialogue_messages m
            LEFT JOIN dialogue_semantic_index s
                ON s.message_id = m.id
                AND s.model = ?
                AND s.dimensions = ?
                AND s.text_hash = m.text_hash
            WHERE s.message_id IS NULL
            ORDER BY m.created_at DESC, m.id DESC
            LIMIT ?
            """,
            (SEMANTIC_MODEL, dimensions, safe_limit),
        ).fetchall()
        for row in rows:
            _index_semantic_message(
                conn,
                message_id=int(row["id"]),
                text=_safe_str(row["text"]),
                text_hash=_safe_str(row["text_hash"]),
            )
            indexed += 1
    return {"indexed": indexed, "model": SEMANTIC_MODEL, "dimensions": dimensions}


def _redacted_metadata(payload: dict[str, Any] | None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    metadata = dict(_metadata(payload))
    safe: dict[str, Any] = {}
    for key in (
        "gateway",
        "gateway_version",
        "source",
        "onebot_post_type",
        "onebot_message_type",
        "attachment_followup_after_ingest",
        "sticker_followup_after_import",
        "qq_rich_message",
        "qq_sticker_count",
        "qq_image_count",
        "qq_forward_count",
        "qq_forward_message_count",
        "qq_image_context_available",
        "delegated_by_model",
        "dialogue_context_included",
    ):
        if key in metadata:
            safe[key] = _json_safe(metadata.get(key))
    if "qq_rich_summary" in metadata:
        safe["qq_rich_summary"] = _scrub_context_text(metadata.get("qq_rich_summary"), limit=800)
    if "qq_message_segments" in metadata:
        safe["qq_message_segments"] = _safe_rich_segments(metadata.get("qq_message_segments"))
    if "qq_image_context" in metadata:
        safe["qq_image_context"] = _safe_image_context(metadata.get("qq_image_context"))
    if "qq_image_context_notes" in metadata:
        notes = metadata.get("qq_image_context_notes")
        if isinstance(notes, list):
            safe["qq_image_context_notes"] = [_scrub_context_text(note, limit=120) for note in notes[:8]]
    for key in ("platform", "adapter", "message_type", "source"):
        if key in payload:
            safe[key] = _json_safe(payload.get(key))
    for key in ("user_id", "group_id", "session_id", "message_id", "bot_id"):
        value = payload.get(key) if key in payload else metadata.get(key)
        if value not in (None, ""):
            safe[f"{key}_hash"] = _hash_id(value)
    if extra:
        safe.update(_json_safe(extra))
    return safe


def _upsert_session(conn: sqlite3.Connection, scope: DialogueScope, *, seen_at: str) -> None:
    conn.execute(
        """
        INSERT INTO dialogue_sessions (
            session_key_hash, scope, channel, owner_user_hash, group_id_hash,
            created_at, last_seen_at, message_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(session_key_hash, scope) DO UPDATE SET
            last_seen_at = excluded.last_seen_at,
            channel = excluded.channel,
            owner_user_hash = COALESCE(NULLIF(excluded.owner_user_hash, ''), dialogue_sessions.owner_user_hash),
            group_id_hash = COALESCE(NULLIF(excluded.group_id_hash, ''), dialogue_sessions.group_id_hash)
        """,
        (
            scope.session_key_hash,
            scope.scope,
            scope.channel,
            scope.owner_user_hash,
            scope.group_id_hash,
            seen_at,
            seen_at,
        ),
    )


def archive_message(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    role: str,
    text: str,
    created_at: str | None = None,
    message_type: str = "",
    privacy_scope: str = "",
    source_event_id: str = "",
    reply_to_id: int | None = None,
    codex_task_id: str = "",
    quality_flags: dict[str, Any] | list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> int | None:
    clean_text = _safe_str(text).strip()
    clean_role = _safe_str(role).strip()
    if clean_role not in {"user", "assistant", "system_event", "codex_result", "learning_event"} or not clean_text:
        return None
    scope = resolve_dialogue_scope(payload)
    if not _should_archive_scope(scope):
        return None
    seen_at = created_at or _created_at_from_payload(payload)
    flags: dict[str, Any]
    if isinstance(quality_flags, dict):
        flags = quality_flags
    elif isinstance(quality_flags, list):
        flags = {"flags": quality_flags}
    else:
        flags = {}
    redacted = _redacted_metadata(payload, metadata)
    text_hash = _text_hash(clean_text)
    with _connection(root) as conn:
        _ensure_schema(conn)
        _upsert_session(conn, scope, seen_at=seen_at)
        cursor = conn.execute(
            """
            INSERT INTO dialogue_messages (
                session_key_hash, scope, channel, role, text, text_hash, created_at,
                message_type, privacy_scope, source_event_id, reply_to_id, codex_task_id,
                quality_flags_json, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope.session_key_hash,
                scope.scope,
                scope.channel,
                clean_role,
                clean_text,
                text_hash,
                seen_at,
                message_type or _payload_value(payload, "message_type"),
                privacy_scope or scope.privacy_scope,
                source_event_id or _payload_value(payload, "message_id"),
                reply_to_id,
                codex_task_id,
                _json_dumps(flags),
                _json_dumps(redacted),
            ),
        )
        message_id = int(cursor.lastrowid)
        if _fts_available(conn):
            conn.execute("INSERT INTO dialogue_fts(message_id, text) VALUES (?, ?)", (message_id, clean_text))
        _index_semantic_message(conn, message_id=message_id, text=clean_text, text_hash=text_hash)
        conn.execute(
            """
            UPDATE dialogue_sessions
            SET message_count = message_count + 1, last_seen_at = ?
            WHERE session_key_hash = ? AND scope = ?
            """,
            (seen_at, scope.session_key_hash, scope.scope),
        )
        return message_id


def archive_dialogue_turn(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    assistant_reply: str,
    message_type: str = "",
    quality_flags: dict[str, Any] | list[str] | None = None,
) -> dict[str, Any]:
    scope = resolve_dialogue_scope(payload)
    if not _should_archive_scope(scope):
        return {"archived": False, "notes": ["dialogue_archive_skipped"], "message_ids": [], "scope": scope.scope}

    created_at = _created_at_from_payload(payload)
    user_id = archive_message(
        root,
        payload,
        role="user",
        text=user_text,
        created_at=created_at,
        message_type=message_type or _payload_value(payload, "message_type"),
    )
    reply_id = archive_message(
        root,
        payload,
        role="assistant",
        text=assistant_reply,
        created_at=_now_iso(),
        message_type=message_type or _payload_value(payload, "message_type"),
        reply_to_id=user_id,
        quality_flags=quality_flags,
    )
    message_ids = [item for item in (user_id, reply_id) if item is not None]
    return {
        "archived": bool(message_ids),
        "notes": ["dialogue_archive_written"] if message_ids else ["dialogue_archive_empty"],
        "message_ids": message_ids,
        "scope": scope.scope,
        "session_key_hash": scope.session_key_hash,
    }


def _tokenize_query(text: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9_+#./-]{2,}|[\u4e00-\u9fff]{2,}", text):
        token = token.strip()
        if not token:
            continue
        candidates = [token]
        if re.fullmatch(r"[\u4e00-\u9fff]{5,}", token):
            candidates.extend(token[idx : idx + 2] for idx in range(0, len(token) - 1))
            candidates.extend(token[idx : idx + 3] for idx in range(0, len(token) - 2))
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                tokens.append(candidate)
    return tokens[:12]


def _fts_query(text: str) -> str:
    terms = [term.replace('"', '""') for term in _tokenize_query(text) if len(term) >= 2]
    return " OR ".join(f'"{term}"' for term in terms[:8])


def _scope_clause(scopes: Iterable[str] | None, params: list[Any]) -> str:
    safe_scopes = [scope for scope in (scopes or []) if scope]
    if not safe_scopes:
        return ""
    placeholders = ",".join("?" for _ in safe_scopes)
    params.extend(safe_scopes)
    return f" AND m.scope IN ({placeholders})"


def _session_clause(session_key: str | None, params: list[Any], *, table_alias: str = "m") -> str:
    if not session_key:
        return ""
    params.append(_hash_id(session_key))
    return f" AND {table_alias}.session_key_hash = ?"


def _record_from_row(row: sqlite3.Row, *, rank_score: float = 0.0, retrieval_source: str = "") -> DialogueArchiveRecord:
    quality = _json_loads(_safe_str(row["quality_flags_json"]), {})
    metadata = _json_loads(_safe_str(row["metadata_json"]), {})
    return DialogueArchiveRecord(
        message_id=int(row["id"]),
        session_key_hash=_safe_str(row["session_key_hash"]),
        scope=_safe_str(row["scope"]),
        channel=_safe_str(row["channel"]),
        role=_safe_str(row["role"]),
        text=_safe_str(row["text"]),
        created_at=_safe_str(row["created_at"]),
        message_type=_safe_str(row["message_type"]),
        privacy_scope=_safe_str(row["privacy_scope"]),
        source_event_id=_safe_str(row["source_event_id"]),
        reply_to_id=int(row["reply_to_id"]) if row["reply_to_id"] is not None else None,
        codex_task_id=_safe_str(row["codex_task_id"]),
        quality_flags=quality if isinstance(quality, dict) else {},
        metadata=metadata if isinstance(metadata, dict) else {},
        rank_score=rank_score,
        retrieval_source=retrieval_source,
    )


def _select_sql(prefix: str = "m") -> str:
    return (
        f"{prefix}.id, {prefix}.session_key_hash, {prefix}.scope, {prefix}.channel, "
        f"{prefix}.role, {prefix}.text, {prefix}.text_hash, {prefix}.created_at, "
        f"{prefix}.message_type, {prefix}.privacy_scope, {prefix}.source_event_id, "
        f"{prefix}.reply_to_id, {prefix}.codex_task_id, {prefix}.quality_flags_json, {prefix}.metadata_json"
    )


def _search_dialogue_archive_semantic_conn(
    conn: sqlite3.Connection,
    query_text: str,
    *,
    scopes: Iterable[str] | None = None,
    session_key: str | None = None,
    limit: int = 12,
) -> list[DialogueArchiveRecord]:
    if not semantic_retrieval_enabled():
        return []
    query = _safe_str(query_text).strip()
    if not query:
        return []
    dimensions = semantic_embedding_dimensions()

    missing_params: list[Any] = [SEMANTIC_MODEL, dimensions]
    missing_scope_sql = _scope_clause(scopes, missing_params)
    missing_session_sql = _session_clause(session_key, missing_params)
    missing_params.append(semantic_max_scan())
    missing_rows = conn.execute(
        f"""
        SELECT m.id, m.text, m.text_hash
        FROM dialogue_messages m
        LEFT JOIN dialogue_semantic_index s
            ON s.message_id = m.id
            AND s.model = ?
            AND s.dimensions = ?
            AND s.text_hash = m.text_hash
        WHERE s.message_id IS NULL{missing_scope_sql}{missing_session_sql}
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT ?
        """,
        missing_params,
    ).fetchall()
    for row in missing_rows:
        _index_semantic_message(
            conn,
            message_id=int(row["id"]),
            text=_safe_str(row["text"]),
            text_hash=_safe_str(row["text_hash"]),
        )

    params: list[Any] = [SEMANTIC_MODEL, dimensions]
    scope_sql = _scope_clause(scopes, params)
    session_sql = _session_clause(session_key, params)
    params.append(semantic_max_scan())
    rows = conn.execute(
        f"""
        SELECT {_select_sql("m")}, s.embedding_json
        FROM dialogue_messages m
        JOIN dialogue_semantic_index s ON s.message_id = m.id
        WHERE s.model = ? AND s.dimensions = ?{scope_sql}{session_sql}
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    query_embedding = _hash_embedding(query, dimensions=dimensions)
    scored: list[DialogueArchiveRecord] = []
    min_score = semantic_min_score()
    for row in rows:
        embedding = _json_loads(_safe_str(row["embedding_json"]), [])
        if not isinstance(embedding, list):
            continue
        vector = [float(value) for value in embedding if isinstance(value, (int, float))]
        score = _cosine_similarity(query_embedding, vector)
        if score >= min_score:
            scored.append(_record_from_row(row, rank_score=score, retrieval_source="semantic"))
    scored.sort(key=lambda item: item.rank_score, reverse=True)
    return scored[: max(1, int(limit))]


def search_dialogue_archive(
    root: Path,
    query_text: str,
    *,
    scopes: Iterable[str] | None = None,
    session_key: str | None = None,
    limit: int = 12,
) -> list[DialogueArchiveRecord]:
    if not archive_enabled():
        return []
    safe_limit = max(1, int(limit))
    query = _safe_str(query_text).strip()
    records: dict[int, DialogueArchiveRecord] = {}
    with _connection(root) as conn:
        _ensure_schema(conn)
        if query and _fts_available(conn):
            fts = _fts_query(query)
            if fts:
                params: list[Any] = [fts]
                scope_sql = _scope_clause(scopes, params)
                session_sql = _session_clause(session_key, params)
                params.append(safe_limit * 3)
                try:
                    rows = conn.execute(
                        f"""
                        SELECT {_select_sql("m")}, bm25(dialogue_fts) AS fts_rank
                        FROM dialogue_fts
                        JOIN dialogue_messages m ON m.id = dialogue_fts.message_id
                        WHERE dialogue_fts.text MATCH ?{scope_sql}{session_sql}
                        ORDER BY fts_rank ASC, m.created_at DESC
                        LIMIT ?
                        """,
                        params,
                    ).fetchall()
                    for row in rows:
                        records[int(row["id"])] = _record_from_row(
                            row,
                            rank_score=float(row["fts_rank"] or 0.0),
                            retrieval_source="fts",
                        )
                except sqlite3.OperationalError:
                    pass

        terms = _tokenize_query(query)
        params = []
        scope_sql = _scope_clause(scopes, params)
        session_sql = _session_clause(session_key, params)
        if terms:
            like_parts = []
            for term in terms[:8]:
                like_parts.append("m.text LIKE ?")
                params.append(f"%{term}%")
            text_sql = " AND (" + " OR ".join(like_parts) + ")"
        else:
            text_sql = ""
        params.append(safe_limit * 3)
        rows = conn.execute(
            f"""
            SELECT {_select_sql("m")}
            FROM dialogue_messages m
            WHERE 1=1{scope_sql}{session_sql}{text_sql}
            ORDER BY m.created_at DESC, m.id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        for row in rows:
            records.setdefault(int(row["id"]), _record_from_row(row, rank_score=0.0, retrieval_source="like"))
        if semantic_retrieval_enabled() and query:
            for record in _search_dialogue_archive_semantic_conn(
                conn,
                query,
                scopes=scopes,
                session_key=session_key,
                limit=safe_limit,
            ):
                records.setdefault(record.message_id, record)
    return list(records.values())[:safe_limit]


def record_recalled_context_log(
    root: Path,
    *,
    turn_id: str,
    query_text: str,
    selected_message_ids: list[int],
    selected_memory_refs: list[str],
    notes: dict[str, Any] | None = None,
) -> bool:
    if not archive_enabled():
        return False
    with _connection(root) as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO recalled_context_log (
                turn_id, created_at, query_text, selected_message_ids_json,
                selected_memory_refs_json, notes_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                turn_id,
                _now_iso(),
                query_text,
                _json_dumps(selected_message_ids),
                _json_dumps(selected_memory_refs),
                _json_dumps(notes or {}),
            ),
        )
    return True


def store_memory_candidate(
    root: Path,
    *,
    candidate_id: str,
    candidate_type: str,
    source_message_ids: list[int],
    candidate_text: str,
    confidence_score: int,
    target_gate: str,
    target_memory_layer: str,
    reason: str,
    review_notes: str = "",
    created_at: str | None = None,
) -> bool:
    clean_id = _safe_str(candidate_id).strip()
    clean_text = _safe_str(candidate_text).strip()
    if not clean_id or not clean_text:
        return False
    with _connection(root) as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO memory_candidates (
                candidate_id, created_at, candidate_type, source_message_ids_json,
                candidate_text, confidence_score, status, target_gate,
                target_memory_layer, reason, review_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """,
            (
                clean_id,
                created_at or _now_iso(),
                candidate_type,
                _json_dumps(source_message_ids),
                clean_text,
                max(0, min(100, int(confidence_score))),
                target_gate,
                target_memory_layer,
                reason,
                review_notes,
            ),
        )
        return cursor.rowcount > 0


def list_memory_candidates(root: Path, *, status: str = "pending", limit: int = 50) -> list[dict[str, Any]]:
    with _connection(root) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT * FROM memory_candidates
            WHERE status = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (status, max(1, int(limit))),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["source_message_ids"] = _json_loads(_safe_str(item.pop("source_message_ids_json", "[]")), [])
        result.append(item)
    return result


def update_memory_candidate_status(
    root: Path,
    *,
    candidate_id: str,
    status: str,
    review_notes: str = "",
) -> bool:
    clean_id = _safe_str(candidate_id).strip()
    clean_status = _safe_str(status).strip()
    if not clean_id or not clean_status:
        return False
    with _connection(root) as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            """
            UPDATE memory_candidates
            SET status = ?, review_notes = ?
            WHERE candidate_id = ?
            """,
            (clean_status, _safe_str(review_notes).strip(), clean_id),
        )
        return cursor.rowcount > 0


def _trace_type_for_candidate(candidate_type: str) -> tuple[str, str]:
    normalized = _safe_str(candidate_type).strip()
    mapping = {
        "voice_correction": ("procedural_voice_trace", "owner -> corrected -> XinYu voice style"),
        "owner_preference": ("owner_preference_trace", "owner -> preferred -> reply habit"),
        "relationship_signal": ("relationship_emotion_trace", "owner/XinYu -> carried -> relationship residue"),
        "project_fact": ("project_continuity_trace", "conversation -> carried -> project fact candidate"),
        "codex_result": ("codex_delegation_trace", "XinYu/Codex -> produced -> local task result"),
    }
    return mapping.get(normalized, ("candidate_trace", "candidate -> awaits -> existing gate review"))


def store_temporal_trace_from_candidate(
    root: Path,
    *,
    candidate_id: str,
    candidate_type: str,
    source_message_ids: list[int],
    candidate_text: str,
    confidence_score: int,
    target_gate: str,
    target_memory_layer: str,
    reason: str,
    scope: str = "",
    created_at: str | None = None,
) -> bool:
    if not temporal_traces_enabled():
        return False
    clean_candidate_id = _safe_str(candidate_id).strip()
    clean_text = _safe_str(candidate_text).strip()
    if not clean_candidate_id or not clean_text:
        return False
    trace_type, relation = _trace_type_for_candidate(candidate_type)
    trace_id = "trace-" + hashlib.sha256(
        f"{clean_candidate_id}|{candidate_type}|{relation}".encode("utf-8", errors="replace")
    ).hexdigest()[:18]
    now = created_at or _now_iso()
    summary = re.sub(r"\s+", " ", clean_text).strip()
    if len(summary) > 260:
        summary = summary[:257].rstrip() + "..."
    evidence_text = clean_text
    clean_reason = _safe_str(reason).strip()
    if clean_reason:
        evidence_text = f"{clean_text}\nreason: {clean_reason}"
    with _connection(root) as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO temporal_traces (
                trace_id, created_at, updated_at, source_candidate_id, candidate_type,
                trace_type, relation, scope, confidence_score, source_message_ids_json,
                summary, evidence_text, target_gate, target_memory_layer, status, boundary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending',
                'temporal trace only; not stable memory unless an existing gate approves it')
            """,
            (
                trace_id,
                now,
                now,
                clean_candidate_id,
                _safe_str(candidate_type).strip(),
                trace_type,
                relation,
                _safe_str(scope, "candidate_scope").strip() or "candidate_scope",
                max(0, min(100, int(confidence_score))),
                _json_dumps(source_message_ids),
                summary,
                evidence_text,
                _safe_str(target_gate).strip(),
                _safe_str(target_memory_layer).strip(),
            ),
        )
        return cursor.rowcount > 0


def list_temporal_traces(root: Path, *, status: str = "pending", limit: int = 50) -> list[dict[str, Any]]:
    with _connection(root) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT * FROM temporal_traces
            WHERE status = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (status, max(1, int(limit))),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["source_message_ids"] = _json_loads(_safe_str(item.pop("source_message_ids_json", "[]")), [])
        result.append(item)
    return result


def search_temporal_traces(root: Path, query_text: str, *, status: str = "pending", limit: int = 8) -> list[dict[str, Any]]:
    query = _safe_str(query_text).strip()
    terms = _tokenize_query(query)
    if not terms:
        return []
    params: list[Any] = [status]
    like_parts: list[str] = []
    for term in terms[:8]:
        like_parts.extend(
            [
                "summary LIKE ?",
                "evidence_text LIKE ?",
                "relation LIKE ?",
                "candidate_type LIKE ?",
                "trace_type LIKE ?",
            ]
        )
        like = f"%{term}%"
        params.extend([like, like, like, like, like])
    params.append(max(1, int(limit)))
    with _connection(root) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            f"""
            SELECT * FROM temporal_traces
            WHERE status = ? AND ({" OR ".join(like_parts)})
            ORDER BY confidence_score DESC, created_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["source_message_ids"] = _json_loads(_safe_str(item.pop("source_message_ids_json", "[]")), [])
        result.append(item)
    return result
