from __future__ import annotations

import json
from pathlib import Path

from ops.validation.queue_boundary_audit import build_queue_boundary_audit, render_markdown


def _write_manifest(app_root: Path, *, allowed_raw_readers: list[str]) -> Path:
    manifest = app_root / "stores/queue_boundary_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "queues": [
                    {
                        "queue_id": "sample",
                        "path": "memory/context/sample_queue.json",
                        "owner_module": "owner",
                        "owner_symbols": ["write_sample"],
                        "projection_paths": ["memory/context/sample_state.md"],
                        "allowed_raw_readers": allowed_raw_readers,
                        "privacy": "private_runtime_queue",
                        "retention_policy": "operational_queue",
                        "body_policy": "no_body_migration",
                        "stable_memory_policy": "runtime_queue_not_stable_memory",
                        "status": "compat_runtime_queue",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return manifest


def test_queue_boundary_audit_accepts_declared_reader_reference(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    manifest = _write_manifest(app, allowed_raw_readers=["owner.py"])
    owner = app / "owner.py"
    owner.parent.mkdir(parents=True, exist_ok=True)
    owner.write_text('QUEUE = "memory/context/sample_queue.json"\n', encoding="utf-8")
    queue_file = app / "memory/context/sample_queue.json"
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    queue_file.write_text('{"body": "private queued payload"}\n', encoding="utf-8")

    audit = build_queue_boundary_audit(app, manifest_path=manifest)

    assert audit["status"] == "pass"
    assert audit["items"][0]["decision"] == "pass_declared_queue_boundary"
    assert "private queued payload" not in str(audit)


def test_queue_boundary_audit_holds_undeclared_reader(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    manifest = _write_manifest(app, allowed_raw_readers=["owner.py"])
    (app / "owner.py").parent.mkdir(parents=True, exist_ok=True)
    (app / "owner.py").write_text('QUEUE = "memory/context/sample_queue.json"\n', encoding="utf-8")
    (app / "rogue.py").write_text('QUEUE = "sample_queue.json"\n', encoding="utf-8")

    audit = build_queue_boundary_audit(app, manifest_path=manifest)

    assert audit["status"] == "fail"
    assert audit["items"][0]["decision"] == "hold_undeclared_raw_reader"
    assert audit["items"][0]["undeclared_reference_examples"] == ["rogue.py"]


def test_queue_boundary_audit_ignores_archived_manual_smokes(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    manifest = _write_manifest(app, allowed_raw_readers=["owner.py"])
    (app / "owner.py").parent.mkdir(parents=True, exist_ok=True)
    (app / "owner.py").write_text('QUEUE = "memory/context/sample_queue.json"\n', encoding="utf-8")
    archived = app / "ops/archive/manual-smokes/2026-05-19/tests/smoke/initiative/old_smoke.py"
    archived.parent.mkdir(parents=True, exist_ok=True)
    archived.write_text('QUEUE = "memory/context/sample_queue.json"\n', encoding="utf-8")

    audit = build_queue_boundary_audit(app, manifest_path=manifest)

    assert audit["status"] == "pass"
    assert audit["items"][0]["undeclared_reference_examples"] == []


def test_queue_boundary_audit_markdown_is_body_safe() -> None:
    rendered = render_markdown(
        {
            "status": "pass",
            "manifest_ok": True,
            "queue_count": 1,
            "undeclared_reference_count": 0,
            "items": [
                {
                    "path": "memory/context/sample_queue.json",
                    "queue_id": "sample",
                    "decision": "pass_declared_queue_boundary",
                    "reference_count": 1,
                    "undeclared_reference_count": 0,
                    "reference_examples": ["owner.py"],
                    "undeclared_reference_examples": [],
                }
            ],
        }
    )

    assert "Queue Boundary Audit" in rendered
    assert "does not read or print queue bodies" in rendered
    assert "owner.py" in rendered
