from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_archive import archive_dialogue_turn
from xinyu_dialogue_working_memory import save_dialogue_tail
from xinyu_short_term_continuity import build_short_term_continuity_prompt_block
from xinyu_short_term_continuity import evaluate_short_term_continuity


def test_short_term_continuity_anchors_direct_reference_to_recent_tail(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_PERSIST_9182"
    visible_reply = "刚才那句回答确实太像在问卷。"
    tail = [
        {"role": "user", "content": raw_private, "recorded_at": "2026-05-27T18:00:00+08:00"},
        {"role": "assistant", "content": visible_reply, "recorded_at": "2026-05-27T18:00:10+08:00"},
    ]

    block = build_short_term_continuity_prompt_block(
        tmp_path,
        user_text="她才刚说过，还要问我哪一句，这是何意",
        dialogue_tail=tail,
        turn_id="turn-short-continuity",
    )

    state_text = (tmp_path / "memory/context/short_term_continuity_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/short_term_continuity_trace.jsonl").read_text(encoding="utf-8")
    trace = json.loads(trace_text.splitlines()[0])

    assert "short-term continuity sidecar:" in block
    assert "tail_status: tail_available" in block
    assert raw_private in block
    assert visible_reply in block
    assert "do not ask 哪一句/哪几句" in block
    assert "- direct_reference: true" in state_text
    assert "- recall_status: tail_available" in state_text
    assert raw_private not in state_text
    assert visible_reply not in state_text
    assert raw_private not in trace_text
    assert visible_reply not in trace_text
    assert trace["latest_user_ref"].startswith("sha256:")
    assert trace["latest_assistant_ref"].startswith("sha256:")
    assert trace["raw_private_body_retained"] is False


def test_short_term_continuity_recovers_recent_archive_when_tail_is_empty(tmp_path: Path) -> None:
    raw_private = "ARCHIVE_OWNER_PRIVATE_LINE_SHOULD_NOT_PERSIST_7731"
    visible_reply = "刚才那句我问得太空了。"
    payload = {
        "session_id": "qq:private:owner",
        "message_type": "private_text",
        "user_id": "owner",
        "platform": "qq",
        "metadata": {"is_owner_user": True},
    }
    archive_dialogue_turn(
        tmp_path,
        payload,
        user_text=raw_private,
        assistant_reply=visible_reply,
        message_type="private_text",
    )

    block = build_short_term_continuity_prompt_block(
        tmp_path,
        payload=payload,
        user_text="刚才她说了什么？",
        dialogue_tail=[],
        turn_id="turn-short-continuity-archive",
    )

    state_text = (tmp_path / "memory/context/short_term_continuity_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/short_term_continuity_trace.jsonl").read_text(encoding="utf-8")

    assert "tail_status: tail_available" in block
    assert "tail_source: dialogue_archive" in block
    assert raw_private in block
    assert visible_reply in block
    assert "- recall_status: tail_available" in state_text
    assert "- recall_source: dialogue_archive" in state_text
    assert "- archive_recovered_count: 2" in state_text
    assert raw_private not in state_text
    assert visible_reply not in state_text
    assert raw_private not in trace_text
    assert visible_reply not in trace_text


def test_short_term_continuity_recovers_working_memory_when_tail_input_is_empty(tmp_path: Path) -> None:
    session_key = "qq:private:owner"
    raw_private = "WORKING_MEMORY_OWNER_PRIVATE_LINE_5511"
    visible_reply = "刚才那句我其实已经说得很明确了。"
    assert save_dialogue_tail(
        tmp_path,
        session_key,
        [
            {"role": "user", "content": raw_private, "recorded_at": "2026-05-27T18:30:00+08:00"},
            {"role": "assistant", "content": visible_reply, "recorded_at": "2026-05-27T18:30:10+08:00"},
        ],
        max_entries=24,
    )

    block = build_short_term_continuity_prompt_block(
        tmp_path,
        user_text="你刚刚不是才说过吗？",
        dialogue_tail=[],
        session_key=session_key,
        turn_id="turn-short-continuity-working-memory",
    )

    state_text = (tmp_path / "memory/context/short_term_continuity_state.md").read_text(encoding="utf-8")
    trace = json.loads((tmp_path / "runtime/short_term_continuity_trace.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert "tail_status: tail_available" in block
    assert "tail_source: dialogue_working_memory" in block
    assert raw_private in block
    assert visible_reply in block
    assert "- recall_source: dialogue_working_memory" in state_text
    assert "- tail_storage_status: available" in state_text
    assert trace["tail_storage_status"] == "available"
    assert trace["tail_storage_usable_row_count"] == 2
    assert "working_memory_tail_recovered" in trace["notes"]


def test_short_term_continuity_missing_tail_is_diagnostic_not_fabrication(tmp_path: Path) -> None:
    block = build_short_term_continuity_prompt_block(
        tmp_path,
        user_text="刚才我说的是什么？",
        dialogue_tail=[],
    )

    state = evaluate_short_term_continuity(
        tmp_path,
        user_text="刚才我说的是什么？",
        dialogue_tail=[],
    )

    assert "tail_status: tail_missing" in block
    assert "do not fabricate" in block
    assert "- none" in block
    assert state.direct_reference is True
    assert state.recall_status == "tail_missing"


def test_short_term_continuity_stays_out_of_ordinary_turns(tmp_path: Path) -> None:
    block = build_short_term_continuity_prompt_block(
        tmp_path,
        user_text="今天继续做主线",
        dialogue_tail=[{"role": "assistant", "content": "上一句"}],
    )

    state_text = (tmp_path / "memory/context/short_term_continuity_state.md").read_text(encoding="utf-8")
    assert block == ""
    assert "- status: inactive" in state_text
    assert "- direct_reference: false" in state_text
