from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_conversation_experience_cases import (
    add_group_scenario_card,
    get_case,
    import_seed_owner_cases,
    initialize_conversation_experience_cases,
    list_cases,
    update_case_review_status,
)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-conversation-experience-cases-") as tmp:
        root = Path(tmp)
        init = initialize_conversation_experience_cases(root)
        if init.get("schema_version") != 1:
            failures.append(f"schema version changed: {init}")
        imported = import_seed_owner_cases(root, seed_path=ROOT / "data/conversation_experience/seed_owner_cases.jsonl")
        if imported.get("imported", 0) < 10 or imported.get("errors"):
            failures.append(f"seed import failed: {imported}")
        if get_case(root, "case-owner-execution-stopped-001") is None:
            failures.append("seed owner execution case missing")

        card = add_group_scenario_card(
            root,
            {
                "case_id": "case-smoke-group-pending",
                "source_ref": "smoke",
                "scenario_tags": ["status_question"],
                "turn_markers": ["status"],
                "user_likely_intent": "The user wants status.",
                "bad_pattern": "Explain internals.",
                "useful_adjustment": "Give status.",
                "boundary": "Advisory only.",
                "confidence": 0.8,
            },
        )
        if card.review_status != "pending":
            failures.append("group card did not default to pending")
        if not update_case_review_status(root, card.case_id, review_status="approved", note="smoke"):
            failures.append("group card approval failed")
        approved_ids = {case.case_id for case in list_cases(root, review_status="approved", limit=20)}
        if card.case_id not in approved_ids:
            failures.append("approved group card missing from approved list")

    if failures:
        print("conversation_experience_cases_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("conversation_experience_cases_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
