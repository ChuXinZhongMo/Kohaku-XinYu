from __future__ import annotations

import json
import os

from xinyu_tool_targets import TargetRegistry
from xinyu_tool_targets_store import (
    glob_tool_target_paths,
    read_tool_target_config_text,
    tool_target_config_exists,
    tool_target_path_exists,
    tool_target_path_is_dir,
    tool_target_path_is_file,
    tool_target_path_mtime,
)


def test_tool_targets_store_reads_config_and_path_metadata(tmp_path) -> None:
    config_path = tmp_path / "config/tool_targets.json"
    logs_dir = tmp_path / "logs"
    log_path = logs_dir / "app.log"

    assert tool_target_config_exists(config_path) is False
    assert tool_target_path_exists(logs_dir) is False

    logs_dir.mkdir()
    log_path.write_text("line\n", encoding="utf-8")
    config_path.parent.mkdir(parents=True)
    config_path.write_text('{"targets": {}}', encoding="utf-8")

    assert tool_target_config_exists(config_path) is True
    assert read_tool_target_config_text(config_path) == '{"targets": {}}'
    assert tool_target_path_exists(logs_dir) is True
    assert tool_target_path_is_dir(logs_dir) is True
    assert glob_tool_target_paths(logs_dir, "*.log") == [log_path]
    assert tool_target_path_is_file(log_path) is True
    assert isinstance(tool_target_path_mtime(log_path), float)


def test_target_registry_uses_store_backed_config_and_log_iteration(tmp_path) -> None:
    logs_dir = tmp_path / "runtime/logs"
    logs_dir.mkdir(parents=True)
    older = logs_dir / "older.log"
    newer = logs_dir / "newer.log"
    older.write_text("old\n", encoding="utf-8")
    newer.write_text("new\n", encoding="utf-8")
    os.utime(older, (100.0, 100.0))
    os.utime(newer, (200.0, 200.0))
    config_path = tmp_path / "config/tool_targets.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "targets": {
                    "runtime_logs": {
                        "kind": "logs",
                        "read_roots": ["runtime/logs"],
                        "patterns": ["*.log"],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    registry = TargetRegistry.load(tmp_path)

    assert registry.aliases() == ["runtime_logs"]
    assert [path.name for path in registry.iter_log_files("runtime_logs", max_files=2)] == [
        "newer.log",
        "older.log",
    ]
