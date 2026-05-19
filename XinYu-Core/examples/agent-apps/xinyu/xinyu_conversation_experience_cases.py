from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from xinyu_storage_paths import seed_owner_cases_path


DB_REL_PATH = Path("runtime/conversation_experience/conversation_experience.sqlite3")
SCHEMA_VERSION = 1

APPROVED_REVIEW_STATUS = "approved"
PENDING_REVIEW_STATUS = "pending"
DISABLED_REVIEW_STATUS = "disabled"

ALLOWED_REVIEW_STATUSES = {
    APPROVED_REVIEW_STATUS,
    PENDING_REVIEW_STATUS,
    "rejected",
    DISABLED_REVIEW_STATUS,
}
ALLOWED_CONSENT_STATUSES = {
    "owner_owned",
    "group_contributor_consented",
    "public_dataset_allowed",
    "synthetic_reviewed",
}
BLOCKED_CONSENT_STATUSES = {"blocked_no_consent", "unknown", ""}
ALLOWED_SOURCE_TIERS = {
    "owner_xinyu",
    "reviewed_group",
    "group_contributed",
    "public_pattern",
    "synthetic_reviewed",
    "negative_case",
}
ALLOWED_PRIVACY_SCOPES = {
    "owner_private",
    "qq_group",
    "qq_private_non_owner",
    "desktop_private",
    "general",
}


class ConversationExperienceCaseError(ValueError):
    pass


@dataclass(frozen=True)
class ConversationExperienceCase:
    case_id: str
    version: int
    source_tier: str
    source_ref: str
    consent_status: str
    privacy_scope: str
    channel_scope: str
    review_status: str
    scenario_tags: tuple[str, ...]
    turn_markers: tuple[str, ...]
    user_likely_intent: str
    bad_pattern: str
    useful_adjustment: str
    boundary: str
    confidence: float
    language: str
    created_at: str
    updated_at: str
    notes: tuple[str, ...]
    expires_at: str = ""

    @property
    def searchable_text(self) -> str:
        return " ".join(
            part
            for part in (
                " ".join(self.scenario_tags),
                " ".join(self.turn_markers),
                self.user_likely_intent,
                self.bad_pattern,
                self.useful_adjustment,
            )
            if part
        )


def conversation_experience_db_path(root: Path) -> Path:
    return root / DB_REL_PATH


def initialize_conversation_experience_cases(root: Path) -> dict[str, Any]:
    with _connection(root) as conn:
        _ensure_schema(conn)
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    return {"path": str(conversation_experience_db_path(root)), "schema_version": version}


