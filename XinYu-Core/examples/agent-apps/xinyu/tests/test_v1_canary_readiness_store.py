from __future__ import annotations

import json
from pathlib import Path

from xinyu_v1_canary_readiness import OWNER_CONFIG_REL as MODULE_OWNER_CONFIG_REL
from xinyu_v1_canary_readiness import STATE_REL as MODULE_STATE_REL
from xinyu_v1_canary_readiness import TRACE_REL as MODULE_TRACE_REL
from xinyu_v1_canary_readiness_store import OWNER_CONFIG_REL
from xinyu_v1_canary_readiness_store import STATE_REL
from xinyu_v1_canary_readiness_store import TRACE_REL
from xinyu_v1_canary_readiness_store import append_v1_canary_trace_event
from xinyu_v1_canary_readiness_store import read_v1_canary_text
from xinyu_v1_canary_readiness_store import read_v1_owner_config
from xinyu_v1_canary_readiness_store import read_v1_shadow_observation_tail
from xinyu_v1_canary_readiness_store import v1_canary_state_path
from xinyu_v1_canary_readiness_store import v1_canary_trace_path
from xinyu_v1_canary_readiness_store import v1_owner_config_path
from xinyu_v1_canary_readiness_store import write_v1_canary_text


def test_v1_canary_store_exports_legacy_paths() -> None:
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert OWNER_CONFIG_REL == MODULE_OWNER_CONFIG_REL
    assert STATE_REL == Path("memory/context/v1_canary_readiness_state.md")
    assert TRACE_REL == Path("runtime/v1_shadow_trace.jsonl")
    assert OWNER_CONFIG_REL == Path("xinyu_qq_gateway.config.json")


def test_v1_canary_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert v1_canary_state_path(tmp_path) == root / STATE_REL
    assert v1_canary_trace_path(tmp_path) == root / TRACE_REL
    assert v1_owner_config_path(tmp_path) == root / OWNER_CONFIG_REL


def test_v1_canary_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / STATE_REL

    assert read_v1_canary_text(path) == ""

    write_v1_canary_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_v1_canary_text(path) == "state\n"


def test_v1_canary_store_appends_trace_with_sorted_keys(tmp_path: Path) -> None:
    path = tmp_path / TRACE_REL

    append_v1_canary_trace_event(path, {"route": "fast_path", "event_kind": "v1_shadow_observation"})

    line = path.read_text(encoding="utf-8").splitlines()[0]
    assert line == '{"event_kind": "v1_shadow_observation", "route": "fast_path"}'
    assert json.loads(line) == {"event_kind": "v1_shadow_observation", "route": "fast_path"}


def test_v1_canary_store_reads_only_shadow_observation_tail(tmp_path: Path) -> None:
    path = tmp_path / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                '{"event_kind":"v1_shadow_observation","trace_id":"tr-1"}',
                '{"event_kind":"v1_canary_owner_proposal_queued","trace_id":"proposal"}',
                "not-json",
                '{"event_kind":"v1_shadow_observation","trace_id":"tr-2"}',
                '{"event_kind":"v1_shadow_observation","trace_id":"tr-3"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows, total = read_v1_shadow_observation_tail(path, limit=2)

    assert total == 3
    assert [row["trace_id"] for row in rows] == ["tr-2", "tr-3"]


def test_v1_canary_store_reads_owner_config_status(tmp_path: Path) -> None:
    path = tmp_path / OWNER_CONFIG_REL

    assert read_v1_owner_config(path) == ("not_found", None)

    path.write_text("{bad", encoding="utf-8")
    assert read_v1_owner_config(path) == ("unreadable", None)

    path.write_text('{"owner_user_ids":["123"]}', encoding="utf-8")
    assert read_v1_owner_config(path) == ("ok", {"owner_user_ids": ["123"]})
