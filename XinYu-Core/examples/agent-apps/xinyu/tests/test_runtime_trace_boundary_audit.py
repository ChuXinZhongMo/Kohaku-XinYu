from __future__ import annotations

import json
from pathlib import Path

from ops.validation.runtime_trace_boundary_audit import build_runtime_trace_boundary_audit, render_markdown


def _write_manifest(app_root: Path, *, allowed_raw_readers: list[str]) -> Path:
    manifest = app_root / "stores/runtime_trace_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "traces": [
                    {
                        "trace_id": "sample",
                        "path": "memory/context/sample_trace.jsonl",
                        "owner_module": "owner",
                        "owner_symbol": "write_sample",
                        "projection_paths": ["memory/context/sample_state.md"],
                        "allowed_raw_readers": allowed_raw_readers,
                        "privacy": "internal_runtime_trace",
                        "retention_policy": "append_only_pending_rotation",
                        "body_policy": "no_body_migration",
                        "stable_memory_policy": "runtime_trace_not_stable_memory",
                        "status": "compat_runtime_trace",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return manifest


def test_runtime_trace_boundary_audit_accepts_declared_reader_reference(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    manifest = _write_manifest(app, allowed_raw_readers=["owner.py"])
    owner = app / "owner.py"
    owner.parent.mkdir(parents=True, exist_ok=True)
    owner.write_text('TRACE = "memory/context/sample_trace.jsonl"\n', encoding="utf-8")
    trace_file = app / "memory/context/sample_trace.jsonl"
    trace_file.parent.mkdir(parents=True, exist_ok=True)
    trace_file.write_text('{"body": "private trace body"}\n', encoding="utf-8")

    audit = build_runtime_trace_boundary_audit(app, manifest_path=manifest)

    assert audit["status"] == "pass"
    assert audit["items"][0]["decision"] == "pass_declared_runtime_trace_boundary"
    assert "private trace body" not in str(audit)


def test_runtime_trace_boundary_audit_holds_undeclared_reader(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    manifest = _write_manifest(app, allowed_raw_readers=["owner.py"])
    (app / "owner.py").parent.mkdir(parents=True, exist_ok=True)
    (app / "owner.py").write_text('TRACE = "memory/context/sample_trace.jsonl"\n', encoding="utf-8")
    (app / "rogue.py").write_text('TRACE = "sample_trace.jsonl"\n', encoding="utf-8")

    audit = build_runtime_trace_boundary_audit(app, manifest_path=manifest)

    assert audit["status"] == "fail"
    assert audit["items"][0]["decision"] == "hold_undeclared_raw_reader"
    assert audit["items"][0]["undeclared_reference_examples"] == ["rogue.py"]


def test_runtime_trace_boundary_audit_markdown_is_body_safe() -> None:
    rendered = render_markdown(
        {
            "status": "pass",
            "manifest_ok": True,
            "trace_count": 1,
            "undeclared_reference_count": 0,
            "items": [
                {
                    "path": "memory/context/sample_trace.jsonl",
                    "trace_id": "sample",
                    "decision": "pass_declared_runtime_trace_boundary",
                    "reference_count": 1,
                    "undeclared_reference_count": 0,
                    "reference_examples": ["owner.py"],
                    "undeclared_reference_examples": [],
                }
            ],
        }
    )

    assert "Runtime Trace Boundary Audit" in rendered
    assert "does not read or print JSONL trace bodies" in rendered
    assert "owner.py" in rendered
