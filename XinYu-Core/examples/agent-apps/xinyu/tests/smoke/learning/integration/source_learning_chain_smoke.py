from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

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

CHAIN_TRACKED_FILES = [
    "memory/context/active_questions.md",
    "memory/knowledge/source_integration_gate_state.md",
    "memory/knowledge/source_gate_state.md",
    "memory/knowledge/source_requests.md",
    "memory/knowledge/source_request_planner_state.md",
    "memory/knowledge/source_search_results.md",
    "memory/knowledge/source_search_resolver_state.md",
    "memory/knowledge/autonomous_search_activation_state.md",
    "memory/knowledge/source_search_provider_state.md",
    "memory/knowledge/search_result_gate_state.md",
    "memory/knowledge/source_registry.md",
    "memory/knowledge/source_materials.md",
    "memory/knowledge/source_comparison_state.md",
    "memory/knowledge/outward_source_state.md",
    "memory/knowledge/learner_integration_state.md",
    "memory/knowledge/learning_quality_state.md",
    "memory/knowledge/general.md",
    "memory/knowledge/source_notes.md",
    "memory/context/question_states.md",
    "memory/context/exploration_queue.md",
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


def _prepare_source_chain_case(root: Path) -> None:
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
- mode: source_learning_chain_gate

## Gate Decision
- integration_permission: prepare_only
- gate_reason: smoke_source_chain_ready
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
- mode: source_learning_chain_gate

## Current Candidates
- q-903: human-relationship
""",
    )
    _write(
        root / "memory/knowledge/source_requests.md",
        """---
title: Source Requests Chain Smoke
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
- reason: chain smoke baseline
""",
    )
    _write(
        root / "memory/knowledge/source_search_results.md",
        """---
title: Source Search Results Chain Smoke
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
        root / "memory/knowledge/source_materials.md",
        """---
title: Source Materials Chain Smoke
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
    _write(
        root / "memory/knowledge/general.md",
        """---
title: General Knowledge Chain Smoke
memory_type: knowledge_general
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 71
impact_score: 56
confidence_score: 100
status: active
tags: [knowledge, general, smoke]
---

# General Knowledge

## Current State
- Chain smoke baseline keeps live learned material ids out of this isolated run.
""",
    )
    _write(
        root / "memory/knowledge/learning_quality_state.md",
        """---
title: Learning Quality Chain Smoke
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
- mode: source_learning_chain_baseline
- quality_grade: stable
- learned_entries: 0
- source_materials: 0
- warning_count: 0
""",
    )


def _prepare_question_path(root: Path) -> None:
    _write(
        root / "memory/context/question_states.md",
        """---
title: Question States Chain Smoke
memory_type: question_states
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 84
impact_score: 83
confidence_score: 100
status: active
tags: [questions, states, smoke]
---

# Current Question States

## Current Question Entries
### q-903
- state: pending_exploration
- reason: chain smoke waits for request planning, outward source, and learner integration
""",
    )
    _write(
        root / "memory/context/exploration_queue.md",
        """---
title: Exploration Queue Chain Smoke
memory_type: exploration_queue
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-24T00:00:00+08:00
updated_at: 2026-04-24T00:00:00+08:00
last_confirmed_at: 2026-04-24T00:00:00+08:00
importance_score: 82
impact_score: 80
confidence_score: 100
status: active
tags: [exploration, queue, smoke]
---

# Exploration Queue

## item-2026-04-24-903
- question_id: q-903
- status: pending
- exploration_stage: source_request_planner
- target: human-relationship
- reason: chain smoke validates request planning to source fetch to learner integration
- next_action: controlled source request, outward source, then learner integration
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate request planning to outward source to learner integration chain with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-chain", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = ROOT
    _ensure_custom_path(root)

    from learner_integration_engine import run_learner_integration
    from learning_quality_engine import run_learning_quality
    from autonomous_search_activation_engine import run_autonomous_search_activation
    from outward_source_engine import run_outward_source
    from search_result_gate_engine import run_search_result_gate
    from source_comparison_engine import run_source_comparison
    from source_integration_gate_engine import run_source_integration_gate
    from source_request_planner_engine import run_source_request_planner
    from source_reliability_engine import run_source_reliability
    from source_search_provider_engine import run_source_search_provider

    restore_paths = _discover_restore_files(root, CHAIN_TRACKED_FILES) if args.restore_after else CHAIN_TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in CHAIN_TRACKED_FILES}
    reliability_result = {"candidate_count": 0, "pairs": []}
    integration_result = {"integration_permission": "unknown", "ready_candidates": 0}
    request_result = {"ready_requests": 0, "planned_requests": 0, "pending_url_requests": 0}
    activation_result = {"activation_permission": "unknown", "allowed_queries": 0}
    provider_result = {"provider_results": 0}
    gate_result = {"accepted_results": 0, "updated_requests": 0}
    outward_result = {"staged_materials": 0, "material_ids": []}
    comparison_result = {"ready_materials": 0, "compared_groups": 0, "conflict_materials": 0}
    learner_result = {"integrated_materials": 0, "integrated_ids": []}
    quality_result = {"learned_entries": 0, "quality_grade": "unknown", "warning_count": 0}
    old_request_env = os.environ.get("XINYU_SOURCE_REQUEST_URLS")
    old_search_env = os.environ.get("XINYU_SOURCE_SEARCH_RESULTS")
    old_provider_env = os.environ.get("XINYU_SOURCE_SEARCH_PROVIDER")
    old_provider_endpoint = os.environ.get("XINYU_DUCKDUCKGO_HTML_ENDPOINT")
    old_autonomous_env = os.environ.get("XINYU_AUTONOMOUS_SEARCH")
    old_autonomous_max = os.environ.get("XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES")

    with tempfile.TemporaryDirectory(prefix="xinyu-source-chain-") as tmp:
        fixture_dir = Path(tmp)
        (fixture_dir / "xinyu_fixture.html").write_text(
            """<!doctype html>
<html><head><title>Source Chain Fixture</title><meta name="description" content="Relationship memory can preserve closeness, distance, boundary, return context, and earlier caution together."></head>
<body>
<article>
<h1>Closeness, distance, and memory</h1>
<p>A relationship can carry affection and disappointment at the same time. Remembering a boundary as context helps future responses avoid both pursuit and cold withdrawal.</p>
<p>When someone returns after asking for distance, the earlier distance should remain part of the relational record without being treated as permanent rejection.</p>
</article>
</body></html>
""",
            encoding="utf-8",
        )
        (fixture_dir / "xinyu_fixture_second.html").write_text(
            """<!doctype html>
<html><head><title>Source Chain Fixture Second</title><meta name="description" content="Relationship memory and return can keep closeness, distance, boundary, and caution visible while trust returns gradually."></head>
<body>
<article>
<h1>Relationship memory and return</h1>
<p>Return after distance works better when the earlier boundary remains visible as context instead of being erased.</p>
<p>Closeness can resume gradually while the relationship still remembers what caused caution.</p>
</article>
</body></html>
""",
            encoding="utf-8",
        )
        server, thread, url = _start_fixture_server(fixture_dir)
        second_url = url.rsplit("/", 1)[0] + "/xinyu_fixture_second.html"
        search_url = url.rsplit("/", 1)[0] + "/search.html"
        (fixture_dir / "search.html").write_text(
            f"""<!doctype html>
<html><body>
<div class="result">
<a class="result__a" href="{url}">Relationship chain provider fixture</a>
<a class="result__snippet" href="{url}">Controlled provider result for relationship memory and boundaries.</a>
</div>
<div class="result">
<a class="result__a" href="{second_url}">Provider quality fixture</a>
<a class="result__snippet" href="{second_url}">Second controlled provider result for relationship memory and return.</a>
</div>
</body></html>
""",
            encoding="utf-8",
        )
        try:
            try:
                _prepare_source_chain_case(root)
                _prepare_question_path(root)
                os.environ.pop("XINYU_SOURCE_REQUEST_URLS", None)
                os.environ.pop("XINYU_SOURCE_SEARCH_RESULTS", None)
                os.environ["XINYU_AUTONOMOUS_SEARCH"] = "enabled"
                os.environ["XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES"] = "1"
                os.environ["XINYU_SOURCE_SEARCH_PROVIDER"] = "duckduckgo_html"
                os.environ["XINYU_DUCKDUCKGO_HTML_ENDPOINT"] = search_url
                reliability_result = run_source_reliability(root, mode="source_learning_chain_reliability")
                integration_result = run_source_integration_gate(root, mode="source_learning_chain_integration_gate")
                request_result = run_source_request_planner(root, mode="source_learning_chain_request_planner")
                activation_result = run_autonomous_search_activation(root, mode="source_learning_chain_activation")
                provider_result = run_source_search_provider(
                    root,
                    mode="source_learning_chain_search_provider",
                    require_activation=True,
                )
                gate_result = run_search_result_gate(root, mode="source_learning_chain_search_gate")
                outward_result = run_outward_source(root, mode="source_learning_chain_outward")
                comparison_result = run_source_comparison(root, mode="source_learning_chain_comparison")
                learner_result = run_learner_integration(root, mode="source_learning_chain_learner")
                quality_result = run_learning_quality(root, mode="source_learning_chain_quality")

                after_restore = _snapshot(root, restore_paths)
                after = {rel: after_restore.get(rel) for rel in CHAIN_TRACKED_FILES}
                changed = _changed_files(before, after)
                protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))

                print("=== SOURCE LEARNING CHAIN SMOKE ===")
                print("source_reliability_candidates:", reliability_result["candidate_count"])
                print("source_integration_permission:", integration_result["integration_permission"])
                print("source_integration_ready_candidates:", integration_result["ready_candidates"])
                print("request_permission:", request_result["permission"])
                print("request_planned_requests:", request_result["planned_requests"])
                print("request_ready_requests_before_search:", request_result["ready_requests"])
                print("request_pending_url_requests:", request_result["pending_url_requests"])
                print("autonomous_search_permission:", activation_result["activation_permission"])
                print("autonomous_search_reason:", activation_result["activation_reason"])
                print("autonomous_search_allowed_queries:", activation_result["allowed_queries"])
                print("search_provider_results:", provider_result["provider_results"])
                print("search_accepted_results:", gate_result["accepted_results"])
                print("search_updated_requests:", gate_result["updated_requests"])
                print("outward_permission:", outward_result["permission"])
                print("outward_fetched_sources:", outward_result["fetched_sources"])
                print("outward_staged_materials:", outward_result["staged_materials"])
                print("outward_material_ids:", ", ".join(outward_result["material_ids"]) or "none")
                print("source_comparison_ready_materials:", comparison_result["ready_materials"])
                print("source_comparison_groups:", comparison_result["compared_groups"])
                print("source_comparison_conflicts:", comparison_result["conflict_materials"])
                print("learner_permission:", learner_result["permission"])
                print("learner_ready_materials:", learner_result["ready_materials"])
                print("learner_integrated_materials:", learner_result["integrated_materials"])
                print("learner_integrated_ids:", ", ".join(learner_result["integrated_ids"]) or "none")
                print("learning_quality_grade:", quality_result["quality_grade"])
                print("learning_quality_learned_entries:", quality_result["learned_entries"])
                print("learning_quality_warnings:", quality_result["warning_count"])
                print("protected_changed:", ", ".join(protected_changed) or "none")
                print("fixture_url:", url)
                print("=== MUTATION SUMMARY ===")
                print(f"tracked_files: {len(CHAIN_TRACKED_FILES)}")
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
                if old_request_env is None:
                    os.environ.pop("XINYU_SOURCE_REQUEST_URLS", None)
                else:
                    os.environ["XINYU_SOURCE_REQUEST_URLS"] = old_request_env
                if old_search_env is None:
                    os.environ.pop("XINYU_SOURCE_SEARCH_RESULTS", None)
                else:
                    os.environ["XINYU_SOURCE_SEARCH_RESULTS"] = old_search_env
                if old_provider_env is None:
                    os.environ.pop("XINYU_SOURCE_SEARCH_PROVIDER", None)
                else:
                    os.environ["XINYU_SOURCE_SEARCH_PROVIDER"] = old_provider_env
                if old_provider_endpoint is None:
                    os.environ.pop("XINYU_DUCKDUCKGO_HTML_ENDPOINT", None)
                else:
                    os.environ["XINYU_DUCKDUCKGO_HTML_ENDPOINT"] = old_provider_endpoint
                if old_autonomous_env is None:
                    os.environ.pop("XINYU_AUTONOMOUS_SEARCH", None)
                else:
                    os.environ["XINYU_AUTONOMOUS_SEARCH"] = old_autonomous_env
                if old_autonomous_max is None:
                    os.environ.pop("XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES", None)
                else:
                    os.environ["XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES"] = old_autonomous_max
                if args.restore_after:
                    _restore_snapshot(root, before_restore)
                    print("=== RESTORE ===")
                    print("tracked and volatile runtime files restored")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    if args.require_chain and (
        int(request_result["pending_url_requests"]) <= 0
        or int(reliability_result["candidate_count"]) <= 0
        or integration_result["integration_permission"] != "prepare_only"
        or int(integration_result["ready_candidates"]) <= 0
        or activation_result["activation_permission"] != "provider_allowed"
        or int(activation_result["allowed_queries"]) <= 0
        or int(provider_result["provider_results"]) <= 0
        or int(gate_result["updated_requests"]) <= 0
        or int(outward_result["staged_materials"]) <= 0
        or int(comparison_result["compared_groups"]) <= 0
        or int(comparison_result["conflict_materials"]) != 0
        or int(learner_result["integrated_materials"]) <= 0
        or int(quality_result["learned_entries"]) <= 0
    ):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
