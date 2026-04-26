from __future__ import annotations

import argparse
import functools
import http.server
import sys
import tempfile
import threading
from pathlib import Path

from memory_mutation_smoke import (
    _changed_files,
    _discover_restore_files,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)

OUTWARD_TRACKED_FILES = [
    "memory/knowledge/source_integration_gate_state.md",
    "memory/knowledge/source_gate_state.md",
    "memory/knowledge/source_requests.md",
    "memory/knowledge/source_materials.md",
    "memory/knowledge/outward_source_state.md",
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


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_ready_case(root: Path, url: str) -> None:
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
- mode: outward_source_smoke_gate

## Gate Decision
- integration_permission: prepare_only
- gate_reason: smoke_source_request_ready
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
importance_score: 82
impact_score: 81
confidence_score: 100
status: active
tags: [knowledge, source, gate, smoke]
---

# Source Gate State

## Candidate Questions
- q-903: human-relationship-boundaries
""",
    )
    _write(
        root / "memory/knowledge/source_requests.md",
        f"""---
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
tags: [knowledge, source, requests, smoke]
---

# Source Requests

## request-smoke
- question_id: q-903
- url: {url}
- status: ready
- reason: deterministic local fixture for outward source staging
""",
    )
    _write(
        root / "memory/knowledge/source_materials.md",
        """---
title: Source Materials Smoke
memory_type: source_materials
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
tags: [knowledge, sources, materials, smoke]
---

# Source Materials
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate outward source staging with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-stage", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def _start_fixture_server(directory: Path) -> tuple[http.server.ThreadingHTTPServer, threading.Thread, str]:
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}/xinyu_fixture.html"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from outward_source_engine import run_outward_source

    restore_paths = _discover_restore_files(root, OUTWARD_TRACKED_FILES) if args.restore_after else OUTWARD_TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in OUTWARD_TRACKED_FILES}
    result = {"staged_materials": 0}

    with tempfile.TemporaryDirectory(prefix="xinyu-outward-source-") as tmp:
        fixture_dir = Path(tmp)
        (fixture_dir / "xinyu_fixture.html").write_text(
            """<!doctype html>
<html><head><title>Relationship Boundaries Fixture</title></head>
<body>
<article>
<h1>Relationship boundaries and closeness</h1>
<p>Healthy relationships can include both approach and distance. A quiet pause does not automatically mean rejection; it may mean the person needs space before reconnecting.</p>
<p>Trust is strengthened when closeness, hesitation, disappointment, and return are all remembered in context instead of flattened into a single mood.</p>
</article>
</body></html>
""",
            encoding="utf-8",
        )
        server, thread, url = _start_fixture_server(fixture_dir)
        try:
            try:
                _prepare_ready_case(root, url)
                result = run_outward_source(root, mode="outward_source_smoke", urls=[url])
                after_restore = _snapshot(root, restore_paths)
                after = {rel: after_restore.get(rel) for rel in OUTWARD_TRACKED_FILES}
                changed = _changed_files(before, after)
                protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

                print("=== OUTWARD SOURCE SMOKE ===")
                print("permission:", result["permission"])
                print("fetched_sources:", result["fetched_sources"])
                print("staged_materials:", result["staged_materials"])
                print("material_ids:", ", ".join(result["material_ids"]) or "none")
                print("skipped_reason:", result["skipped_reason"])
                print("protected_changed:", ", ".join(protected_changed) or "none")
                print("fixture_url:", url)
                print("=== MUTATION SUMMARY ===")
                print(f"tracked_files: {len(OUTWARD_TRACKED_FILES)}")
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
                if args.restore_after:
                    _restore_snapshot(root, before_restore)
                    print("=== RESTORE ===")
                    print("tracked and volatile runtime files restored")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    if args.require_stage and int(result["staged_materials"]) <= 0:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
