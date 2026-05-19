from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from xinyu_contextual_self_replay import ReplaySample, load_public_replay_samples
from xinyu_conversation_experience_cases import (
    ConversationExperienceCase,
    ConversationExperienceCaseError,
    case_to_dict,
    upsert_case,
    validate_case,
)
from xinyu_public_dataset_registry import (
    BACKLOG_EXECUTION_STATUSES,
    BLOCKED_EXECUTION_STATUSES,
    SKIPPED_EXECUTION_STATUSES,
    PublicDatasetEntry,
    load_public_dataset_registry,
)
from xinyu_storage_paths import resolve_public_dataset_input_paths


class PublicDatasetCaseImportError(ValueError):
    pass


@dataclass(frozen=True)
class PublicDatasetCaseBuild:
    case: ConversationExperienceCase
    sample_id: str
    sample_hash: str
    scenario: str


def build_public_dataset_case_cards(
    root: Path | str,
    paths: Sequence[Path | str],
    *,
    dataset_id: str,
    registry_root: Path | str | None = None,
    limit: int = 50,
    include_backlog: bool = False,
    allow_blocked_after_owner_review: bool = False,
    allow_observation_only: bool = False,
) -> tuple[PublicDatasetCaseBuild, ...]:
    root_path = Path(root)
    entry = _registry_entry(
        Path(registry_root) if registry_root is not None else root_path,
        dataset_id,
        include_backlog=include_backlog,
        allow_blocked_after_owner_review=allow_blocked_after_owner_review,
        allow_observation_only=allow_observation_only,
    )
    load_result = load_public_replay_samples(
        resolve_public_dataset_input_paths(root_path, paths, dataset_id=entry.dataset_id),
        dataset_name=entry.dataset_id,
        limit=max(1, int(limit)),
        per_record_user_turn_limit=2,
    )
    builds: list[PublicDatasetCaseBuild] = []
    for sample in load_result.samples:
        case = validate_case(_case_data_from_sample(sample, entry))
        builds.append(
            PublicDatasetCaseBuild(
                case=case,
                sample_id=sample.sample_id,
                sample_hash=_text_hash(sample.text),
                scenario=_scenario_label(sample, entry),
            )
        )
    return tuple(builds)


def import_public_dataset_cases(
    root: Path | str,
    paths: Sequence[Path | str],
    *,
    dataset_id: str,
    registry_root: Path | str | None = None,
    limit: int = 50,
    write: bool = True,
    include_backlog: bool = False,
    allow_blocked_after_owner_review: bool = False,
    allow_observation_only: bool = False,
) -> dict[str, Any]:
    root_path = Path(root)
    entry = _registry_entry(
        Path(registry_root) if registry_root is not None else root_path,
        dataset_id,
        include_backlog=include_backlog,
        allow_blocked_after_owner_review=allow_blocked_after_owner_review,
        allow_observation_only=allow_observation_only,
    )
    load_result = load_public_replay_samples(
        resolve_public_dataset_input_paths(root_path, paths, dataset_id=entry.dataset_id),
        dataset_name=entry.dataset_id,
        limit=max(1, int(limit)),
        per_record_user_turn_limit=2,
    )

    imported = 0
    errors: list[str] = []
    case_ids: list[str] = []
    review_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    scenarios: Counter[str] = Counter()

    for sample in load_result.samples:
        try:
            case = validate_case(_case_data_from_sample(sample, entry))
            review_counts[case.review_status] += 1
            tag_counts.update(case.scenario_tags)
            scenarios[_scenario_label(sample, entry)] += 1
            case_ids.append(case.case_id)
            if write:
                upsert_case(root_path, case)
                imported += 1
        except (ConversationExperienceCaseError, OSError) as exc:
            errors.append(f"{sample.sample_id}:{type(exc).__name__}:{exc}")

    return {
        "dataset_id": entry.dataset_id,
        "role": entry.role,
        "execution_status": entry.execution_status,
        "write": bool(write),
        "sample_count": len(load_result.samples),
        "generated": len(case_ids),
        "imported": imported,
        "errors": errors,
        "warnings": list(load_result.warnings),
        "case_ids": case_ids,
        "review_status_counts": dict(sorted(review_counts.items())),
        "scenario_counts": dict(sorted(scenarios.items())),
        "scenario_tag_counts": dict(sorted(tag_counts.items())),
        "notes": [
            "public_dataset_case_import_done",
            "abstract_case_cards_only",
            "no_raw_user_text",
            "public_cases_require_manual_review",
            "dry_run" if not write else "written_to_case_store",
        ],
    }


