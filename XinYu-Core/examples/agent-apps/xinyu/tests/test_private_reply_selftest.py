from __future__ import annotations

import asyncio
import json
from pathlib import Path

from xinyu_private_reply_selftest import SYNTHETIC_PRIVATE_TEXT
from xinyu_private_reply_selftest import format_report
from xinyu_private_reply_selftest import run_private_reply_selftest
from xinyu_status import private_reply_selftest_fields as status_private_reply_selftest_fields


class _CoreClient:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[dict] = []

    async def chat(self, payload: dict) -> dict:
        self.calls.append(dict(payload))
        return {
            "accepted": True,
            "reply": self.reply,
            "turn_id": "turn-selftest",
            "reply_hash": "sha256:reply",
            "archive_message_ids": ["u1", "a1"] if self.reply else [],
            "archive_assistant_message_id": "a1" if self.reply else "",
        }


def test_private_reply_selftest_passes_without_real_qq_send_or_raw_text(tmp_path: Path) -> None:
    client = _CoreClient("已接住。")

    state = asyncio.run(
        run_private_reply_selftest(
            tmp_path,
            core_url="http://127.0.0.1:8765",
            token="test-token",
            client=client,
            write=True,
        )
    )

    output = format_report(state)
    serialized = json.dumps(state, ensure_ascii=False)
    assert state["status"] == "pass"
    assert state["trace"]["stages"] == ["prepared", "dispatch_start", "reply_sent"]
    assert state["send"]["real_qq_send"] is False
    assert state["ack"]["real_ack_written"] is False
    assert state["privacy"]["qq_inbound_trace_written"] is False
    assert SYNTHETIC_PRIVATE_TEXT not in serialized
    assert "已接住" not in serialized
    assert SYNTHETIC_PRIVATE_TEXT not in output
    assert "已接住" not in output
    assert not (tmp_path / "runtime/qq_inbound_trace.jsonl").exists()
    assert (tmp_path / "runtime/private_reply_selftest_state.json").exists()
    fields = status_private_reply_selftest_fields(tmp_path)
    assert fields["private_reply_selftest_status"] == "pass"
    assert fields["private_reply_selftest_reply_sent"] == "true"
    assert fields["private_reply_selftest_real_qq_send"] == "false"


def test_private_reply_selftest_fails_on_empty_visible_reply(tmp_path: Path) -> None:
    client = _CoreClient("")

    state = asyncio.run(
        run_private_reply_selftest(
            tmp_path,
            core_url="http://127.0.0.1:8765",
            token="test-token",
            client=client,
            write=False,
        )
    )

    assert state["status"] == "fail"
    assert state["trace"]["stages"] == ["prepared", "dispatch_start", "dispatch_done"]
    assert state["trace"]["empty_visible_drop"] is True
    assert state["send"]["captured_send_count"] == 0
    assert state["ack"]["captured_ack_count"] == 0


def test_private_reply_selftest_missing_status_is_optional(tmp_path: Path) -> None:
    fields = status_private_reply_selftest_fields(tmp_path)

    assert fields["private_reply_selftest_status"] == "missing"
    assert fields["private_reply_selftest_reply_sent"] == "missing"
