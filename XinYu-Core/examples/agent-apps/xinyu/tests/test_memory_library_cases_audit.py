from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from memory_library_cases_audit import (  # noqa: E402
    boundary_concern,
    classify_zone,
    collect_boundary_records,
    frontmatter_fields,
    summarize,
)


def test_frontmatter_fields_reads_only_metadata_keys(tmp_path: Path) -> None:
    path = tmp_path / "item.md"
    path.write_text(
        """---
title: Private Body Should Not Be Reported
memory_type: relationship_memory
source: owner
---

private body text
""",
        encoding="utf-8",
    )

    assert frontmatter_fields(path) == {"memory_type": "relationship_memory", "source": "owner"}


def test_classify_zone_for_canonical_and_legacy_paths(tmp_path: Path) -> None:
    repo = tmp_path
    app = repo / "XinYu-Core/examples/agent-apps/xinyu"

    assert classify_zone(repo, repo / "cases/conversation/seed.jsonl") == "cases"
    assert classify_zone(repo, repo / "library/datasets/public.jsonl") == "library"
    assert classify_zone(repo, app / "memory/knowledge/general.md") == "memory.knowledge"
    assert classify_zone(repo, app / "data/conversation_experience/old.jsonl") == "legacy.cases"
    assert classify_zone(repo, app / "data/external/old.jsonl") == "legacy.library"


def test_boundary_concern_flags_legacy_and_mixed_metadata() -> None:
    assert boundary_concern("x/data/external/old.jsonl", "legacy.library", {}) == "legacy_fallback_review"
    assert (
        boundary_concern("library/datasets/a.md", "library", {"memory_type": "stable_memory"})
        == "library_file_has_memory_frontmatter"
    )
    assert (
        boundary_concern("cases/conversation/a.md", "cases", {"memory_type": "relationship_memory"})
        == "case_file_declares_non_case_memory_type"
    )


def test_collect_boundary_records_summarizes_without_body_text(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    memory_file = app / "memory/knowledge/general.md"
    legacy_file = app / "data/external/public.jsonl"
    memory_file.parent.mkdir(parents=True)
    legacy_file.parent.mkdir(parents=True)
    memory_file.write_text("---\nmemory_type: knowledge\nsource: system\n---\nsecret body\n", encoding="utf-8")
    legacy_file.write_text('{"body": "secret dataset row"}\n', encoding="utf-8")

    summary = summarize(collect_boundary_records(tmp_path))

    assert summary["total_files"] == 2
    assert summary["zone_counts"]["memory.knowledge"] == 1
    assert summary["zone_counts"]["legacy.library"] == 1
    assert "secret body" not in str(summary)
    assert "secret dataset row" not in str(summary)
