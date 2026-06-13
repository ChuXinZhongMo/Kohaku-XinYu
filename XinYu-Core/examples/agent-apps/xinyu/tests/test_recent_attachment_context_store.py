from __future__ import annotations

from xinyu_recent_attachment_context_store import read_recent_attachment_context_json
from xinyu_recent_attachment_context_store import read_recent_attachment_text
from xinyu_recent_attachment_context_store import write_recent_attachment_context_json


def test_recent_attachment_context_store_writes_context_and_reads_text(tmp_path) -> None:
    context_path = tmp_path / "runtime/recent_attachment_context/session.json"
    text_path = tmp_path / "runtime/extracted/file.txt"
    context = {"attachments": [{"title": "file", "extracted_text_path": "runtime/extracted/file.txt"}]}

    write_recent_attachment_context_json(context_path, context)
    text_path.parent.mkdir(parents=True)
    text_path.write_bytes(b"\xef\xbb\xbfattachment body")

    assert read_recent_attachment_context_json(context_path) == context
    assert read_recent_attachment_context_json(tmp_path / "missing.json") == {"attachments": []}
    assert read_recent_attachment_text(text_path) == "attachment body"
    assert read_recent_attachment_text(tmp_path / "missing.txt") == ""
