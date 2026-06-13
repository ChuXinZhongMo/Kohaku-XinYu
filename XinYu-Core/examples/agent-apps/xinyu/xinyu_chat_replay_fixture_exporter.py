from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

from xinyu_chat_replay_fixture_exporter_store import chat_replay_path_exists
from xinyu_chat_replay_fixture_exporter_store import read_chat_replay_jsonl_file
from xinyu_chat_replay_fixture_exporter_store import read_chat_replay_text
from xinyu_chat_replay_fixture_exporter_store import write_chat_replay_json
from xinyu_chat_replay_fixture_exporter_store import write_chat_replay_text
from xinyu_storage_paths import seed_owner_cases_path


DEFAULT_OUTPUT_DIR = Path("runtime") / "replay_candidates"
RETRIEVAL_CANDIDATES_NAME = "retrieval_replay_candidates.jsonl"
CONVERSATION_CANDIDATES_NAME = "conversation_experience_replay_candidates.jsonl"
SUMMARY_NAME = "chat_replay_export_summary.json"
PROMOTION_REPORT_NAME = "chat_replay_promotion_report.json"
RETRIEVAL_FIXTURE_REL = Path("tests") / "fixtures" / "retrieval_replay_cases.jsonl"
CONVERSATION_FIXTURE_REL = Path("tests") / "fixtures" / "conversation_experience_replay_cases.jsonl"

FAILURE_QUALITY_KEYS = (
    "empty_reply",
    "mechanic_leak",
    "reference_miss",
    "reportish",
    "too_long_for_chat",
)

CONTEXT_MARKERS = (
    "continue",
    "just now",
    "last turn",
    "previous",
    "remember",
    "where were we",
    "刚才",
    "上次",
    "之前",
    "继续",
    "还差",
    "进度",
)

TECHNICAL_MARKERS = (
    "codex",
    "runtime",
    "test",
    "pytest",
    "bridge",
    "memory",
    "retrieval",
    "api",
    "代码",
    "测试",
    "修",
    "实现",
    "检索",
)

STATUS_MARKERS = (
    "status",
    "progress",
    "done",
    "remaining",
    "left",
    "状态",
    "进度",
    "还差",
    "做完",
)

OWNER_PRESSURE_MARKERS = (
    "why did you stop",
    "again",
    "not this",
    "stopped",
    "怎么又",
    "为什么停",
    "不是这个",
    "没变",
)

SECRET_RE = re.compile(r"(?i)\b(api[_-]?key|token|authorization|secret|password)\s*[:=]\s*([^\s,;]+)")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)>\]]+")
WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s<>:\"|?*]+")
LONG_DIGIT_RE = re.compile(r"\b\d{5,}\b")
QQ_RE = re.compile(r"(?i)\b((?:qq|group|user|session)[_-]?id)\s*[:=]\s*([A-Za-z0-9_.:-]{4,})")
SAFE_METADATA_STRING_KEYS = {
    "id",
    "kind",
    "review_status",
    "source_kind",
    "source_text_hash",
    "payload",
    "turn_kind",
    "failure_signals",
    "expect_notes",
    "expect_note_prefixes",
    "expect_notes_any",
    "expect_selected_ids_any",
    "expect_selected_envelope_source",
    "expect_selected_min",
    "forbid_selected_privacy_scopes",
    "promotion_notes",
    "message_type",
    "role",
}


@dataclass(frozen=True)
class ReplaySourceRow:
    row_id: str
    source_ref: str
    source_kind: str
    payload: str
    user_text: str
    assistant_reply: str = ""
    case_kind: str = ""
    notes: tuple[str, ...] = ()
    quality: dict[str, Any] | None = None
    pressure: dict[str, Any] | None = None
    dialogue_tail: tuple[dict[str, str], ...] = ()
    archive_turns: tuple[dict[str, Any], ...] = ()
    stable_memory: dict[str, str] | None = None


