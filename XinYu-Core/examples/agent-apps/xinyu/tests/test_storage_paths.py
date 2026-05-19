from __future__ import annotations

from pathlib import Path

import pytest

from xinyu_storage_paths import (
    cases_conversation_dir,
    public_dataset_source_dirs,
    storage_boundary_table,
    knowledge_dir,
    knowledge_file_path,
    knowledge_ref,
)


def test_storage_boundary_table_declares_canonical_and_legacy_paths() -> None:
    rows = {name: (canonical, legacy, policy) for name, canonical, legacy, policy in storage_boundary_table()}

    assert rows["cases.conversation"] == (
        "cases/conversation",
        ("data/conversation_experience",),
        "canonical_preferred_legacy_fallback",
    )
    assert rows["library.datasets"] == (
        "library/datasets",
        ("data/external",),
        "canonical_preferred_legacy_fallback",
    )
    assert rows["memory.knowledge"] == (
        "memory/knowledge",
        (),
        "mixed_knowledge_pending_library_split",
    )


def test_cases_conversation_dir_prefers_canonical_and_keeps_legacy_fallback(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core" / "examples" / "agent-apps" / "xinyu"
    (app / "config.yaml").parent.mkdir(parents=True)
    (app / "config.yaml").write_text("xinyu: test\n", encoding="utf-8")
    legacy = app / "data" / "conversation_experience"
    legacy.mkdir(parents=True)

    assert cases_conversation_dir(app) == legacy

    canonical = tmp_path / "cases" / "conversation"
    canonical.mkdir(parents=True)

    assert cases_conversation_dir(app) == canonical


def test_public_dataset_source_dirs_keeps_canonical_before_legacy(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core" / "examples" / "agent-apps" / "xinyu"
    (app / "config.yaml").parent.mkdir(parents=True)
    (app / "config.yaml").write_text("xinyu: test\n", encoding="utf-8")

    dirs = public_dataset_source_dirs(app)

    assert dirs[:3] == (
        app / "library" / "datasets",
        tmp_path / "library" / "datasets",
        app / "data" / "external",
    )


def test_knowledge_file_path_uses_app_memory_knowledge_for_plain_roots(tmp_path: Path) -> None:
    assert knowledge_dir(tmp_path) == tmp_path / "memory" / "knowledge"
    assert knowledge_file_path(tmp_path, "general.md") == tmp_path / "memory" / "knowledge" / "general.md"
    assert knowledge_ref("general.md") == "memory/knowledge/general.md"


def test_knowledge_file_path_resolves_workspace_root_to_app_memory_knowledge(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core" / "examples" / "agent-apps" / "xinyu"
    app.mkdir(parents=True)
    (app / "config.yaml").write_text("xinyu: test\n", encoding="utf-8")

    assert knowledge_file_path(tmp_path, "source_notes.md") == app / "memory" / "knowledge" / "source_notes.md"


def test_knowledge_file_path_rejects_nested_names(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected bare filename"):
        knowledge_file_path(tmp_path, "../general.md")
