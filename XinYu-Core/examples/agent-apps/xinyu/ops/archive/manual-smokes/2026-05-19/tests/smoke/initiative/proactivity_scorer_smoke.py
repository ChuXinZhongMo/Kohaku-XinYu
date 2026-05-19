from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path

from xinyu_proactivity_scorer import STATE_REL, TRACE_REL, run_proactivity_scorer_shadow


CHECKED_AT = "2026-05-07T09:00:00+08:00"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _last_jsonl(path: Path) -> dict[str, object]:
    lines = [line for line in _read(path).splitlines() if line.strip()]
    return json.loads(lines[-1])


def _seed_dream(root: Path) -> None:
    _write(
        root / "memory/dreams/dream_output_state.md",
        """---
title: Dream Output State
updated_at: 2026-05-07T08:55:00+08:00
---

# Dream Output State

## Latest Dream Output
- produced_at: 2026-05-07T08:55:00+08:00
- dream_id: dream-smoke-001
- dream_surface: A hallway folded into a chat window.
- emotional_weight: 80
- reflection_candidate: yes
""",
    )


def _seed_task_failed(root: Path) -> None:
    _write(
        root / "memory/context/runtime_program_awareness.md",
        """# Runtime Program Awareness

## Subsystems
- codex_delegate: status=failed timed_out=true job_id=job-smoke report_label=report.md
""",
    )


def _seed_stale_task_failed(root: Path) -> None:
    _write(
        root / "memory/context/runtime_program_awareness.md",
        """# Runtime Program Awareness

## Subsystems
- codex_delegate: status=failed timed_out=false updated_at=2026-05-06T23:00:00+08:00 job_id=job-stale report_label=report.md
""",
    )


def _seed_task_done(root: Path) -> None:
    _write(
        root / "memory/context/runtime_program_awareness.md",
        """# Runtime Program Awareness

## Subsystems
- codex_delegate: status=finished timed_out=false job_id=job-smoke report_label=report.md
""",
    )


def _seed_qq_outbox_dead(root: Path, *, last_dead_at: str, recent_dead_count: int = 0) -> None:
    _write(
        root / "memory/context/runtime_program_awareness.md",
        f"""# Runtime Program Awareness

## Subsystems
- qq_outbox: last_event=claim_empty queue_items=80 queued_count=0 claimed_count=0 sent_count=79 failed_count=0 dead_count=1 recent_failed_count=0 recent_dead_count={recent_dead_count} last_failed_at=none last_dead_at={last_dead_at}
""",
    )
    _write(
        root / "memory/context/qq_outbox_dispatch_state.md",
        f"""# QQ Outbox Dispatch State

## Queue
- last_event: claim_empty
- queued_count: 0
- claimed_count: 0
- sent_count: 79
- failed_count: 0
- dead_count: 1
- last_failed_at: none
- last_dead_at: {last_dead_at}
""",
    )


def _seed_watched_source_error(root: Path) -> None:
    _write(
        root / "memory/context/runtime_program_awareness.md",
        """# Runtime Program Awareness

## Subsystems
- watched_source: status=error updated_at=2026-05-07T08:50:00+08:00 source_id=linux-do-latest read_only=true scanned_items=0 matched_items=0
""",
    )


def _seed_leaky_request(root: Path) -> None:
    _write(
        root / "memory/context/proactive_request_state.md",
        """---
title: Proactive Request State
status: active
---

# Proactive Request State

## Current Request
- request_id: proreq-leak
- created_at: 2026-05-07T08:50:00+08:00
- status: candidate_only
- kind: clarify
- focus_kind: reflection_queue
- evidence_label: leak smoke
- concrete_question: Codex source_seed dream_weight should be visible?
- requested_action: owner_answer
""",
    )


def _seed_context(root: Path, **fields: object) -> None:
    body = "\n".join(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}" for key, value in fields.items())
    _write(root / "memory/context/proactive_decision_context.md", "# Proactive Decision Context\n\n" + body)