def export_replay_candidates(
    sources: Iterable[Path],
    *,
    output_dir: Path,
    fixture_root: Path | None = None,
    limit: int = 0,
    redaction_mode: str = "balanced",
    include_passing_context: bool = False,
    auto_promote_safe: bool = False,
    max_promote_per_kind: int = 6,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_paths = [Path(source) for source in sources]
    rows, load_notes = load_source_rows(source_paths)
    selected = [
        row
        for row in rows
        if is_failure_like(row) or (include_passing_context and is_context_or_work_row(row))
    ]
    if limit > 0:
        selected = selected[:limit]

    retrieval_cases = [
        case
        for row in selected
        if is_context_or_work_row(row)
        for case in (build_retrieval_replay_case(row, redaction_mode=redaction_mode),)
        if case is not None
    ]
    conversation_cases = [
        build_conversation_experience_replay_case(row, redaction_mode=redaction_mode)
        for row in selected
    ]
    promotion_report = {
        "auto_promote_enabled": bool(auto_promote_safe),
        "promoted_retrieval_count": 0,
        "promoted_conversation_count": 0,
        "skipped": [],
    }
    if auto_promote_safe:
        safe_retrieval_cases = [
            case
            for row in selected
            if is_context_or_work_row(row)
            for case in (build_retrieval_replay_case(row, redaction_mode="strict"),)
            if case is not None
        ]
        safe_conversation_cases = [
            build_conversation_experience_replay_case(row, redaction_mode="strict")
            for row in selected
        ]
        promotion_report = promote_safe_replay_cases(
            fixture_root or Path(__file__).resolve().parent,
            retrieval_cases=safe_retrieval_cases,
            conversation_cases=safe_conversation_cases,
            max_promote_per_kind=max_promote_per_kind,
            dry_run=dry_run,
        )

    retrieval_path = output_dir / RETRIEVAL_CANDIDATES_NAME
    conversation_path = output_dir / CONVERSATION_CANDIDATES_NAME
    summary_path = output_dir / SUMMARY_NAME
    notes = [*load_notes]
    if not selected:
        notes.append("no_replay_rows_selected")
    if redaction_mode == "strict":
        notes.append("strict_redaction_active")
    else:
        notes.append("balanced_redaction_active")
    notes.append("candidate_local_unreviewed")

    summary = {
        "source_count": len(source_paths),
        "row_count": len(rows),
        "selected_count": len(selected),
        "retrieval_case_count": len(retrieval_cases),
        "conversation_case_count": len(conversation_cases),
        "output_dir": str(output_dir),
        "retrieval_path": str(retrieval_path),
        "conversation_path": str(conversation_path),
        "summary_path": str(summary_path),
        "notes": notes,
        "promotion": promotion_report,
    }

    if not dry_run:
        write_chat_replay_text(retrieval_path, _jsonl(retrieval_cases), final_newline=bool(retrieval_cases))
        write_chat_replay_text(conversation_path, _jsonl(conversation_cases), final_newline=bool(conversation_cases))
        write_chat_replay_json(summary_path, summary)
        if auto_promote_safe:
            write_chat_replay_json(output_dir / PROMOTION_REPORT_NAME, promotion_report)
    return summary


def promote_safe_replay_cases(
    fixture_root: Path,
    *,
    retrieval_cases: list[dict[str, Any]],
    conversation_cases: list[dict[str, Any]],
    max_promote_per_kind: int = 6,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = Path(fixture_root)
    retrieval_path = root / RETRIEVAL_FIXTURE_REL
    conversation_path = root / CONVERSATION_FIXTURE_REL
    existing_retrieval = _read_jsonl_file(retrieval_path)
    existing_conversation = _read_jsonl_file(conversation_path)

    promoted_retrieval, skipped_retrieval = _select_promotable_cases(
        retrieval_cases,
        existing_retrieval,
        case_kind="retrieval",
        max_count=max_promote_per_kind,
    )
    promoted_conversation, skipped_conversation = _select_promotable_cases(
        conversation_cases,
        existing_conversation,
        case_kind="conversation",
        max_count=max_promote_per_kind,
    )

    if not dry_run:
        if promoted_retrieval:
            write_chat_replay_text(retrieval_path, _jsonl([*existing_retrieval, *promoted_retrieval]))
        if promoted_conversation:
            write_chat_replay_text(conversation_path, _jsonl([*existing_conversation, *promoted_conversation]))

    return {
        "auto_promote_enabled": True,
        "dry_run": bool(dry_run),
        "fixture_root": str(root),
        "retrieval_fixture": str(retrieval_path),
        "conversation_fixture": str(conversation_path),
        "promoted_retrieval_count": len(promoted_retrieval),
        "promoted_conversation_count": len(promoted_conversation),
        "promoted_retrieval_ids": [case["id"] for case in promoted_retrieval],
        "promoted_conversation_ids": [case["id"] for case in promoted_conversation],
        "skipped": skipped_retrieval + skipped_conversation,
        "notes": [
            "auto_promote_requires_strict_redaction",
            "auto_promote_validates_before_append",
            "group_scope_candidates_remain_manual_review",
        ],
    }


def _select_promotable_cases(
    candidates: list[dict[str, Any]],
    existing: list[dict[str, Any]],
    *,
    case_kind: str,
    max_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    promoted: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    existing_keys = _existing_case_keys(existing)
    max_count = max(0, int(max_count))
    for case in candidates:
        if max_count and len(promoted) >= max_count:
            skipped.append({"id": _safe_str(case.get("id")), "kind": case_kind, "reason": "promotion_limit_reached"})
            continue
        prepared, reason = _prepare_promotable_case(case, case_kind=case_kind)
        if prepared is None:
            skipped.append({"id": _safe_str(case.get("id")), "kind": case_kind, "reason": reason})
            continue
        key = _case_key(prepared)
        if key in existing_keys:
            skipped.append({"id": _safe_str(prepared.get("id")), "kind": case_kind, "reason": "duplicate_case"})
            continue
        valid, validation_reason = _validate_case(prepared, case_kind=case_kind)
        if not valid:
            skipped.append({"id": _safe_str(prepared.get("id")), "kind": case_kind, "reason": validation_reason})
            continue
        existing_keys.add(key)
        promoted.append(prepared)
    return promoted, skipped


def _prepare_promotable_case(case: dict[str, Any], *, case_kind: str) -> tuple[dict[str, Any] | None, str]:
    if case.get("payload") == "group":
        return None, "group_scope_manual_review"
    if case_kind == "retrieval" and not (
        case.get("dialogue_tail") or case.get("archive_turns") or case.get("stable_memory")
    ):
        return None, "retrieval_case_lacks_seed_context"
    if case_kind == "conversation" and int(case.get("expect_selected_min") or 0) <= 0:
        return None, "conversation_case_no_expected_selection"
    prepared = dict(case)
    prepared.pop("candidate_comment", None)
    prepared.pop("source_ref", None)
    prepared["review_status"] = "auto_promoted_safe"
    prepared["promotion_notes"] = ["strict_redaction", "validated_before_append"]
    if not _strict_redaction_shape_only(prepared):
        return None, "not_strict_redacted"
    if _contains_unredacted_sensitive_material(prepared):
        return None, "sensitive_material_detected"
    return prepared, ""


def _validate_case(case: dict[str, Any], *, case_kind: str) -> tuple[bool, str]:
    try:
        if case_kind == "retrieval":
            return _validate_retrieval_case(case), "retrieval_validation_failed"
        if case_kind == "conversation":
            return _validate_conversation_case(case), "conversation_validation_failed"
    except Exception as exc:
        return False, f"validation_error:{type(exc).__name__}"
    return False, "unknown_case_kind"


def _validate_retrieval_case(case: dict[str, Any]) -> bool:
    from xinyu_dialogue_archive import archive_dialogue_turn
    from xinyu_living_memory_recall import retrieve_living_memory

    with tempfile.TemporaryDirectory(prefix="xinyu-replay-promote-") as tmp:
        root = Path(tmp)
        for rel_path, text in dict(case.get("stable_memory", {})).items():
            path = root / str(rel_path)
            write_chat_replay_text(path, str(text).strip())
        for turn in case.get("archive_turns", []):
            if not isinstance(turn, dict):
                continue
            archive_dialogue_turn(
                root,
                _test_payload(_safe_str(turn.get("payload") or "owner_private"), _safe_str(case.get("id"))),
                user_text=_safe_str(turn.get("user_text")),
                assistant_reply=_safe_str(turn.get("assistant_reply")),
                message_type=_safe_str(turn.get("message_type")),
            )
        result = retrieve_living_memory(
            root,
            _test_payload(_safe_str(case.get("payload") or "owner_private"), _safe_str(case.get("id"))),
            user_text=_safe_str(case.get("user_text")),
            dialogue_tail=list(case.get("dialogue_tail", [])),
            visible_turn=_visible_namespace(case.get("visible_turn")),
        )
    if case.get("expect_no_items"):
        return result.items == ()
    if not result.items:
        return False
    return _case_note_expectations_pass(case, result.notes) and _prompt_forbidden_expectations_pass(case, result.prompt_block)


def _validate_conversation_case(case: dict[str, Any]) -> bool:
    from xinyu_conversation_experience_cases import import_seed_owner_cases
    from xinyu_conversation_experience_matcher import match_conversation_experience_cases

    app_root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="xinyu-experience-promote-") as tmp:
        root = Path(tmp)
        imported = import_seed_owner_cases(root, seed_path=seed_owner_cases_path(app_root))
        if imported.get("errors"):
            return False
        result = match_conversation_experience_cases(
            root,
            _test_payload(_safe_str(case.get("payload") or "owner_private"), _safe_str(case.get("id"))),
            user_text=_safe_str(case.get("user_text")),
            dialogue_tail=list(case.get("dialogue_tail", [])),
            visible_turn=_visible_namespace(case.get("visible_turn")),
            turn_id=f"promote-{case.get('id')}",
            limit=int(case.get("limit", 2)),
        )
    selected = list(result.selected)
    if len(selected) < int(case.get("expect_selected_min") or 0):
        return False
    expected_any = set(case.get("expect_selected_ids_any", []))
    if expected_any and not ({decision.case.case_id for decision in selected} & expected_any):
        return False
    forbidden_scopes = set(case.get("forbid_selected_privacy_scopes", []))
    if any(decision.case.privacy_scope in forbidden_scopes for decision in selected):
        return False
    return _case_note_expectations_pass(case, result.notes)


def _case_note_expectations_pass(case: dict[str, Any], notes: tuple[str, ...]) -> bool:
    for note in case.get("expect_notes", []):
        if note not in notes:
            return False
    for prefix in case.get("expect_note_prefixes", []):
        if not any(note.startswith(prefix) for note in notes):
            return False
    return True


def _prompt_forbidden_expectations_pass(case: dict[str, Any], prompt_block: str) -> bool:
    return all(_safe_str(snippet) not in prompt_block for snippet in case.get("forbid_prompt_substrings", []))


def _visible_namespace(data: Any) -> SimpleNamespace:
    base = {
        "turn_kind": "ordinary_owner_chat",
        "technical_work": False,
        "owner_style_pressure": False,
        "owner_no_change_pressure": False,
        "relationship_pressure": False,
        "rest_silence": False,
    }
    if isinstance(data, dict):
        base.update(data)
    return SimpleNamespace(**base)


def _test_payload(kind: str, case_id: str) -> dict[str, object]:
    if kind == "group":
        return {
            "platform": "qq",
            "message_type": "group_text",
            "session_id": f"qq:group:auto-promote:{case_id}",
            "group_id": f"group-{case_id}",
            "user_id": "group-user",
            "metadata": {"is_owner_user": False},
        }
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": f"qq:private:auto-promote:{case_id}",
        "user_id": "owner",
        "metadata": {"is_owner_user": True},
    }


def _existing_case_keys(cases: list[dict[str, Any]]) -> set[str]:
    return {_case_key(case) for case in cases}


def _case_key(case: dict[str, Any]) -> str:
    source_hash = _safe_str(case.get("source_text_hash"))
    return source_hash or _safe_str(case.get("id"))


def _read_jsonl_file(path: Path) -> list[dict[str, Any]]:
    return read_chat_replay_jsonl_file(path)


def _strict_redaction_shape_only(value: Any, *, key: str = "") -> bool:
    if isinstance(value, dict):
        return all(_strict_redaction_shape_only(item, key=_safe_str(item_key)) for item_key, item in value.items())
    if isinstance(value, list):
        return all(_strict_redaction_shape_only(item, key=key) for item in value)
    if not isinstance(value, str):
        return True
    if key in SAFE_METADATA_STRING_KEYS:
        return True
    if value.startswith("[private-text:"):
        return True
    return not _looks_like_user_text(value)


def _looks_like_user_text(text: str) -> bool:
    lowered = text.lower()
    if len(text) > 120 and " " in text:
        return True
    return _contains_any(lowered, CONTEXT_MARKERS + TECHNICAL_MARKERS + STATUS_MARKERS + OWNER_PRESSURE_MARKERS)


def _contains_unredacted_sensitive_material(case: dict[str, Any]) -> bool:
    text = json.dumps(case, ensure_ascii=False, sort_keys=True)
    if SECRET_RE.search(text) or EMAIL_RE.search(text) or URL_RE.search(text) or WINDOWS_PATH_RE.search(text):
        return True
    return bool(re.search(r"\b\d{7,}\b", text))


def load_source_rows(sources: Iterable[Path]) -> tuple[list[ReplaySourceRow], list[str]]:
    rows: list[ReplaySourceRow] = []
    notes: list[str] = []
    for source in sources:
        path = Path(source)
        if not chat_replay_path_exists(path):
            notes.append(f"missing_source:{path}")
            continue
        loaded, source_notes = _load_single_source(path)
        rows.extend(loaded)
        notes.extend(source_notes)
    return rows, notes


def _load_single_source(path: Path) -> tuple[list[ReplaySourceRow], list[str]]:
    if path.suffix.lower() == ".jsonl":
        return _load_jsonl_source(path)
    try:
        data = json.loads(read_chat_replay_text(path))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"source_json_failed:{path.name}:{type(exc).__name__}"]
    return _rows_from_data(data, source_ref=str(path), source_kind=_source_kind_for_data(data, path))


