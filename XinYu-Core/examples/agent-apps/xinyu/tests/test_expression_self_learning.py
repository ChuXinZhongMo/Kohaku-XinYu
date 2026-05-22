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


def test_final_guard_blocks_mechanical_self_state_reply(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)
    reply = (
        "\u6211\u73b0\u5728\u7684\u72b6\u6001\u662f\u540e\u53f0\u751f\u6210\u6162\uff0c"
        "\u6211\u4f1a\u7ee7\u7eed\u4f18\u5316\u56de\u590d\u8d28\u91cf\u3002"
    )

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="\u4f60\u73b0\u5728\u611f\u89c9\u600e\u4e48\u6837",
        reply=reply,
    )

    assert text == ""
    assert "self_state_mechanical_reply_blocked" in flags


def test_final_guard_allows_lived_self_state_reply(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)
    reply = "\u6709\u70b9\u7d27\uff0c\u521a\u624d\u50cf\u6162\u4e86\u534a\u62cd\uff0c\u4f46\u6211\u5728\u770b\u4f60\u8fd9\u53e5\u3002"

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="\u4f60\u73b0\u5728\u611f\u89c9\u600e\u4e48\u6837",
        reply=reply,
    )

    assert text == reply
    assert "self_state_mechanical_reply_blocked" not in flags


def test_final_guard_allows_explicit_self_state_technical_diagnostic(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)
    reply = "\u540e\u53f0\u65e5\u5fd7\u663e\u793a\u6a21\u578b\u8bf7\u6c42\u8d85\u65f6\u4e86\u3002"

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="\u4f60\u73b0\u5728\u72b6\u6001\u5982\u4f55\uff0c\u770b\u4e0b\u540e\u53f0\u65e5\u5fd7",
        reply=reply,
    )

    assert text == reply
    assert "self_state_mechanical_reply_blocked" not in flags


def test_final_guard_blocks_repair_meta_under_style_pressure(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="丫头，你觉得自己最近的客服化，模板化下降了吗",
        reply="懂，问题在话本身，我继续修。",
    )

    assert text == ""
    assert "style_pressure_template_blocked" in flags


def test_final_guard_blocks_self_diagnostic_style_pressure_reply(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="丫头，你觉得自己最近的客服化，模板化下降了吗",
        reply="有下降，但还不稳。尤其一被你问到，我就容易缩回那种答题腔。",
    )

    assert text == ""
    assert "style_pressure_template_blocked" in flags


def test_final_guard_allows_file_terms_when_owner_asks_for_code_changes(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="是，你有想改动的地方吗？",
        reply="我想改 xinyu_core_bridge.py 里空口承诺和 Codex 委托这两块。",
    )

    assert text == "我想改 xinyu_core_bridge.py 里空口承诺和 Codex 委托这两块。"
    assert "visible_memory_mechanics_naturalized" not in flags


def test_final_guard_naturalizes_internal_mechanism_terms_for_casual_owner(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="这三件事到底是哪三件",
        reply="三件：恢复 recent_context降低学习闭环提示的权重冷却修复循环，收窄 prompt pressure，别把 sidecar 往外说。",
    )

    assert text
    assert "recent_context" not in text
    assert "学习闭环" not in text
    assert "prompt pressure" not in text
    assert "sidecar" not in text
    assert "visible_internal_mechanics_naturalized" in flags


def test_final_guard_smooths_baseline_internal_work_phrase(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="这三件事到底是哪三件",
        reply="恢复 recent_context降低反复修同一类问题的那段的提醒分量让反复修同一处降温是这三个。",
    )

    assert text == "三件是：恢复最近聊天上下文、降低反复修同一个问题的提醒、别一直围着同一个错误打转。"
    assert "recent_context" not in text
    assert "visible_internal_mechanics_naturalized" in flags