def validate_case(data: dict[str, Any]) -> ConversationExperienceCase:
    now = _now_iso()
    case_id = _safe_str(data.get("case_id")).strip()
    if not case_id:
        raise ConversationExperienceCaseError("missing case_id")

    source_tier = _safe_str(data.get("source_tier"), "owner_xinyu").strip()
    if source_tier not in ALLOWED_SOURCE_TIERS:
        raise ConversationExperienceCaseError(f"invalid source_tier:{source_tier}")

    consent_status = _safe_str(data.get("consent_status"), "unknown").strip()
    if consent_status in BLOCKED_CONSENT_STATUSES:
        raise ConversationExperienceCaseError(f"blocked consent_status:{consent_status or 'unknown'}")
    if consent_status not in ALLOWED_CONSENT_STATUSES:
        raise ConversationExperienceCaseError(f"invalid consent_status:{consent_status}")

    privacy_scope = _safe_str(data.get("privacy_scope"), "general").strip()
    if privacy_scope not in ALLOWED_PRIVACY_SCOPES:
        raise ConversationExperienceCaseError(f"invalid privacy_scope:{privacy_scope}")

    channel_scope = _safe_str(data.get("channel_scope"), privacy_scope).strip() or "general"
    if channel_scope not in ALLOWED_PRIVACY_SCOPES:
        raise ConversationExperienceCaseError(f"invalid channel_scope:{channel_scope}")

    review_status = _safe_str(data.get("review_status"), PENDING_REVIEW_STATUS).strip() or PENDING_REVIEW_STATUS
    if review_status not in ALLOWED_REVIEW_STATUSES:
        raise ConversationExperienceCaseError(f"invalid review_status:{review_status}")
    if review_status == APPROVED_REVIEW_STATUS and not _can_approve(consent_status):
        raise ConversationExperienceCaseError("approved case requires allowed consent")

    user_likely_intent = _required_text(data, "user_likely_intent")
    bad_pattern = _required_text(data, "bad_pattern")
    useful_adjustment = _required_text(data, "useful_adjustment")
    boundary = _safe_str(
        data.get("boundary"),
        "Advisory only. Current user message and explicit instructions outrank this case.",
    ).strip()
    if not boundary:
        raise ConversationExperienceCaseError("missing boundary")

    confidence = _bounded_float(data.get("confidence"), default=0.5)
    scenario_tags = _as_tuple(data.get("scenario_tags"))
    turn_markers = _as_tuple(data.get("turn_markers"))
    if not scenario_tags:
        raise ConversationExperienceCaseError("missing scenario_tags")

    return ConversationExperienceCase(
        case_id=case_id,
        version=max(1, int(_safe_str(data.get("version"), "1") or "1")),
        source_tier=source_tier,
        source_ref=_safe_str(data.get("source_ref")).strip(),
        consent_status=consent_status,
        privacy_scope=privacy_scope,
        channel_scope=channel_scope,
        review_status=review_status,
        scenario_tags=scenario_tags,
        turn_markers=turn_markers,
        user_likely_intent=user_likely_intent,
        bad_pattern=bad_pattern,
        useful_adjustment=useful_adjustment,
        boundary=boundary,
        confidence=confidence,
        language=_safe_str(data.get("language"), "mixed").strip() or "mixed",
        created_at=_timestamp_or_now_iso(data.get("created_at") or now),
        updated_at=_timestamp_or_now_iso(data.get("updated_at") or now),
        notes=_as_tuple(data.get("notes")),
        expires_at=_safe_str(data.get("expires_at")).strip(),
    )


def case_to_dict(case: ConversationExperienceCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "version": case.version,
        "source_tier": case.source_tier,
        "source_ref": case.source_ref,
        "consent_status": case.consent_status,
        "privacy_scope": case.privacy_scope,
        "channel_scope": case.channel_scope,
        "review_status": case.review_status,
        "scenario_tags": list(case.scenario_tags),
        "turn_markers": list(case.turn_markers),
        "user_likely_intent": case.user_likely_intent,
        "bad_pattern": case.bad_pattern,
        "useful_adjustment": case.useful_adjustment,
        "boundary": case.boundary,
        "confidence": case.confidence,
        "language": case.language,
        "created_at": _timestamp_or_now_iso(case.created_at),
        "updated_at": _timestamp_or_now_iso(case.updated_at),
        "notes": list(case.notes),
        "expires_at": case.expires_at,
    }


