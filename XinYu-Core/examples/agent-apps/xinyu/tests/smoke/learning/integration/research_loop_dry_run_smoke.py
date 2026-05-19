from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from ops.probes.xinyu_research_loop_dry_run import run_research_loop_dry_run


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _seed_source_requests(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_requests.md",
        """# Source Requests

## request-smoke-ai-domain
- question_id: q-006
- target: ai-self-understanding
- query: long-term agent memory context tool use alignment safety reliable source
- url: http://127.0.0.1/smoke-ai-domain.html
- status: ready
- source_policy: controlled_fetch_only
- planned_at: 2026-04-26T17:20:00+08:00
- reason: research_loop_dry_run_smoke_fixture
""",
    )


def main() -> int:
    root = ROOT
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-research-dry-run-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/knowledge"
        _seed_source_requests(temp_root)
        result = run_research_loop_dry_run(
            temp_root,
            evaluated_at="2026-04-26T17:25:00+08:00",
            mode="smoke_research_loop_dry_run",
        )
        if int(result["ai_domain_ready_requests"]) < 1:
            failures.append("expected at least one ai-domain ready request")
        state = (target / "research_loop_dry_run_state.md").read_text(encoding="utf-8")
        for marker in (
            "planning_ai_domain_source_work_without_live_search",
            "target: ai-self-understanding",
            "does not search the web by itself",
            "owner_visible_review_before_fetch_or_learning",
        ):
            if marker not in state:
                failures.append(f"state missing marker: {marker}")
    if failures:
        print("Research loop dry-run smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Research loop dry-run smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
