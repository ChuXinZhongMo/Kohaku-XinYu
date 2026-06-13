from __future__ import annotations

import pytest

from xinyu_bridge_learning_ingest_request import (
    ATTACHMENT_DIRS_ENV,
    LEGACY_ATTACHMENT_DIRS_ENV,
    resolve_learning_ingest_path,
)
from xinyu_bridge_learning_ingest_scope_store import (
    read_learning_ingest_scope_env,
    resolve_learning_ingest_scope_root,
)


def test_learning_ingest_scope_store_reads_env_and_resolves_roots(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ATTACHMENT_DIRS_ENV, raising=False)

    assert read_learning_ingest_scope_env(ATTACHMENT_DIRS_ENV) == ""

    monkeypatch.setenv(ATTACHMENT_DIRS_ENV, str(tmp_path))

    assert read_learning_ingest_scope_env(ATTACHMENT_DIRS_ENV) == str(tmp_path)
    assert resolve_learning_ingest_scope_root(str(tmp_path)) == tmp_path.resolve()


def test_learning_ingest_path_accepts_new_and_legacy_attachment_env_roots(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_root = tmp_path / "new_attachments"
    legacy_root = tmp_path / "legacy_attachments"
    new_root.mkdir()
    legacy_root.mkdir()
    new_file = new_root / "new.txt"
    legacy_file = legacy_root / "legacy.txt"
    new_file.write_text("new\n", encoding="utf-8")
    legacy_file.write_text("legacy\n", encoding="utf-8")

    monkeypatch.setenv(ATTACHMENT_DIRS_ENV, str(new_root))
    monkeypatch.setenv(LEGACY_ATTACHMENT_DIRS_ENV, str(legacy_root))

    assert resolve_learning_ingest_path(tmp_path, str(new_file)) == new_file.resolve()
    assert resolve_learning_ingest_path(tmp_path, str(legacy_file)) == legacy_file.resolve()
