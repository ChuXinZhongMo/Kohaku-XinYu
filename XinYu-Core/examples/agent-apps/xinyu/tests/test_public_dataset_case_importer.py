from __future__ import annotations

import json
from pathlib import Path

import pytest

from xinyu_conversation_experience_cases import case_to_dict, list_cases
from xinyu_public_dataset_case_importer import (
    PublicDatasetCaseImportError,
    build_public_dataset_case_cards,
    import_public_dataset_cases,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "contextual_public_replay_sample.jsonl"


def test_public_dataset_import_writes_pending_abstract_cases_without_raw_text(tmp_path: Path) -> None:
    report = import_public_dataset_cases(tmp_path, [FIXTURE], dataset_id="lufy", registry_root=ROOT, limit=3)

    assert report["dataset_id"] == "lufy"
    assert report["sample_count"] == 3
    assert report["generated"] == 3
    assert report["imported"] == 3
    assert not report["errors"]
    assert report["review_status_counts"] == {"pending": 3}
    assert "no_raw_user_text" in report["notes"]

    cases = list_cases(tmp_path, review_status="pending", limit=10)
    assert len(cases) == 3
    assert all(case.source_tier == "public_pattern" for case in cases)
    assert all(case.consent_status == "public_dataset_allowed" for case in cases)
    assert all(case.privacy_scope == "general" for case in cases)
    assert all(case.channel_scope == "general" for case in cases)
    assert all(case.source_ref.startswith("public_dataset:lufy:") for case in cases)

    serialized = json.dumps([case_to_dict(case) for case in cases], ensure_ascii=False)
    assert "继续实现这个回放模块和测试" not in serialized
    assert "我今天有点难受" not in serialized
    assert "assistant reply" not in serialized


def test_public_dataset_import_dry_run_does_not_write(tmp_path: Path) -> None:
    report = import_public_dataset_cases(
        tmp_path,
        [FIXTURE],
        dataset_id="dailydialog",
        registry_root=ROOT,
        limit=2,
        write=False,
    )

    assert report["generated"] == 2
    assert report["imported"] == 0
    assert "dry_run" in report["notes"]
    assert list_cases(tmp_path, review_status="pending", limit=10) == []


def test_public_dataset_import_resolves_library_dataset_alias(tmp_path: Path) -> None:
    dataset = tmp_path / "library" / "datasets" / "lufy-local.jsonl"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    report = import_public_dataset_cases(
        tmp_path,
        ["lufy"],
        dataset_id="lufy",
        registry_root=ROOT,
        limit=2,
        write=False,
    )

    assert report["generated"] == 2
    assert report["imported"] == 0
    assert not report["warnings"]


def test_public_dataset_import_resolves_dataset_id_without_explicit_path(tmp_path: Path) -> None:
    dataset = tmp_path / "library" / "datasets" / "lufy-auto.jsonl"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    report = import_public_dataset_cases(
        tmp_path,
        [],
        dataset_id="lufy",
        registry_root=ROOT,
        limit=2,
        write=False,
    )

    assert report["generated"] == 2
    assert report["imported"] == 0
    assert not report["warnings"]


def test_public_dataset_import_keeps_legacy_external_alias(tmp_path: Path) -> None:
    dataset = tmp_path / "data" / "external" / "lufy-legacy.jsonl"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    report = import_public_dataset_cases(
        tmp_path,
        ["lufy"],
        dataset_id="lufy",
        registry_root=ROOT,
        limit=1,
        write=False,
    )

    assert report["generated"] == 1
    assert report["imported"] == 0
    assert not report["warnings"]


def test_public_dataset_case_builder_derives_abstract_scenarios() -> None:
    builds = build_public_dataset_case_cards(ROOT, [FIXTURE], dataset_id="lccc_base", limit=5)
    scenarios = {build.scenario for build in builds}
    case_text = json.dumps([case_to_dict(build.case) for build in builds], ensure_ascii=False)

    assert "technical_or_status_followup" in scenarios
    assert "emotion_scene_reference" in scenarios
    assert "memory_retrieval_reference" in scenarios
    assert "source_tier" in case_text
    assert "继续实现这个回放模块和测试" not in case_text
    assert all(build.case.review_status == "pending" for build in builds)


def test_public_dataset_import_rejects_blocked_sources_by_default(tmp_path: Path) -> None:
    with pytest.raises(PublicDatasetCaseImportError, match="blocked"):
        import_public_dataset_cases(tmp_path, [FIXTURE], dataset_id="naturalconv", registry_root=ROOT, limit=1)


def test_public_dataset_import_rejects_skipped_sources_by_default(tmp_path: Path) -> None:
    with pytest.raises(PublicDatasetCaseImportError, match="skipped"):
        import_public_dataset_cases(tmp_path, [FIXTURE], dataset_id="lccc_large", registry_root=ROOT, limit=1)


def test_public_dataset_import_rejects_observation_only_without_explicit_flag(tmp_path: Path) -> None:
    with pytest.raises(PublicDatasetCaseImportError, match="observation-only"):
        import_public_dataset_cases(
            tmp_path,
            [FIXTURE],
            dataset_id="wildchat",
            registry_root=ROOT,
            limit=1,
            include_backlog=True,
        )


def test_public_dataset_import_can_build_disabled_observation_cards_when_explicit(tmp_path: Path) -> None:
    report = import_public_dataset_cases(
        tmp_path,
        [FIXTURE],
        dataset_id="wildchat",
        registry_root=ROOT,
        limit=1,
        include_backlog=True,
        allow_observation_only=True,
    )

    assert report["generated"] == 1
    assert report["imported"] == 1
    assert report["review_status_counts"] == {"disabled": 1}
    cases = list_cases(tmp_path, review_status="disabled", limit=10)
    assert len(cases) == 1
    assert "observation_only" in cases[0].scenario_tags
