from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import sys
import tempfile
from pathlib import Path


SRC = ROOT.parents[2] / "src"
CUSTOM = ROOT / "custom"
for candidate in (SRC, CUSTOM, ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from archive_commit_engine import run_archive_commit  # noqa: E402
from memory_sync_plugin import sync_from_texts  # noqa: E402
from xinyu_memory_event_sourcing import record_chat_event  # noqa: E402


USER_TEXT = "记住这个记忆规则：以后要有选择性，只保留真正重要的部分，其他细节可以淡去。"
ASSISTANT_TEXT = "我会只留下有影响的部分，别把随口的东西压成长期记忆。"
CHECKED_AT = "2026-04-28T03:00:00+08:00"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_archive_commit_ready(root: Path) -> None:
    queue_path = root / "memory/archive/archive_queue.md"
    queue = queue_path.read_text(encoding="utf-8-sig").replace("- status: hold", "- status: ready", 1)
    queue_path.write_text(queue, encoding="utf-8")
    _write(root / "memory/archive/retention_gate_state.md", "# Retention Gate\n\n- archive_permission: compress_ready\n")
    _write(root / "memory/archive/archive_output_state.md", "# Archive Output\n\n- next_action: summarize_then_compress\n")
    _write(root / "memory/archive/compressed.md", "# Compressed Archive\n")
    _write(root / "memory/archive/dormant.md", "# Dormant Archive\n")


def _event_sourced_queue_case() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        record = record_chat_event(
            root,
            {
                "platform": "smoke",
                "message_type": "private_text",
                "session_id": "smoke:owner",
                "user_id": "owner",
                "message_id": "archive-trace-1",
                "timestamp": CHECKED_AT,
                "metadata": {"is_owner_user": True},
            },
            text=USER_TEXT,
        )
        if record.get("gate_status") != "passed":
            failures.append(f"sidecar record did not pass gate: {record}")
        if record.get("claim_count", 0) <= 0:
            failures.append(f"sidecar record did not create a memory-policy claim: {record}")

        changed = sync_from_texts(root, USER_TEXT, ASSISTANT_TEXT)
        queue = (root / "memory/archive/archive_queue.md").read_text(encoding="utf-8-sig")
        for marker in (
            "## item-",
            "- coverage_required: true",
            "- source_trace_status: covered",
            "- source_event_ids: [",
            "- retained_claim_ids: [",
            "- summary_ids: [",
        ):
            if marker not in queue:
                failures.append(f"event-sourced queue missing marker: {marker}")
        if not changed:
            failures.append("sync_from_texts returned false for event-sourced archive candidate")

        _prepare_archive_commit_ready(root)
        commit = run_archive_commit(root, checked_at=CHECKED_AT, mode="archive_queue_trace_smoke_commit")
        if commit["commit_action"] != "committed":
            failures.append(f"event-sourced archive queue did not commit after coverage: {commit}")
        if commit["summary_coverage_permission"] != "allowed":
            failures.append(f"event-sourced archive queue was not coverage-allowed: {commit}")
    return failures


def _legacy_fallback_case() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        changed = sync_from_texts(root, USER_TEXT, ASSISTANT_TEXT)
        queue = (root / "memory/archive/archive_queue.md").read_text(encoding="utf-8-sig")
        if not changed:
            failures.append("sync_from_texts returned false for legacy fallback candidate")
        if "- source_trace_status: raw_event_not_found" not in queue:
            failures.append("legacy fallback queue did not record missing source trace status")
        if "- coverage_required: true" in queue:
            failures.append("legacy fallback queue incorrectly required event-sourced coverage")
    return failures


def main() -> int:
    failures: list[str] = []
    failures.extend(_event_sourced_queue_case())
    failures.extend(_legacy_fallback_case())
    if failures:
        print("Archive queue trace smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Archive queue trace smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

