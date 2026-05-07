from __future__ import annotations

import tempfile
from pathlib import Path

from xinyu_dialogue_observation_compile import compile_reviews


def _snapshot_memory(root: Path) -> set[str]:
    memory = root / "memory"
    if not memory.exists():
        return set()
    return {str(path.relative_to(root)) for path in memory.rglob("*") if path.is_file()}


def run_smoke() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-dialogue-observation-compile-") as tmp:
        root = Path(tmp)
        curated = root / "curated"
        curated.mkdir(parents=True)
        (curated / "sample_review_batch_001.md").write_text(
            """# Sample Review Batch

## Candidate 1: dlgobs-yes

- source_file: sample.txt
- line_index: 7
- speaker: A
- signals: remembered_detail, repair
- xinyu_fit_score: 10
- reject_risks:

```text
line: raw source text must not be copied to drafts
```

keep: [x] yes  [ ] no
scene_summary:
relationship_state:
trigger:
observed_response_strategy:
relationship_effect:
xinyu_rule:
xinyu_do_not_learn:

## Candidate 2: dlgobs-no

- source_file: sample.txt
- line_index: 8
- speaker: B
- signals: low_mood
- xinyu_fit_score: 4
- reject_risks: role_lore

```text
line: rejected raw source text
```

keep: [ ] yes  [x] no
scene_summary:
relationship_state:
trigger:
observed_response_strategy:
relationship_effect:
xinyu_rule:
xinyu_do_not_learn:
""",
            encoding="utf-8",
        )
        before_memory = _snapshot_memory(root)
        result = compile_reviews(curated)
        after_memory = _snapshot_memory(root)
        draft = (curated / "accepted_rule_card_drafts.md").read_text(encoding="utf-8")
        index = (curated / "sample_accepted_index.md").read_text(encoding="utf-8")
        summary = (curated / "dialogue_observation_flow_summary.md").read_text(encoding="utf-8")

        if result.get("accepted_count") != 1:
            failures.append("compiler should keep exactly one accepted candidate")
        if "dlgobs-yes" not in draft or "dlgobs-yes" not in index:
            failures.append("accepted candidate missing from output")
        if "dlgobs-no" in draft or "dlgobs-no" in index:
            failures.append("rejected candidate leaked into accepted output")
        if "raw source text must not be copied" in draft:
            failures.append("draft should not copy raw source text")
        if "stable_profile_write blocked" not in draft:
            failures.append("draft boundary marker missing")
        if "| sample_review_batch_001.md | 2 | 1 | 1 | 0 | 0 | sample_accepted_index.md |" not in summary:
            failures.append("summary counts are wrong")
        if before_memory != after_memory:
            failures.append("compiler must not write memory")

    return failures


def main_smoke() -> int:
    failures = run_smoke()
    if failures:
        print("xinyu_dialogue_observation_compile_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS xinyu_dialogue_observation_compile_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_smoke())
