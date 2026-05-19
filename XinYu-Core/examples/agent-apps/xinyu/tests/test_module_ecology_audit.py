from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_module_ecology_audit import build_module_ecology_audit  # noqa: E402
from xinyu_module_ecology_audit import classify_module_ecology_item  # noqa: E402
from xinyu_module_ecology_audit import filter_module_ecology_audit  # noqa: E402
from xinyu_module_ecology_audit import main as module_ecology_main  # noqa: E402
from xinyu_module_ecology_audit import parse_git_short_status  # noqa: E402
from xinyu_module_ecology_audit import render_module_ecology_report  # noqa: E402


def test_module_ecology_keeps_active_core_module() -> None:
    item = classify_module_ecology_item(
        "xinyu_scene_frame.py",
        reference_count=3,
        test_count=2,
        imported_by_live=True,
    )

    assert item.bucket == "core"
    assert item.ecology_decision == "keep_active_niche"
    assert item.niche == "turn_policy_core"


def test_module_ecology_marks_duplicate_shim_for_merge() -> None:
    item = classify_module_ecology_item(
        "xinyu_daily_digest.py",
        reference_count=1,
        duplicate_group="daily_digest",
        canonical_path="services/daily_digest.py",
    )

    assert item.bucket == "services"
    assert item.ecology_decision == "merge_keep_compat_shim"
    assert "daily_digest" in item.activity_signal


def test_module_ecology_deleted_file_requires_reference_audit() -> None:
    item = classify_module_ecology_item(
        "context_retrieval_smoke.py",
        status=" D",
        reference_count=0,
        test_count=0,
    )

    assert item.bucket == "delete"
    assert item.ecology_decision == "delete_candidate_requires_reference_audit"


def test_module_ecology_archives_unreferenced_lab_asset() -> None:
    item = classify_module_ecology_item(
        "tests/fixtures/old_replay_pack.py",
        reference_count=0,
        test_count=0,
    )

    assert item.bucket == "lab"
    assert item.ecology_decision == "archive_candidate_lab_stale"


def test_module_ecology_keeps_pytest_collected_tests() -> None:
    item = classify_module_ecology_item(
        "tests/test_runtime_context.py",
        reference_count=0,
        test_count=0,
    )

    assert item.bucket == "lab"
    assert item.ecology_decision == "keep_lab_shadow"
    assert item.activity_signal == "test_runner_collected"


def test_module_ecology_keeps_pytest_conftest() -> None:
    item = classify_module_ecology_item(
        "tests/conftest.py",
        reference_count=0,
        test_count=0,
    )

    assert item.bucket == "lab"
    assert item.ecology_decision == "keep_lab_shadow"
    assert item.activity_signal == "test_runner_collected"


def test_module_ecology_classifies_learning_and_metadata_boundaries() -> None:
    learning_item = classify_module_ecology_item("learning/self_found/source.py", reference_count=1)
    data_item = classify_module_ecology_item("data/", reference_count=1)
    pytest_item = classify_module_ecology_item("pytest.ini", reference_count=1)
    env_example_item = classify_module_ecology_item("xinyu.local.env.example", reference_count=1)

    assert learning_item.bucket == "lab"
    assert data_item.bucket == "stores"
    assert pytest_item.bucket == "ops"
    assert env_example_item.bucket == "ops"


def test_build_module_ecology_audit_skips_private_memory_bodies(tmp_path: Path) -> None:
    (tmp_path / "memory/context").mkdir(parents=True)
    (tmp_path / "memory/context/private.json").write_text('{"body":"secret memory body"}', encoding="utf-8")
    (tmp_path / "xinyu_scene_frame.py").write_text("def build_scene_frame(): pass\n", encoding="utf-8")
    (tmp_path / "xinyu_runtime_context.py").write_text("import xinyu_scene_frame\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_scene_frame.py").write_text("from xinyu_scene_frame import build_scene_frame\n", encoding="utf-8")

    audit = build_module_ecology_audit(
        tmp_path,
        module_paths=("xinyu_scene_frame.py", "xinyu_runtime_context.py"),
    )
    rendered = render_module_ecology_report(audit)

    by_path = {item["path"]: item for item in audit["items"]}
    assert by_path["xinyu_scene_frame.py"]["ecology_decision"] == "keep_active_niche"
    assert "secret memory body" not in rendered
    assert "secret memory body" not in str(audit)


