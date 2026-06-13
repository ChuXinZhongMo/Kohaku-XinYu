from __future__ import annotations

import json

from xinyu_qq_voice_transcript_store import append_voice_input_trace


def test_qq_voice_transcript_store_appends_voice_input_trace(tmp_path) -> None:
    path = tmp_path / "runtime/voice_input_trace.jsonl"

    append_voice_input_trace(path, {"status": "transcribed", "engine": "fake_stt"})

    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [
        {"engine": "fake_stt", "status": "transcribed"}
    ]
