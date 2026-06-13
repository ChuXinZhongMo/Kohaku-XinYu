from __future__ import annotations

import os
from pathlib import Path

import pytest

from xinyu_autonomy_journal_store import autonomy_journal_env_has_key
from xinyu_autonomy_journal_store import read_autonomy_journal_env_lines
from xinyu_autonomy_journal_store import read_autonomy_journal_text
from xinyu_autonomy_journal_store import write_autonomy_journal_env
from xinyu_autonomy_journal_store import write_autonomy_journal_thought


def test_autonomy_journal_store_reads_text_and_missing(tmp_path: Path) -> None:
    path = tmp_path / "memory/self/personality_profile.md"

    assert read_autonomy_journal_text(path) == ""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("profile\n", encoding="utf-8-sig")

    assert read_autonomy_journal_text(path) == "profile\n"


def test_autonomy_journal_store_reads_env_lines(tmp_path: Path) -> None:
    path = tmp_path / "xinyu.local.env"

    assert read_autonomy_journal_env_lines(path) == []

    path.write_text("A=1\n# ignored later by caller\n", encoding="utf-8-sig")

    assert read_autonomy_journal_env_lines(path) == ["A=1", "# ignored later by caller"]


def test_autonomy_journal_store_reads_and_writes_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XINYU_AUTONOMY_JOURNAL_TEST", raising=False)

    assert autonomy_journal_env_has_key("XINYU_AUTONOMY_JOURNAL_TEST") is False

    write_autonomy_journal_env("XINYU_AUTONOMY_JOURNAL_TEST", "1")

    assert os.environ["XINYU_AUTONOMY_JOURNAL_TEST"] == "1"
    assert autonomy_journal_env_has_key("XINYU_AUTONOMY_JOURNAL_TEST") is True


def test_autonomy_journal_store_writes_thought_file(tmp_path: Path) -> None:
    path = tmp_path / "thoughts/2026-06-09/12-00-00-xinyu-thoughts.md"

    write_autonomy_journal_thought(path, "hello\n")

    assert path.read_text(encoding="utf-8-sig") == "hello\n"
