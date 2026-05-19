from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from git_change_group_audit import parse_short_status  # noqa: E402
from git_change_package_plan import build_package_plan, render_markdown  # noqa: E402


def test_build_package_plan_groups_review_packages() -> None:
    entries = parse_short_status(
        " M plan.md\n"
        " M XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_engine.py\n"
        " M XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.py\n"
        " M XinYu_Desktop/src/main/index.ts\n"
        " D XinYu-Core/examples/agent-apps/xinyu/old_smoke.py\n"
    )

    plan = build_package_plan(entries, max_examples=2)

    assert plan["total"] == 5
    by_id = {package["id"]: package for package in plan["packages"]}
    assert by_id["P00"]["count"] == 1
    assert by_id["P03"]["groups"] == {"core": 1}
    assert by_id["P04"]["groups"] == {"adapters": 1}
    assert by_id["P05"]["groups"] == {"desktop": 1}
    assert by_id["P07"]["status"] == {"deleted": 1}


def test_build_package_plan_marks_memory_data_review_only() -> None:
    entries = parse_short_status(
        " M XinYu-Core/examples/agent-apps/xinyu/memory/knowledge/general.md\n"
        " M XinYu-Core/examples/agent-apps/xinyu/library/source_notes.md\n"
    )

    plan = build_package_plan(entries)

    package = plan["packages"][0]
    assert package["id"] == "P06"
    assert package["risk"] == "high"
    assert "Do not auto-delete" in package["handling"]


def test_render_markdown_includes_validation_and_privacy_note() -> None:
    entries = parse_short_status("?? XinYu-Core/examples/agent-apps/xinyu/tests/test_new.py\n")
    plan = build_package_plan(entries)

    rendered = render_markdown(plan)

    assert "Generated from `git status --short` paths only." in rendered
    assert "raw QQ content" in rendered
    assert "P02 tests-smokes-regression" in rendered
    assert ".\\.venv\\Scripts\\python.exe -m pytest tests -q" in rendered


def test_build_package_plan_has_no_unknown_for_repo_infra_and_runtime_package() -> None:
    entries = parse_short_status(
        " M .gitignore\n"
        " M XinYu-Core/examples/agent-apps/xinyu/config.yaml\n"
        " M XinYu-Core/src/xinyu_runtime/core/agent.py\n"
        "?? diagnostics/check_xinyu_health.py\n"
        "?? XinYu-Core/memory/\n"
    )

    plan = build_package_plan(entries)

    assert "P99" not in {package["id"] for package in plan["packages"]}