def _assert_no_dispatch(root: Path, failures: list[str]) -> None:
    for rel in (
        "memory/context/qq_outbox_queue.json",
        "memory/context/proactive_qq_dispatch_state.md",
    ):
        if (root / rel).exists():
            failures.append(f"shadow scorer created dispatch file: {rel}")


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-dream-") as tmp:
        root = Path(tmp)
        _seed_dream(root)
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        state = _read(root / STATE_REL)
        if result["source_type"] != "dream_residue":
            failures.append(f"dream candidate should be selected: {result}")
        if result["recommendation"] == "send_now" or result["preferred_channel"] == "qq":
            failures.append(f"dream residue must not recommend QQ send: {result}")
        if "qq_send_disabled_for_dream_v0" not in result["hard_blocks"]:
            failures.append("dream hard block was not recorded")
        if "Latest Shadow Decision" not in state:
            failures.append("decision md state was not written")
        if _last_jsonl(root / TRACE_REL).get("event_kind") != "proactive_decision":
            failures.append("decision jsonl trace was not written")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-task-failed-") as tmp:
        root = Path(tmp)
        _seed_task_failed(root)
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        if result["source_type"] != "task_failed" or result["recommendation"] != "send_now":
            failures.append(f"task_failed should shadow-recommend send_now: {result}")
        if result["preferred_channel"] != "qq" or result["shadow_only"] is not True:
            failures.append(f"task_failed should stay qq-preferred but shadow_only: {result}")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-stale-task-failed-") as tmp:
        root = Path(tmp)
        _seed_stale_task_failed(root)
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        if result["status"] != "no_candidates":
            failures.append(f"stale codex_delegate failure should not trigger task_failed: {result}")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-stale-qq-dead-") as tmp:
        root = Path(tmp)
        _seed_qq_outbox_dead(root, last_dead_at="2026-05-06T23:00:00+08:00")
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        if result["status"] != "no_candidates":
            failures.append(f"stale dead-only QQ outbox should not trigger diagnostics: {result}")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-recent-qq-dead-") as tmp:
        root = Path(tmp)
        _seed_qq_outbox_dead(root, last_dead_at="2026-05-07T08:30:00+08:00", recent_dead_count=1)
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        if result["source_type"] != "task_failed" or result["intent_type"] != "dispatch_failure":
            failures.append(f"recent dead-only QQ outbox should still trigger dispatch diagnosis: {result}")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-watched-source-error-") as tmp:
        root = Path(tmp)
        _seed_watched_source_error(root)
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        if result["status"] != "no_candidates":
            failures.append(f"read-only watched_source error should not trigger proactive send: {result}")
        _assert_no_dispatch(root, failures)

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-screen-locked-") as tmp:
        root = Path(tmp)
        _seed_dream(root)
        _seed_context(root, screen_locked=True)
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        if result["recommendation"] != "hold":
            failures.append(f"screen_locked dream should hold: {result}")
        if "screen_locked_emotion_or_dream_hold" not in result["hard_blocks"]:
            failures.append("screen locked dream hold block missing")

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-unanswered-") as tmp:
        root = Path(tmp)
        _seed_task_failed(root)
        _seed_context(root, unanswered_proactive_count=2)
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        if result["recommendation"] != "hold":
            failures.append(f"unanswered proactive count should hold even high utility: {result}")
        if "unanswered_proactive_limit_hold" not in result["hard_blocks"]:
            failures.append("unanswered proactive hold block missing")

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-leak-") as tmp:
        root = Path(tmp)
        _seed_leaky_request(root)
        result = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        if result["recommendation"] != "drop":
            failures.append(f"internal marker leak should drop: {result}")
        if "owner_visible_text_internal_marker" not in result["hard_blocks"]:
            failures.append("internal marker hard block missing")

    with tempfile.TemporaryDirectory(prefix="xinyu-proscore-repeat-") as tmp:
        root = Path(tmp)
        _seed_task_done(root)
        first = run_proactivity_scorer_shadow(root, checked_at=CHECKED_AT)
        second = run_proactivity_scorer_shadow(root, checked_at="2026-05-07T09:05:00+08:00")
        state = _read(root / STATE_REL)
        trace = _last_jsonl(root / TRACE_REL)
        if first["source_type"] != "task_done" or second["source_type"] != "task_done":
            failures.append(f"task_done repeat setup failed: first={first} second={second}")
        if "repetition_penalty" not in second["reasons_negative"]:
            failures.append(f"repeated candidate should record repetition_penalty: {second}")
        if "- repetition_penalty: 35" not in state:
            failures.append("md state did not expose repetition penalty")
        if trace.get("score", {}).get("repetition_penalty") != 35:
            failures.append("jsonl trace did not expose repetition penalty")
        _assert_no_dispatch(root, failures)

    if failures:
        print("Proactivity scorer smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Proactivity scorer smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
