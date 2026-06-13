from __future__ import annotations

import json
from pathlib import Path

from xinyu_self_code_approval import PROACTIVE_REQUEST_REL
from xinyu_self_code_approval import STATE_REL
from xinyu_self_code_approval import TRACE_REL
from xinyu_self_code_approval import active_self_code_approval_request
from xinyu_self_code_approval import build_self_code_approval_prompt_block
from xinyu_self_code_approval import consume_self_code_approval
from xinyu_self_code_approval import create_direct_self_code_approval
from xinyu_self_code_approval import mark_self_code_execution_scheduled


OWNER_PRIVATE = {"message_type": "private", "user_id": "owner", "metadata": {"is_owner_user": True}}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _seed_pending_request(root: Path) -> None:
    _write(
        root / PROACTIVE_REQUEST_REL,
        """# Proactive Request State

## Current Request
- request_id: proreq-self-code-test
- status: ready
- kind: permission
- focus_kind: self_code_approval
- focus_label: self-code-runtime-fix
- evidence_label: runtime self-code patch request
- evidence_hash: sha256:abcdef1234567890
- concrete_question: approve one bounded patch?
- requested_action: owner_permission
- after_owner_replies: execute one-time ticket
""",
    )


def test_self_code_approval_consumes_pending_owner_private_request(tmp_path: Path) -> None:
    _seed_pending_request(tmp_path)

    active = active_self_code_approval_request(tmp_path)
    result = consume_self_code_approval(
        tmp_path,
        OWNER_PRIVATE,
        owner_text="approved, go ahead",
        session_key="qq:private:owner",
        observed_at="2026-06-01T10:00:00+08:00",
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    trace = json.loads((tmp_path / TRACE_REL).read_text(encoding="utf-8").splitlines()[0])

    assert active["request_id"] == "proreq-self-code-test"
    assert result["approved"] is True
    assert "status: approved_once" in state
    assert "require_prior_qq_application: true" in state
    assert trace["decision"] == "approved"
    assert "one-time bounded approval" in result["task_text"]


def test_direct_self_code_approval_and_execution_schedule_update_state(tmp_path: Path) -> None:
    result = create_direct_self_code_approval(
        tmp_path,
        OWNER_PRIVATE,
        owner_text="please modify your own code",
        session_key="qq:private:owner",
        observed_at="2026-06-01T10:00:00+08:00",
    )

    mark_self_code_execution_scheduled(
        tmp_path,
        approval_id=result["approval_id"],
        job_id="codex-job-1",
        watchdog_snapshot_id="snapshot-1",
        watchdog_manifest_path="runtime/self_code_watchdog/snapshots/snapshot-1/manifest.json",
        observed_at="2026-06-01T10:01:00+08:00",
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    rows = [json.loads(line) for line in (tmp_path / TRACE_REL).read_text(encoding="utf-8").splitlines()]
    prompt = build_self_code_approval_prompt_block(tmp_path)

    assert result["approved"] is True
    assert "status: executing" in state
    assert "approval_route: direct_owner_private_qq_request" in state
    assert "execution_job_id: codex-job-1" in state
    assert rows[-1]["event_kind"] == "execution_scheduled"
    assert "watchdog_snapshot_id: snapshot-1" in prompt
