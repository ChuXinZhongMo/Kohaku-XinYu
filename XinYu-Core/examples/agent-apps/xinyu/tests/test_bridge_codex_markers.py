from __future__ import annotations

import re

from xinyu_bridge_codex_markers import extract_model_codex_delegate, extract_self_code_approval_id


CODEX_DELEGATE_PATTERNS = (
    re.compile(
        r"\[\[XINYU_CODEX_DELEGATE\]\]\s*(?P<task>.*?)\s*\[\[/XINYU_CODEX_DELEGATE\]\]",
        re.S,
    ),
)


def test_extract_model_codex_delegate_strips_task_prefix_and_limits_text() -> None:
    reply = "[[XINYU_CODEX_DELEGATE]] @@task = inspect runtime status [[/XINYU_CODEX_DELEGATE]]"

    assert extract_model_codex_delegate(reply, CODEX_DELEGATE_PATTERNS) == "inspect runtime status"


def test_extract_self_code_approval_id_reads_exact_marker_line() -> None:
    assert (
        extract_self_code_approval_id("Task\nSelf-code approval id: selfcode-direct-abc_123\nMore")
        == "selfcode-direct-abc_123"
    )
    assert extract_self_code_approval_id("no marker") == "unknown"
