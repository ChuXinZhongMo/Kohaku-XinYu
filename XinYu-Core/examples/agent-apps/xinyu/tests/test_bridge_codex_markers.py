from __future__ import annotations

from xinyu_bridge_codex_markers import (
    CODEX_DELEGATE_CLOSE,
    CODEX_DELEGATE_OPEN,
    CODEX_DELEGATE_PATTERNS,
    extract_model_codex_delegate,
    extract_model_codex_delegate_default,
    extract_self_code_approval_id,
)


def test_extract_model_codex_delegate_strips_task_prefix_and_limits_text() -> None:
    reply = "[[XINYU_CODEX_DELEGATE]] @@task = inspect runtime status [[/XINYU_CODEX_DELEGATE]]"

    assert extract_model_codex_delegate(reply, CODEX_DELEGATE_PATTERNS) == "inspect runtime status"
    assert extract_model_codex_delegate_default(reply) == "inspect runtime status"


def test_extract_model_codex_delegate_accepts_legacy_visible_marker() -> None:
    reply = "[/codex] @@task = inspect legacy marker [codex/]"

    assert extract_model_codex_delegate_default(reply) == "inspect legacy marker"


def test_codex_delegate_marker_constants_match_protocol() -> None:
    assert CODEX_DELEGATE_OPEN == "[[XINYU_CODEX_DELEGATE]]"
    assert CODEX_DELEGATE_CLOSE == "[[/XINYU_CODEX_DELEGATE]]"
    assert len(CODEX_DELEGATE_PATTERNS) == 2


def test_extract_self_code_approval_id_reads_exact_marker_line() -> None:
    assert (
        extract_self_code_approval_id("Task\nSelf-code approval id: selfcode-direct-abc_123\nMore")
        == "selfcode-direct-abc_123"
    )
    assert extract_self_code_approval_id("no marker") == "unknown"