def upsert_case(root: Path, data: dict[str, Any] | ConversationExperienceCase) -> ConversationExperienceCase:
    case = data if isinstance(data, ConversationExperienceCase) else validate_case(data)
    with _connection(root) as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO conversation_experience_cases (
                case_id, version, source_tier, source_ref, consent_status,
                privacy_scope, channel_scope, review_status, scenario_tags_json,
                turn_markers_json, user_likely_intent, bad_pattern, useful_adjustment,
                boundary, confidence, language, created_at, updated_at, expires_at, notes_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                version = excluded.version,
                source_tier = excluded.source_tier,
                source_ref = excluded.source_ref,
                consent_status = excluded.consent_status,
                privacy_scope = excluded.privacy_scope,
                channel_scope = excluded.channel_scope,
                review_status = excluded.review_status,
                scenario_tags_json = excluded.scenario_tags_json,
                turn_markers_json = excluded.turn_markers_json,
                user_likely_intent = excluded.user_likely_intent,
                bad_pattern = excluded.bad_pattern,
                useful_adjustment = excluded.useful_adjustment,
                boundary = excluded.boundary,
                confidence = excluded.confidence,
                language = excluded.language,
                updated_at = excluded.updated_at,
                expires_at = excluded.expires_at,
                notes_json = excluded.notes_json
            """,
            _case_sql_values(case),
        )
        _upsert_fts(conn, case)
    return case


def get_case(root: Path, case_id: str) -> ConversationExperienceCase | None:
    clean_id = _safe_str(case_id).strip()
    if not clean_id:
        return None
    with _connection(root) as conn:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT * FROM conversation_experience_cases WHERE case_id = ?",
            (clean_id,),
        ).fetchone()
    return _case_from_row(row) if row is not None else None


def list_cases(
    root: Path,
    *,
    review_status: str | None = None,
    limit: int = 50,
) -> list[ConversationExperienceCase]:
    params: list[Any] = []
    where = ""
    if review_status:
        where = "WHERE review_status = ?"
        params.append(review_status)
    params.append(max(1, int(limit)))
    with _connection(root) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            f"""
            SELECT * FROM conversation_experience_cases
            {where}
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [_case_from_row(row) for row in rows if row is not None]


def update_case_review_status(
    root: Path,
    case_id: str,
    *,
    review_status: str,
    note: str = "",
) -> bool:
    clean_id = _safe_str(case_id).strip()
    clean_status = _safe_str(review_status).strip()
    if clean_status not in ALLOWED_REVIEW_STATUSES:
        raise ConversationExperienceCaseError(f"invalid review_status:{clean_status}")
    case = get_case(root, clean_id)
    if case is None:
        return False
    if clean_status == APPROVED_REVIEW_STATUS and not _can_approve(case.consent_status):
        raise ConversationExperienceCaseError("approved case requires allowed consent")
    notes = [*case.notes]
    if note:
        notes.append(note)
    updated = validate_case(
        {
            **case_to_dict(case),
            "review_status": clean_status,
            "updated_at": _now_iso(),
            "notes": notes,
        }
    )
    upsert_case(root, updated)
    return True


def disable_case(root: Path, case_id: str, *, reason: str = "") -> bool:
    return update_case_review_status(
        root,
        case_id,
        review_status=DISABLED_REVIEW_STATUS,
        note=f"disabled:{reason}" if reason else "disabled",
    )


def add_group_scenario_card(root: Path, data: dict[str, Any]) -> ConversationExperienceCase:
    card = {
        **data,
        "source_tier": "reviewed_group",
        "consent_status": _safe_str(data.get("consent_status"), "group_contributor_consented"),
        "privacy_scope": _safe_str(data.get("privacy_scope"), "general") or "general",
        "channel_scope": _safe_str(data.get("channel_scope"), "general") or "general",
        "review_status": PENDING_REVIEW_STATUS,
        "notes": [*_as_tuple(data.get("notes")), "group_scenario_pending_review"],
    }
    return upsert_case(root, card)


def import_cases_from_jsonl(
    root: Path,
    path: Path,
    *,
    default_review_status: str | None = None,
) -> dict[str, Any]:
    imported = 0
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        clean = line.strip()
        if not clean:
            continue
        try:
            data = json.loads(clean)
            if default_review_status and "review_status" not in data:
                data["review_status"] = default_review_status
            upsert_case(root, data)
            imported += 1
        except (json.JSONDecodeError, ConversationExperienceCaseError, OSError, sqlite3.Error) as exc:
            errors.append(f"line_{line_number}:{type(exc).__name__}:{exc}")
    return {"imported": imported, "errors": errors, "notes": ["conversation_experience_import_done"]}


def import_seed_owner_cases(root: Path, *, seed_path: Path | None = None) -> dict[str, Any]:
    path = seed_path or seed_owner_cases_path(root)
    if not path.exists():
        return {"imported": 0, "errors": [f"missing_seed_path:{path}"], "notes": ["seed_cases_missing"]}
    return import_cases_from_jsonl(root, path, default_review_status=APPROVED_REVIEW_STATUS)


def compatible_scopes(current_scope: str) -> tuple[str, ...]:
    scope = _safe_str(current_scope, "general").strip() or "general"
    if scope == "owner_private":
        return ("owner_private", "general")
    if scope == "desktop_private":
        return ("desktop_private", "owner_private", "general")
    if scope == "qq_group":
        return ("qq_group", "general")
    if scope == "qq_private_non_owner":
        return ("qq_private_non_owner", "general")
    return ("general",)


def candidate_cases(
    root: Path,
    *,
    query_text: str,
    scenario_tags: Iterable[str] = (),
    privacy_scope: str = "general",
    channel_scope: str = "general",
    min_confidence: float = 0.3,
    limit: int = 80,
) -> list[ConversationExperienceCase]:
    scope_values = compatible_scopes(privacy_scope)
    channel_values = compatible_scopes(channel_scope)
    now = _now_iso()
    params: list[Any] = [
        APPROVED_REVIEW_STATUS,
        *scope_values,
        *channel_values,
        max(0.0, min(1.0, float(min_confidence))),
        now,
        max(1, int(limit)),
    ]
    scope_placeholders = ",".join("?" for _ in scope_values)
    channel_placeholders = ",".join("?" for _ in channel_values)
    with _connection(root) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            f"""
            SELECT * FROM conversation_experience_cases
            WHERE review_status = ?
              AND privacy_scope IN ({scope_placeholders})
              AND channel_scope IN ({channel_placeholders})
              AND consent_status != 'blocked_no_consent'
              AND confidence >= ?
              AND (expires_at = '' OR expires_at > ?)
            ORDER BY confidence DESC, updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    cases = [_case_from_row(row) for row in rows if row is not None]
    return _prioritize_fts_like(cases, query_text=query_text, scenario_tags=tuple(scenario_tags))


def record_match_trace(
    root: Path,
    *,
    turn_id: str,
    query_text: str,
    selected_case_ids: list[str],
    suppressed_case_ids: list[str],
    notes: list[str],
) -> None:
    with _connection(root) as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO conversation_experience_matches (
                turn_id, created_at, query_text, selected_case_ids_json,
                suppressed_case_ids_json, notes_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _safe_str(turn_id, "unknown") or "unknown",
                _now_iso(),
                _safe_str(query_text),
                _json_dumps(selected_case_ids),
                _json_dumps(suppressed_case_ids),
                _json_dumps(notes),
            ),
        )


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversation_experience_cases (
            id INTEGER PRIMARY KEY,
            case_id TEXT NOT NULL UNIQUE,
            version INTEGER NOT NULL DEFAULT 1,
            source_tier TEXT NOT NULL,
            source_ref TEXT NOT NULL DEFAULT '',
            consent_status TEXT NOT NULL,
            privacy_scope TEXT NOT NULL,
            channel_scope TEXT NOT NULL DEFAULT 'general',
            review_status TEXT NOT NULL DEFAULT 'pending',
            scenario_tags_json TEXT NOT NULL DEFAULT '[]',
            turn_markers_json TEXT NOT NULL DEFAULT '[]',
            user_likely_intent TEXT NOT NULL,
            bad_pattern TEXT NOT NULL,
            useful_adjustment TEXT NOT NULL,
            boundary TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            language TEXT NOT NULL DEFAULT 'mixed',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL DEFAULT '',
            notes_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS conversation_experience_matches (
            id INTEGER PRIMARY KEY,
            turn_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            query_text TEXT NOT NULL,
            selected_case_ids_json TEXT NOT NULL DEFAULT '[]',
            suppressed_case_ids_json TEXT NOT NULL DEFAULT '[]',
            notes_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE INDEX IF NOT EXISTS idx_conversation_cases_review_scope
            ON conversation_experience_cases(review_status, privacy_scope, channel_scope, confidence);
        CREATE INDEX IF NOT EXISTS idx_conversation_matches_turn
            ON conversation_experience_matches(turn_id, created_at);
        """
    )
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS conversation_experience_fts USING fts5(
                case_id UNINDEXED,
                tags,
                user_likely_intent,
                bad_pattern,
                useful_adjustment
            )
            """
        )
    except sqlite3.OperationalError:
        pass
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def _connect(root: Path) -> sqlite3.Connection:
    path = conversation_experience_db_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def _connection(root: Path) -> Iterable[sqlite3.Connection]:
    conn = _connect(root)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _case_sql_values(case: ConversationExperienceCase) -> tuple[Any, ...]:
    return (
        case.case_id,
        case.version,
        case.source_tier,
        case.source_ref,
        case.consent_status,
        case.privacy_scope,
        case.channel_scope,
        case.review_status,
        _json_dumps(case.scenario_tags),
        _json_dumps(case.turn_markers),
        case.user_likely_intent,
        case.bad_pattern,
        case.useful_adjustment,
        case.boundary,
        case.confidence,
        case.language,
        case.created_at,
        case.updated_at,
        case.expires_at,
        _json_dumps(case.notes),
    )


def _case_from_row(row: sqlite3.Row) -> ConversationExperienceCase:
    return ConversationExperienceCase(
        case_id=_safe_str(row["case_id"]),
        version=int(row["version"]),
        source_tier=_safe_str(row["source_tier"]),
        source_ref=_safe_str(row["source_ref"]),
        consent_status=_safe_str(row["consent_status"]),
        privacy_scope=_safe_str(row["privacy_scope"]),
        channel_scope=_safe_str(row["channel_scope"]),
        review_status=_safe_str(row["review_status"]),
        scenario_tags=_as_tuple(_json_loads(_safe_str(row["scenario_tags_json"]), [])),
        turn_markers=_as_tuple(_json_loads(_safe_str(row["turn_markers_json"]), [])),
        user_likely_intent=_safe_str(row["user_likely_intent"]),
        bad_pattern=_safe_str(row["bad_pattern"]),
        useful_adjustment=_safe_str(row["useful_adjustment"]),
        boundary=_safe_str(row["boundary"]),
        confidence=_bounded_float(row["confidence"], default=0.5),
        language=_safe_str(row["language"], "mixed"),
        created_at=_safe_str(row["created_at"]),
        updated_at=_safe_str(row["updated_at"]),
        expires_at=_safe_str(row["expires_at"]),
        notes=_as_tuple(_json_loads(_safe_str(row["notes_json"]), [])),
    )


def _upsert_fts(conn: sqlite3.Connection, case: ConversationExperienceCase) -> None:
    if not _fts_available(conn):
        return
    try:
        conn.execute("DELETE FROM conversation_experience_fts WHERE case_id = ?", (case.case_id,))
        conn.execute(
            """
            INSERT INTO conversation_experience_fts (
                case_id, tags, user_likely_intent, bad_pattern, useful_adjustment
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                case.case_id,
                " ".join([*case.scenario_tags, *case.turn_markers]),
                case.user_likely_intent,
                case.bad_pattern,
                case.useful_adjustment,
            ),
        )
    except sqlite3.OperationalError:
        return


