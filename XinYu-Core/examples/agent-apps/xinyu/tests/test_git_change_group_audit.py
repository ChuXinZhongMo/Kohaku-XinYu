from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from git_change_group_audit import classify_change, parse_short_status, summarize  # noqa: E402


def test_parse_short_status_handles_basic_paths_and_renames() -> None:
    entries = parse_short_status(
        " M plan.md\n"
        " D XinYu-Core/examples/agent-apps/xinyu/old_smoke.py\n"
        "R  old.py -> XinYu-Core/examples/agent-apps/xinyu/tests/smoke/new_smoke.py\n"
    )

    assert [entry.status for entry in entries] == [" M", " D", "R "]
    assert entries[2].path == "XinYu-Core/examples/agent-apps/xinyu/tests/smoke/new_smoke.py"


def test_classify_change_groups_live_and_cleanup_paths() -> None:
    assert classify_change("plan.md", " M") == "docs"
    assert classify_change("XinYu_Desktop/src/renderer/src/main.tsx", " M") == "desktop"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/old_smoke.py", " D") == "archive/delete"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/validate_scaffold.py", " D") == "archive/delete"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/sync_memory_seeds.py", " D") == "archive/delete"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/xinyu_research_loop_dry_run.py", " D") == "archive/delete"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/tests/smoke/foo.py", "??") == "tests"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/memory/knowledge/general.md", " M") == "memory-data"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.py", " M") == "adapters"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/stores/state_service.py", " M") == "stores"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/services/daily_digest.py", " M") == "services"
    assert classify_change(".gitignore", " M") == "ops"
    assert classify_change("diagnostics/check_xinyu_health.py", "??") == "ops"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/config.yaml", " M") == "ops"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/pytest.ini", "??") == "ops"
    assert classify_change("XinYu-Core/src/xinyu_runtime/core/agent.py", " M") == "core"
    assert classify_change("XinYu-Core/memory/foo.md", "??") == "memory-data"
    assert classify_change("Start-XinYu-Desktop.ps1", " M") == "desktop"
    assert classify_change("Stop-XinYu-Desktop.ps1", " M") == "desktop"
    assert classify_change("Start-XinYu-TinyKernel.ps1", "??") == "ops"
    assert classify_change("Stop-XinYu-TinyKernel.bat", "??") == "ops"
    assert classify_change("XinYu-TinyKernel/server/app.py", "??") == "core"
    assert classify_change("XinYu-Core/examples/agent-apps/xinyu/xinyu.local.env.example", " M") == "ops"


def test_summarize_counts_groups_without_reading_files() -> None:
    entries = parse_short_status(
        " M plan.md\n"
        " M XinYu_Desktop/src/main/index.ts\n"
        " D XinYu-Core/examples/agent-apps/xinyu/bridge_values_smoke.py\n"
    )

    summary = summarize(entries)

    assert summary["total"] == 3
    assert summary["by_status"] == {"deleted": 1, "modified": 2}
    assert summary["by_group"]["docs"]["count"] == 1
    assert summary["by_group"]["desktop"]["count"] == 1
    assert summary["by_group"]["archive/delete"]["count"] == 1
