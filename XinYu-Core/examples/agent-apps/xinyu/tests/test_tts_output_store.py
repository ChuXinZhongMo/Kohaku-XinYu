from __future__ import annotations

import json

from xinyu_tts_output_store import append_tts_output_trace


def test_append_tts_output_trace_uses_state_service_jsonl_writer(tmp_path) -> None:
    path = tmp_path / "runtime/tts_output_trace.jsonl"

    append_tts_output_trace(path, {"status": "played", "engine": "audio_speech"})

    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [
        {"engine": "audio_speech", "status": "played"}
    ]
