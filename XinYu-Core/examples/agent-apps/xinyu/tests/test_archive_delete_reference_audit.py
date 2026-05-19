from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from archive_delete_reference_audit import build_archive_delete_reference_audit, render_markdown  # noqa: E402
from git_change_group_audit import parse_short_status  # noqa: E402


def test_archive_delete_audit_detects_relocation_and_references(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    (app / "tests/smoke/memory").mkdir(parents=True)
    (app / "custom").mkdir(parents=True)
    (app / "tests/smoke/memory/context_retrieval_smoke.py").write_text("print('ok')\n", encoding="utf-8")
    (app / "custom/inner_framework_manifest.py").write_text(
        'MANIFEST = "source_gate_manifest.py"\n',
        encoding="utf-8",
    )
    entries = parse_short_status(
        " D XinYu-Core/examples/agent-apps/xinyu/context_retrieval_smoke.py\n"
        " D XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_manifest.py\n"
        " D XinYu-Core/examples/agent-apps/xinyu/check_runtime_env.py\n"
    )

    audit = build_archive_delete_reference_audit(tmp_path, entries=entries)
    by_path = {item["path"]: item for item in audit["items"]}

    relocated = by_path["XinYu-Core/examples/agent-apps/xinyu/context_retrieval_smoke.py"]
    assert relocated["decision"] == "accept_delete_relocated"
    assert relocated["relocation_examples"] == [
        "XinYu-Core/examples/agent-apps/xinyu/tests/smoke/memory/context_retrieval_smoke.py"
    ]

    referenced = by_path["XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_manifest.py"]
    assert referenced["decision"] == "hold_delete_referenced"
    assert referenced["reference_examples"] == [
        "XinYu-Core/examples/agent-apps/xinyu/custom/inner_framework_manifest.py"
    ]

    no_refs = by_path["XinYu-Core/examples/agent-apps/xinyu/check_runtime_env.py"]
    assert no_refs["decision"] == "accept_delete_no_live_refs"


def test_archive_delete_audit_ignores_self_test_references(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    (app / "tests").mkdir(parents=True)
    (app / "ops/validation").mkdir(parents=True)
    (app / "tests/test_archive_delete_reference_audit.py").write_text(
        '"custom/source_gate_manifest.py"\n',
        encoding="utf-8",
    )
    (app / "ops/validation/archive_delete_reference_audit.py").write_text(
        '"source_gate_manifest.py"\n',
        encoding="utf-8",
    )
    entries = parse_short_status(
        " D XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_manifest.py\n"
    )

    audit = build_archive_delete_reference_audit(tmp_path, entries=entries)
    by_path = {item["path"]: item for item in audit["items"]}

    item = by_path["XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_manifest.py"]
    assert item["decision"] == "accept_delete_no_live_refs"
    assert item["reference_examples"] == []


def test_archive_delete_audit_accepts_ops_archive_relocation_and_ignores_reports(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    (app / "ops/archive/custom-manifests/2026-05-17").mkdir(parents=True)
    (app / "ops/reports").mkdir(parents=True)
    (app / "ops/archive/custom-manifests/2026-05-17/source_gate_manifest.py").write_text(
        "ARCHIVED = True\n",
        encoding="utf-8",
    )
    (app / "ops/reports/module_ecology.md").write_text(
        "custom/source_gate_manifest.py\n",
        encoding="utf-8",
    )
    entries = parse_short_status(
        " D XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_manifest.py\n"
    )

    audit = build_archive_delete_reference_audit(tmp_path, entries=entries)
    item = audit["items"][0]

    assert item["decision"] == "accept_delete_relocated"
    assert item["relocation_examples"] == [
        "XinYu-Core/examples/agent-apps/xinyu/ops/archive/custom-manifests/2026-05-17/source_gate_manifest.py"
    ]
    assert item["reference_examples"] == []


def test_archive_delete_audit_accepts_ops_validation_relocation(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    (app / "ops/validation").mkdir(parents=True)
    (app / "ops/validation/validate_scaffold.py").write_text("def main(): return 0\n", encoding="utf-8")
    entries = parse_short_status(
        " D XinYu-Core/examples/agent-apps/xinyu/validate_scaffold.py\n"
    )

    audit = build_archive_delete_reference_audit(tmp_path, entries=entries)
    item = audit["items"][0]

    assert item["candidate_kind"] == "root_validator"
    assert item["decision"] == "accept_delete_relocated"
    assert item["relocation_examples"] == [
        "XinYu-Core/examples/agent-apps/xinyu/ops/validation/validate_scaffold.py"
    ]


def test_archive_delete_audit_accepts_core_and_ops_orphan_archive_relocations(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    (app / "ops/archive/core-orphans/2026-05-19/xinyu_v1/storage").mkdir(parents=True)
    (app / "ops/archive/ops-orphans/2026-05-19").mkdir(parents=True)
    (app / "ops/archive/core-orphans/2026-05-19/xinyu_v1/storage/sqlite_meta.py").write_text(
        "ARCHIVED = True\n",
        encoding="utf-8",
    )
    (app / "ops/archive/ops-orphans/2026-05-19/NAMING-CONVENTIONS.md").write_text(
        "# archived\n",
        encoding="utf-8",
    )
    entries = parse_short_status(
        " D XinYu-Core/examples/agent-apps/xinyu/xinyu_v1/storage/sqlite_meta.py\n"
        " D XinYu-Core/examples/agent-apps/xinyu/NAMING-CONVENTIONS.md\n"
    )

    audit = build_archive_delete_reference_audit(tmp_path, entries=entries)
    by_path = {item["path"]: item for item in audit["items"]}

    core = by_path["XinYu-Core/examples/agent-apps/xinyu/xinyu_v1/storage/sqlite_meta.py"]
    assert core["candidate_kind"] == "core_orphan"
    assert core["decision"] == "accept_delete_relocated"
    assert core["relocation_examples"] == [
        "XinYu-Core/examples/agent-apps/xinyu/ops/archive/core-orphans/2026-05-19/xinyu_v1/storage/sqlite_meta.py"
    ]

    ops = by_path["XinYu-Core/examples/agent-apps/xinyu/NAMING-CONVENTIONS.md"]
    assert ops["candidate_kind"] == "ops_orphan"
    assert ops["decision"] == "accept_delete_relocated"
    assert ops["relocation_examples"] == [
        "XinYu-Core/examples/agent-apps/xinyu/ops/archive/ops-orphans/2026-05-19/NAMING-CONVENTIONS.md"
    ]


def test_archive_delete_audit_report_is_privacy_safe() -> None:
    rendered = render_markdown(
        {
            "total_candidates": 1,
            "by_decision": {"accept_delete_no_live_refs": 1},
            "by_kind": {"root_diagnostic": 1},
            "items": [
                {
                    "path": "XinYu-Core/examples/agent-apps/xinyu/check_runtime_env.py",
                    "candidate_kind": "root_diagnostic",
                    "decision": "accept_delete_no_live_refs",
                    "relocation_count": 0,
                    "relocation_examples": [],
                    "reference_count": 0,
                    "reference_examples": [],
                }
            ],
        }
    )

    assert "Archive/Delete Reference Audit" in rendered
    assert "does not read or print private memory" in rendered
    assert "accept_delete_no_live_refs" in rendered
