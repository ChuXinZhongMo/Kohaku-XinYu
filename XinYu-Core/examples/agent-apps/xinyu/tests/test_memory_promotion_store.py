from __future__ import annotations

from pathlib import Path

import pytest

import xinyu_memory_promotion_store as store
from xinyu_memory_promotion_store import PROMOTION_DRY_RUN_REL
from xinyu_memory_promotion_store import promotion_dry_run_path
from xinyu_memory_promotion_store import promotion_path_exists
from xinyu_memory_promotion_store import promotion_target_path
from xinyu_memory_promotion_store import read_promotion_text
from xinyu_memory_promotion_store import safe_promotion_filename
from xinyu_memory_promotion_store import write_promotion_dry_run_text
from xinyu_memory_promotion_store import write_promotion_text


def test_memory_promotion_store_reads_missing_and_bom_text(tmp_path: Path) -> None:
    path = tmp_path / "memory/reflection/growth_log.md"

    assert promotion_path_exists(path) is False
    assert read_promotion_text(path) == ""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xef\xbb\xbf# Growth Log\n")

    assert promotion_path_exists(path) is True
    assert read_promotion_text(path) == "# Growth Log\n"


def test_memory_promotion_store_builds_safe_paths(tmp_path: Path) -> None:
    assert safe_promotion_filename(" ../bad:id?中文 ") == "bad-id"
    assert safe_promotion_filename("", default="fallback") == "fallback"

    target = promotion_target_path(tmp_path, Path("memory/reflection/growth_log.md"))
    preview = promotion_dry_run_path(tmp_path, " ../bad:id?中文 ")

    assert target == tmp_path / "memory/reflection/growth_log.md"
    assert preview == tmp_path / PROMOTION_DRY_RUN_REL / "bad-id.md"


def test_memory_promotion_store_writes_text_without_adding_newline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, str, bool]] = []

    def fake_atomic_write_text(path: Path, text: str, *, final_newline: bool = True) -> None:
        calls.append((Path(path), text, final_newline))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")

    monkeypatch.setattr(store, "atomic_write_text", fake_atomic_write_text)
    path = tmp_path / "memory/reflection/growth_log.md"

    write_promotion_text(path, "no-newline")

    assert calls == [(path, "no-newline", False)]
    assert path.read_text(encoding="utf-8") == "no-newline"


def test_memory_promotion_store_writes_dry_run_preview(tmp_path: Path) -> None:
    path = write_promotion_dry_run_text(tmp_path, "memcand/1", "# Preview\n")

    assert path == tmp_path / PROMOTION_DRY_RUN_REL / "memcand-1.md"
    assert path.read_text(encoding="utf-8") == "# Preview\n"
