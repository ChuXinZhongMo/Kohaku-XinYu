from __future__ import annotations

import json
from pathlib import Path

from xinyu_action_experience_digest_store import append_action_experience_digest_jsonl
from xinyu_action_experience_digest_store import read_action_experience_digest_json
from xinyu_action_experience_digest_store import read_action_experience_digest_jsonl
from xinyu_action_experience_digest_store import read_action_experience_digest_text
from xinyu_action_experience_digest_store import write_action_experience_digest_json
from xinyu_action_experience_digest_store import write_action_experience_digest_text


def test_action_experience_digest_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/dreams/dream_seeds.md"

    assert read_action_experience_digest_text(path) == ""

    write_action_experience_digest_text(path, "# Dream Seeds\n")

    assert path.read_text(encoding="utf-8") == "# Dream Seeds\n"
    assert read_action_experience_digest_text(path) == "# Dream Seeds\n"


def test_action_experience_digest_store_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "runtime/life_kernel/action_experience_digest_state.json"

    assert read_action_experience_digest_json(path, {"version": 1}) == {"version": 1}

    write_action_experience_digest_json(path, {"version": 1, "digested_ids": ["exp-1"]})

    assert read_action_experience_digest_json(path) == {"version": 1, "digested_ids": ["exp-1"]}


def test_action_experience_digest_store_jsonl_read_skips_invalid_rows(tmp_path: Path) -> None:
    path = tmp_path / "runtime/life_kernel/action_experience_residue.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"experience_id":"exp-1"}\nnot-json\n["not", "dict"]\n', encoding="utf-8")

    assert read_action_experience_digest_jsonl(path) == [{"experience_id": "exp-1"}]


def test_action_experience_digest_store_appends_jsonl_without_sorting_keys(tmp_path: Path) -> None:
    path = tmp_path / "runtime/life_kernel/action_experience_digest_trace.jsonl"

    append_action_experience_digest_jsonl(path, {"event_id": "digest-1", "seed_id": "seed-1"})

    line = path.read_text(encoding="utf-8").splitlines()[0]
    assert line == '{"event_id":"digest-1","seed_id":"seed-1"}'
    assert json.loads(line) == {"event_id": "digest-1", "seed_id": "seed-1"}