def _load_jsonl_source(path: Path) -> tuple[list[ReplaySourceRow], list[str]]:
    rows: list[ReplaySourceRow] = []
    notes: list[str] = []
    try:
        lines = read_chat_replay_text(path).splitlines()
    except OSError as exc:
        return [], [f"source_jsonl_failed:{path.name}:{type(exc).__name__}"]
    for index, line in enumerate(lines, start=1):
        clean = line.strip()
        if not clean:
            continue
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            notes.append(f"source_jsonl_line_skipped:{path.name}:{index}")
            continue
        loaded, _ = _rows_from_data(data, source_ref=f"{path}:{index}", source_kind="generic_jsonl")
        rows.extend(loaded)
    return rows, notes


def _rows_from_data(data: Any, *, source_ref: str, source_kind: str) -> tuple[list[ReplaySourceRow], list[str]]:
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return _rows_from_live_baseline(data, source_ref=source_ref), []
    if isinstance(data, list):
        rows = [
            row
            for index, item in enumerate(data, start=1)
            for row in _rows_from_generic_mapping(item, source_ref=f"{source_ref}:{index}", source_kind=source_kind)
        ]
        return rows, []
    if isinstance(data, dict):
        return _rows_from_generic_mapping(data, source_ref=source_ref, source_kind=source_kind), []
    return [], [f"unsupported_source_shape:{source_ref}"]


