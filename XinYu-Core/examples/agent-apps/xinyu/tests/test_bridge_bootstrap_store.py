from __future__ import annotations

import os

import pytest

from xinyu_bridge_bootstrap import load_local_env
from xinyu_bridge_bootstrap_store import (
    bootstrap_env_file_exists,
    bootstrap_env_has_key,
    read_bootstrap_env_file_lines,
    write_bootstrap_env,
)


def test_bridge_bootstrap_store_reads_env_file_and_environment(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "xinyu.local.env"
    monkeypatch.delenv("XINYU_BOOTSTRAP_TEST", raising=False)

    assert bootstrap_env_file_exists(path) is False
    assert bootstrap_env_has_key("XINYU_BOOTSTRAP_TEST") is False

    path.write_text("XINYU_BOOTSTRAP_TEST=file\n", encoding="utf-8")

    assert bootstrap_env_file_exists(path) is True
    assert read_bootstrap_env_file_lines(path) == ["XINYU_BOOTSTRAP_TEST=file"]

    write_bootstrap_env("XINYU_BOOTSTRAP_TEST", "store")

    assert os.environ["XINYU_BOOTSTRAP_TEST"] == "store"
    assert bootstrap_env_has_key("XINYU_BOOTSTRAP_TEST") is True


def test_load_local_env_preserves_existing_env_and_parses_values(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_EXISTING", "keep")
    monkeypatch.delenv("XINYU_NEW_DOUBLE", raising=False)
    monkeypatch.delenv("XINYU_NEW_SINGLE", raising=False)
    monkeypatch.delenv("XINYU_SPACED", raising=False)

    (tmp_path / "xinyu.local.env").write_text(
        "\n".join(
            [
                "# comment",
                "XINYU_EXISTING=replace",
                'XINYU_NEW_DOUBLE=\"double\"',
                "XINYU_NEW_SINGLE='single'",
                " XINYU_SPACED = value ",
                "ignored_without_separator",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    load_local_env(tmp_path)

    assert os.environ["XINYU_EXISTING"] == "keep"
    assert os.environ["XINYU_NEW_DOUBLE"] == "double"
    assert os.environ["XINYU_NEW_SINGLE"] == "single"
    assert os.environ["XINYU_SPACED"] == "value"
