from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import xinyu_dialogue_working_memory_store as store
from xinyu_dialogue_working_memory import load_dialogue_tail
from xinyu_dialogue_working_memory import remove_matching_assistant_reply
from xinyu_dialogue_working_memory import save_dialogue_tail
from xinyu_dialogue_working_memory_store import clear_dialogue_working_memory_rows
from xinyu_dialogue_working_memory_store import dialogue_working_memory_path_exists
from xinyu_dialogue_working_memory_store import dialogue_working_memory_session_hash
from xinyu_dialogue_working_memory_store import dialogue_working_memory_session_path
from xinyu_dialogue_working_memory_store import read_dialogue_working_memory_raw
from xinyu_dialogue_working_memory_store import read_dialogue_working_memory_rows
from xinyu_dialogue_working_memory_store import write_dialogue_working_memory_rows


def test_dialogue_working_memory_store_builds_stable_session_path(tmp_path: Path) -> None:
    expected_hash = hashlib.sha256("qq:private:owner".encode("utf-8")).hexdigest()[:24]

    assert dialogue_working_memory_session_hash("qq:private:owner") == expected_hash
    assert dialogue_working_memory_session_hash("") == hashlib.sha256("default".encode("utf-8")).hexdigest()[:24]
    assert dialogue_working_memory_session_path(tmp_path, "qq:private:owner") == (
        tmp_path / "runtime/dialogue_working_memory" / f"{expected_hash}.jsonl"
    )


def test_dialogue_working_memory_store_reads_rows_and_ignores_bad_lines(tmp_path: Path) -> None:
    path = tmp_path / "runtime/dialogue_working_memory/session.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b'\xef\xbb\xbf{"role":"user","content":"hello"}\nnot-json\n[]\n{"role":"assistant","content":"hi"}\n'
    )

    raw, error = read_dialogue_working_memory_raw(path)

    assert error == ""
    assert "hello" in raw
    assert read_dialogue_working_memory_rows(path) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert read_dialogue_working_memory_rows(tmp_path / "missing.jsonl") == []
    assert dialogue_working_memory_path_exists(path) is True


def test_dialogue_working_memory_store_writes_and_clears_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, str, bool]] = []

    def fake_atomic_write_text(path: Path, text: str, *, final_newline: bool = True) -> None:
        calls.append((Path(path), text, final_newline))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text + ("\n" if final_newline else ""), encoding="utf-8")

    monkeypatch.setattr(store, "atomic_write_text", fake_atomic_write_text)
    path = tmp_path / "runtime/dialogue_working_memory/session.jsonl"

    write_dialogue_working_memory_rows(path, [{"role": "assistant", "content": "你好"}])
    clear_dialogue_working_memory_rows(path)

    assert calls == [
        (path, '{"content": "你好", "role": "assistant"}\n', False),
        (path, "", False),
    ]
    assert path.read_text(encoding="utf-8") == ""


def test_dialogue_working_memory_uses_store_backed_save_load_and_remove(tmp_path: Path) -> None:
    tail = [
        {"role": "user", "content": "hello", "recorded_at": "2026-01-01T00:00:00+08:00"},
        {"role": "assistant", "content": "visible reply", "recorded_at": "2026-01-01T00:00:01+08:00"},
    ]

    assert save_dialogue_tail(tmp_path, "qq:private:owner", tail, max_entries=32)
    assert load_dialogue_tail(tmp_path, "qq:private:owner", include_timestamps=True) == tail

    removed = remove_matching_assistant_reply(tmp_path, "qq:private:owner", reply="visible reply")

    assert removed["removed"] is True
    assert load_dialogue_tail(tmp_path, "qq:private:owner") == [{"role": "user", "content": "hello"}]
    path = dialogue_working_memory_session_path(tmp_path, "qq:private:owner")
    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [
        {"content": "hello", "recorded_at": "2026-01-01T00:00:00+08:00", "role": "user"}
    ]
