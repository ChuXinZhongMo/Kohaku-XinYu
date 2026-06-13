from __future__ import annotations

from types import SimpleNamespace

import pytest

from xinyu_bridge_promise_candidate import owner_private_user_id
from xinyu_bridge_promise_owner_identity_store import (
    read_promise_owner_config_text,
    read_promise_owner_ids_env,
)
from xinyu_bridge_values import as_str_set


def test_promise_owner_identity_store_reads_env_and_config(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "xinyu_qq_gateway.config.json"
    monkeypatch.delenv("XINYU_OWNER_USER_IDS", raising=False)

    assert read_promise_owner_ids_env() == ""
    assert read_promise_owner_config_text(config_path) == ""

    monkeypatch.setenv("XINYU_OWNER_USER_IDS", "owner-b,owner-a")
    config_path.write_text('{"owner_user_ids": ["owner-c"]}', encoding="utf-8")

    assert read_promise_owner_ids_env() == "owner-b,owner-a"
    assert read_promise_owner_config_text(config_path) == '{"owner_user_ids": ["owner-c"]}'


def test_owner_private_user_id_prefers_runtime_then_env_then_config(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = SimpleNamespace(v1_owner_user_ids={"owner-runtime"}, xinyu_dir=tmp_path)
    monkeypatch.setenv("XINYU_OWNER_USER_IDS", "owner-env")
    (tmp_path / "xinyu_qq_gateway.config.json").write_text(
        '{"owner_user_ids": ["owner-config"]}',
        encoding="utf-8",
    )

    assert owner_private_user_id(runtime, as_str_set_func=as_str_set) == "owner-runtime"

    runtime.v1_owner_user_ids = set()
    assert owner_private_user_id(runtime, as_str_set_func=as_str_set) == "owner-env"

    monkeypatch.delenv("XINYU_OWNER_USER_IDS", raising=False)
    assert owner_private_user_id(runtime, as_str_set_func=as_str_set) == "owner-config"

    (tmp_path / "xinyu_qq_gateway.config.json").write_text("{bad", encoding="utf-8")
    assert owner_private_user_id(runtime, as_str_set_func=as_str_set) == ""
