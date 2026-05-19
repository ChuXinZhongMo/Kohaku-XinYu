from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from sanitized_learning_metadata import build_sanitized_metadata_manifest, render_markdown  # noqa: E402


def test_sanitized_metadata_suppresses_urls_tokens_and_raw_fields(tmp_path: Path) -> None:
    root = tmp_path / "learning/owner_supplied"
    item = root / "bundle"
    item.mkdir(parents=True)
    (item / "metadata.json").write_text(
        """
{
  "claim": "raw owner instruction http://example.test/?openid=abc&rkey=secret",
  "content_type": "text/markdown",
  "created_at": "2026-05-06T19:27:19+08:00",
  "id": "learn-1",
  "kind": "url",
  "origin": "owner_supplied",
  "question_id": "qq-file-learning",
  "reason": "raw reason should not print",
  "source_type": "public_web_source",
  "source_url": "http://example.test/qqdownloadftnv5?openid=abc&rkey=secret",
  "stage_status": "not_staged",
  "stored_paths": ["learning/owner_supplied/bundle/report.md"],
  "title": "report.md"
}
""".strip(),
        encoding="utf-8",
    )

    manifest = build_sanitized_metadata_manifest(root)
    rendered = render_markdown(manifest)

    assert "learn-1" in rendered
    assert "owner_supplied" in rendered
    assert "claim" in rendered
    assert "reason" in rendered
    assert "source_url" in rendered
    assert "report.md" not in rendered
    assert "raw owner instruction" not in rendered
    assert "raw reason should not print" not in rendered
    assert "http://" not in rendered
    assert "openid=" not in rendered
    assert "rkey=" not in rendered
    assert "qqdownloadftnv5" not in rendered
    assert "sha256:" in rendered
    assert "Stored paths" in rendered


def test_sanitized_metadata_handles_invalid_json_without_echoing_parser_text(tmp_path: Path) -> None:
    root = tmp_path / "learning/owner_supplied"
    item = root / "bundle"
    item.mkdir(parents=True)
    (item / "metadata.json").write_text(
        """
{
  "claim": "unterminated raw field with http://example.test/?openid=abc&rkey=secret,
  "created_at": "2026-05-06T19:27:19+08:00",
  "id": "learn-invalid",
  "origin": "owner_supplied",
  "source_url": "http://example.test/qqdownloadftnv5?openid=abc&rkey=secret",
  "stored_paths": ["learning/owner_supplied/bundle/report.md"],
  "title": "report.md"
}
""".strip(),
        encoding="utf-8",
    )

    manifest = build_sanitized_metadata_manifest(root)
    rendered = render_markdown(manifest)

    assert "failed:JSONDecodeError" in rendered
    assert "learn-invalid" in rendered
    assert "http://" not in rendered
    assert "openid=" not in rendered
    assert "rkey=" not in rendered
    assert "qqdownloadftnv5" not in rendered
    assert "unterminated raw field" not in rendered
