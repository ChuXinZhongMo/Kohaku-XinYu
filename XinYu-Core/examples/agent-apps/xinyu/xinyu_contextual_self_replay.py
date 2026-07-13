from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Sequence

from xinyu_contextual_recall import (
    append_contextual_recall_trace,
    build_contextual_recall_snapshot,
    write_contextual_recall_state,
)
from xinyu_contextual_self_loop import (
    build_contextual_self_loop_snapshot,
    append_contextual_self_loop_trace,
    write_contextual_self_loop_state,
)
from xinyu_contextual_self_observatory import run_contextual_self_observatory
from xinyu_storage_paths import resolve_public_dataset_input_paths


TRACE_REL = Path("runtime/contextual_self_replay_trace.jsonl")
SUMMARY_REL = Path("runtime/contextual_self_replay_summary.json")
CALIBRATION_REPORT_REL = Path("runtime/contextual_self_replay_calibration_report.json")
STATE_REL = Path("memory/context/contextual_self_replay_state.md")
CANONICAL_RECALL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
CONTEXTUAL_SELF_REPLAY_ROLE = "ops/lab_public_dataset_replay"
CONTEXTUAL_SELF_REPLAY_BOUNDARY = "offline_replay_not_live_recall_owner"

SUPPORTED_SUFFIXES = {".jsonl", ".ndjson", ".json", ".parquet"}
VALID_SCENES = {
    "project_work",
    "memory_review",
    "initiative_feedback",
    "runtime_status",
    "emotional_relation",
    "casual_chat",
}

TEXT_FIELD_KEYS = (
    "user_text",
    "prompt",
    "instruction",
    "query",
    "question",
    "input",
    "text",
    "raw_dialogue",
)
CONVERSATION_KEYS = (
    "conversation",
    "conversations",
    "messages",
    "dialogue",
    "turns",
    "history",
)
ROLE_KEYS = ("role", "from", "speaker", "author")
CONTENT_KEYS = ("content", "value", "text", "message", "utterance")
USER_ROLES = {"user", "human", "prompter", "owner", "client", "customer"}
ASSISTANT_ROLES = {"assistant", "gpt", "bot", "model", "chatgpt", "agent"}


@dataclass(frozen=True, slots=True)
class ReplaySample:
    sample_id: str
    dataset: str
    text: str
    expected_scene: str = ""
    evidence_like: bool = False
    source_ref: str = ""
    turn_index: int = 0


@dataclass(frozen=True, slots=True)
class ReplayLoadResult:
    samples: tuple[ReplaySample, ...]
    warnings: tuple[str, ...]


def load_public_replay_samples(
    paths: Sequence[Path | str],
    *,
    dataset_name: str = "",
    limit: int = 0,
    per_record_user_turn_limit: int = 3,
) -> ReplayLoadResult:
    samples: list[ReplaySample] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for input_path in paths:
        path = Path(input_path)
        for record, source_ref in _iter_public_records(path, warnings=warnings):
            dataset = _clean_token(dataset_name or _record_dataset(record) or path.stem, default="public")
            expected_scene = _expected_scene(record)
            evidence_like = _evidence_like_record(record)
            for turn_index, text in enumerate(_extract_user_texts(record)[: max(1, per_record_user_turn_limit)]):
                clean_text = _clean_text(text)
                if not clean_text:
                    continue
                text_hash = _short_hash(clean_text, length=16)
                dedupe_key = f"{dataset}:{text_hash}"
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                sample_id = _record_id(record) or f"{dataset}-{len(samples) + 1:05d}-{text_hash}"
                samples.append(
                    ReplaySample(
                        sample_id=_clean_token(sample_id, default=f"sample-{len(samples) + 1}"),
                        dataset=dataset,
                        text=clean_text,
                        expected_scene=expected_scene,
                        evidence_like=evidence_like,
                        source_ref=source_ref,
                        turn_index=turn_index,
                    )
                )
                if limit and len(samples) >= limit:
                    return ReplayLoadResult(samples=tuple(samples), warnings=tuple(warnings))
    return ReplayLoadResult(samples=tuple(samples), warnings=tuple(warnings))


