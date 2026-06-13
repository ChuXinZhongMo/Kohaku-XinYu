from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_storage_paths import public_dataset_registry_path as resolve_public_dataset_registry_path


ALLOWED_PRIORITIES = {"P0", "P1", "P1.5", "P2", "P3"}
ALLOWED_DATASET_KINDS = {"owner_seed", "owner_eval_seed", "public_dataset"}
ALLOWED_SOURCE_TIERS = {"owner_xinyu", "public_pattern"}
ALLOWED_REVIEW_STATUSES = {"approved", "pending", "disabled"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
READY_EXECUTION_STATUSES = {
    "owner_active",
    "ready_for_sample",
    "ready_local_research_only",
}
BLOCKED_EXECUTION_STATUSES = {
    "blocked_license_review",
    "blocked_license_acceptance",
}
SKIPPED_EXECUTION_STATUSES = {
    "skipped_first_batch",
}
BACKLOG_EXECUTION_STATUSES = {
    "backlog",
    "backlog_user_input_only",
}
ALLOWED_EXECUTION_STATUSES = (
    READY_EXECUTION_STATUSES
    | BLOCKED_EXECUTION_STATUSES
    | SKIPPED_EXECUTION_STATUSES
    | BACKLOG_EXECUTION_STATUSES
)


class PublicDatasetRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class PublicDatasetEntry:
    dataset_id: str
    priority: str
    order: int
    dataset_kind: str
    source_tier: str
    role: str
    source_url: str
    license_name: str
    license_status: str
    raw_data_policy: str
    stable_memory_allowed: bool
    owner_relationship_allowed: bool
    default_review_status: str
    execution_status: str
    risk_level: str
    first_batch: bool
    case_card_only: bool
    notes: tuple[str, ...]

    @property
    def is_public_dataset(self) -> bool:
        return self.dataset_kind == "public_dataset"

    @property
    def is_ready(self) -> bool:
        return self.execution_status in READY_EXECUTION_STATUSES


def public_dataset_registry_path(root: Path) -> Path:
    return resolve_public_dataset_registry_path(root)


def load_public_dataset_registry(root: Path) -> tuple[PublicDatasetEntry, ...]:
    path = public_dataset_registry_path(Path(root))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PublicDatasetRegistryError(f"missing registry:{path}") from exc
    except json.JSONDecodeError as exc:
        raise PublicDatasetRegistryError(f"invalid registry json:{exc}") from exc

    datasets = payload.get("datasets") if isinstance(payload, dict) else None
    if not isinstance(datasets, list):
        raise PublicDatasetRegistryError("registry datasets must be a list")

    entries = tuple(validate_public_dataset_registry_entry(item) for item in datasets)
    _validate_registry_set(entries)
    return entries


def validate_public_dataset_registry_entry(data: dict[str, Any]) -> PublicDatasetEntry:
    if not isinstance(data, dict):
        raise PublicDatasetRegistryError("registry entry must be an object")

    dataset_id = _required_str(data, "dataset_id")
    priority = _required_str(data, "priority")
    if priority not in ALLOWED_PRIORITIES:
        raise PublicDatasetRegistryError(f"{dataset_id}: invalid priority:{priority}")

    dataset_kind = _required_str(data, "dataset_kind")
    if dataset_kind not in ALLOWED_DATASET_KINDS:
        raise PublicDatasetRegistryError(f"{dataset_id}: invalid dataset_kind:{dataset_kind}")

    source_tier = _required_str(data, "source_tier")
    if source_tier not in ALLOWED_SOURCE_TIERS:
        raise PublicDatasetRegistryError(f"{dataset_id}: invalid source_tier:{source_tier}")

    default_review_status = _required_str(data, "default_review_status")
    if default_review_status not in ALLOWED_REVIEW_STATUSES:
        raise PublicDatasetRegistryError(f"{dataset_id}: invalid default_review_status:{default_review_status}")

    execution_status = _required_str(data, "execution_status")
    if execution_status not in ALLOWED_EXECUTION_STATUSES:
        raise PublicDatasetRegistryError(f"{dataset_id}: invalid execution_status:{execution_status}")

    risk_level = _required_str(data, "risk_level")
    if risk_level not in ALLOWED_RISK_LEVELS:
        raise PublicDatasetRegistryError(f"{dataset_id}: invalid risk_level:{risk_level}")

    entry = PublicDatasetEntry(
        dataset_id=dataset_id,
        priority=priority,
        order=_required_int(data, "order"),
        dataset_kind=dataset_kind,
        source_tier=source_tier,
        role=_required_str(data, "role"),
        source_url=_required_str(data, "source_url"),
        license_name=_required_str(data, "license_name"),
        license_status=_required_str(data, "license_status"),
        raw_data_policy=_required_str(data, "raw_data_policy"),
        stable_memory_allowed=_required_bool(data, "stable_memory_allowed"),
        owner_relationship_allowed=_required_bool(data, "owner_relationship_allowed"),
        default_review_status=default_review_status,
        execution_status=execution_status,
        risk_level=risk_level,
        first_batch=_required_bool(data, "first_batch"),
        case_card_only=_required_bool(data, "case_card_only"),
        notes=tuple(str(item).strip() for item in data.get("notes", []) if str(item).strip()),
    )
    _validate_entry_policy(entry)
    return entry


def recommended_first_batch(root: Path, *, include_backlog: bool = False) -> tuple[PublicDatasetEntry, ...]:
    entries = load_public_dataset_registry(root)
    allowed_statuses = set(READY_EXECUTION_STATUSES)
    if include_backlog:
        allowed_statuses |= BACKLOG_EXECUTION_STATUSES
    return tuple(
        sorted(
            (
                entry
                for entry in entries
                if entry.first_batch
                and entry.execution_status in allowed_statuses
                and entry.risk_level != "high"
            ),
            key=lambda entry: (entry.order, entry.dataset_id),
        )
    )


def registry_policy_report(root: Path) -> dict[str, Any]:
    entries = load_public_dataset_registry(root)
    first_batch = recommended_first_batch(root)
    blocked = tuple(entry for entry in entries if entry.execution_status in BLOCKED_EXECUTION_STATUSES)
    skipped = tuple(entry for entry in entries if entry.execution_status in SKIPPED_EXECUTION_STATUSES)
    return {
        "registry_path": str(public_dataset_registry_path(Path(root))),
        "total": len(entries),
        "first_batch": [entry.dataset_id for entry in first_batch],
        "blocked": [entry.dataset_id for entry in blocked],
        "skipped": [entry.dataset_id for entry in skipped],
        "public_sources_owner_relationship_allowed": [
            entry.dataset_id
            for entry in entries
            if entry.is_public_dataset and entry.owner_relationship_allowed
        ],
        "public_sources_stable_memory_allowed": [
            entry.dataset_id
            for entry in entries
            if entry.is_public_dataset and entry.stable_memory_allowed
        ],
    }


def _validate_registry_set(entries: tuple[PublicDatasetEntry, ...]) -> None:
    seen: set[str] = set()
    for entry in entries:
        if entry.dataset_id in seen:
            raise PublicDatasetRegistryError(f"duplicate dataset_id:{entry.dataset_id}")
        seen.add(entry.dataset_id)

    if "owner_xinyu_seed_cases" not in seen:
        raise PublicDatasetRegistryError("missing required owner_xinyu_seed_cases")


def _validate_entry_policy(entry: PublicDatasetEntry) -> None:
    if entry.dataset_kind == "owner_seed":
        if entry.dataset_id != "owner_xinyu_seed_cases":
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: only owner_xinyu_seed_cases may be owner_seed")
        if entry.priority != "P0" or entry.source_tier != "owner_xinyu":
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: owner seed must be P0 owner_xinyu")
        if entry.raw_data_policy != "committed_abstract_seed_cases_only":
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: invalid owner raw_data_policy")
        return

    if entry.dataset_kind == "owner_eval_seed":
        if entry.priority != "P0" or entry.source_tier != "owner_xinyu":
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: owner eval seed must be P0 owner_xinyu")
        if entry.raw_data_policy != "committed_abstract_eval_cases_only":
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: invalid owner eval raw_data_policy")
        if entry.stable_memory_allowed:
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: owner eval seed cannot allow stable memory writes")
        if entry.license_status != "owner_owned":
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: owner eval seed must be owner_owned")
        if entry.default_review_status != "approved" or entry.execution_status != "owner_active":
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: owner eval seed must be approved owner_active")
        if not entry.case_card_only:
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: owner eval seed must be case_card_only")
        return

    if entry.priority == "P0":
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: public datasets cannot be P0")
    if entry.source_tier != "public_pattern":
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: public datasets must use public_pattern tier")
    if entry.raw_data_policy != "local_ignored_only":
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: public raw data must be local_ignored_only")
    if entry.stable_memory_allowed:
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: public dataset cannot allow stable memory writes")
    if entry.owner_relationship_allowed:
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: public dataset cannot shape owner relationship")
    if entry.default_review_status == "approved":
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: public dataset cases cannot default to approved")
    if not entry.case_card_only:
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: public dataset must be case_card_only")
    if entry.first_batch and entry.execution_status in BLOCKED_EXECUTION_STATUSES | SKIPPED_EXECUTION_STATUSES:
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: blocked/skipped dataset cannot be first_batch")
    if entry.first_batch and entry.risk_level == "high":
        raise PublicDatasetRegistryError(f"{entry.dataset_id}: high-risk dataset cannot be first_batch")

    if entry.dataset_id == "lccc_large":
        if entry.risk_level != "high":
            raise PublicDatasetRegistryError("lccc_large must remain high risk")
        if entry.first_batch:
            raise PublicDatasetRegistryError("lccc_large cannot be first_batch")
        if entry.default_review_status == "approved":
            raise PublicDatasetRegistryError("lccc_large cannot default to approved")

    if entry.dataset_id in {"wildchat", "lmsys_chat_1m"}:
        if entry.role != "user_input_distribution":
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: role must be user_input_distribution")
        if entry.first_batch:
            raise PublicDatasetRegistryError(f"{entry.dataset_id}: observation-only source cannot be first_batch")


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    text = str(value).strip() if value is not None else ""
    if not text:
        raise PublicDatasetRegistryError(f"missing {key}")
    return text


def _required_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise PublicDatasetRegistryError(f"{_entry_name(data)}: {key} must be boolean")
    return value


def _required_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PublicDatasetRegistryError(f"{_entry_name(data)}: {key} must be integer")
    return value


def _entry_name(data: dict[str, Any]) -> str:
    return str(data.get("dataset_id") or "<entry>").strip()
