from __future__ import annotations

from pathlib import Path

from xinyu_expression_self_learning import record_expression_self_learning_event
from xinyu_speech_controller import XinyuSpeechController


def test_expression_self_learning_records_failure_and_source_request(tmp_path: Path) -> None:
    result = record_expression_self_learning_event(
        tmp_path,
        user_text="不要任何模版",
        bad_reply="<tool_call> <function=memory_read>...</function> </tool_call>",
        repaired_reply="",
        flags=["pseudo_tool_call_naturalized", "machine_introspection_naturalized"],
        observed_at="2026-05-02T03:10:00+08:00",
        failure_kind="visible_mechanism_or_template_leak",
    )

    state = (tmp_path / "memory/self/expression_self_learning_state.md").read_text(encoding="utf-8")
    requests = (tmp_path / "memory/knowledge/source_requests.md").read_text(encoding="utf-8")
    trace = (tmp_path / "runtime/expression_self_learning_trace.jsonl").read_text(encoding="utf-8")

    assert result["recorded"] is True
    assert "failure_kind: visible_mechanism_or_template_leak" in state
    assert "visible_reply_policy:" in state
    assert "repair_policy:" in state
    assert "q-006" in requests
    assert "pending_url" in requests
    assert "conversational agents natural dialogue" in requests
    assert "expr-learn-" in trace


def test_expression_self_learning_reuses_existing_request(tmp_path: Path) -> None:
    first = record_expression_self_learning_event(
        tmp_path,
        user_text="第一次",
        bad_reply="memory_read",
        observed_at="2026-05-02T03:10:00+08:00",
    )
    second = record_expression_self_learning_event(
        tmp_path,
        user_text="第二次",
        bad_reply="memory_read",
        observed_at="2026-05-02T03:11:00+08:00",
    )

    requests = (tmp_path / "memory/knowledge/source_requests.md").read_text(encoding="utf-8")

    assert first["source_request_id"] == second["source_request_id"]
    assert second["source_request_created"] is False
    assert requests.count("q-006") == 1


def test_final_guard_blocks_false_codex_manual_only_claim(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="自己想不通的话就调用 Codex 搜索帮助。",
        reply="Codex 作为 skill 走不通，得你手动发 /codex <任务> 才能触发。",
    )

    assert text == ""
    assert "false_codex_unavailable_claim_blocked" in flags


def test_final_guard_allows_file_terms_when_owner_asks_for_code_changes(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="是，你有想改动的地方吗？",
        reply="我想改 xinyu_core_bridge.py 里空口承诺和 Codex 委托这两块。",
    )

    assert text == "我想改 xinyu_core_bridge.py 里空口承诺和 Codex 委托这两块。"
    assert "visible_memory_mechanics_naturalized" not in flags