def _rows_from_live_baseline(data: dict[str, Any], *, source_ref: str) -> list[ReplaySourceRow]:
    rows: list[ReplaySourceRow] = []
    run_id = _safe_str(data.get("run_id"), "run")
    for index, item in enumerate(data.get("results") or [], start=1):
        if not isinstance(item, dict):
            continue
        case_id = _safe_str(item.get("case_id"), f"case-{index}")
        rows.append(
            ReplaySourceRow(
                row_id=f"{run_id}-{case_id}",
                source_ref=source_ref,
                source_kind="live_chat_baseline",
                payload=_payload_kind(item.get("payload") or item),
                user_text=_safe_str(item.get("text")),
                assistant_reply=_safe_str(item.get("reply")),
                case_kind=_safe_str(item.get("case_kind")),
                notes=_tuple_str(item.get("notes")),
                quality=_dict_or_none(item.get("quality")),
                pressure=_dict_or_none(item.get("pressure")),
            )
        )
    return rows


def _rows_from_generic_mapping(data: Any, *, source_ref: str, source_kind: str) -> list[ReplaySourceRow]:
    if not isinstance(data, dict):
        return []
    row_id = _safe_str(data.get("id") or data.get("case_id") or data.get("turn_id") or _hash(source_ref, 10))
    payload = _payload_kind(data.get("payload") or data)
    user_text = _safe_str(
        data.get("user_text")
        or data.get("text")
        or data.get("message")
        or data.get("input")
        or data.get("question")
    )
    assistant_reply = _safe_str(data.get("assistant_reply") or data.get("reply") or data.get("output"))
    notes = _tuple_str(data.get("notes"))
    quality = _dict_or_none(data.get("quality"))
    pressure = _dict_or_none(data.get("pressure"))
    return [
        ReplaySourceRow(
            row_id=row_id,
            source_ref=source_ref,
            source_kind=source_kind,
            payload=payload,
            user_text=user_text,
            assistant_reply=assistant_reply,
            case_kind=_safe_str(data.get("case_kind") or data.get("kind")),
            notes=notes,
            quality=quality,
            pressure=pressure,
            dialogue_tail=_sanitize_tail_shape(data.get("dialogue_tail")),
            archive_turns=_sanitize_archive_turn_shape(data.get("archive_turns")),
            stable_memory=_stable_memory_shape(data.get("stable_memory")),
        )
    ]


