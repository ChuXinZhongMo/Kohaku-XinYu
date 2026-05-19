from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from stores.state_service import atomic_write_text


BOUNDARY_ID = "stores/source_extracts"
COMPATIBILITY_NOTE = (
    "legacy memory/creative/planning/inspiration/safe_extracts.jsonl physical path kept as safe source-extract storage"
)

SOURCE_EXTRACTS_REL = Path("memory/creative/planning/inspiration/safe_extracts.jsonl")


def source_extracts_path(root: Path) -> Path:
    return Path(root) / SOURCE_EXTRACTS_REL


def serialize_source_extracts(entries: Iterable[Mapping[str, Any]]) -> str:
    return "".join(json.dumps(dict(entry), ensure_ascii=False, sort_keys=True) + "\n" for entry in entries)


def write_source_extracts(root: Path, entries: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_text(source_extracts_path(root), serialize_source_extracts(entries), final_newline=False)
