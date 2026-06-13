from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import xinyu_bridge_proactive_context


def _write_dispatch(root, *, status: str = "claimed", message: str = "proactive hello", claimed_at: str = "") -> None:
    path = root / "memory/context/proactive_qq_dispatch_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"- last_claim_status: {status}",
                f"- last_claimed_message: {message}",
                f"- last_claimed_at: {claimed_at or datetime.now().astimezone().isoformat(timespec='seconds')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_sync_recent_proactive_to_dialogue_tail_skips_non_owner_or_invalid_dispatch(tmp_path) -> None:
    session = SimpleNamespace(key="session-1", dialogue_tail=[])
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=4,
        dialogue_persisted_tail_entries=5,
        _owner_private_payload_matches=lambda payload: False,
    )

    assert xinyu_bridge_proactive_context.sync_recent_proactive_to_dialogue_tail(runtime, session, {}) is False
    assert session.dialogue_tail == []

    runtime._owner_private_payload_matches = lambda payload: True
    _write_dispatch(tmp_path, status="queued")

    assert xinyu_bridge_proactive_context.sync_recent_proactive_to_dialogue_tail(runtime, session, {}) is False
    assert session.dialogue_tail == []


def test_sync_recent_proactive_to_dialogue_tail_appends_trims_sorts_and_saves(monkeypatch, tmp_path) -> None:
    saved: list[tuple[object, str, list[dict[str, str]], int]] = []

    def fake_save(root, session_key, tail, *, max_entries):
        saved.append((root, session_key, list(tail), max_entries))
        return True

    monkeypatch.setattr(xinyu_bridge_proactive_context, "save_dialogue_tail", fake_save)
    claimed_at = (datetime.now().astimezone() - timedelta(minutes=5)).isoformat(timespec="seconds")
    _write_dispatch(tmp_path, status="sent", message="proactive hello", claimed_at=claimed_at)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=2,
        dialogue_persisted_tail_entries=6,
        _owner_private_payload_matches=lambda payload: True,
    )
    session = SimpleNamespace(
        key="session-1",
        dialogue_tail=[
            {"role": "user", "content": "old", "recorded_at": "2026-01-01T00:00:00+08:00"},
            {"role": "assistant", "content": "newer", "recorded_at": "2099-01-01T00:00:00+08:00"},
        ],
    )

    assert xinyu_bridge_proactive_context.sync_recent_proactive_to_dialogue_tail(runtime, session, {}) is True

    assert [item["content"] for item in session.dialogue_tail] == ["proactive hello", "newer"]
    assert session.dialogue_tail[0] == {
        "role": "assistant",
        "content": "proactive hello",
        "recorded_at": claimed_at,
    }
    assert saved == [(tmp_path, "session-1", session.dialogue_tail, 6)]


def test_sync_recent_proactive_to_dialogue_tail_dedupes_and_skips_stale_claims(tmp_path) -> None:
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=4,
        dialogue_persisted_tail_entries=6,
        _owner_private_payload_matches=lambda payload: True,
    )
    session = SimpleNamespace(
        key="session-1",
        dialogue_tail=[{"role": "assistant", "content": "proactive hello", "recorded_at": "old"}],
    )
    _write_dispatch(tmp_path, message="proactive hello")

    assert xinyu_bridge_proactive_context.sync_recent_proactive_to_dialogue_tail(runtime, session, {}) is False
    assert len(session.dialogue_tail) == 1

    stale_at = (datetime.now().astimezone() - timedelta(hours=7)).isoformat(timespec="seconds")
    _write_dispatch(tmp_path, message="another message", claimed_at=stale_at)

    assert xinyu_bridge_proactive_context.sync_recent_proactive_to_dialogue_tail(runtime, session, {}) is False
    assert len(session.dialogue_tail) == 1


def test_sync_recent_proactive_to_dialogue_tail_swallows_save_errors(monkeypatch, tmp_path) -> None:
    def failing_save(*args, **kwargs):
        raise OSError("save failed")

    monkeypatch.setattr(xinyu_bridge_proactive_context, "save_dialogue_tail", failing_save)
    _write_dispatch(tmp_path, message="proactive hello")
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=4,
        dialogue_persisted_tail_entries=6,
        _owner_private_payload_matches=lambda payload: True,
    )
    session = SimpleNamespace(key="session-1", dialogue_tail=[])

    assert xinyu_bridge_proactive_context.sync_recent_proactive_to_dialogue_tail(runtime, session, {}) is True
    assert session.dialogue_tail[0]["content"] == "proactive hello"