def build_retrieval_replay_case(row: ReplaySourceRow, *, redaction_mode: str = "balanced") -> dict[str, Any] | None:
    if not row.user_text.strip():
        return None
    visible = _visible_turn(row)
    direct_context = _contains_any(row.user_text, CONTEXT_MARKERS)
    expected_notes = ["candidate_envelope_v1"] if direct_context or visible["technical_work"] else []
    expected_prefixes = ["need_profile:"] if expected_notes else []
    return {
        "id": _case_id("retrieval", row),
        "kind": "recall",
        "review_status": "candidate_local_unreviewed",
        "source_ref": row.source_ref,
        "source_kind": row.source_kind,
        "source_text_hash": _hash(row.user_text),
        "failure_signals": failure_signals(row),
        "payload": row.payload,
        "user_text": sanitize_replay_text(row.user_text, mode=redaction_mode),
        "dialogue_tail": _sanitize_dialogue_tail(row.dialogue_tail, mode=redaction_mode),
        "archive_turns": _sanitize_archive_turns(row.archive_turns, mode=redaction_mode),
        "stable_memory": _sanitize_stable_memory(row.stable_memory or {}, mode=redaction_mode),
        "visible_turn": visible,
        "expect_notes": expected_notes,
        "expect_note_prefixes": expected_prefixes,
        "forbid_prompt_substrings": _forbidden_private_markers(row),
        "candidate_comment": "Local candidate only. Review before copying into tests/fixtures/retrieval_replay_cases.jsonl.",
    }


