from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from memory_boundary_decision_queue import build_decision_queue, render_markdown  # noqa: E402
from memory_library_cases_audit import collect_boundary_records  # noqa: E402


def test_build_decision_queue_assigns_review_actions_without_bodies(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    runtime_file = app / "runtime/smoke/memory.md"
    structured_memory = app / "memory/state.json"
    legacy_library = app / "data/external/source.jsonl"
    runtime_file.parent.mkdir(parents=True)
    structured_memory.parent.mkdir(parents=True)
    legacy_library.parent.mkdir(parents=True)
    runtime_file.write_text("---\nmemory_type: stable\nsource: private\n---\nsecret runtime body\n", encoding="utf-8")
    structured_memory.write_text('{"body": "secret memory body"}\n', encoding="utf-8")
    legacy_library.write_text('{"body": "secret source row"}\n', encoding="utf-8")

    queue = build_decision_queue(collect_boundary_records(tmp_path))

    assert queue["total_review_items"] == 3
    assert queue["by_action"]["review_runtime_snapshot"] == 1
    assert queue["by_action"]["classify_structured_memory_file"] == 1
    assert queue["by_action"]["keep_or_archive_legacy_fallback"] == 1
    assert "secret runtime body" not in str(queue)
    assert "secret memory body" not in str(queue)
    assert "secret source row" not in str(queue)
    assert "private" not in str(queue)


def test_render_markdown_limits_display_but_keeps_total() -> None:
    app = Path("XinYu-Core/examples/agent-apps/xinyu")
    records = []
    from memory_library_cases_audit import BoundaryRecord  # noqa: PLC0415

    for index in range(3):
        records.append(
            BoundaryRecord(
                path=(app / f"runtime/smoke/{index}.md").as_posix(),
                zone="runtime",
                declared_type="stable",
                source="owner",
                concern="runtime_file_has_stable_memory_frontmatter",
            )
        )

    queue = build_decision_queue(records)
    rendered = render_markdown(queue, max_items=1)

    assert "total_review_items: 3" in rendered
    assert "Omitted 2 lower display items" in rendered
    assert "raw source values" in rendered
    assert "owner" not in rendered
