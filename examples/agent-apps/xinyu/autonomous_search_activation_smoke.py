from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from memory_mutation_smoke import (
    _changed_files,
    _discover_restore_files,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)
from outward_source_smoke import _start_fixture_server


TRACKED_FILES = [
    "memory/knowledge/source_integration_gate_state.md",
    "memory/knowledge/source_requests.md",
    "memory/knowledge/source_search_results.md",
    "memory/knowledge/autonomous_search_activation_state.md",
    "memory/knowledge/source_search_provider_state.md",
    "memory/knowledge/learning_quality_state.md",
    "memory/context/owner_permission_grants.md",
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


def _prepare_case(root: Path, quality_grade: str = "stable", warning_count: int = 0) -> None:
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
- mode: autonomous_search_activation_smoke_gate

## Gate Decision
- integration_permission: prepare_only
- gate_reason: smoke_activation_ready
- ready_candidates: 2
""",
    )
    _write(
        root / "memory/knowledge/source_requests.md",
        """---
title: Source Requests Activation Smoke
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

## request-2026-04-24-931
- question_id: q-931
- target: human-relationship
- query: human relationships attachment boundaries closeness distance trust reliable source
- url: none
- status: pending_url
- source_policy: controlled_fetch_only
- planned_at: 2026-04-24T00:00:00+08:00
- reason: smoke pending activation request

## request-2026-04-24-932
- question_id: q-932
- target: memory-emotion
- query: emotion memory consolidation dreams affective memory reliable source
- url: none
- status: pending_url
- source_policy: controlled_fetch_only
- planned_at: 2026-04-24T00:00:00+08:00
- reason: smoke second pending activation request
""",
    )
    _write(
        root / "memory/knowledge/source_search_results.md",
        """---
title: Source Search Results Activation Smoke
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
    _write(
        root / "memory/knowledge/learning_quality_state.md",
        f"""---
title: Learning Quality State
memory_type: learning_quality_state
time_scope: mid_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 83
impact_score: 82
confidence_score: 100
status: active
tags: [knowledge, learning, quality, smoke]
---

# Learning Quality State

## Last Evaluation
- evaluated_at: 2026-04-24T00:00:00+08:00
- mode: autonomous_search_activation_smoke_quality
- quality_grade: {quality_grade}
- learned_entries: 1
- source_materials: 1
- unique_learned_hosts: 1
- dominant_host: alpha.example
- dominant_host_entries: 1
- single_source_learned: 0
- corroborated_learned: 1
- limited_independence_learned: 0
- conflict_hold_materials: 0
- uncompared_ready_materials: 0
- warning_count: {warning_count}
""",
    )
    _write(
        root / "memory/context/owner_permission_grants.md",
        "# Owner Permission Grants\n",
    )


def _prepare_no_pending_case(root: Path) -> None:
    _prepare_case(root, quality_grade="stable", warning_count=0)
    _write(
        root / "memory/knowledge/source_requests.md",
        """---
title: Source Requests Activation Smoke No Pending
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
- reason: smoke no pending request baseline
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate autonomous search activation with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-activation", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from autonomous_search_activation_engine import run_autonomous_search_activation
    from source_search_provider_engine import run_source_search_provider

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    disabled_result = {"activation_permission": "unknown"}
    dry_result = {"activation_permission": "unknown"}
    blocked_result = {"activation_permission": "unknown"}
    no_pending_result = {"activation_permission": "unknown", "activation_reason": "unknown"}
    provider_blocked_result = {"provider_results": 0, "skipped_reason": "unknown"}
    high_override_result = {"activation_permission": "unknown", "allowed_queries": 0}
    provider_override_result = {"provider_results": 0, "pending_requests": 0}
    enabled_result = {"activation_permission": "unknown", "allowed_queries": 0}
    provider_result = {"provider_results": 0, "pending_requests": 0}
    old_provider = os.environ.get("XINYU_SOURCE_SEARCH_PROVIDER")
    old_endpoint = os.environ.get("XINYU_DUCKDUCKGO_HTML_ENDPOINT")
    old_autonomous = os.environ.get("XINYU_AUTONOMOUS_SEARCH")
    old_max = os.environ.get("XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES")

    with tempfile.TemporaryDirectory(prefix="xinyu-autonomous-search-") as tmp:
        fixture_dir = Path(tmp)
        (fixture_dir / "xinyu_fixture.html").write_text(
            """<!doctype html><html><body><article><h1>Activation fixture</h1><p>Boundaries and memory can be checked cautiously.</p></article></body></html>""",
            encoding="utf-8",
        )
        server, thread, fixture_url = _start_fixture_server(fixture_dir)
        search_url = fixture_url.rsplit("/", 1)[0] + "/search.html"
        (fixture_dir / "search.html").write_text(
            f"""<!doctype html>
<html><body>
<div class="result">
<a class="result__a" href="{fixture_url}">Activation provider fixture</a>
<a class="result__snippet" href="{fixture_url}">Controlled activation result.</a>
</div>
</body></html>
""",
            encoding="utf-8",
        )
        try:
            try:
                os.environ["XINYU_SOURCE_SEARCH_PROVIDER"] = "duckduckgo_html"
                os.environ["XINYU_DUCKDUCKGO_HTML_ENDPOINT"] = search_url

                _prepare_case(root, quality_grade="stable", warning_count=0)
                os.environ["XINYU_AUTONOMOUS_SEARCH"] = "disabled"
                os.environ["XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES"] = "1"
                disabled_result = run_autonomous_search_activation(root, mode="activation_smoke_disabled")

                _prepare_case(root, quality_grade="stable", warning_count=0)
                os.environ["XINYU_AUTONOMOUS_SEARCH"] = "dry_run"
                dry_result = run_autonomous_search_activation(root, mode="activation_smoke_dry_run")

                _prepare_case(root, quality_grade="review_needed", warning_count=2)
                os.environ["XINYU_AUTONOMOUS_SEARCH"] = "enabled"
                blocked_result = run_autonomous_search_activation(root, mode="activation_smoke_quality_blocked")
                provider_blocked_result = run_source_search_provider(
                    root,
                    mode="activation_smoke_provider_blocked",
                    require_activation=True,
                )

                _prepare_case(root, quality_grade="review_needed", warning_count=2)
                _write(
                    root / "memory/context/owner_permission_grants.md",
                    (
                        "- grant_high_autonomy_learning_search: "
                        "approved_budgeted_ai_domain_and_quality_followup_search_through_gates\n"
                    ),
                )
                os.environ["XINYU_AUTONOMOUS_SEARCH"] = "enabled"
                high_override_result = run_autonomous_search_activation(root, mode="activation_smoke_high_override")
                provider_override_result = run_source_search_provider(
                    root,
                    mode="activation_smoke_provider_high_override",
                    require_activation=True,
                )

                _prepare_no_pending_case(root)
                os.environ["XINYU_AUTONOMOUS_SEARCH"] = "enabled"
                no_pending_result = run_autonomous_search_activation(root, mode="activation_smoke_no_pending")

                _prepare_case(root, quality_grade="stable", warning_count=0)
                os.environ["XINYU_AUTONOMOUS_SEARCH"] = "enabled"
                os.environ["XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES"] = "1"
                enabled_result = run_autonomous_search_activation(root, mode="activation_smoke_enabled")
                provider_result = run_source_search_provider(
                    root,
                    mode="activation_smoke_provider",
                    require_activation=True,
                )

                after_restore = _snapshot(root, restore_paths)
                after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
                changed = _changed_files(before, after)
                protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

                print("=== AUTONOMOUS SEARCH ACTIVATION SMOKE ===")
                print("disabled_permission:", disabled_result["activation_permission"])
                print("dry_run_permission:", dry_result["activation_permission"])
                print("quality_block_permission:", blocked_result["activation_permission"])
                print("quality_block_reason:", blocked_result["activation_reason"])
                print("provider_blocked_results:", provider_blocked_result["provider_results"])
                print("provider_blocked_reason:", provider_blocked_result["skipped_reason"])
                print("high_override_permission:", high_override_result["activation_permission"])
                print("high_override_allowed_queries:", high_override_result["allowed_queries"])
                print("provider_override_results:", provider_override_result["provider_results"])
                print("no_pending_permission:", no_pending_result["activation_permission"])
                print("no_pending_reason:", no_pending_result["activation_reason"])
                print("enabled_permission:", enabled_result["activation_permission"])
                print("enabled_allowed_queries:", enabled_result["allowed_queries"])
                print("provider_pending_requests_seen:", provider_result["pending_requests"])
                print("provider_results:", provider_result["provider_results"])
                print("protected_changed:", ", ".join(protected_changed) or "none")
                print("search_url:", search_url)
                print("fixture_url:", fixture_url)
                print("=== MUTATION SUMMARY ===")
                print(f"tracked_files: {len(TRACKED_FILES)}")
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
                if old_provider is None:
                    os.environ.pop("XINYU_SOURCE_SEARCH_PROVIDER", None)
                else:
                    os.environ["XINYU_SOURCE_SEARCH_PROVIDER"] = old_provider
                if old_endpoint is None:
                    os.environ.pop("XINYU_DUCKDUCKGO_HTML_ENDPOINT", None)
                else:
                    os.environ["XINYU_DUCKDUCKGO_HTML_ENDPOINT"] = old_endpoint
                if old_autonomous is None:
                    os.environ.pop("XINYU_AUTONOMOUS_SEARCH", None)
                else:
                    os.environ["XINYU_AUTONOMOUS_SEARCH"] = old_autonomous
                if old_max is None:
                    os.environ.pop("XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES", None)
                else:
                    os.environ["XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES"] = old_max
                if args.restore_after:
                    _restore_snapshot(root, before_restore)
                    print("=== RESTORE ===")
                    print("tracked and volatile runtime files restored")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    if args.require_activation and (
        disabled_result["activation_permission"] != "disabled"
        or dry_result["activation_permission"] != "observe_only"
        or blocked_result["activation_permission"] != "blocked"
        or int(provider_blocked_result["provider_results"]) != 0
        or not str(provider_blocked_result["skipped_reason"]).startswith("activation_not_allowed")
        or high_override_result["activation_permission"] != "provider_allowed"
        or int(high_override_result["allowed_queries"]) != 1
        or int(provider_override_result["provider_results"]) <= 0
        or no_pending_result["activation_permission"] != "blocked"
        or no_pending_result["activation_reason"] != "no_pending_url_requests"
        or enabled_result["activation_permission"] != "provider_allowed"
        or int(enabled_result["allowed_queries"]) != 1
        or int(provider_result["pending_requests"]) != 1
        or int(provider_result["provider_results"]) <= 0
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
