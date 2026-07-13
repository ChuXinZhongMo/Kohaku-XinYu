from __future__ import annotations

import os

import pytest

from xinyu_bridge_stores import (
    read_voice_flag_env,
    read_voice_flags_env_file_lines,
    write_voice_flag_env,
    write_voice_flags_env_file_lines,
)


def test_voice_flags_store_reads_and_writes_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XINYU_TEST_VOICE_FLAG", raising=False)

    assert read_voice_flag_env("XINYU_TEST_VOICE_FLAG") == ""

    write_voice_flag_env("XINYU_TEST_VOICE_FLAG", "1")

    assert os.environ["XINYU_TEST_VOICE_FLAG"] == "1"
    assert read_voice_flag_env("XINYU_TEST_VOICE_FLAG") == "1"


def test_voice_flags_store_reads_and_writes_env_file_lines(tmp_path) -> None:
    path = tmp_path / "nested/xinyu.local.env"

    assert read_voice_flags_env_file_lines(path) == []

    write_voice_flags_env_file_lines(path, ["# config", "XINYU_FLAG=1"])

    assert read_voice_flags_env_file_lines(path) == ["# config", "XINYU_FLAG=1"]
    assert path.read_text(encoding="utf-8") == "# config\nXINYU_FLAG=1\n"
