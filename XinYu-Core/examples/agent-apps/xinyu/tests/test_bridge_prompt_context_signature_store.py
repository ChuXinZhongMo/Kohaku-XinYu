from __future__ import annotations

from xinyu_bridge_prompt_context_signature_store import prompt_context_file_signature


def test_prompt_context_signature_store_reads_file_metadata(tmp_path) -> None:
    path = tmp_path / "prompts/system.md"

    assert prompt_context_file_signature(path) is None

    path.parent.mkdir(parents=True)
    path.write_text("system\n", encoding="utf-8")

    signature = prompt_context_file_signature(path)
    assert signature is not None
    assert signature.size == len(path.read_bytes())
    assert isinstance(signature.mtime_ns, int)
