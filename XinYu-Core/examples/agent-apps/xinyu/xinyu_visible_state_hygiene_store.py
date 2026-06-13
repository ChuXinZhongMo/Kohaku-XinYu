from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text
from state_service import read_text_safe


def iter_visible_state_candidate_rels(
    root: Path,
    *,
    relative_files: tuple[str, ...],
    relative_globs: tuple[str, ...],
) -> tuple[str, ...]:
    root = Path(root)
    candidates: list[str] = list(relative_files)
    for pattern in relative_globs:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            try:
                candidates.append(path.relative_to(root).as_posix())
            except ValueError:
                continue
    return tuple(sorted(dict.fromkeys(candidates)))


def read_visible_state_text(path: Path) -> str:
    path = Path(path)
    if not path.exists() or not path.is_file():
        return ""
    return read_text_safe(path, default="")


def write_visible_state_text(path: Path, text: str) -> None:
    atomic_write_text(Path(path), text.rstrip(), final_newline=True)