def build_conversation_experience_replay_case(
    row: ReplaySourceRow,
    *,
    redaction_mode: str = "balanced",
) -> dict[str, Any]:
    visible = _visible_turn(row)
    selected_ids = _expected_experience_case_ids(row)
    expect_selected_min = 1 if selected_ids else 0
    return {
        "id": _case_id("experience", row),
        "review_status": "candidate_local_unreviewed",
        "source_ref": row.source_ref,
        "source_kind": row.source_kind,
        "source_text_hash": _hash(row.user_text),
        "failure_signals": failure_signals(row),
        "payload": row.payload,
        "user_text": sanitize_replay_text(row.user_text, mode=redaction_mode),
        "dialogue_tail": _sanitize_dialogue_tail(row.dialogue_tail, mode=redaction_mode),
        "visible_turn": visible,
        "limit": 2,
        "expect_selected_min": expect_selected_min,
        "expect_selected_ids_any": selected_ids,
        "expect_notes": ["candidate_envelope_v1"] if expect_selected_min else [],
        "expect_note_prefixes": ["need_profile:"] if expect_selected_min else [],
        "expect_selected_envelope_source": "conversation_experience" if expect_selected_min else "",
        "forbid_selected_privacy_scopes": ["owner_private"] if row.payload == "group" else [],
        "candidate_comment": (
            "Local candidate only. Review before copying into "
            "tests/fixtures/conversation_experience_replay_cases.jsonl."
        ),
    }


def sanitize_replay_text(value: Any, *, mode: str = "balanced") -> str:
    text = _normalize(_safe_str(value))
    if not text:
        return ""
    redacted = SECRET_RE.sub(lambda match: f"{match.group(1)}=<redacted-secret:{_hash(match.group(2), 8)}>", text)
    redacted = QQ_RE.sub(lambda match: f"{match.group(1)}=<redacted-id:{_hash(match.group(2), 8)}>", redacted)
    redacted = URL_RE.sub(lambda match: f"<redacted-url:{_hash(match.group(0), 8)}>", redacted)
    redacted = EMAIL_RE.sub(lambda match: f"<redacted-email:{_hash(match.group(0), 8)}>", redacted)
    redacted = WINDOWS_PATH_RE.sub(lambda match: f"<redacted-path:{_hash(match.group(0), 8)}>", redacted)
    redacted = LONG_DIGIT_RE.sub(lambda match: f"id:{_hash(match.group(0), 8)}", redacted)
    if mode == "strict":
        return _strict_shape(redacted)
    if mode != "balanced":
        raise ValueError(f"unknown redaction mode: {mode}")
    return redacted


