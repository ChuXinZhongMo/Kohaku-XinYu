from __future__ import annotations

from pathlib import Path

import pytest

import xinyu_visible_state_hygiene_store as store
from xinyu_visible_state_hygiene import sanitize_visible_state_files
from xinyu_visible_state_hygiene import visible_state_marker_hits
from xinyu_visible_state_hygiene_store import iter_visible_state_candidate_rels
from xinyu_visible_state_hygiene_store import read_visible_state_text
from xinyu_visible_state_hygiene_store import write_visible_state_text


def test_visible_state_hygiene_store_reads_missing_dirs_and_bom(tmp_path: Path) -> None:
    missing = tmp_path / "memory/context/missing.md"
    directory = tmp_path / "memory/context/dir.md"
    path = tmp_path / "memory/context/state.md"

    directory.mkdir(parents=True)
    path.write_bytes(b"\xef\xbb\xbf# State\n")

    assert read_visible_state_text(missing) == ""
    assert read_visible_state_text(directory) == ""
    assert read_visible_state_text(path) == "# State\n"


def test_visible_state_hygiene_store_writes_single_final_newline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, str, bool]] = []

    def fake_atomic_write_text(path: Path, text: str, *, final_newline: bool = True) -> None:
        calls.append((Path(path), text, final_newline))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text + ("\n" if final_newline else ""), encoding="utf-8")

    monkeypatch.setattr(store, "atomic_write_text", fake_atomic_write_text)
    path = tmp_path / "memory/context/state.md"

    write_visible_state_text(path, "body\n\n")

    assert calls == [(path, "body", True)]
    assert path.read_text(encoding="utf-8") == "body\n"


def test_visible_state_hygiene_store_enumerates_unique_glob_candidates(tmp_path: Path) -> None:
    file_path = tmp_path / "runtime/dialogue_working_memory/session.jsonl"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("{}\n", encoding="utf-8")
    (file_path.parent / "nested.jsonl").mkdir()

    candidates = iter_visible_state_candidate_rels(
        tmp_path,
        relative_files=("runtime/dialogue_working_memory/session.jsonl", "memory/context/state.md"),
        relative_globs=("runtime/dialogue_working_memory/*.jsonl",),
    )

    assert candidates == (
        "memory/context/state.md",
        "runtime/dialogue_working_memory/session.jsonl",
    )


def test_visible_state_hygiene_uses_store_for_dry_run_and_write(tmp_path: Path) -> None:
    rel = "memory/context/continuity_index.md"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    original = "- note: [Tool batch completed] ## read_9601cfa6 - OK 1-> done\n"
    path.write_text(original, encoding="utf-8")

    dry = sanitize_visible_state_files(tmp_path, relative_files=(rel,), relative_globs=(), dry_run=True)

    assert dry["changed"] == [rel]
    assert path.read_text(encoding="utf-8") == original
    assert visible_state_marker_hits(tmp_path, relative_files=(rel,), relative_globs=())

    changed = sanitize_visible_state_files(tmp_path, relative_files=(rel,), relative_globs=())

    assert changed["changed"] == [rel]
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert not visible_state_marker_hits(tmp_path, relative_files=(rel,), relative_globs=())