def run_public_dataset_replay(
    root: Path | str,
    paths: Sequence[Path | str],
    *,
    dataset_name: str = "",
    limit: int = 50,
    started_at: str | None = None,
    run_initiative: bool = False,
    write_summary: bool = True,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    dataset_paths = resolve_public_dataset_input_paths(root_path, paths, dataset_id=dataset_name)
    load_result = load_public_replay_samples(dataset_paths, dataset_name=dataset_name, limit=limit)
    return replay_samples(
        root_path,
        load_result.samples,
        started_at=started_at,
        run_initiative=run_initiative,
        write_summary=write_summary,
        load_warnings=load_result.warnings,
    )


def replay_samples(
    root: Path | str,
    samples: Sequence[ReplaySample],
    *,
    started_at: str | None = None,
    run_initiative: bool = False,
    write_summary: bool = True,
    load_warnings: Sequence[str] = (),
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    base_time = _parse_iso(started_at) or datetime.now().astimezone()
    events: list[dict[str, Any]] = []
    for index, sample in enumerate(samples):
        evaluated_at = (base_time + timedelta(seconds=index)).isoformat(timespec="seconds")
        snapshot = build_contextual_self_loop_snapshot(
            root_path,
            user_text=sample.text,
            trigger="public_dataset_replay",
            evaluated_at=evaluated_at,
        )
        write_contextual_self_loop_state(root_path, snapshot)
        append_contextual_self_loop_trace(root_path, snapshot, user_text=sample.text)
        recall = build_contextual_recall_snapshot(
            root_path,
            contextual_self=snapshot,
            user_text=sample.text,
            evaluated_at=evaluated_at,
            max_items=4,
        )
        write_contextual_recall_state(root_path, recall)
        append_contextual_recall_trace(root_path, recall, user_text=sample.text)
        initiative_status = ""
        if run_initiative:
            initiative_status = _run_initiative_dry(root_path, checked_at=evaluated_at)
        event = _replay_event(
            sample=sample,
            evaluated_at=evaluated_at,
            observed_scene=snapshot.current_scene,
            retrieval_pressure=snapshot.retrieval_pressure,
            retrieval_pressure_signals=snapshot.retrieval_pressure_signals,
            recall_admitted_count=len(recall.admitted),
            evidence_sufficiency=recall.evidence_sufficiency,
            answer_discipline=recall.answer_discipline,
            initiative_status=initiative_status,
        )
        _append_jsonl(root_path / TRACE_REL, event)
        events.append(event)

    observed_at = _timestamp_or_now_iso((base_time + timedelta(seconds=max(0, len(samples)))).isoformat(timespec="seconds"))
    observatory = run_contextual_self_observatory(root_path, observed_at=observed_at)
    summary = _build_replay_summary(
        events=events,
        observatory=observatory,
        load_warnings=load_warnings,
        observed_at=observed_at,
    )
    if write_summary:
        _write_json_atomic(root_path / SUMMARY_REL, summary)
        _write_json_atomic(
            root_path / CALIBRATION_REPORT_REL,
            build_replay_calibration_report_from_events(events, observed_at=observed_at),
        )
        _write_state(root_path, summary)
    return summary


def run_replay_calibration_report(
    root: Path | str,
    *,
    limit: int = 500,
    observed_at: str | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    events = _read_jsonl(root_path / TRACE_REL)
    if limit > 0:
        events = events[-limit:]
    report = build_replay_calibration_report_from_events(
        events,
        observed_at=_timestamp_or_now_iso(observed_at),
    )
    _write_json_atomic(root_path / CALIBRATION_REPORT_REL, report)
    return report


def build_replay_calibration_report_from_events(
    events: Sequence[dict[str, Any]],
    *,
    observed_at: str,
) -> dict[str, Any]:
    observed_at = _timestamp_or_now_iso(observed_at)
    dataset_pressure_counts: dict[str, dict[str, int]] = {}
    dataset_scene_counts: dict[str, dict[str, int]] = {}
    dataset_sufficiency_counts: dict[str, dict[str, int]] = {}
    evidence_like_events: list[dict[str, Any]] = []
    evidence_like_missed: list[dict[str, Any]] = []
    over_retrieval_candidates: list[dict[str, Any]] = []

    for event in events:
        dataset = _safe_str(event.get("dataset"), "unknown")
        pressure = _safe_str(event.get("retrieval_pressure"), "unknown")
        scene = _safe_str(event.get("observed_scene"), "unknown")
        dataset_pressure_counts.setdefault(dataset, {})
        dataset_pressure_counts[dataset][pressure] = dataset_pressure_counts[dataset].get(pressure, 0) + 1
        dataset_scene_counts.setdefault(dataset, {})
        dataset_scene_counts[dataset][scene] = dataset_scene_counts[dataset].get(scene, 0) + 1
        sufficiency = _safe_str(event.get("evidence_sufficiency"), "unknown")
        dataset_sufficiency_counts.setdefault(dataset, {})
        dataset_sufficiency_counts[dataset][sufficiency] = dataset_sufficiency_counts[dataset].get(sufficiency, 0) + 1

        evidence_like = bool(event.get("evidence_like"))
        if evidence_like:
            evidence_like_events.append(event)
            if pressure not in {"medium", "high"}:
                evidence_like_missed.append(event)
        elif pressure == "high":
            over_retrieval_candidates.append(event)

    evidence_like_detected = [
        event for event in evidence_like_events if event.get("retrieval_pressure") in {"medium", "high"}
    ]
    high_pressure_count = sum(
        1 for event in events if _safe_str(event.get("retrieval_pressure")) == "high"
    )
    medium_high_count = sum(
        1 for event in events if _safe_str(event.get("retrieval_pressure")) in {"medium", "high"}
    )
    return _clean_json_value(
        {
            "updated_at": _timestamp_or_now_iso(observed_at),
            "sample_count": len(events),
            "dataset_pressure_counts": _sort_nested_counts(dataset_pressure_counts),
            "dataset_scene_counts": _sort_nested_counts(dataset_scene_counts),
            "dataset_sufficiency_counts": _sort_nested_counts(dataset_sufficiency_counts),
            "medium_high_ratio": round(medium_high_count / len(events), 4) if events else None,
            "high_pressure_count": high_pressure_count,
            "evidence_like_sample_count": len(evidence_like_events),
            "evidence_like_pressure_detected_rate": round(len(evidence_like_detected) / len(evidence_like_events), 4)
            if evidence_like_events
            else None,
            "evidence_like_missed": [_diagnostic_event(event) for event in evidence_like_missed[:50]],
            "over_retrieval_candidates": [_diagnostic_event(event) for event in over_retrieval_candidates[:50]],
            "notes": [
                "calibration_only",
                "no_raw_user_text",
                "inspect_missed_evidence_and_high_pressure_non_evidence",
            ],
        }
    )


def _iter_public_records(path: Path, *, warnings: list[str]) -> Iterator[tuple[dict[str, Any], str]]:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix.lower() in SUPPORTED_SUFFIXES:
                yield from _iter_public_records(child, warnings=warnings)
        return
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        yield from _iter_jsonl(path, warnings=warnings)
        return
    if suffix == ".json":
        yield from _iter_json(path, warnings=warnings)
        return
    if suffix == ".parquet":
        yield from _iter_parquet(path, warnings=warnings)
        return
    warnings.append(f"unsupported_file:{path}")


def _iter_jsonl(path: Path, *, warnings: list[str]) -> Iterator[tuple[dict[str, Any], str]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError as exc:
        warnings.append(f"read_failed:{path}:{type(exc).__name__}")
        return
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            warnings.append(f"json_decode_failed:{path}:{line_number}")
            continue
        if isinstance(data, dict):
            yield data, f"{path.name}:{line_number}"


def _iter_json(path: Path, *, warnings: list[str]) -> Iterator[tuple[dict[str, Any], str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"json_read_failed:{path}:{type(exc).__name__}")
        return
    records = _records_from_json_value(data)
    for index, record in enumerate(records, start=1):
        yield record, f"{path.name}:{index}"


def _iter_parquet(path: Path, *, warnings: list[str]) -> Iterator[tuple[dict[str, Any], str]]:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError:
        warnings.append(f"parquet_skipped_missing_pyarrow:{path}")
        return
    try:
        table = pq.read_table(path)
        rows = table.to_pylist()
    except Exception as exc:  # pragma: no cover - depends on optional pyarrow/runtime file
        warnings.append(f"parquet_read_failed:{path}:{type(exc).__name__}")
        return
    for index, row in enumerate(rows, start=1):
        if isinstance(row, dict):
            yield row, f"{path.name}:{index}"


def _records_from_json_value(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [_normalize_public_record(item) for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("data", "rows", "records", "samples", "train", "validation", "test"):
        child = value.get(key)
        if isinstance(child, list):
            return [_normalize_public_record(item) for item in child if isinstance(item, dict)]
    return [_normalize_public_record(value)]


def _normalize_public_record(record: dict[str, Any]) -> dict[str, Any]:
    row = record.get("row")
    if isinstance(row, dict):
        merged = dict(row)
        for key in ("dataset", "source", "corpus", "origin", "expected_scene", "scene", "id", "sample_id"):
            if key in record and key not in merged:
                merged[key] = record[key]
        return merged
    return record


def _extract_user_texts(record: dict[str, Any]) -> list[str]:
    row = record.get("row")
    if isinstance(row, dict):
        return _extract_user_texts(row)
    role = _turn_role(record)
    content = _turn_content(record)
    if content and (role in USER_ROLES or not role):
        return [content]
    for key in CONVERSATION_KEYS:
        value = record.get(key)
        if isinstance(value, list):
            texts = _extract_from_turn_list(value)
            if texts:
                return texts
    raw_dialogue = record.get("raw_dialogue")
    if isinstance(raw_dialogue, str):
        texts = _extract_from_raw_dialogue(raw_dialogue)
        if texts:
            return texts
    for key in TEXT_FIELD_KEYS:
        value = record.get(key)
        if isinstance(value, str) and _field_is_user_like(key, value):
            return [value]
    return []


def _extract_from_turn_list(turns: list[Any]) -> list[str]:
    texts: list[str] = []
    for index, turn in enumerate(turns):
        if isinstance(turn, str):
            if index % 2 == 0:
                texts.append(turn)
            continue
        if not isinstance(turn, dict):
            continue
        role = _turn_role(turn)
        content = _turn_content(turn)
        if not content:
            continue
        if role in USER_ROLES or (not role and index % 2 == 0):
            texts.append(content)
        elif role and role not in ASSISTANT_ROLES and index % 2 == 0:
            texts.append(content)
    return texts


def _extract_from_raw_dialogue(text: str) -> list[str]:
    for line in text.splitlines():
        clean = line.strip()
        if not clean or clean.startswith("\u4e3b\u9898") or clean.startswith("\u7ec6\u5316\u4e3b\u9898"):
            continue
        if "\uff1a" not in clean and ":" not in clean:
            continue
        speaker, content = re.split(r"[:\uff1a]", clean, maxsplit=1)
        speaker = speaker.strip().lower()
        content = content.strip()
        if not content:
            continue
        if speaker in {"lucy", "assistant", "system"} or "\u52a9\u624b" in speaker:
            continue
        return [content]
    return []


def _turn_role(turn: dict[str, Any]) -> str:
    for key in ROLE_KEYS:
        value = turn.get(key)
        if isinstance(value, str):
            return value.strip().lower()
    return ""


def _turn_content(turn: dict[str, Any]) -> str:
    for key in CONTENT_KEYS:
        value = turn.get(key)
        if isinstance(value, str):
            return value
    return ""


def _field_is_user_like(key: str, value: str) -> bool:
    del value
    return key in set(TEXT_FIELD_KEYS)


def _expected_scene(record: dict[str, Any]) -> str:
    for key in ("expected_scene", "scene", "label_scene", "xinyu_scene"):
        value = record.get(key)
        if isinstance(value, str):
            clean = value.strip()
            if clean in VALID_SCENES:
                return clean
    return ""


def _evidence_like_record(record: dict[str, Any]) -> bool:
    row = record.get("row")
    if isinstance(row, dict):
        return _evidence_like_record(row)
    for key in ("evidence_turn_ids", "evidence", "evidence_turns", "supporting_turns", "gold_turn_ids"):
        value = record.get(key)
        if isinstance(value, list) and len(value) > 0:
            return True
        if isinstance(value, str) and value.strip() not in {"", "[]", "null", "none"}:
            return True
    return False


def _record_dataset(record: dict[str, Any]) -> str:
    for key in ("dataset", "source", "corpus", "origin"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _record_id(record: dict[str, Any]) -> str:
    for key in ("id", "conversation_id", "sample_id", "uid", "uuid"):
        value = record.get(key)
        if isinstance(value, (str, int)):
            return str(value)
    return ""


def _run_initiative_dry(root: Path, *, checked_at: str) -> str:
    try:
        from xinyu_initiative_orchestrator import run_initiative_orchestrator
    except ImportError:
        return "unavailable"
    result = run_initiative_orchestrator(
        root,
        checked_at=checked_at,
        trigger="public_dataset_replay",
        dry_run=True,
    )
    return _clean_token(result.get("status"), default="unknown")


def _replay_event(
    *,
    sample: ReplaySample,
    evaluated_at: str,
    observed_scene: str,
    retrieval_pressure: str,
    retrieval_pressure_signals: Sequence[str],
    recall_admitted_count: int,
    evidence_sufficiency: str,
    answer_discipline: str,
    initiative_status: str,
) -> dict[str, Any]:
    expected = sample.expected_scene
    return {
        "event_id": "ctxreplay-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + "-" + _short_hash(time.time_ns()),
        "ts": evaluated_at,
        "stage": "public_dataset_replay",
        "status": "evaluated",
        "sample_id": sample.sample_id,
        "dataset": sample.dataset,
        "source_ref": sample.source_ref,
        "turn_index": sample.turn_index,
        "user_text_hash": _short_hash(sample.text, length=16),
        "text_shape": _text_shape(sample.text),
        "expected_scene": expected,
        "observed_scene": observed_scene,
        "retrieval_pressure": retrieval_pressure,
        "retrieval_pressure_signals": list(retrieval_pressure_signals),
        "recall_admitted_count": recall_admitted_count,
        "evidence_sufficiency": evidence_sufficiency,
        "answer_discipline": answer_discipline,
        "evidence_like": sample.evidence_like,
        "candidate_reason": _candidate_reason(
            evidence_like=sample.evidence_like,
            retrieval_pressure=retrieval_pressure,
            signals=retrieval_pressure_signals,
            recall_admitted_count=recall_admitted_count,
        ),
        "scene_match": bool(expected and expected == observed_scene),
        "initiative_status": initiative_status,
        "notes": ["no_llm_call", "no_raw_user_text", "public_data_local_only"],
    }


def _build_replay_summary(
    *,
    events: Sequence[dict[str, Any]],
    observatory: dict[str, Any],
    load_warnings: Sequence[str],
    observed_at: str,
) -> dict[str, Any]:
    observed_at = _timestamp_or_now_iso(observed_at)
    expected = [event for event in events if event.get("expected_scene")]
    matched = [event for event in expected if event.get("scene_match")]
    scene_counts: dict[str, int] = {}
    dataset_counts: dict[str, int] = {}
    pressure_counts: dict[str, int] = {}
    mismatches: list[dict[str, Any]] = []
    for event in events:
        scene = _safe_str(event.get("observed_scene"), "unknown")
        dataset = _safe_str(event.get("dataset"), "unknown")
        pressure = _safe_str(event.get("retrieval_pressure"), "unknown")
        scene_counts[scene] = scene_counts.get(scene, 0) + 1
        dataset_counts[dataset] = dataset_counts.get(dataset, 0) + 1
        pressure_counts[pressure] = pressure_counts.get(pressure, 0) + 1
        if event.get("expected_scene") and not event.get("scene_match"):
            mismatches.append(
                {
                    "sample_id": event.get("sample_id"),
                    "dataset": event.get("dataset"),
                    "expected_scene": event.get("expected_scene"),
                    "observed_scene": event.get("observed_scene"),
                    "user_text_hash": event.get("user_text_hash"),
                }
            )
    high_pressure_events = [event for event in events if event.get("retrieval_pressure") == "high"]
    high_pressure_none = [event for event in high_pressure_events if event.get("evidence_sufficiency") == "none"]
    high_pressure_weak = [event for event in high_pressure_events if event.get("evidence_sufficiency") == "weak"]
    high_pressure_usable = [event for event in high_pressure_events if event.get("evidence_sufficiency") == "usable"]
    evidence_like_events = [event for event in events if event.get("evidence_like")]
    evidence_like_recalled = [event for event in evidence_like_events if int(event.get("recall_admitted_count") or 0) > 0]
    evidence_like_pressure_detected = [
        event for event in evidence_like_events if event.get("retrieval_pressure") in {"medium", "high"}
    ]
    return _clean_json_value(
        {
            "updated_at": _timestamp_or_now_iso(observed_at),
            "sample_count": len(events),
            "dataset_counts": dict(sorted(dataset_counts.items())),
            "observed_scene_counts": dict(sorted(scene_counts.items())),
            "retrieval_pressure_counts": dict(sorted(pressure_counts.items())),
            "high_pressure_recall_admitted_count": sum(int(event.get("recall_admitted_count") or 0) for event in high_pressure_events),
            "high_pressure_no_evidence_count": len(high_pressure_none),
            "high_pressure_weak_evidence_count": len(high_pressure_weak),
            "high_pressure_usable_evidence_count": len(high_pressure_usable),
            "evidence_like_sample_count": len(evidence_like_events),
            "evidence_like_sample_recall_rate": round(len(evidence_like_recalled) / len(evidence_like_events), 4) if evidence_like_events else None,
            "evidence_like_pressure_detected_rate": round(len(evidence_like_pressure_detected) / len(evidence_like_events), 4) if evidence_like_events else None,
            "expected_scene_count": len(expected),
            "scene_match_count": len(matched),
            "scene_match_rate": round(len(matched) / len(expected), 4) if expected else None,
            "mismatches": mismatches[:50],
            "load_warnings": list(load_warnings)[:50],
            "observatory": {
                "posture": observatory.get("posture"),
                "self_loop_event_count_24h": observatory.get("self_loop_event_count_24h"),
                "recall_event_count_24h": observatory.get("recall_event_count_24h"),
                "recall_admitted_count_24h": observatory.get("recall_admitted_count_24h"),
                "initiative_held_by_context_count_24h": observatory.get("initiative_held_by_context_count_24h"),
                "initiative_allowed_by_context_count_24h": observatory.get("initiative_allowed_by_context_count_24h"),
            },
            "boundaries": {
                "llm_calls": "blocked",
                "raw_user_text_in_trace": "blocked",
                "public_dataset_source": "local_file_only",
                "initiative_delivery": "dry_run_only_when_enabled",
            },
        }
    )


def _diagnostic_event(event: dict[str, Any]) -> dict[str, Any]:
    signals = event.get("retrieval_pressure_signals")
    if not isinstance(signals, list):
        signals = []
    return {
        "sample_id": event.get("sample_id"),
        "dataset": event.get("dataset"),
        "source_ref": event.get("source_ref"),
        "turn_index": event.get("turn_index"),
        "user_text_hash": event.get("user_text_hash"),
        "text_shape": event.get("text_shape"),
        "observed_scene": event.get("observed_scene"),
        "retrieval_pressure": event.get("retrieval_pressure"),
        "retrieval_pressure_signals": signals,
        "evidence_sufficiency": event.get("evidence_sufficiency"),
        "answer_discipline": event.get("answer_discipline"),
        "candidate_reason": event.get("candidate_reason"),
        "recall_admitted_count": event.get("recall_admitted_count"),
        "evidence_like": event.get("evidence_like"),
    }


def _candidate_reason(
    *,
    evidence_like: bool,
    retrieval_pressure: str,
    signals: Sequence[str],
    recall_admitted_count: int,
) -> str:
    if evidence_like and retrieval_pressure not in {"medium", "high"}:
        return "missed_evidence_like_pressure"
    if (not evidence_like) and retrieval_pressure == "high":
        return "high_pressure_without_evidence_label"
    if recall_admitted_count <= 0 and retrieval_pressure in {"medium", "high"}:
        return "pressure_without_recall"
    if signals:
        return "signal_driven_pressure"
    return "ordinary_replay_sample"


def _text_shape(text: str) -> dict[str, Any]:
    clean = _clean_text(text)
    length = len(clean)
    if length < 40:
        bucket = "short"
    elif length < 180:
        bucket = "medium"
    elif length < 800:
        bucket = "long"
    else:
        bucket = "very_long"
    ascii_letters = sum(1 for ch in clean if ("a" <= ch.lower() <= "z"))
    cjk_chars = sum(1 for ch in clean if "\u4e00" <= ch <= "\u9fff")
    if cjk_chars > ascii_letters:
        language_guess = "zh"
    elif ascii_letters:
        language_guess = "en"
    else:
        language_guess = "unknown"
    return {
        "length_bucket": bucket,
        "language_guess": language_guess,
        "has_question_mark": "?" in clean or "\uff1f" in clean,
        "has_cjk": cjk_chars > 0,
        "has_ascii_letters": ascii_letters > 0,
    }


def _sort_nested_counts(data: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    return {key: dict(sorted(value.items())) for key, value in sorted(data.items())}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    return events


def _write_state(root: Path, summary: dict[str, Any]) -> None:
    lines = [
        "---",
        "title: Contextual Self Replay State",
        "memory_type: contextual_self_replay_state",
        "time_scope: calibration_runtime",
        "subject_ids: [xinyu]",
        "protected: true",
        "source: xinyu_contextual_self_replay",
        f"updated_at: {_timestamp_or_now_iso(summary.get('updated_at'))}",
        "status: active",
        "tags: [context, replay, calibration, public_data]",
        "---",
        "",
        "# Contextual Self Replay State",
        "",
        f"- updated_at: {_timestamp_or_now_iso(summary.get('updated_at'))}",
        f"- sample_count: {_safe_str(summary.get('sample_count'))}",
        f"- expected_scene_count: {_safe_str(summary.get('expected_scene_count'))}",
        f"- scene_match_count: {_safe_str(summary.get('scene_match_count'))}",
        f"- scene_match_rate: {_safe_str(summary.get('scene_match_rate'))}",
        f"- evidence_like_sample_count: {_safe_str(summary.get('evidence_like_sample_count'))}",
        f"- evidence_like_sample_recall_rate: {_safe_str(summary.get('evidence_like_sample_recall_rate'))}",
        f"- evidence_like_pressure_detected_rate: {_safe_str(summary.get('evidence_like_pressure_detected_rate'))}",
        f"- high_pressure_recall_admitted_count: {_safe_str(summary.get('high_pressure_recall_admitted_count'))}",
        f"- high_pressure_no_evidence_count: {_safe_str(summary.get('high_pressure_no_evidence_count'))}",
        f"- high_pressure_weak_evidence_count: {_safe_str(summary.get('high_pressure_weak_evidence_count'))}",
        f"- high_pressure_usable_evidence_count: {_safe_str(summary.get('high_pressure_usable_evidence_count'))}",
        "",
        "## Boundaries",
        "- llm_calls: blocked",
        "- raw_user_text_in_trace: blocked",
        "- public_dataset_source: local_file_only",
        "- initiative_delivery: dry_run_only_when_enabled",
        "",
        "## Observed Scene Counts",
    ]
    scene_counts = summary.get("observed_scene_counts")
    if isinstance(scene_counts, dict) and scene_counts:
        lines.extend(f"- {key}: {value}" for key, value in scene_counts.items())
    else:
        lines.append("- none")
    lines.extend(["", "## Retrieval Pressure Counts"])
    pressure_counts = summary.get("retrieval_pressure_counts")
    if isinstance(pressure_counts, dict) and pressure_counts:
        lines.extend(f"- {key}: {value}" for key, value in pressure_counts.items())
    else:
        lines.append("- none")
    lines.extend(["", "## Dataset Counts"])
    dataset_counts = summary.get("dataset_counts")
    if isinstance(dataset_counts, dict) and dataset_counts:
        lines.extend(f"- {key}: {value}" for key, value in dataset_counts.items())
    else:
        lines.append("- none")
    _write_text_atomic(root / STATE_REL, "\n".join(lines).rstrip() + "\n")


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


def _clean_text(value: str) -> str:
    text = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    return text[:4000]


def _clean_token(value: Any, *, default: str = "unknown") -> str:
    text = _safe_str(value, default).strip() or default
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "-" for ch in text)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:120] or default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _short_hash(value: Any, *, length: int = 10) -> str:
    return hashlib.sha256(_safe_str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_clean_json_value(event), ensure_ascii=False, sort_keys=True) + "\n")


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(_clean_json_value(data), ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _safe_str(value)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay public dialogue data through XinYu contextual self calibration.")
    parser.add_argument("--root", default=".", help="XinYu app root. Defaults to current directory.")
    parser.add_argument("--dataset", action="append", help="Local JSON/JSONL/Parquet file, directory, or alias.")
    parser.add_argument("--dataset-name", default="", help="Dataset label and default alias when --dataset is omitted.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum replay samples.")
    parser.add_argument("--started-at", default="", help="Optional ISO timestamp used as synthetic replay start.")
    parser.add_argument("--run-initiative", action="store_true", help="Also run initiative orchestrator in dry-run mode.")
    parser.add_argument("--report-only", action="store_true", help="Build calibration report from existing replay trace.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.report_only:
        report = run_replay_calibration_report(Path(args.root), limit=args.limit)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not args.dataset and not args.dataset_name:
        parser.error("--dataset or --dataset-name is required unless --report-only is set")
    summary = run_public_dataset_replay(
        Path(args.root),
        [Path(item) for item in args.dataset or ()],
        dataset_name=args.dataset_name,
        limit=args.limit,
        started_at=args.started_at or None,
        run_initiative=args.run_initiative,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