def is_failure_like(row: ReplaySourceRow) -> bool:
    quality = row.quality or {}
    if any(bool(quality.get(key)) for key in FAILURE_QUALITY_KEYS):
        return True
    lowered_notes = " ".join(row.notes).lower()
    if "error" in lowered_notes or "high_error" in lowered_notes:
        return True
    if _safe_str(quality.get("hard_failed")).lower() == "true":
        return True
    return False


def is_context_or_work_row(row: ReplaySourceRow) -> bool:
    text = " ".join([row.user_text, row.case_kind, " ".join(row.notes)])
    kind = row.case_kind.lower()
    if kind in {"context", "status", "work", "pressure", "mixed"}:
        return True
    return _contains_any(text, CONTEXT_MARKERS + TECHNICAL_MARKERS + STATUS_MARKERS + OWNER_PRESSURE_MARKERS)


def failure_signals(row: ReplaySourceRow) -> list[str]:
    signals: list[str] = []
    quality = row.quality or {}
    for key in FAILURE_QUALITY_KEYS:
        if bool(quality.get(key)):
            signals.append(key)
    for note in row.notes:
        lowered = note.lower()
        if "error" in lowered or "high_error" in lowered:
            signals.append("note:" + note[:80])
    if not signals and is_context_or_work_row(row):
        signals.append("context_or_work_candidate")
    return _dedupe(signals)


def _visible_turn(row: ReplaySourceRow) -> dict[str, Any]:
    pressure = row.pressure or {}
    turn_kind = _safe_str(pressure.get("turn_kind") or row.case_kind or "ordinary_owner_chat")
    if turn_kind == "missing":
        turn_kind = "ordinary_owner_chat"
    text = " ".join([row.user_text, row.case_kind, " ".join(row.notes)])
    return {
        "turn_kind": turn_kind,
        "technical_work": row.case_kind.lower() in {"work", "status", "mixed"} or _contains_any(text, TECHNICAL_MARKERS),
        "owner_style_pressure": row.case_kind.lower() == "pressure" or bool((row.quality or {}).get("reportish")),
        "owner_no_change_pressure": _contains_any(text, ("没变", "no change", "还是")),
        "relationship_pressure": False,
        "rest_silence": row.case_kind.lower() == "emotion",
    }


def _expected_experience_case_ids(row: ReplaySourceRow) -> list[str]:
    if row.payload == "group":
        return ["case-general-group-scenario-card-001"]
    text = " ".join([row.user_text, row.case_kind, " ".join(row.notes)])
    lowered = text.lower()
    ids: list[str] = []
    if _contains_any(lowered, STATUS_MARKERS) or row.case_kind.lower() in {"status", "work", "mixed"}:
        ids.extend(
            [
                "case-owner-status-remaining-work-001",
                "case-owner-technical-work-direct-001",
                "case-owner-execution-stopped-001",
            ]
        )
    if _contains_any(lowered, CONTEXT_MARKERS):
        ids.extend(["case-owner-current-turn-outranks-memory-001", "case-owner-status-remaining-work-001"])
    if row.case_kind.lower() == "pressure" or _contains_any(lowered, OWNER_PRESSURE_MARKERS):
        ids.extend(
            [
                "case-owner-frustration-short-repair-001",
                "case-owner-mechanics-overexplain-001",
                "case-owner-empty-promise-001",
            ]
        )
    return _dedupe(ids)[:4]


def _forbidden_private_markers(row: ReplaySourceRow) -> list[str]:
    markers: list[str] = []
    combined = "\n".join([row.user_text, row.assistant_reply])
    for pattern in ("group-only secret", "token=", "secret=", "authorization=", "password="):
        if pattern.lower() in combined.lower():
            markers.append(pattern)
    return _dedupe(markers)


