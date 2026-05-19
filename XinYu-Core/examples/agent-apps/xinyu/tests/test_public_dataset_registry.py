from __future__ import annotations

from pathlib import Path

import pytest

from xinyu_public_dataset_registry import (
    PublicDatasetRegistryError,
    load_public_dataset_registry,
    public_dataset_registry_path,
    recommended_first_batch,
    registry_policy_report,
    validate_public_dataset_registry_entry,
)
from xinyu_storage_paths import conversation_case_source_path, resolve_public_dataset_input_paths


ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_required_sources() -> None:
    entries = load_public_dataset_registry(ROOT)
    ids = {entry.dataset_id for entry in entries}

    assert {
        "owner_xinyu_seed_cases",
        "lufy",
        "chmap_data",
        "naturalconv",
        "dailydialog",
        "lccc_base",
        "lccc_large",
        "empatheticdialogues",
        "topical_chat",
        "wildchat",
        "lmsys_chat_1m",
    } <= ids


def test_registry_loader_prefers_cases_conversation_alias(tmp_path: Path) -> None:
    path = tmp_path / "cases" / "conversation" / "public_dataset_registry.json"
    path.parent.mkdir(parents=True)
    path.write_text(_registry_payload_text(), encoding="utf-8")

    entries = load_public_dataset_registry(tmp_path)

    assert public_dataset_registry_path(tmp_path) == path
    assert [entry.dataset_id for entry in entries] == ["owner_xinyu_seed_cases"]


def test_registry_loader_keeps_legacy_data_fallback(tmp_path: Path) -> None:
    path = tmp_path / "data" / "conversation_experience" / "public_dataset_registry.json"
    path.parent.mkdir(parents=True)
    path.write_text(_registry_payload_text(), encoding="utf-8")

    entries = load_public_dataset_registry(tmp_path)

    assert public_dataset_registry_path(tmp_path) == path
    assert [entry.dataset_id for entry in entries] == ["owner_xinyu_seed_cases"]


