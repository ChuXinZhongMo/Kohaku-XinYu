from __future__ import annotations

from pathlib import Path

from stores.source_extracts import (
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    SOURCE_EXTRACTS_REL,
    serialize_source_extracts,
    source_extracts_path,
    write_source_extracts,
)
from xinyu_creative_writing import REFERENCE_EXTRACTS_REL


def test_source_extracts_store_keeps_legacy_path_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/source_extracts"
    assert "legacy memory/creative" in COMPATIBILITY_NOTE
    assert SOURCE_EXTRACTS_REL == REFERENCE_EXTRACTS_REL

    write_source_extracts(
        tmp_path,
        [
            {
                "source_id": "source-a",
                "storage_policy": "metadata_summary_structure_only_no_raw_chapter_text",
            },
            {
                "source_id": "source-b",
                "storage_policy": "metadata_only_no_chapter_fetch",
            },
        ],
    )

    path = source_extracts_path(tmp_path)
    assert path == tmp_path / "memory/creative/planning/inspiration/safe_extracts.jsonl"
    assert path.read_text(encoding="utf-8").splitlines() == [
        '{"source_id": "source-a", "storage_policy": "metadata_summary_structure_only_no_raw_chapter_text"}',
        '{"source_id": "source-b", "storage_policy": "metadata_only_no_chapter_fetch"}',
    ]


def test_source_extracts_serializer_preserves_empty_file_semantics() -> None:
    assert serialize_source_extracts([]) == ""