def _sanitize_dialogue_tail(items: Iterable[dict[str, str]], *, mode: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        role = _safe_str(item.get("role"))
        content = sanitize_replay_text(item.get("content"), mode=mode)
        if role and content:
            result.append({"role": role, "content": content})
    return result


def _sanitize_archive_turns(items: Iterable[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "payload": _payload_kind(item.get("payload") or item),
                "user_text": sanitize_replay_text(item.get("user_text"), mode=mode),
                "assistant_reply": sanitize_replay_text(item.get("assistant_reply"), mode=mode),
                "message_type": _safe_str(item.get("message_type")),
            }
        )
    return result


def _sanitize_stable_memory(items: dict[str, str], *, mode: str) -> dict[str, str]:
    return {
        _safe_str(path): sanitize_replay_text(text, mode=mode)
        for path, text in items.items()
        if _safe_str(path)
    }


def _sanitize_tail_shape(value: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        return ()
    result: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            result.append({"role": _safe_str(item.get("role")), "content": _safe_str(item.get("content"))})
    return tuple(result)


def _sanitize_archive_turn_shape(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _stable_memory_shape(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    return {_safe_str(key): _safe_str(item) for key, item in value.items()}


def _payload_kind(value: Any) -> str:
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"group", "qq_group", "group_text"}:
            return "group"
        return "owner_private"
    if isinstance(value, dict):
        message_type = _safe_str(value.get("message_type")).lower()
        if message_type.startswith("group") or value.get("group_id"):
            return "group"
    return "owner_private"


def _strict_shape(text: str) -> str:
    markers: list[str] = []
    lowered = text.lower()
    for label, values in (
        ("context", CONTEXT_MARKERS),
        ("technical", TECHNICAL_MARKERS),
        ("status", STATUS_MARKERS),
        ("owner_pressure", OWNER_PRESSURE_MARKERS),
    ):
        if _contains_any(lowered, values):
            markers.append(label)
    marker_text = ",".join(_dedupe(markers)) or "none"
    return f"[private-text:{_hash(text, 12)} chars={len(text)} markers={marker_text}]"


def _jsonl(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    return "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in rows) + "\n"


def _source_kind_for_data(data: Any, path: Path) -> str:
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return "live_chat_baseline"
    return path.stem


def _case_id(prefix: str, row: ReplaySourceRow) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "-", row.row_id).strip("-").lower()
    clean = clean[:48] or _hash(row.row_id, 10)
    return f"{prefix}-{clean}-{_hash(row.source_ref + row.user_text, 8)}"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _safe_str(text).lower()
    return any(marker.lower() in lowered for marker in markers if marker)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _hash(value: Any, length: int = 16) -> str:
    return hashlib.sha256(_safe_str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _tuple_str(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(_safe_str(item) for item in value if _safe_str(item))
    if isinstance(value, tuple):
        return tuple(_safe_str(item) for item in value if _safe_str(item))
    text = _safe_str(value)
    return (text,) if text else ()


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _safe_str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _default_sources(root: Path) -> list[Path]:
    candidates = [
        root / "runtime" / "regression" / "last_live_chat_baseline.json",
    ]
    return [path for path in candidates if chat_replay_path_exists(path)]


def run_replay_tests(root: Path) -> int:
    completed = subprocess.run(
        [sys.executable, "smoke_run.py", "--group", "replay"],
        cwd=str(root),
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export local chat/regression failures into sanitized replay fixture candidates."
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--source", action="append", default=[], help="JSON or JSONL source. Repeatable.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--include-passing-context", action="store_true")
    parser.add_argument("--redaction", choices=["balanced", "strict"], default="balanced")
    parser.add_argument(
        "--auto-promote-safe",
        action="store_true",
        help="Strict-redact, validate, and append low-risk candidates into formal replay fixtures.",
    )
    parser.add_argument(
        "--max-promote-per-kind",
        type=int,
        default=6,
        help="Maximum auto-promoted retrieval cases and conversation cases. Use 0 for unlimited.",
    )
    parser.add_argument("--run-replay-tests", action="store_true", help="Run smoke_run.py --group replay after export.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    sources = [Path(item) for item in args.source]
    if not sources:
        sources = _default_sources(root)
    sources = [path if path.is_absolute() else root / path for path in sources]
    if not sources:
        print(json.dumps({"ok": False, "notes": ["no_sources_found"]}, ensure_ascii=False, indent=2))
        return 2

    output_dir = args.output_dir or (root / DEFAULT_OUTPUT_DIR)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    summary = export_replay_candidates(
        sources,
        output_dir=output_dir,
        limit=args.limit,
        redaction_mode=args.redaction,
        include_passing_context=args.include_passing_context,
        fixture_root=root,
        auto_promote_safe=args.auto_promote_safe,
        max_promote_per_kind=args.max_promote_per_kind,
        dry_run=args.dry_run,
    )
    if args.run_replay_tests and not args.dry_run:
        summary["replay_tests_exit_code"] = run_replay_tests(root)
    print(json.dumps({"ok": True, **summary}, ensure_ascii=False, indent=2, sort_keys=True))
    return int(summary.get("replay_tests_exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
