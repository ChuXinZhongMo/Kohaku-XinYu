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

SEARCH_TRACKED_FILES = [
    "memory/knowledge/source_requests.md",
    "memory/knowledge/source_search_results.md",
    "memory/knowledge/source_search_resolver_state.md",
    "memory/knowledge/search_result_gate_state.md",
    "memory/knowledge/source_registry.md",
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


def _prepare_pending_request(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_requests.md",
        """---
title: Source Requests Search Smoke
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

## request-2026-04-24-905
- question_id: q-905
- target: human-relationship
- query: human relationships attachment boundaries closeness distance trust reliable source
- url: none
- status: pending_url
- source_policy: controlled_fetch_only
- planned_at: 2026-04-24T00:00:00+08:00
- reason: smoke pending search request
""",
    )
    _write(
        root / "memory/knowledge/source_search_results.md",
        """---
title: Source Search Results Smoke
memory_type: source_search_results
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
tags: [knowledge, source, search, results, smoke]
---

# Source Search Results

## result-none
- request_id: none
- question_id: none
- url: none
- status: hold
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate pending source request search resolution with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-resolution", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from source_search_resolver_engine import run_source_search_resolver
    from search_result_gate_engine import run_search_result_gate

    restore_paths = _discover_restore_files(root, SEARCH_TRACKED_FILES) if args.restore_after else SEARCH_TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in SEARCH_TRACKED_FILES}
    resolver_result = {"resolved_results": 0}
    gate_result = {"accepted_results": 0, "updated_requests": 0}
    old_env = os.environ.get("XINYU_SOURCE_SEARCH_RESULTS")

    with tempfile.TemporaryDirectory(prefix="xinyu-search-resolution-") as tmp:
        fixture_dir = Path(tmp)
        (fixture_dir / "xinyu_fixture.html").write_text(
            """<!doctype html><html><body><article><h1>Search gate fixture</h1><p>Boundaries and closeness can coexist.</p></article></body></html>""",
            encoding="utf-8",
        )
        server, thread, url = _start_fixture_server(fixture_dir)
        try:
            try:
                _prepare_pending_request(root)
                os.environ["XINYU_SOURCE_SEARCH_RESULTS"] = f"q-905={url}|Relationship boundary fixture|Controlled local search fixture"
                resolver_result = run_source_search_resolver(root, mode="source_search_resolution_smoke_resolver")
                gate_result = run_search_result_gate(root, mode="source_search_resolution_smoke_gate")

                after_restore = _snapshot(root, restore_paths)
                after = {rel: after_restore.get(rel) for rel in SEARCH_TRACKED_FILES}
                changed = _changed_files(before, after)
                protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

                print("=== SOURCE SEARCH RESOLUTION SMOKE ===")
                print("pending_requests:", resolver_result["pending_requests"])
                print("resolved_results:", resolver_result["resolved_results"])
                print("candidate_results:", gate_result["candidate_results"])
                print("accepted_results:", gate_result["accepted_results"])
                print("updated_requests:", gate_result["updated_requests"])
                print("protected_changed:", ", ".join(protected_changed) or "none")
                print("fixture_url:", url)
                print("=== MUTATION SUMMARY ===")
                print(f"tracked_files: {len(SEARCH_TRACKED_FILES)}")
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
                    os.environ.pop("XINYU_SOURCE_SEARCH_RESULTS", None)
                else:
                    os.environ["XINYU_SOURCE_SEARCH_RESULTS"] = old_env
                if args.restore_after:
                    _restore_snapshot(root, before_restore)
                    print("=== RESTORE ===")
                    print("tracked and volatile runtime files restored")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    if args.require_resolution and (int(resolver_result["resolved_results"]) <= 0 or int(gate_result["updated_requests"]) <= 0):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
