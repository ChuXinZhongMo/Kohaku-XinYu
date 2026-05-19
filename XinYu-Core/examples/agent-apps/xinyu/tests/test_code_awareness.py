from __future__ import annotations

import json
from pathlib import Path

from xinyu_code_awareness import (
    RUNTIME_SOURCE_RELS,
    SNAPSHOT_REL,
    STATE_REL,
    TRACE_REL,
    read_code_awareness_summary,
    record_code_awareness,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_runtime_sources(root: Path) -> None:
    for rel in RUNTIME_SOURCE_RELS:
        _write(root / rel, f"# {rel}\nVALUE = {rel!r}\n")
    _write(root / "xinyu_qq_gateway.py", "GATEWAY = 'old'\n")
    _write(root / "prompts/system.md", "system prompt\n")


def test_code_awareness_detects_source_change_and_restart_need(tmp_path: Path) -> None:
    _seed_runtime_sources(tmp_path)
    first = record_code_awareness(tmp_path)

    _write(tmp_path / "xinyu_speech_controller.py", "# changed\nVALUE = 'new speech'\n")
    second = record_code_awareness(
        tmp_path,
        running_bridge_digest=str(first["current_bridge_digest"]),
        running_runtime_digest=str(first["current_runtime_digest"]),
    )

    assert second["status"] == "changed"
    assert second["source_changed"] is True
    assert second["bridge_restart_required"] is False
    assert second["runtime_restart_required"] is True
    assert any(item["path"] == "xinyu_speech_controller.py" for item in second["changed_files"])
    assert (tmp_path / SNAPSHOT_REL).exists()
    assert (tmp_path / TRACE_REL).exists()

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    assert "memory_type: code_change_awareness_state" in state
    assert "- runtime_restart_required: true" in state
    assert "modified:xinyu_speech_controller.py" in state

    summary = read_code_awareness_summary(tmp_path)
    assert summary["observed"] == "true"
    assert summary["runtime_restart_required"] == "true"


def test_code_awareness_marks_gateway_restart_may_be_needed(tmp_path: Path) -> None:
    _seed_runtime_sources(tmp_path)
    record_code_awareness(tmp_path)

    _write(tmp_path / "xinyu_qq_gateway.py", "GATEWAY = 'new'\n")
    result = record_code_awareness(tmp_path)

    assert result["gateway_restart_may_be_needed"] is True
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / TRACE_REL).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    assert trace_rows[-1]["gateway_restart_may_be_needed"] is True
