from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from xinyu_goldmark import OVERLAY_REL, mark_goldmark_request, read_goldmark_overlay
from xinyu_goldmark_dehydrate import (
    SKIP_TOO_SHORT,
    extract_json_from_markdown,
    preprocess_dehydration_source,
    run_goldmark_dehydration_maintenance,
)
from xinyu_sent_reply_index import register_sent_reply_ack


def _register_and_mark(tmp_path: Path, *, adapter_id: str, text: str, note: str = "") -> None:
    register_sent_reply_ack(
        tmp_path,
        {
            "adapter": "xinyu_native_qq_gateway",
            "adapter_message_id": adapter_id,
            "route": "chat",
            "session_id": "qq:private:42",
            "turn_id": "turn-20260503T193453-sha256:" + adapter_id,
            "archive_assistant_message_id": "",
            "visible_text": text,
        },
    )
    result = mark_goldmark_request(
        tmp_path,
        {
            "adapter": "xinyu_native_qq_gateway",
            "adapter_message_id": adapter_id,
            "route": "chat",
            "owner_note": note,
        },
    )
    assert result["marked"] is True


def test_dehydrate_skips_too_short_mark_without_hallucinating_features(tmp_path: Path) -> None:
    _register_and_mark(tmp_path, adapter_id="short-1", text="删了重跑，别废话。", note="很干脆")

    result = run_goldmark_dehydration_maintenance(tmp_path, limit=5, provider="local")

    assert result["processed"] == 1
    assert result["skipped"] == 1
    overlay = read_goldmark_overlay(tmp_path)
    assert overlay[0]["dehydration_status"] == "done"
    assert overlay[0]["vibe_features"] == SKIP_TOO_SHORT
    assert overlay[0]["dehydration_skip_reason"] == "too_short_or_minimal_instruction"


def test_dehydrate_recovers_stale_processing_lock(tmp_path: Path) -> None:
    old_started = (datetime.now().astimezone() - timedelta(minutes=20)).isoformat(timespec="seconds")
    path = tmp_path / OVERLAY_REL
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            [
                {
                    "mark_id": "gm-stale",
                    "turn_id": "turn-stale",
                    "adapter": "xinyu_native_qq_gateway",
                    "adapter_msg_id": "stale-1",
                    "route": "chat",
                    "visible_text_preview": "先把问题切小，再确认最容易失败的路径，最后只改必要的一层。",
                    "dehydration_status": "processing",
                    "processing_started_at": old_started,
                    "owner_note": "排错顺序很准",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_goldmark_dehydration_maintenance(tmp_path, limit=5, provider="local")

    assert result["recovered"] == 1
    assert result["processed"] == 1
    overlay = read_goldmark_overlay(tmp_path)
    assert overlay[0]["dehydration_status"] == "done"
    assert isinstance(overlay[0]["vibe_features"], dict)


def test_preprocess_removes_code_blocks_tracebacks_and_json_noise() -> None:
    text = """
先别动主流程，先看最小复现。
```python
def broken():
    raise AttributeError("boom")
```
Traceback (most recent call last):
File "x.py", line 1, in <module>
{"long": "json", "with": "many", "keys": "that", "should": "go", "away": true}
然后再补一条针对边界的测试。
"""

    cleaned = preprocess_dehydration_source(text)

    assert "先别动主流程" in cleaned
    assert "然后再补一条" in cleaned
    assert "AttributeError" not in cleaned
    assert "Traceback" not in cleaned
    assert '"long"' not in cleaned


def test_extract_json_from_markdown_handles_prefix_fence_and_trailing_commas() -> None:
    parsed = extract_json_from_markdown(
        """
好的，分析如下：
```json
{
  "tone_tags": ["简洁", "非防御性",],
  "structural_pattern": "直接给出核心反应，避免模板前缀。",
}
```
"""
    )

    assert parsed["tone_tags"] == ["简洁", "非防御性"]
    assert parsed["structural_pattern"] == "直接给出核心反应，避免模板前缀。"
