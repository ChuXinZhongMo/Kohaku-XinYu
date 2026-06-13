from __future__ import annotations

from xinyu_bridge_state_text_store import read_text_safe


def test_state_text_store_reads_utf8_sig_and_default(tmp_path) -> None:
    path = tmp_path / "memory/context/state.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xef\xbb\xbf- status: ready\n")

    assert read_text_safe(path) == "- status: ready\n"
    assert read_text_safe(tmp_path / "missing.md") == ""
    assert read_text_safe(tmp_path / "missing.md", default="fallback") == "fallback"
