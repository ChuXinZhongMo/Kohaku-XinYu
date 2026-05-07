from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from outward_source_smoke import _start_fixture_server


ROOT = Path(__file__).resolve().parent
CUSTOM = ROOT / "custom"
if str(CUSTOM) not in sys.path:
    sys.path.insert(0, str(CUSTOM))

from research_handoff_engine import run_research_handoff_loop


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _seed_source_route(root: Path) -> None:
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State

## Research Handoff
- research_needed: true
- route: source_search_provider
- handoff_target: source_search_provider_bridge
- source_request_id: request-2026-05-01-801
- question_id: q-801
- target: ai-self-understanding
- query: large language model memory agents context tool use reliable source
- execution_ceiling: candidate_urls_only_existing_source_gates
- codex_launch_permission: not_needed_source_pipeline_first
- memory_boundary: candidate_results_only_no_stable_memory_without_gates
""",
    )
    _write(
        root / "memory/knowledge/source_integration_gate_state.md",
        """# Source Integration Gate State

## Gate Decision
- integration_permission: prepare_only
- gate_reason: research_handoff_smoke
""",
    )
    _write(
        root / "memory/knowledge/source_requests.md",
        """# Source Requests

## request-2026-05-01-801
- question_id: q-801
- target: ai-self-understanding
- query: large language model memory agents context tool use reliable source
- url: none
- status: pending_url
- source_policy: controlled_fetch_only
- planned_at: 2026-05-01T00:00:00+08:00
- reason: research handoff smoke pending request
""",
    )
    _write(
        root / "memory/knowledge/source_search_results.md",
        """# Source Search Results

## result-none
- request_id: none
- question_id: none
- url: none
- status: hold
""",
    )
    _write(
        root / "memory/knowledge/learning_quality_state.md",
        """# Learning Quality State

## Last Evaluation
- quality_grade: stable
- learned_entries: 0
- warning_count: 0
""",
    )
    _write(
        root / "memory/context/capability_zones_state.md",
        "- autonomous_search_provider: enabled_duckduckgo_html_bounded_ai_domain\n",
    )
    _write(
        root / "memory/context/owner_permission_grants.md",
        "- grant_autonomous_source_collect: approved_bounded_candidate_material_only\n",
    )
    _write(root / "memory/self/core.md", "stable self")
    _write(root / "memory/people/owner.md", "owner")
    _write(root / "memory/relationships/index.md", "relationship")
    _write(root / "memory/emotions/current_state.md", "emotion")


def _seed_codex_route(root: Path) -> None:
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State

## Research Handoff
- research_needed: true
- route: codex_delegate_candidate
- handoff_target: codex_delegate_candidate
- source_request_id: request-2026-05-01-802
- question_id: q-802
- target: local-project-runtime
- query: inspect local runtime failure without rewriting memory
- execution_ceiling: bounded_codex_report_only_no_memory_write
- codex_launch_permission: owner_granted_state_gated
- memory_boundary: candidate_results_only_no_stable_memory_without_gates
""",
    )


def main() -> int:
    failures: list[str] = []
    old_provider = os.environ.get("XINYU_SOURCE_SEARCH_PROVIDER")
    old_endpoint = os.environ.get("XINYU_DUCKDUCKGO_HTML_ENDPOINT")
    old_autonomous = os.environ.get("XINYU_AUTONOMOUS_SEARCH")
    old_max = os.environ.get("XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES")

    with tempfile.TemporaryDirectory(prefix="xinyu-research-handoff-") as tmp:
        fixture_dir = Path(tmp) / "fixture"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "xinyu_fixture.html").write_text(
            "<!doctype html><html><body><h1>Research handoff fixture</h1></body></html>",
            encoding="utf-8",
        )
        server, thread, fixture_url = _start_fixture_server(fixture_dir)
        search_url = fixture_url.rsplit("/", 1)[0] + "/search.html"
        (fixture_dir / "search.html").write_text(
            f"""<!doctype html>
<html><body>
<div class="result">
<a class="result__a" href="{fixture_url}">Research handoff provider fixture</a>
<a class="result__snippet" href="{fixture_url}">Candidate only.</a>
</div>
</body></html>
""",
            encoding="utf-8",
        )
        try:
            try:
                root = Path(tmp) / "root"
                _seed_source_route(root)
                stable_before = _read(root / "memory/self/core.md")
                os.environ.pop("XINYU_SOURCE_SEARCH_PROVIDER", None)
                os.environ["XINYU_DUCKDUCKGO_HTML_ENDPOINT"] = search_url
                os.environ.pop("XINYU_AUTONOMOUS_SEARCH", None)
                os.environ["XINYU_AUTONOMOUS_SEARCH_MAX_QUERIES"] = "1"
                source_result = run_research_handoff_loop(
                    root,
                    evaluated_at="2026-05-01T20:00:00+08:00",
                    execution_level="execute",
                    allow_live_search=True,
                )
                state = _read(root / "memory/context/research_handoff_state.md")
                search_results = _read(root / "memory/knowledge/source_search_results.md")
                if source_result["status"] != "source_provider_completed":
                    failures.append(f"source route did not complete provider search: {source_result}")
                if int(source_result["provider_results"]) <= 0:
                    failures.append("source route did not write provider results")
                for marker in (
                    "candidate_material_only: true",
                    "source_results_must_pass_existing_gates: true",
                    "codex_must_use_visible_xinyu_window: true",
                ):
                    if marker not in state:
                        failures.append(f"research handoff state missing marker: {marker}")
                if fixture_url not in search_results or "- status: candidate" not in search_results:
                    failures.append("provider result was not stored as a candidate search result")
                if _read(root / "memory/self/core.md") != stable_before:
                    failures.append("research handoff modified stable self memory")
                if (root / "memory/context/qq_outbox_queue.json").exists():
                    failures.append("research handoff created QQ outbox")

                codex_root = Path(tmp) / "codex-root"
                _seed_codex_route(codex_root)
                codex_result = run_research_handoff_loop(
                    codex_root,
                    evaluated_at="2026-05-01T20:05:00+08:00",
                    execution_level="execute_codex",
                    allow_codex=False,
                )
                codex_state = _read(codex_root / "memory/context/research_handoff_state.md")
                if codex_result["status"] != "codex_candidate" or codex_result["codex_status"] != "candidate":
                    failures.append(f"codex route should remain candidate without allow_codex: {codex_result}")
                for marker in (
                    "visible_codex_window_required: true",
                    "codex_must_use_visible_xinyu_window: true",
                    "codex_status: candidate",
                ):
                    if marker not in codex_state:
                        failures.append(f"codex candidate state missing marker: {marker}")
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
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    if failures:
        print("Research handoff smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Research handoff smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
