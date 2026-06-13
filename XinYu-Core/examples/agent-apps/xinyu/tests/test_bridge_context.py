from __future__ import annotations

from types import SimpleNamespace

import xinyu_bridge_context


def test_prompt_context_signature_records_missing_and_existing_files(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("version: test\n", encoding="utf-8")

    signature = xinyu_bridge_context.prompt_context_signature(
        tmp_path,
        ("config.yaml", "missing.md"),
    )

    assert "config.yaml:" in signature
    assert "missing.md:missing" in signature


def test_runtime_session_prompt_signature_uses_default_file_list(tmp_path) -> None:
    first = xinyu_bridge_context.runtime_session_prompt_signature(SimpleNamespace(xinyu_dir=tmp_path))
    target = tmp_path / "prompts/system.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("system prompt\n", encoding="utf-8")

    second = xinyu_bridge_context.runtime_session_prompt_signature(SimpleNamespace(xinyu_dir=tmp_path))

    assert first != second
    assert "prompts/system.md:" in second


def test_prompt_context_signature_files_include_knowledge_refs() -> None:
    assert "memory/knowledge/ai_domain.md" in xinyu_bridge_context.PROMPT_CONTEXT_SIGNATURE_FILES
    assert "memory/knowledge/social_inquiry_policy.md" in xinyu_bridge_context.PROMPT_CONTEXT_SIGNATURE_FILES