def test_case_source_prefers_workspace_cases_over_app_legacy_when_root_is_app(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core" / "examples" / "agent-apps" / "xinyu"
    (app / "config.yaml").parent.mkdir(parents=True)
    (app / "config.yaml").write_text("xinyu: test\n", encoding="utf-8")
    canonical = tmp_path / "cases" / "conversation" / "public_dataset_registry.json"
    legacy = app / "data" / "conversation_experience" / "public_dataset_registry.json"
    canonical.parent.mkdir(parents=True)
    legacy.parent.mkdir(parents=True)
    canonical.write_text(_registry_payload_text(), encoding="utf-8")
    legacy.write_text(_registry_payload_text(), encoding="utf-8")

    assert conversation_case_source_path(app, "public_dataset_registry.json") == canonical


def test_public_dataset_alias_prefers_workspace_library_over_app_legacy(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core" / "examples" / "agent-apps" / "xinyu"
    (app / "config.yaml").parent.mkdir(parents=True)
    (app / "config.yaml").write_text("xinyu: test\n", encoding="utf-8")
    canonical = tmp_path / "library" / "datasets" / "lufy-canonical.jsonl"
    legacy = app / "data" / "external" / "lufy-legacy.jsonl"
    canonical.parent.mkdir(parents=True)
    legacy.parent.mkdir(parents=True)
    canonical.write_text("{}\n", encoding="utf-8")
    legacy.write_text("{}\n", encoding="utf-8")

    assert resolve_public_dataset_input_paths(app, [], dataset_id="lufy") == (canonical,)


def test_public_dataset_alias_keeps_app_legacy_fallback_when_library_missing(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core" / "examples" / "agent-apps" / "xinyu"
    (app / "config.yaml").parent.mkdir(parents=True)
    (app / "config.yaml").write_text("xinyu: test\n", encoding="utf-8")
    legacy = app / "data" / "external" / "lufy-legacy.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("{}\n", encoding="utf-8")

    assert resolve_public_dataset_input_paths(app, [], dataset_id="lufy") == (legacy,)


def test_public_sources_cannot_shape_owner_relationship_or_stable_memory() -> None:
    entries = load_public_dataset_registry(ROOT)

    public_entries = [entry for entry in entries if entry.dataset_kind == "public_dataset"]
    assert public_entries
    assert all(not entry.owner_relationship_allowed for entry in public_entries)
    assert all(not entry.stable_memory_allowed for entry in public_entries)
    assert all(entry.raw_data_policy == "local_ignored_only" for entry in public_entries)
    assert all(entry.default_review_status != "approved" for entry in public_entries)


def test_recommended_first_batch_excludes_blocked_skipped_and_observation_only_sources() -> None:
    first_batch = recommended_first_batch(ROOT)
    ids = [entry.dataset_id for entry in first_batch]

    assert "owner_xinyu_seed_cases" in ids
    assert "lufy" in ids
    assert "chmap_data" in ids
    assert "lccc_base" in ids
    assert "dailydialog" in ids
    assert "empatheticdialogues" in ids
    assert "lccc_large" not in ids
    assert "naturalconv" not in ids
    assert "wildchat" not in ids
    assert "lmsys_chat_1m" not in ids


def test_registry_report_has_no_policy_violations() -> None:
    report = registry_policy_report(ROOT)

    assert report["total"] >= 11
    assert not report["public_sources_owner_relationship_allowed"]
    assert not report["public_sources_stable_memory_allowed"]
    assert "naturalconv" in report["blocked"]
    assert "lmsys_chat_1m" in report["blocked"]
    assert "lccc_large" in report["skipped"]


def test_public_entry_rejects_stable_memory_permission() -> None:
    data = _public_entry("bad_public_memory")
    data["stable_memory_allowed"] = True

    with pytest.raises(PublicDatasetRegistryError, match="stable memory"):
        validate_public_dataset_registry_entry(data)


def test_public_entry_rejects_owner_relationship_permission() -> None:
    data = _public_entry("bad_public_relationship")
    data["owner_relationship_allowed"] = True

    with pytest.raises(PublicDatasetRegistryError, match="owner relationship"):
        validate_public_dataset_registry_entry(data)


def test_lccc_large_cannot_be_first_batch() -> None:
    data = _public_entry("lccc_large")
    data["risk_level"] = "high"
    data["first_batch"] = True

    with pytest.raises(PublicDatasetRegistryError, match="high-risk|lccc_large"):
        validate_public_dataset_registry_entry(data)


def test_wildchat_role_is_observation_only() -> None:
    data = _public_entry("wildchat")
    data["role"] = "daily_scene_reference"
    data["risk_level"] = "high"
    data["first_batch"] = False
    data["default_review_status"] = "disabled"
    data["execution_status"] = "backlog_user_input_only"

    with pytest.raises(PublicDatasetRegistryError, match="user_input_distribution"):
        validate_public_dataset_registry_entry(data)


def _public_entry(dataset_id: str) -> dict[str, object]:
    return {
        "dataset_id": dataset_id,
        "priority": "P2",
        "order": 999,
        "dataset_kind": "public_dataset",
        "source_tier": "public_pattern",
        "role": "daily_scene_reference",
        "source_url": "https://example.invalid/dataset",
        "license_name": "example",
        "license_status": "example",
        "raw_data_policy": "local_ignored_only",
        "stable_memory_allowed": False,
        "owner_relationship_allowed": False,
        "default_review_status": "pending",
        "execution_status": "ready_for_sample",
        "risk_level": "medium",
        "first_batch": False,
        "case_card_only": True,
        "notes": ["test"],
    }


def _registry_payload_text() -> str:
    return """{
  "datasets": [
    {
      "dataset_id": "owner_xinyu_seed_cases",
      "priority": "P0",
      "order": 1,
      "dataset_kind": "owner_seed",
      "source_tier": "owner_xinyu",
      "role": "owner_reviewed_seed_cases",
      "source_url": "local",
      "license_name": "owner",
      "license_status": "owner_owned",
      "raw_data_policy": "committed_abstract_seed_cases_only",
      "stable_memory_allowed": true,
      "owner_relationship_allowed": true,
      "default_review_status": "approved",
      "execution_status": "owner_active",
      "risk_level": "low",
      "first_batch": true,
      "case_card_only": true,
      "notes": ["test"]
    }
  ]
}
"""
