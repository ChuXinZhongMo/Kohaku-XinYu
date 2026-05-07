from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from xinyu_research_loop_dry_run import run_research_loop_dry_run


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-research-dry-run-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/knowledge"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "memory/knowledge/source_requests.md", target / "source_requests.md")
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