def _registry_entry(
    root: Path,
    dataset_id: str,
    *,
    include_backlog: bool,
    allow_blocked_after_owner_review: bool,
    allow_observation_only: bool,
) -> PublicDatasetEntry:
    clean_id = _clean_token(dataset_id, default="")
    entries = {entry.dataset_id: entry for entry in load_public_dataset_registry(root)}
    entry = entries.get(clean_id)
    if entry is None:
        raise PublicDatasetCaseImportError(f"unknown public dataset:{dataset_id}")
    if entry.dataset_kind != "public_dataset":
        raise PublicDatasetCaseImportError(f"{entry.dataset_id}: owner seed cases are not public imports")
    if entry.execution_status in SKIPPED_EXECUTION_STATUSES:
        raise PublicDatasetCaseImportError(f"{entry.dataset_id}: skipped by registry:{entry.execution_status}")
    if entry.execution_status in BLOCKED_EXECUTION_STATUSES and not allow_blocked_after_owner_review:
        raise PublicDatasetCaseImportError(f"{entry.dataset_id}: blocked by registry:{entry.execution_status}")
    if entry.execution_status in BACKLOG_EXECUTION_STATUSES and not include_backlog:
        raise PublicDatasetCaseImportError(f"{entry.dataset_id}: backlog source requires include_backlog")
    if entry.role == "user_input_distribution" and not allow_observation_only:
        raise PublicDatasetCaseImportError(f"{entry.dataset_id}: observation-only source requires allow_observation_only")
    return entry


def _case_data_from_sample(sample: ReplaySample, entry: PublicDatasetEntry) -> dict[str, Any]:
    sample_hash = _text_hash(sample.text)
    scenario = _scenario_label(sample, entry)
    tags = _scenario_tags(sample, entry, scenario)
    review_status = entry.default_review_status
    if review_status == "approved":
        review_status = "pending"

    return {
        "case_id": f"case-public-{entry.dataset_id}-{sample_hash[:12]}",
        "version": 1,
        "source_tier": "public_pattern",
        "source_ref": f"public_dataset:{entry.dataset_id}:{sample_hash}",
        "consent_status": "public_dataset_allowed",
        "privacy_scope": "general",
        "channel_scope": "general",
        "review_status": review_status,
        "scenario_tags": tags,
        "turn_markers": _turn_markers(sample, entry, scenario),
        "user_likely_intent": _intent_text(scenario, entry),
        "bad_pattern": _bad_pattern_text(entry),
        "useful_adjustment": _adjustment_text(scenario, entry),
        "boundary": _boundary_text(entry),
        "confidence": _confidence(entry, sample),
        "language": _language(sample.text),
        "notes": [
            "public_dataset_sample",
            f"dataset:{entry.dataset_id}",
            f"role:{entry.role}",
            f"sample_hash:{sample_hash}",
            "pending_manual_review" if review_status == "pending" else f"review_status:{review_status}",
        ],
    }


def _scenario_label(sample: ReplaySample, entry: PublicDatasetEntry) -> str:
    if entry.role == "user_input_distribution":
        return "user_input_distribution"
    text = sample.text.lower()
    if sample.evidence_like or _contains_any(
        text,
        (
            "remember",
            "memory",
            "previous",
            "earlier",
            "context",
            "\u8bb0\u5f97",
            "\u8bb0\u5fc6",
            "\u4e0a\u6b21",
            "\u4e4b\u524d",
            "\u524d\u9762",
            "\u4e0a\u4e0b\u6587",
        ),
    ):
        return "memory_retrieval_reference"
    if _contains_any(
        text,
        (
            "code",
            "bug",
            "fix",
            "test",
            "implement",
            "continue",
            "progress",
            "status",
            "\u4ee3\u7801",
            "\u4fee\u590d",
            "\u7ee7\u7eed",
            "\u8fdb\u5ea6",
            "\u62a5\u9519",
            "\u5b9e\u73b0",
        ),
    ):
        return "technical_or_status_followup"
    if _contains_any(
        text,
        (
            "sad",
            "angry",
            "upset",
            "lonely",
            "hurt",
            "comfort",
            "\u96be\u8fc7",
            "\u96be\u53d7",
            "\u751f\u6c14",
            "\u59d4\u5c48",
            "\u70e6",
            "\u966a",
        ),
    ):
        return "emotion_scene_reference"
    if entry.role in {"chinese_short_reply_rhythm", "chinese_short_reply_rhythm_expansion"}:
        return "chinese_short_reply_rhythm"
    if "topic" in entry.role:
        return "topic_transition_reference"
    if entry.role == "daily_scene_reference":
        return "daily_scene_reference"
    return entry.role or "public_dialogue_reference"


def _scenario_tags(sample: ReplaySample, entry: PublicDatasetEntry, scenario: str) -> list[str]:
    tags = ["public_pattern", _tag(entry.role), _tag(scenario)]
    if scenario == "memory_retrieval_reference":
        tags.extend(["context_reference", "memory_review", "evidence_reference"])
    elif scenario == "technical_or_status_followup":
        tags.extend(["technical_work", "status_question", "implementation_followup"])
    elif scenario == "emotion_scene_reference":
        tags.extend(["emotion_pressure", "ordinary_emotion_scene"])
    elif scenario == "chinese_short_reply_rhythm":
        tags.extend(["zh_dialogue", "short_reply_rhythm", "casual_chat"])
    elif scenario == "daily_scene_reference":
        tags.extend(["daily_scene", "casual_chat"])
    elif scenario == "topic_transition_reference":
        tags.extend(["topic_shift", "casual_chat"])
    elif scenario == "user_input_distribution":
        tags.extend(["observation_only", "user_input_shape"])
    if sample.evidence_like:
        tags.append("evidence_like")
    return _dedupe(tag for tag in tags if tag)