def _fts_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_experience_fts'"
    ).fetchone()
    return row is not None


def _prioritize_fts_like(
    cases: list[ConversationExperienceCase],
    *,
    query_text: str,
    scenario_tags: tuple[str, ...],
) -> list[ConversationExperienceCase]:
    query_terms = set(_tokens(query_text))
    tag_terms = {_safe_str(tag).lower() for tag in scenario_tags if _safe_str(tag)}

    def rank(case: ConversationExperienceCase) -> tuple[float, float, str]:
        case_terms = set(_tokens(case.searchable_text))
        overlap = len(query_terms & case_terms) / max(1, len(query_terms))
        tag_overlap = len(tag_terms & {_safe_str(tag).lower() for tag in case.scenario_tags}) / max(1, len(tag_terms))
        return (overlap + tag_overlap + case.confidence, case.confidence, case.case_id)

    return sorted(cases, key=rank, reverse=True)


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_\-]+", _safe_str(text))
        if len(token) >= 2
    ]


def _required_text(data: dict[str, Any], key: str) -> str:
    value = _safe_str(data.get(key)).strip()
    if not value:
        raise ConversationExperienceCaseError(f"missing {key}")
    return value


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw = value.replace(";", ",").split(",")
    elif isinstance(value, Iterable):
        raw = value
    else:
        raw = (value,)
    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = _safe_str(item).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _json_loads(text: str, default: Any) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _can_approve(consent_status: str) -> bool:
    return consent_status in ALLOWED_CONSENT_STATUSES


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed
