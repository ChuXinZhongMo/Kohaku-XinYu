from __future__ import annotations

from xinyu_runtime_presence_text import (
    clip_preview,
    normalize_codex_status,
    normalize_turn_status,
    path_label,
    scrub_field,
    stable_hash,
)


def test_scrub_and_clip_redacts_secrets_and_paths() -> None:
    text = scrub_field("Authorization: Bearer sk-abcdefghijklmnopqrstuvw token=abcdef123456")
    assert "sk-" not in text
    assert "[redacted-secret]" in text
    assert path_label(r"D:\XinYu\Codex\Requests\job.md") == "job.md"
    assert clip_preview("a" * 200, limit=20).endswith("...")


def test_normalize_status_helpers() -> None:
    assert normalize_turn_status("SUCCESS") == "ok"
    assert normalize_turn_status("timed_out") == "timeout"
    assert normalize_codex_status("done") == "finished"
    assert normalize_codex_status("running", timed_out=True) == "timed_out"
    assert stable_hash("abc").startswith("sha256:")