def test_build_module_ecology_audit_includes_deleted_status_paths(tmp_path: Path) -> None:
    (tmp_path / "xinyu_runtime_context.py").write_text("import xinyu_scene_frame\n", encoding="utf-8")

    audit = build_module_ecology_audit(
        tmp_path,
        statuses={"old_root_smoke.py": " D"},
    )

    by_path = {item["path"]: item for item in audit["items"]}
    assert by_path["old_root_smoke.py"]["bucket"] == "delete"
    assert by_path["old_root_smoke.py"]["ecology_decision"] == "delete_candidate_requires_reference_audit"
    assert "delete candidates still require archive/delete reference audit evidence" in audit["remaining_risks"][0]


def test_build_module_ecology_audit_ignores_non_live_report_and_learning_refs(tmp_path: Path) -> None:
    (tmp_path / "xinyu_scene_frame.py").write_text("def build_scene_frame(): pass\n", encoding="utf-8")
    (tmp_path / "ops/reports").mkdir(parents=True)
    (tmp_path / "ops/reports/module_ecology.md").write_text("xinyu_scene_frame.py\n", encoding="utf-8")
    (tmp_path / "learning/self_found").mkdir(parents=True)
    (tmp_path / "learning/self_found/source.py").write_text("import xinyu_scene_frame\n", encoding="utf-8")

    audit = build_module_ecology_audit(tmp_path, module_paths=("xinyu_scene_frame.py",))

    item = audit["items"][0]
    assert item["reference_count"] == 0
    assert item["ecology_decision"] == "archive_candidate_no_live_refs"


