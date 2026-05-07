from __future__ import annotations

import argparse
import os
import tempfile
import sys
from pathlib import Path

from memory_mutation_smoke import (
    _changed_files,
    _discover_restore_files,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)
from outward_source_smoke import _start_fixture_server

REQUEST_TRACKED_FILES = [
    "memory/knowledge/source_integration_gate_state.md",
    "memory/knowledge/source_gate_state.md",
    "memory/knowledge/source_requests.md",
    "memory/knowledge/source_request_planner_state.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_gate_case(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_integration_gate_state.md",
        """---
title: Source Integration Gate State
memory_type: source_integration_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 82
impact_score: 81
confidence_score: 100
status: active
tags: [knowledge, integration, gate, smoke]
---

# Source Integration Gate State

## Last Evaluation
- checked_at: 2026-04-24T00:00:00+08:00
- mode: source_request_planner_smoke_gate

## Gate Decision
- integration_permission: prepare_only
- gate_reason: smoke_source_request_planner_ready
- ready_candidates: 1
""",
    )
    _write(
        root / "memory/knowledge/source_gate_state.md",
        """---
title: Source Gate State
memory_type: source_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 79
impact_score: 79
confidence_score: 100
status: active
tags: [knowledge, source_gate, smoke]
---

# Source Gate State

## Last Evaluation
- checked_at: 2026-04-24T00:00:00+08:00
- mode: source_request_planner_smoke_gate

## Current Candidates
- q-904: human-relationship
""",
    )


def _reset_requests(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_requests.md",
        """---
title: Source Requests Smoke
memory_type: source_requests
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 74
impact_score: 72
confidence_score: 100
status: active
tags: [knowledge, outward, requests, smoke]
---

# Source Requests

## request-none
- question_id: none
- target: none
- query: none
- url: none
- status: hold
- source_policy: controlled_fetch_only
- reason: smoke baseline
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate source request planning with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-plan", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from source_request_planner_engine import run_source_request_planner

    restore_paths = _discover_restore_files(root, REQUEST_TRACKED_FILES) if args.restore_after else REQUEST_TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in REQUEST_TRACKED_FILES}
    pending_result = {"planned_requests": 0, "pending_url_requests": 0}
    ready_result = {"planned_requests": 0, "ready_requests": 0}

    old_env = os.environ.get("XINYU_SOURCE_REQUEST_URLS")
    with tempfile.TemporaryDirectory(prefix="xinyu-source-request-") as tmp:
        fixture_dir = Path(tmp)
        (fixture_dir / "xinyu_fixture.html").write_text(
            """<!doctype html><html><body><article><h1>Relationship source fixture</h1><p>Boundaries and closeness can coexist in human relationships.</p></article></body></html>""",
            encoding="utf-8",
        )
        server, thread, url = _start_fixture_server(fixture_dir)
        try:
            try:
                _prepare_gate_case(root)
                _reset_requests(root)
                os.environ.pop("XINYU_SOURCE_REQUEST_URLS", None)
                pending_result = run_source_request_planner(root, mode="source_request_planner_smoke_pending")

                _reset_requests(root)
                os.environ["XINYU_SOURCE_REQUEST_URLS"] = f"q-904={url}"
                ready_result = run_source_request_planner(root, mode="source_request_planner_smoke_ready")

                after_restore = _snapshot(root, restore_paths)
                after = {rel: after_restore.get(rel) for rel in REQUEST_TRACKED_FILES}
                changed = _changed_files(before, after)
                protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

                print("=== SOURCE REQUEST PLANNER SMOKE ===")
                print("pending_permission:", pending_result["permission"])
                print("pending_planned_requests:", pending_result["planned_requests"])
                print("pending_url_requests:", pending_result["pending_url_requests"])
                print("ready_permission:", ready_result["permission"])
                print("ready_planned_requests:", ready_result["planned_requests"])
                print("ready_requests:", ready_result["ready_requests"])
                print("protected_changed:", ", ".join(protected_changed) or "none")
                print("fixture_url:", url)
                print("=== MUTATION SUMMARY ===")
                print(f"tracked_files: {len(REQUEST_TRACKED_FILES)}")
                print(f"changed_files: {len(changed)}")
                print(f"restore_after: {args.restore_after}")
                print("=== CHANGED FILES ===")
                if changed:
                    for rel in changed:
                        print(rel)
                else:
                    print("(none)")
                if args.diff_lines > 0 and changed:
                    print("=== DIFFS ===")
                    for rel in changed:
                        print(f"--- {rel} ---")
                        for line in _render_diff(before.get(rel), after.get(rel), rel, args.diff_lines):
                            print(line)
                if protected_changed:
                    return 5
            finally:
                if old_env is None:
                    os.environ.pop("XINYU_SOURCE_REQUEST_URLS", None)
                else:
                    os.environ["XINYU_SOURCE_REQUEST_URLS"] = old_env
                if args.restore_after:
                    _restore_snapshot(root, before_restore)
                    print("=== RESTORE ===")
                    print("tracked and volatile runtime files restored")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    if args.require_plan and (int(pending_result["pending_url_requests"]) <= 0 or int(ready_result["ready_requests"]) <= 0):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
