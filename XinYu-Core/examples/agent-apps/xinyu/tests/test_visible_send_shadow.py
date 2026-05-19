from __future__ import annotations

import json
from pathlib import Path

from xinyu_qq_visible_send_shadow import (
    STATE_REL,
    TRACE_REL,
    record_visible_send_shadow,
)


def test_visible_send_shadow_records_hashes_without_raw_reply(tmp_path: Path) -> None:
    context = tmp_path / "memory/context/contextual_recall_state.md"
    context.parent.mkdir(parents=True)
    context.write_text(
        "\n".join(
            [
                "- retrieval_pressure: high",
                "- evidence_sufficiency: none",
                "- answer_discipline: answer_current_only_acknowledge_missing_evidence",
            ]
        ),
        encoding="utf-8",
    )
    raw_reply = "The previous conversation definitely said this, so continue from that history."

    result = record_visible_send_shadow(
        tmp_path,
        reply=raw_reply,
        source="direct_chat_pre_send",
        route="chat",
        target_kind="private",
        session_id="qq:private:123456",
        turn_id="turn-sensitive",
        message_id="msg-sensitive",
    )

    trace_text = (tmp_path / TRACE_REL).read_text(encoding="utf-8")
    state_text = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    row = json.loads(trace_text.splitlines()[0])

    assert result["recorded"] is True
    assert row["passed"] is False
    assert row["constraint_id"] == "high_missing_evidence"
    assert row["flags"]["unsupported_history_claim"] is True
    assert row["reply_hash"].startswith("sha256:")
    assert "previous conversation definitely" not in trace_text
    assert "previous conversation definitely" not in state_text
    assert "123456" not in trace_text
    assert "turn-sensitive" not in trace_text
    assert "msg-sensitive" not in trace_text
    assert "- raw_reply_saved: false" in state_text
    assert "- send_blocked: false" in state_text


def test_visible_send_shadow_defaults_to_current_message_guard(tmp_path: Path) -> None:
    result = record_visible_send_shadow(
        tmp_path,
        reply="ok",
        source="qq_outbox_pre_send",
        route="qq_outbox",
        target_kind="private",
        delivery_kind="text",
    )

    assert result["recorded"] is True
    assert result["passed"] is True
    assert result["context"]["retrieval_pressure"] == "none"


def test_visible_send_shadow_recomputes_placeholder_reply_hash(tmp_path: Path) -> None:
    result = record_visible_send_shadow(
        tmp_path,
        reply="ok",
        source="direct_chat_pre_send",
        reply_hash="sha256:reply",
    )

    assert result["reply_hash"].startswith("sha256:")
    assert result["reply_hash"] != "sha256:reply"
    assert len(result["reply_hash"]) == len("sha256:") + 64