def test_mark_proactive_owner_reply_updates_request_and_records_lifecycle(monkeypatch, tmp_path) -> None:
    lifecycle_calls: list[dict[str, object]] = []
    refresh_calls: list[dict[str, object]] = []

    def fake_append_lifecycle(root, **kwargs):
        lifecycle_calls.append({"root": root, **kwargs})

    monkeypatch.setattr(xinyu_bridge_proactive_context, "append_proactive_lifecycle_event", fake_append_lifecycle)
    request_path = tmp_path / "memory/context/proactive_request_state.md"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        "\n".join(
            [
                "---",
                "updated_at: 2026-06-06T00:00:00+08:00",
                "---",
                "- request_id: req-1",
                "- status: sent",
                "- delivery_level: queue_owner_private",
                "- request_answer_state: sent_waiting_owner_reply",
                "- last_ack_status: sent",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    dispatch_path = tmp_path / "memory/context/proactive_qq_dispatch_state.md"
    dispatch_path.write_text(
        "\n".join(
            [
                "- proactive_request_id: req-1",
                "- last_claim_status: sent",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _owner_private_payload_matches=lambda payload: True,
        _refresh_initiative_spine_after_proactive_feedback=lambda **kwargs: refresh_calls.append(kwargs),
    )

    assert (
        xinyu_bridge_proactive_context.mark_proactive_owner_reply(
            runtime,
            {"metadata": {"is_owner_user": True}},
            text="owner reply",
            reply="xinyu reply",
        )
        is True
    )

    updated = request_path.read_text(encoding="utf-8")
    assert "- status: answered" in updated
    assert "- request_answer_state: owner_replied" in updated
    assert "## Last Owner Reply To Proactive" in updated
    assert "- owner_reply_preview: preview_redacted" in updated
    assert "- owner_reply_ref: sha256:" in updated
    assert "- xinyu_reply_ref: sha256:" in updated
    assert "owner reply" not in updated
    assert "xinyu reply" not in updated
    assert lifecycle_calls[0]["root"] == tmp_path
    assert lifecycle_calls[0]["event_kind"] == "proactive_owner_reply_closed"
    assert lifecycle_calls[0]["request_id"] == "req-1"
    assert refresh_calls[0]["trigger"] == "owner_reply_to_proactive"


def test_mark_proactive_owner_reply_keeps_dismissal_preview(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(xinyu_bridge_proactive_context, "append_proactive_lifecycle_event", lambda *args, **kwargs: None)
    request_path = tmp_path / "memory/context/proactive_request_state.md"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        "\n".join(
            [
                "- request_id: req-dismiss",
                "- status: sent",
                "- delivery_level: queue_owner_private",
                "- request_answer_state: sent_waiting_owner_reply",
                "- last_ack_status: sent",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    dispatch_path = tmp_path / "memory/context/proactive_qq_dispatch_state.md"
    dispatch_path.write_text(
        "\n".join(
            [
                "- proactive_request_id: req-dismiss",
                "- last_claim_status: sent",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _owner_private_payload_matches=lambda payload: True,
        _refresh_initiative_spine_after_proactive_feedback=lambda **kwargs: None,
    )

    assert (
        xinyu_bridge_proactive_context.mark_proactive_owner_reply(
            runtime,
            {"metadata": {"is_owner_user": True}},
            text="stop bringing it up please",
            reply="ok",
        )
        is True
    )

    updated = request_path.read_text(encoding="utf-8")
    assert "- owner_reply_preview: stop bringing it up please" in updated


def test_refresh_initiative_spine_after_proactive_feedback_delegates(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_spine(root, *, checked_at: str, trigger: str) -> dict[str, object]:
        calls.append({"root": root, "checked_at": checked_at, "trigger": trigger})
        return {"accepted": True, "trigger": trigger}

    monkeypatch.setattr(xinyu_bridge_proactive_context, "run_initiative_spine", fake_run_spine)
    runtime = SimpleNamespace(xinyu_dir=tmp_path)

    result = xinyu_bridge_proactive_context.refresh_initiative_spine_after_proactive_feedback(
        runtime,
        trigger="owner_reply_to_proactive",
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert result == {"accepted": True, "trigger": "owner_reply_to_proactive"}
    assert calls == [
        {
            "root": tmp_path,
            "checked_at": "2026-06-06T01:00:00+08:00",
            "trigger": "owner_reply_to_proactive",
        }
    ]


def test_refresh_initiative_spine_after_proactive_feedback_reports_error(monkeypatch, tmp_path) -> None:
    def fake_run_spine(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_proactive_context, "run_initiative_spine", fake_run_spine)
    runtime = SimpleNamespace(xinyu_dir=tmp_path)

    result = xinyu_bridge_proactive_context.refresh_initiative_spine_after_proactive_feedback(
        runtime,
        trigger="owner_reply_to_proactive",
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert result == {"accepted": False, "notes": ["initiative_spine_feedback_error:RuntimeError"]}


def test_mark_proactive_owner_reply_skips_non_owner_or_mismatched_dispatch(tmp_path) -> None:
    request_path = tmp_path / "memory/context/proactive_request_state.md"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        "\n".join(
            [
                "- request_id: req-1",
                "- status: sent",
                "- delivery_level: queue_owner_private",
                "- request_answer_state: pending",
                "- last_ack_status: none",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "memory/context/proactive_qq_dispatch_state.md").write_text(
        "\n".join(
            [
                "- proactive_request_id: other",
                "- last_claim_status: sent",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _owner_private_payload_matches=lambda payload: False,
        _refresh_initiative_spine_after_proactive_feedback=lambda **kwargs: None,
    )

    assert xinyu_bridge_proactive_context.mark_proactive_owner_reply(runtime, {}, text="owner", reply="xinyu") is False

    runtime._owner_private_payload_matches = lambda payload: True

    assert xinyu_bridge_proactive_context.mark_proactive_owner_reply(runtime, {}, text="owner", reply="xinyu") is False