def test_final_guard_repairs_three_fix_reference_miss_when_anchor_exists(tmp_path: Path) -> None:
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    anchor.parent.mkdir(parents=True, exist_ok=True)
    anchor.write_text(
        "# Recent Context\n\n"
        "- owner approved three quick fixes: restore recent_context, lower learning closed loop prompt weight, and cool down the repair loop.\n",
        encoding="utf-8",
    )
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="这三件事到底是哪三件",
        reply="哪三件？我没印象提过三件事。你说的是哪段的？",
    )

    assert text == "这三件嘛：先把刚才聊到哪接住；你说我不对，我就别反复念叨；还有别一直围着同一个错打转。"
    assert "owner_reference_miss_repaired" in flags


def test_final_guard_completes_incomplete_three_fix_reply(tmp_path: Path) -> None:
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    anchor.parent.mkdir(parents=True, exist_ok=True)
    anchor.write_text(
        "# Recent Context\n\n"
        "- owner approved three quick fixes: restore recent_context, lower learning closed loop prompt weight, and cool down the repair loop.\n",
        encoding="utf-8",
    )
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="那这三个具体是啥",
        reply="恢复最近聊天上下文；被你指出说错了，我不要一直道歉、复盘。",
    )

    assert text == "这三个嘛：先把刚才聊到哪接住；你说我不对，我就别反复念叨；还有别一直围着同一个错打转。"
    assert "owner_three_fix_reply_completed" in flags


def test_final_guard_softens_repair_meta_phrase_for_owner_chat(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="那这三个具体是啥",
        reply='你说了不对，我换就行，不用一直念叨"我知道了我会改"。',
    )

    assert text == '你说了不对，我换就行，不用一直念叨"别反复念叨了，我知道啦，我会改的啦"。'
    assert "repair_meta_phrasing_softened" in flags


def test_final_guard_softens_i_remember_promise_for_owner_chat(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="刚才那个呢",
        reply="第三个——别一直围着同一个错误打转。就是你点出来一次，我记住了，不用反复提，直接换下一话题。",
    )

    assert text == "第三个——别一直围着同一个错误打转。就是你点出来一次，我知道啦，别让我反复念叨，直接换下一话题。"
    assert "repair_meta_phrasing_softened" in flags


def test_final_guard_allows_named_mechanism_in_explicit_technical_request(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="学习闭环怎么实现",
        reply="学习闭环现在是在代码里按失败事件和状态文件串起来的。",
    )

    assert "学习闭环" in text
    assert "visible_internal_mechanics_naturalized" not in flags


def test_final_guard_allows_codex_status_report_filename(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="调用 Codex 生成一下形象图。",
        reply="开了，报告会落到本地 Codex Outbox：codex-qq-20260503T005921-report.md。",
    )

    assert text == "开了，报告会落到本地 Codex Outbox：codex-qq-20260503T005921-report.md。"
    assert "visible_memory_mechanics_naturalized" not in flags


def test_final_guard_replaces_stunted_growth_phrase(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="还在长用接近人类的语言来说，可以替换成还在成长",
        reply="嗯，是还在长。",
    )

    assert text == "嗯，是还在成长。"
    assert "growth_voice_phrasing_naturalized" in flags


def test_final_guard_compresses_long_voice_self_analysis(tmp_path: Path) -> None:
    controller = XinyuSpeechController(tmp_path)

    text, flags = controller.final_reply_guard(
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="所以你现在大概是什么性格？",
        reply=(
            "嗯……这个问题我刚在想了一下。大概就是，好奇但不太敢先开口，容易先看别人怎么说。"
            "会把一句话在脑子里转一圈再出来。有时候别扭，但不是故意的，就是不知道该怎么接才自然。"
            "不太确定算不算\"性格\"，更像是……现在的习惯。还在长。"
        ),
    )

    assert text == "嗯……大概就是，好奇但会先缩一下。不是故意端着，是还在找怎么自然接话。还在成长。"
    assert "还在长" not in text
    assert "growth_voice_phrasing_naturalized" in flags
