from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PromptContextFileSignature:
    mtime_ns: int
    size: int


def prompt_context_file_signature(path: Path) -> PromptContextFileSignature | None:
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return PromptContextFileSignature(mtime_ns=stat.st_mtime_ns, size=stat.st_size)
