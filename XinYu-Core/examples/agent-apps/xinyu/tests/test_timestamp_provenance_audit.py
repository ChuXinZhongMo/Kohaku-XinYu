from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from timestamp_provenance_audit import (  # noqa: E402
    build_timestamp_provenance_audit,
    markdown_metadata_fields,
)


def test_markdown_metadata_fields_reads_timestamps_without_body_text(tmp_path: Path) -> None:
    path = tmp_path / "memory.md"
    path.write_text(
        """---
created_at: 2026-05-18T13:30:00+08:00
---

private body should never be reported
""",
        encoding="utf-8",
    )

    assert markdown_metadata_fields(path) == {"created_at": "2026-05-18T13:30:00+08:00"}


def test_timestamp_provenance_audit_reports_counts_without_values_or_bodies(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    memory = app / "memory/context"
    runtime = app / "runtime/events"
    cases = tmp_path / "cases/conversation"
    memory.mkdir(parents=True)
    runtime.mkdir(parents=True)
    cases.mkdir(parents=True)
    (memory / "good.md").write_text(
        "---\ncreated_at: 2026-05-18T13:30:00+08:00\n---\nsecret body alpha\n",
        encoding="utf-8",
    )
    (runtime / "bad.jsonl").write_text(
        '{"created_at": "bad-time", "body": "secret body beta"}\n{"body": "secret body gamma"}\n',
        encoding="utf-8",
    )
    (cases / "case.json").write_text(
        '{"created_at": "2026-05-18T14:00:00+08:00", "content": "secret body delta"}\n',
        encoding="utf-8",
    )

    audit = build_timestamp_provenance_audit(tmp_path)
    rendered = str(audit)

    assert audit["status"] == "hold"
    assert audit["files_with_timestamp"] == 3
    assert audit["files_missing_timestamp"] == 1
    assert audit["files_with_invalid_timestamp"] == 1
    assert audit["missing_timestamp_count"] == 1
    assert audit["invalid_timestamp_count"] == 1
    assert "bad-time" not in rendered
    assert "2026-05-18T13:30:00+08:00" not in rendered
    assert "secret body" not in rendered
