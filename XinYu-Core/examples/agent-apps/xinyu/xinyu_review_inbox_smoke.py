from __future__ import annotations

import json
import tempfile
from pathlib import Path

from xinyu_review_inbox import handle_review_inbox_command, run_review_inbox_maintenance


VOICE_STATE = """---
title: Voice Review
memory_type: voice_profile_review_state
---

# Voice Review

## Gate Summary
- review_status: pending_owner_review

## Candidates

### voice-profile-a
- candidate_id: voice-profile-a
- cluster: a
- owner_review_status: pending
- accepted: no
- rejected: no
- proposed_profile_pressure: pressure a
- owner_correction_examples: example a

### voice-profile-b
- candidate_id: voice-profile-b
- cluster: b
- owner_review_status: pending
- accepted: no
- rejected: no
- proposed_profile_pressure: pressure b
- owner_correction_examples: example b
"""


LEARNING_STATE = """---
title: Learning Quality State
memory_type: learning_quality_state
---

# Learning Quality State

## Last Evaluation
- quality_grade: review_needed
- warning_count: 1

## Warnings
- repeated_question_host: severity=review; target=q-1@example.com; detail=2/2 learned entries share one host
"""


def _write_fixture(root: Path) -> None:
    (root / "memory/self").mkdir(parents=True, exist_ok=True)
    (root / "memory/knowledge").mkdir(parents=True, exist_ok=True)
    (root / "memory/self/voice_profile_review_state.md").write_text(VOICE_STATE, encoding="utf-8")
    (root / "memory/knowledge/learning_quality_state.md").write_text(LEARNING_STATE, encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="xinyu-review-inbox-") as tmp:
        root = Path(tmp)
        _write_fixture(root)

        first = run_review_inbox_maintenance(root, owner_user_id="42", max_items=3)
        assert first["pending_count"] == 3
        assert first["queued"] is False
        assert not (root / "memory/context/qq_outbox_queue.json").exists()
        cursor = _read_json(root / "memory/context/review_inbox_cursor.json")
        assert cursor["items"][0]["source_kind"] == "voice"
        assert cursor["items"][1]["source_kind"] == "learning"
        assert cursor["items"][2]["source_kind"] == "voice"

        visible = run_review_inbox_maintenance(
            root,
            owner_user_id="42",
            max_items=3,
            enqueue=True,
            reason="owner_review_request",
        )
        assert visible["queued"] is True
        queue = _read_json(root / "memory/context/qq_outbox_queue.json")
        assert queue["items"][0]["source"] == "review_inbox"
        assert "[Review Inbox]" not in queue["items"][0]["message"]
        assert "batch=" not in queue["items"][0]["message"]
        assert "!ok all" in queue["items"][0]["message"]

        mod_many = handle_review_inbox_command(
            root,
            {
                "command": "mod",
                "indices": ["1", "2"],
                "mod_text": "rewrite",
                "user_id": "42",
            },
        )
        assert mod_many["accepted"] is False
        assert "only accepts one index" in mod_many["reply"]

        handled = handle_review_inbox_command(
            root,
            {
                "command": "ok",
                "indices": ["all"],
                "user_id": "42",
                "message_id": "m-1",
            },
        )
        assert handled["accepted"] is True
        assert handled["processed_count"] == 3
        assert handled["stale_count"] == 0
        decisions = _read_json(root / "memory/context/review_inbox_decisions.json")
        assert len(decisions["decisions"]) == 3
        assert {item["decision"] for item in decisions["decisions"]} == {"accepted"}

    with tempfile.TemporaryDirectory(prefix="xinyu-review-inbox-stale-") as tmp:
        root = Path(tmp)
        _write_fixture(root)
        run_review_inbox_maintenance(root, owner_user_id="42", max_items=2)
        learning_path = root / "memory/knowledge/learning_quality_state.md"
        learning_path.write_text(LEARNING_STATE.replace("2/2 learned entries", "3/3 learned entries"), encoding="utf-8")
        partial = handle_review_inbox_command(
            root,
            {
                "command": "rej",
                "indices": ["all"],
                "user_id": "42",
                "message_id": "m-2",
            },
        )
        assert partial["accepted"] is True
        assert partial["processed_count"] == 1
        assert partial["stale_count"] == 1
        decisions = _read_json(root / "memory/context/review_inbox_decisions.json")
        assert len(decisions["decisions"]) == 1
        assert decisions["decisions"][0]["decision"] == "rejected"

    print("xinyu_review_inbox_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