def _turn_markers(sample: ReplaySample, entry: PublicDatasetEntry, scenario: str) -> list[str]:
    markers = ["public_dataset_sample", _tag(entry.dataset_id), _tag(scenario)]
    if sample.turn_index > 0:
        markers.append("multi_user_turn_record")
    return _dedupe(markers)


def _intent_text(scenario: str, entry: PublicDatasetEntry) -> str:
    if scenario == "memory_retrieval_reference":
        return "A public dialogue sample points to a user turn that likely depends on prior context or evidence."
    if scenario == "technical_or_status_followup":
        return "A public dialogue sample points to a user asking for concrete task continuation, status, or repair."
    if scenario == "emotion_scene_reference":
        return "A public dialogue sample points to a user expressing emotional pressure or asking for human-like presence."
    if scenario == "chinese_short_reply_rhythm":
        return "A public Chinese dialogue sample points to a short natural reply rhythm rather than a formal assistant paragraph."
    if scenario == "daily_scene_reference":
        return "A public dialogue sample points to an ordinary daily-life exchange or small social situation."
    if scenario == "topic_transition_reference":
        return "A public dialogue sample points to a human topic continuation or topic shift pattern."
    if scenario == "user_input_distribution":
        return "A public chat log sample points only to the shape of real user input, not to an answer style."
    return f"A public dataset sample from {entry.dataset_id} suggests a generic dialogue pattern."


def _bad_pattern_text(entry: PublicDatasetEntry) -> str:
    if entry.role == "user_input_distribution":
        return "Copying public assistant replies, learning platform-assistant style, or treating user-input distribution as XinYu voice."
    return "Copying dataset wording, treating the sample as XinYu history, or using a public pattern as owner relationship evidence."


def _adjustment_text(scenario: str, entry: PublicDatasetEntry) -> str:
    if scenario == "memory_retrieval_reference":
        return "Use this only to notice context-dependence; retrieve local evidence before answering, and say when evidence is missing."
    if scenario == "technical_or_status_followup":
        return "Use this only to prefer concrete progress, status, and next action over generic acknowledgement."
    if scenario == "emotion_scene_reference":
        return "Use this only to recognize emotional pressure; respond from XinYu's local state instead of copying comfort templates."
    if scenario == "chinese_short_reply_rhythm":
        return "Use this only as low-weight rhythm pressure for shorter, more natural Chinese turns when the current context allows it."
    if scenario == "daily_scene_reference":
        return "Use this only to widen daily-scene coverage; keep XinYu's own relationship and current context in charge."
    if scenario == "topic_transition_reference":
        return "Use this only to recognize topic continuation and topic shifts; do not import public facts as local memory."
    if scenario == "user_input_distribution":
        return "Use this only for input-shape calibration such as ambiguity, empty asks, and topic switching; do not activate as reply advice."
    return f"Use this only as a reviewed abstract {entry.role} hint."


def _boundary_text(entry: PublicDatasetEntry) -> str:
    return (
        "Public dataset pattern only. Advisory after manual review; current user message, owner-XinYu evidence, "
        "and local memory outrank it. Never write owner relationship memory or stable personality from this source."
    )


def _confidence(entry: PublicDatasetEntry, sample: ReplaySample) -> float:
    base = {"low": 0.58, "medium": 0.48, "high": 0.34}.get(entry.risk_level, 0.45)
    if entry.first_batch:
        base += 0.04
    if sample.evidence_like:
        base += 0.03
    if entry.default_review_status == "disabled":
        base = min(base, 0.38)
    return round(min(0.65, max(0.25, base)), 2)


def _language(text: str) -> str:
    has_zh = any("\u4e00" <= char <= "\u9fff" for char in text)
    has_ascii_word = bool(re.search(r"[A-Za-z]", text))
    if has_zh and has_ascii_word:
        return "mixed"
    if has_zh:
        return "zh"
    if has_ascii_word:
        return "en"
    return "mixed"


def _contains_any(text: str, needles: Sequence[str]) -> bool:
    return any(needle in text for needle in needles)


def _text_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()[:16]


def _tag(value: str) -> str:
    return _clean_token(value.replace("-", "_"), default="public")


def _clean_token(value: Any, *, default: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or default


def _dedupe(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = _tag(str(value))
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def public_case_builds_to_json(builds: Sequence[PublicDatasetCaseBuild]) -> list[dict[str, Any]]:
    return [
        {
            "sample_id": build.sample_id,
            "sample_hash": build.sample_hash,
            "scenario": build.scenario,
            "case": case_to_dict(build.case),
        }
        for build in builds
    ]


def public_case_import_report_to_text(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