def test_build_module_ecology_audit_does_not_count_generic_stem_words(tmp_path: Path) -> None:
    (tmp_path / "stores").mkdir()
    (tmp_path / "stores/metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "xinyu_runtime_context.py").write_text("metadata = {'ok': True}\n", encoding="utf-8")

    audit = build_module_ecology_audit(tmp_path, module_paths=("stores/metadata.json",))

    assert audit["items"][0]["reference_count"] == 0


def test_build_module_ecology_audit_counts_dotted_python_imports_for_generic_stems(tmp_path: Path) -> None:
    (tmp_path / "xinyu_v1").mkdir()
    (tmp_path / "xinyu_v1/types.py").write_text("class RouteName: pass\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_types.py").write_text("from xinyu_v1.types import RouteName\n", encoding="utf-8")

    audit = build_module_ecology_audit(tmp_path, module_paths=("xinyu_v1/types.py",))

    assert audit["items"][0]["test_count"] == 1
    assert audit["items"][0]["ecology_decision"] == "keep_active_niche"


def test_build_module_ecology_audit_counts_relative_python_imports(tmp_path: Path) -> None:
    (tmp_path / "xinyu_v1/gateway").mkdir(parents=True)
    (tmp_path / "xinyu_v1/gateway/models.py").write_text("class BridgeReply: pass\n", encoding="utf-8")
    (tmp_path / "xinyu_v1/gateway/bridge_gateway.py").write_text(
        "from .models import BridgeReply\n",
        encoding="utf-8",
    )

    audit = build_module_ecology_audit(tmp_path, module_paths=("xinyu_v1/gateway/models.py",))

    assert audit["items"][0]["reference_count"] == 1
    assert audit["items"][0]["ecology_decision"] == "keep_active_niche"


def test_parse_git_short_status_handles_renames_and_deletes() -> None:
    statuses = parse_git_short_status(" D old_smoke.py\nR  old.py -> ops/probes/old.py\n?? new_report.md\n")

    assert statuses["old_smoke.py"] == " D"
    assert statuses["ops/probes/old.py"] == "R "
    assert statuses["new_report.md"] == "??"


def test_module_ecology_cli_writes_markdown_report_without_private_bodies(tmp_path: Path) -> None:
    (tmp_path / "memory/context").mkdir(parents=True)
    (tmp_path / "memory/context/private.json").write_text('{"body":"secret memory body"}', encoding="utf-8")
    (tmp_path / "xinyu_scene_frame.py").write_text("def build_scene_frame(): pass\n", encoding="utf-8")
    output = tmp_path / "reports" / "module_ecology.md"

    rc = module_ecology_main(
        [
            "--root",
            str(tmp_path),
            "--output",
            str(output),
            "--no-git-status",
            "--max-items",
            "20",
        ]
    )

    rendered = output.read_text(encoding="utf-8")
    assert rc == 0
    assert "## Lifecycle Summary" in rendered
    assert "## Remaining Risks" in rendered
    assert "secret memory body" not in rendered


def test_filter_module_ecology_audit_by_decision_prefix_and_bucket() -> None:
    audit = {
        "item_count": 3,
        "by_bucket": {},
        "by_decision": {},
        "items": [
            {
                "path": "old_doc.md",
                "bucket": "ops",
                "ecology_decision": "archive_candidate_no_live_refs",
                "reference_count": 0,
                "test_count": 0,
            },
            {
                "path": "tests/test_old.py",
                "bucket": "lab",
                "ecology_decision": "archive_candidate_lab_stale",
                "reference_count": 0,
                "test_count": 0,
            },
            {
                "path": "xinyu_runtime_context.py",
                "bucket": "core",
                "ecology_decision": "keep_active_niche",
                "reference_count": 2,
                "test_count": 1,
            },
        ],
        "privacy_note": "safe",
    }

    filtered = filter_module_ecology_audit(audit, decision_prefixes=("archive_candidate",), buckets=("lab",))

    assert filtered["item_count"] == 1
    assert filtered["source_item_count"] == 3
    assert filtered["archived"] == 1
    assert filtered["items"][0]["path"] == "tests/test_old.py"


def test_module_ecology_cli_filters_decision_prefix(tmp_path: Path) -> None:
    (tmp_path / "xinyu_scene_frame.py").write_text("def build_scene_frame(): pass\n", encoding="utf-8")
    (tmp_path / "xinyu_runtime_context.py").write_text("import xinyu_scene_frame\n", encoding="utf-8")
    output = tmp_path / "reports" / "archive_candidates.md"

    rc = module_ecology_main(
        [
            "--root",
            str(tmp_path),
            "--output",
            str(output),
            "--no-git-status",
            "--decision-prefix",
            "archive_candidate",
            "--max-items",
            "20",
        ]
    )

    rendered = output.read_text(encoding="utf-8")
    assert rc == 0
    assert "xinyu_scene_frame.py" not in rendered
    assert "xinyu_runtime_context.py" in rendered


def test_render_module_ecology_report_counts_kept_merged_archived_deleted() -> None:
    audit = {
        "item_count": 4,
        "kept": 1,
        "merged": 1,
        "archived": 1,
        "deleted": 1,
        "by_bucket": {"core": 1},
        "by_decision": {
            "keep_active_niche": 1,
            "merge_keep_compat_shim": 1,
            "archive_candidate_no_live_refs": 1,
            "delete_candidate_requires_reference_audit": 1,
        },
        "items": [
            {
                "path": "xinyu_scene_frame.py",
                "bucket": "core",
                "niche": "turn_policy_core",
                "ecology_decision": "keep_active_niche",
                "reference_count": 1,
                "test_count": 1,
            }
        ],
    }

    rendered = render_module_ecology_report(audit)

    assert "kept: 1" in rendered
    assert "merged: 1" in rendered
    assert "archived: 1" in rendered
    assert "deleted: 1" in rendered
    assert "does not read or print memory" in rendered
