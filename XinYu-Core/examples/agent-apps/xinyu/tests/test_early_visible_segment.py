from __future__ import annotations

import asyncio
import json

from xinyu_early_visible_segment import STATE_REL
from xinyu_early_visible_segment import TRACE_REL
from xinyu_early_visible_segment import evaluate_early_visible_segment
from xinyu_early_visible_segment import extract_first_natural_segment
from xinyu_early_visible_segment import observe_early_visible_segment_shadow


def test_extract_first_natural_segment_requires_a_natural_break() -> None:
    assert extract_first_natural_segment("这件事得拆开看。后面再说。") == "这件事得拆开看。"
    assert extract_first_natural_segment("这件事得拆开看") == ""


def test_evaluate_rejects_placeholder_and_mechanic_voice() -> None:
    low = evaluate_early_visible_segment("怎么又不回", "我在想。")
    assert low.status == "rejected_shadow"
    assert "generic_presence_or_meta_prefix" in low.reasons

    mechanic = evaluate_early_visible_segment("什么情况", "后台链路还在跑。")
    assert mechanic.status == "rejected_shadow"
    assert "mechanic_or_backend_leak" in mechanic.reasons


def test_evaluate_accepts_specific_first_segment_candidate() -> None:
    decision = evaluate_early_visible_segment("接下来做什么", "先把延迟这块拆开。")
    assert decision.status == "accepted_shadow"
    assert decision.accepted_shadow is True


def test_observe_shadow_records_hashes_without_raw_text(tmp_path) -> None:
    async def _run():
        chunks: list[str] = []
        stop = asyncio.Event()
        task = asyncio.create_task(
            observe_early_visible_segment_shadow(
                tmp_path,
                chunks,
                payload={
                    "platform": "qq",
                    "message_type": "private",
                    "session_id": "qq:private:owner",
                    "metadata": {"is_owner_user": True},
                },
                user_text="接下来做什么",
                turn_id="turn-early-shadow-test",
                session_key="qq:private:owner",
                stop_event=stop,
                poll_seconds=0.01,
            )
        )
        chunks.append("这件事得拆开看。后面再补。")
        result = await asyncio.wait_for(task, timeout=1)
        return result

    result = asyncio.run(_run())
    assert result.status == "accepted_shadow"

    trace_text = (tmp_path / TRACE_REL).read_text(encoding="utf-8")
    state_text = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    assert "接下来做什么" not in trace_text
    assert "这件事得拆开看" not in trace_text
    assert "raw_user_text_saved" in trace_text
    assert "raw_segment_saved" in trace_text

    row = json.loads(trace_text.strip())
    assert row["accepted_shadow"] is True
    assert row["segment_hash"].startswith("sha256:")
    assert row["user_text_hash"].startswith("sha256:")
    assert row["raw_user_text_saved"] is False
    assert row["raw_segment_saved"] is False
    assert "- raw_segment_saved: false" in state_text
