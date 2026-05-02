from __future__ import annotations

import json

from xinyu_dialogue_working_memory import load_dialogue_tail, save_dialogue_tail
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_recent_attachment_context import record_recent_attachment_context


class FakeController:
    def __init__(self) -> None:
        self._pending_injections: list[dict[str, str]] = []


class FakeAgent:
    def __init__(self) -> None:
        self.controller = FakeController()


def _make_runtime(tmp_path) -> XinYuBridgeRuntime:
    root = tmp_path / "xinyu"
    (root / "memory" / "context").mkdir(parents=True)
    (root / "memory" / "self").mkdir(parents=True)
    (root / "memory" / "relationships").mkdir(parents=True)
    (root / "memory" / "people").mkdir(parents=True)
    (root / "prompts").mkdir(parents=True)
    (root / "config.yaml").write_text("name: xinyu\n", encoding="utf-8")
    (root / "prompts" / "system.md").write_text("# system\n", encoding="utf-8")
    (root / "prompts" / "output.md").write_text("# output\n", encoding="utf-8")
    (root / "prompts" / "live_voice_card.md").write_text("# card\n", encoding="utf-8")
    (root / "memory" / "self" / "core.md").write_text("core\n", encoding="utf-8")
    (root / "memory" / "self" / "personality_profile.md").write_text("profile\n", encoding="utf-8")
    (root / "memory" / "self" / "narrative.md").write_text("narrative\n", encoding="utf-8")
    (root / "memory" / "context" / "persona_surface_state.md").write_text("surface\n", encoding="utf-8")
    (root / "memory" / "context" / "recent_context.md").write_text("recent\n", encoding="utf-8")
    (root / "memory" / "context" / "memory_weight_state.md").write_text("weights\n", encoding="utf-8")

    return XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=3,
        max_text_chars=8000,
        settle_seconds=0,
        outward_renderer=False,
    )


def _seed_pending_self_code_request(runtime: XinYuBridgeRuntime, request_id: str = "proreq-self-code-test") -> None:
    (runtime.xinyu_dir / "memory/context/proactive_request_state.md").write_text(
        "\n".join(
            [
                "# Proactive Request State",
                "",
                "## Current Request",
                f"- request_id: {request_id}",
                "- created_at: 2026-05-02T10:00:00+08:00",
                "- status: ready",
                "- kind: permission",
                "- source: self_thought",
                "- focus_kind: self_code_approval",
                "- focus_label: self-code-runtime-fix",
                "- evidence_label: XinYu wants to patch one runtime continuity bug",
                "- evidence_hash: sha256:testselfcodeapproval",
                "- concrete_question: May XinYu ask Codex to make one bounded runtime code patch?",
                "- requested_action: owner_permission",
                "- after_owner_replies: consume one-time approval ticket and execute bounded Codex patch",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_bridge_uses_restored_live_turn_context_with_session_tail(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()
    hint = "\n".join(
        [
            "## Dialogue Curiosity Soft Hint (This Turn Only)",
            "- previous_prediction_error: 0.82",
            "- stable_memory_write: blocked.",
        ]
    )

    runtime._inject_live_turn_context(
        agent,
        payload={"text": "还是有点客服", "metadata": {"is_owner_user": True}},
        text="还是有点客服",
        dialogue_tail=[
            {"role": "user", "content": "I worked on your backend all day."},
            {"role": "assistant", "content": "You must be tired."},
        ],
        curiosity_context=hint,
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "Live turn context, restored continuity version." in content
    assert "scene: owner_style_pressure" in content
    assert "speaker_relation: owner" in content
    assert "current session tail:" in content
    assert "I worked on your backend all day." in content
    assert "You must be tired." in content
    assert "Dialogue Curiosity Soft Hint" in content
    assert "previous_prediction_error" in content


def test_live_turn_injects_persona_runtime_growth_and_private_bias(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()
    (runtime.xinyu_dir / "memory/self/personality_evolution_state.md").write_text(
        "\n".join(
            [
                "- evolution_stage: active_trial",
                "- trial_permission: runtime_trial_only",
                "- active_trial_habit: replace_explanations_with_one_concrete_owner-facing_line_under_style_pressure",
                "- deprecated_reaction: explaining_prompt_or_quality_mechanics_when_owner_asks_for_changed_speech",
                "- candidate_theme: style repair after repeated owner pressure",
            ]
        ),
        encoding="utf-8",
    )
    (runtime.xinyu_dir / "memory/self/private_thought_state.md").write_text(
        "\n".join(
            [
                "- desire: carry residue into the next reply without a report",
                "- inhibition: do not expose mechanics",
                "- intended_behavior: answer with one situated line",
                "- outcome_status: pending",
            ]
        ),
        encoding="utf-8",
    )

    runtime._inject_live_turn_context(
        agent,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        text="还是模板味很重",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "Persona Runtime State" in content
    assert "replace_explanations_with_one_concrete_owner-facing_line_under_style_pressure" in content
    assert "explaining_prompt_or_quality_mechanics_when_owner_asks_for_changed_speech" in content
    assert "Quiet Autonomy Bias" in content
    assert "carry residue into the next reply without a report" in content
    assert "do_not_print_or_explain_this_layer: true" in content


def test_owner_time_fact_correction_gets_specific_sidecar(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()

    runtime._inject_live_turn_context(
        agent,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        text="？何意味 不是5.5假期才结束",
        dialogue_tail=[
            {"role": "assistant", "content": "晚上好。假期最后一天了。"},
            {"role": "user", "content": "？何意味 不是5.5假期才结束"},
        ],
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "factual/time correction sidecar:" in content
    assert "current_runtime_date:" in content
    assert "time/date/holiday fact" in content
    assert "stale memory" in content
    assert "one ordinary line" in content
    assert "我算错了 / 刚才那句说岔了 / 别理" in content


def test_time_fact_correction_sidecar_stays_out_of_unrelated_turns(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()

    runtime._inject_live_turn_context(
        agent,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        text="晚上好",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "factual/time correction sidecar:" not in content


def test_reflection_share_proactive_thread_marks_stale_codex_context(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    (runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md").write_text(
        "\n".join(
            [
                "- last_claim_status: sent",
                "- last_claimed_at: 2999-01-01T00:00:00+08:00",
                "- last_claimed_message: 那个 Codex 学习超时的事我还没当结束。",
            ]
        ),
        encoding="utf-8",
    )
    (runtime.xinyu_dir / "memory/context/proactive_request_state.md").write_text(
        "\n".join(
            [
                "- kind: reflection_share",
                "- request_answer_state: pending",
                "- evidence_label: reflection queue strong topic: dream residue after Codex 未完成的学习任务不能被关掉",
            ]
        ),
        encoding="utf-8",
    )
    (runtime.xinyu_dir / "memory/context/runtime_self_presence.md").write_text(
        "- codex_status: unknown\n- codex_timed_out: false\n",
        encoding="utf-8",
    )

    block = runtime._proactive_thread_context(
        {
            "message_type": "private_text",
            "metadata": {"is_owner_user": True},
        },
        "这什么情况",
    )

    assert "reflection_share_rule:" in block
    assert "old reflection queue item" in block
    assert "not from a currently running or currently timed-out Codex job" in block


def test_recent_readable_attachment_context_is_injected_for_file_reference(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    extracted = runtime.xinyu_dir / "learning/owner_supplied/item/extracted_text.md"
    extracted.parent.mkdir(parents=True)
    extracted.write_text(
        "# XINYU-CONTEXT-MEMORY-LAYER-PLAN.md\n\n"
        "## Context Memory Plan\n\n"
        "The plan extends short context with a searchable long-term memory layer.\n\n"
        "## Self-preservation Review\n\n"
        "The design must avoid rigid persona constraints and keep XinYu's self-directed replies intact.\n",
        encoding="utf-8",
    )
    payload = {
        "title": "XINYU-CONTEXT-MEMORY-LAYER-PLAN.md",
        "file_name": "XINYU-CONTEXT-MEMORY-LAYER-PLAN.md",
        "metadata": {
            "session_id": "qq:private:owner",
            "message_id": "1001",
            "segment_type": "file",
            "is_owner_user": True,
        },
    }
    result = {
        "learning_item_id": "learn-plan",
        "material_id": "material-plan",
        "extracted_text_path": "learning/owner_supplied/item/extracted_text.md",
    }

    assert record_recent_attachment_context(runtime.xinyu_dir, payload, result)

    agent = FakeAgent()
    runtime._inject_live_turn_context(
        agent,
        payload={
            "session_id": "qq:private:owner",
            "message_type": "private_text",
            "metadata": {"is_owner_user": True, "attachment_followup_after_ingest": True},
        },
        text="我刚发了一个附件。",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "Recent readable attachment context" in content
    assert "XINYU-CONTEXT-MEMORY-LAYER-PLAN.md" in content
    assert "Self-preservation Review" in content
    assert "readable content is available" in content
    assert "do not use a fixed acknowledgement or report template" in content


def test_recent_readable_attachment_context_stays_out_of_unrelated_turns(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    extracted = runtime.xinyu_dir / "learning/owner_supplied/item/extracted_text.md"
    extracted.parent.mkdir(parents=True)
    extracted.write_text("# file\n\ncontent\n", encoding="utf-8")

    assert record_recent_attachment_context(
        runtime.xinyu_dir,
        {
            "title": "notes.md",
            "metadata": {"session_id": "qq:private:owner", "is_owner_user": True},
        },
        {
            "learning_item_id": "learn-notes",
            "material_id": "material-notes",
            "extracted_text_path": "learning/owner_supplied/item/extracted_text.md",
        },
    )

    agent = FakeAgent()
    runtime._inject_live_turn_context(
        agent,
        payload={
            "session_id": "qq:private:owner",
            "message_type": "private_text",
            "metadata": {"is_owner_user": True},
        },
        text="晚安",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "Recent readable attachment context" not in content
    assert "notes.md" not in content


def test_session_prompt_signature_tracks_live_context_files(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    first = runtime._session_prompt_signature()

    (runtime.xinyu_dir / "memory/context/persona_surface_state.md").write_text("changed\n", encoding="utf-8")
    (runtime.xinyu_dir / "memory/context/recent_context.md").write_text("changed\n", encoding="utf-8")
    (runtime.xinyu_dir / "memory/context/memory_weight_state.md").write_text("changed\n", encoding="utf-8")

    assert runtime._session_prompt_signature() != first


def test_session_prompt_signature_tracks_concept_seed_files(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    first = runtime._session_prompt_signature()

    (runtime.xinyu_dir / "memory/self/core.md").write_text("changed\n", encoding="utf-8")

    assert runtime._session_prompt_signature() != first


def test_codex_payload_includes_recent_dialogue_context(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    session_key = "qq:private:owner"
    assert save_dialogue_tail(
        runtime.xinyu_dir,
        session_key,
        [
            {"role": "user", "content": "Search for counterarguments to blindsight Watts."},
            {"role": "assistant", "content": "I can prepare a bounded search task."},
        ],
    )
    payload = {
        "source": "qq_gateway_codex_execute_message",
        "session_id": session_key,
        "raw_owner_task": "Try Codex search.",
        "metadata": {},
    }

    text = runtime._augment_codex_payload_with_dialogue_context(payload, "Use Codex for this task.")

    assert "Recent QQ context before this Codex request:" in text
    assert "counterarguments to blindsight Watts" in text
    assert "Current owner Codex task: Try Codex search." in text
    assert payload["codex_context_included"] is True
    assert payload["metadata"]["dialogue_context_included"] is True


def test_model_codex_delegate_protocol_builds_owner_private_payload(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    marker = "\n".join(
        [
            "[[XINYU_CODEX_DELEGATE]]",
            "Search for philosophical counterarguments to blindsight Watts.",
            "[[/XINYU_CODEX_DELEGATE]]",
        ]
    )
    payload = {
        "platform": "qq",
        "adapter": "xinyu_native_qq_gateway",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._extract_model_codex_delegate(marker)
    codex_payload = runtime._build_model_codex_payload(payload, session_key="qq:private:owner", task_text=task)

    assert task == "Search for philosophical counterarguments to blindsight Watts."
    assert runtime._can_model_delegate_codex(payload) is True
    assert codex_payload["source"] == "qq_gateway_codex_execute_message"
    assert codex_payload["raw_owner_task"] == task
    assert codex_payload["metadata"]["delegated_by_model"] is True
    assert "Use Codex auxiliary brain" in codex_payload["text"]


def test_owner_direct_codex_request_overrides_permission_stalling_reply(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "platform": "qq",
        "adapter": "xinyu_native_qq_gateway",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._owner_direct_codex_task(
        payload,
        user_text="不能总靠我改，想不通就用codex浏览一下网络吧。",
        reply="要现在开始吗？",
        session_key="qq:private:owner",
    )

    assert task
    assert "Owner explicitly asked XinYu to use Codex" in task
    assert "Do not change files" in task


def test_owner_direct_codex_request_respects_negative_instruction(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._owner_direct_codex_task(
        payload,
        user_text="这次先别用codex，自己说说。",
        reply="我说说。",
        session_key="qq:private:owner",
    )

    assert task == ""


def test_owner_self_code_iteration_direct_grant_without_pending_application_builds_codex_task(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "platform": "qq",
        "adapter": "xinyu_native_qq_gateway",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._owner_self_code_iteration_task(
        payload,
        user_text="可以，直接主动修改你的代码，我授权了。",
        reply="那我可以试试。",
        session_key="qq:private:owner",
    )

    assert task
    assert "Self-code approval id: selfcode-direct-" in task
    assert "directly requested or authorized self-code modification" in task
    assert "Owner directly requested or authorized XinYu to modify her own code" in task
    assert "implement the concrete code change requested by the owner" in task
    state = (runtime.xinyu_dir / "memory/context/self_code_approval_state.md").read_text(encoding="utf-8")
    assert "approval_route: direct_owner_private_qq_request" in state
    assert "require_prior_qq_application: false" in state


def test_owner_self_code_iteration_direct_start_uses_recent_direct_grant(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    session_key = "qq:private:owner"
    assert save_dialogue_tail(
        runtime.xinyu_dir,
        session_key,
        [
            {"role": "user", "content": "可以，之后你能主动修改你的代码，我允许。"},
            {"role": "assistant", "content": "我会真的执行，不只说。"},
        ],
    )
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": session_key,
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._owner_self_code_iteration_task(
        payload,
        user_text="现在开始。",
        reply="要现在开始吗？",
        session_key=session_key,
    )

    assert task
    assert "Self-code approval id: selfcode-direct-" in task
    assert "direct owner-private approval" in task


def test_owner_self_code_iteration_direct_grant_rejects_group_or_non_owner(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)

    non_owner = runtime._owner_self_code_iteration_task(
        {
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:other",
            "user_id": "43",
            "metadata": {"is_owner_user": False},
        },
        user_text="可以，直接主动修改你的代码。",
        reply="我去改。",
        session_key="qq:private:other",
    )
    group = runtime._owner_self_code_iteration_task(
        {
            "platform": "qq",
            "message_type": "group_text",
            "session_id": "qq:group:7",
            "group_id": "7",
            "user_id": "42",
            "metadata": {"is_owner_user": True},
        },
        user_text="可以，直接主动修改你的代码。",
        reply="我去改。",
        session_key="qq:group:7",
    )

    assert non_owner == ""
    assert group == ""


def test_owner_self_code_iteration_pending_approval_builds_codex_task(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    _seed_pending_self_code_request(runtime)
    payload = {
        "platform": "qq",
        "adapter": "xinyu_native_qq_gateway",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._owner_self_code_iteration_task(
        payload,
        user_text="approved yes, proceed with the bounded code patch",
        reply="approval acknowledged",
        session_key="qq:private:owner",
    )

    assert task
    assert "Self-code approval id:" in task
    assert "first sent a QQ self-code application" in task
    assert "one-time bounded approval" in task
    assert "one focused, reversible patch" in task
    assert "Add or update focused tests/smokes" in task


def test_owner_self_code_iteration_start_phrase_uses_pending_approval(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    _seed_pending_self_code_request(runtime, request_id="proreq-self-code-start")
    session_key = "qq:private:owner"
    assert save_dialogue_tail(
        runtime.xinyu_dir,
        session_key,
        [
            {"role": "user", "content": "都可以，你甚至可以多主动尝试更改你的代码，我允许了。"},
            {"role": "assistant", "content": "我会试试。"},
        ],
    )
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": session_key,
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._owner_self_code_iteration_task(
        payload,
        user_text="可以现在就开始。",
        reply="要现在开始吗？",
        session_key=session_key,
    )

    assert task
    assert "Owner approved XinYu's prior QQ self-code application." in task


def test_owner_self_code_iteration_negative_instruction_blocks(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._owner_self_code_iteration_task(
        payload,
        user_text="这次先别改代码，先说思路。",
        reply="我先说思路。",
        session_key="qq:private:owner",
    )

    assert task == ""


def test_owner_self_code_iteration_ignores_open_question(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    task = runtime._owner_self_code_iteration_task(
        payload,
        user_text="你有想改动的地方吗？",
        reply="我有两个方向。",
        session_key="qq:private:owner",
    )

    assert task == ""


def test_codex_running_state_blocks_self_code_iteration_start(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    runtime_file = runtime.xinyu_dir / "runtime/codex_presence_state.json"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(
        json.dumps(
            {
                "status": "running",
                "job_id": "codex-qq-test",
                "visible_window_title": "Xinyu codex",
                "report_label": "codex-qq-test-report.md",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    state = runtime._codex_delegate_running()
    reply = runtime._codex_busy_reply(state)

    assert state["running"] is True
    assert "权限不是低" in reply
    assert "codex-qq-test" in reply


def test_owner_private_live_context_exposes_hidden_codex_delegate_contract(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()

    runtime._inject_live_turn_context(
        agent,
        payload={
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:owner",
            "metadata": {"is_owner_user": True},
        },
        text="自己想不通的话就调用 Codex 搜索帮助。",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "codex_delegation_contract:" in content
    assert "[[XINYU_CODEX_DELEGATE]]" in content
    assert "output only that marker and no visible prose" in content
    assert "Do not tell the owner manual /codex is required" in content
    assert "direct owner-private request to modify XinYu code is already a one-time approval" in content


def test_owner_private_live_context_exposes_promise_followup_contract(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()

    runtime._inject_live_turn_context(
        agent,
        payload={
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:owner",
            "metadata": {"is_owner_user": True},
        },
        text="你得自己查看一下。",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "promise_followup_contract:" in content
    assert "do not make a bare promise" in content
    assert "QQ outbox after review" in content


def test_promised_followup_queues_owner_private_completion(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    candidate = runtime._promised_followup_candidate(
        payload,
        user_text="我这边已经做出修改了，你得自己查看一下。",
        reply="好，我再看看。",
        session_key="qq:private:owner",
    )
    result = runtime._run_promised_followup_review(candidate)

    queue = json.loads((runtime.xinyu_dir / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    state = (runtime.xinyu_dir / "memory/context/promise_followup_state.md").read_text(encoding="utf-8")

    assert candidate["dedupe_key"].startswith("promise_followup:")
    assert result["queued"] is True
    assert queue["items"][0]["source"] == "promise_followup"
    assert queue["items"][0]["target"]["user_id"] == "42"
    assert "我看完了" in queue["items"][0]["message"]
    assert "status: queued" in state
    assert "queued_message_id:" in state


def test_promised_followup_ignores_completed_review_reply(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    candidate = runtime._promised_followup_candidate(
        payload,
        user_text="看完告诉我。",
        reply="我看完了，这里没问题。",
        session_key="qq:private:owner",
    )

    assert candidate == {}


def test_promised_followup_status_check_queues_completion(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    candidate = runtime._promised_followup_candidate(
        payload,
        user_text="怎么样了？",
        reply="我看看。",
        session_key="qq:private:owner",
    )

    assert candidate["dedupe_key"].startswith("promise_followup:")


def test_false_codex_manual_only_claim_is_critical_guard_flag(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)

    assert runtime._critical_final_guard_flags(["false_codex_unavailable_claim_blocked"]) == [
        "false_codex_unavailable_claim_blocked"
    ]


def test_model_codex_delegate_accepts_legacy_visible_marker(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    marker = "[/codex] @@task=查找 AI 人格形成和外界互动的研究讨论。[codex/]"

    assert runtime._extract_model_codex_delegate(marker) == "查找 AI 人格形成和外界互动的研究讨论。"


def test_model_codex_delegate_rejects_non_owner_or_group_context(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)

    assert runtime._can_model_delegate_codex({"message_type": "private_text", "metadata": {}}) is False
    assert (
        runtime._can_model_delegate_codex(
            {"message_type": "group_text", "group_id": "7", "metadata": {"is_owner_user": True}}
        )
        is False
    )


def test_dialogue_working_memory_persists_recent_exact_turns(tmp_path) -> None:
    root = tmp_path / "xinyu"
    tail = [
        {"role": "user", "content": "修了一天你的后台"},
        {"role": "assistant", "content": "辛苦啦。"},
        {"role": "user", "content": "有点"},
    ]

    assert save_dialogue_tail(root, "qq:private:owner", tail, max_entries=24)

    assert load_dialogue_tail(root, "qq:private:owner", max_entries=2) == tail[-2:]


def test_autonomous_maintenance_runs_self_thought_and_proactive_sidecars(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    calls: dict[str, object] = {}

    def fake_self_thought(root, *, checked_at, trigger, min_interval_seconds):
        calls["self_thought"] = {
            "root": root,
            "checked_at": checked_at,
            "trigger": trigger,
            "min_interval_seconds": min_interval_seconds,
        }
        return {
            "status": "candidate",
            "outcome": "request_candidate",
            "focus_kind": "dream_residue",
            "intention": "share_dream",
            "candidate_enabled": True,
            "research_needed": False,
            "research_route": "none",
        }

    def fake_proactive_request(root, *, evaluated_at, delivery_level):
        calls["proactive_request"] = {
            "root": root,
            "evaluated_at": evaluated_at,
            "delivery_level": delivery_level,
        }
        return {
            "status": "ready",
            "kind": "dream_share",
            "delivery_level": "queue_owner_private",
        }

    monkeypatch.setattr("xinyu_core_bridge.run_self_thought_loop", fake_self_thought)
    monkeypatch.setattr("xinyu_core_bridge.run_proactive_request_loop", fake_proactive_request)

    notes = runtime._run_autonomous_self_thought_sidecars(checked_at="2026-05-01T23:00:00+08:00")

    assert calls["self_thought"]["trigger"] == "autonomous_maintenance"
    assert calls["self_thought"]["min_interval_seconds"] == runtime.autonomous_maintenance_interval_seconds
    assert calls["proactive_request"]["evaluated_at"] == "2026-05-01T23:00:00+08:00"
    assert calls["proactive_request"]["delivery_level"] == "queue_owner_private"
    assert "self_thought:candidate/request_candidate/dream_residue/share_dream" in notes
    assert "proactive_request:ready/dream_share/queue_owner_private" in notes


def test_autonomous_maintenance_does_not_build_proactive_request_without_candidate(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    calls: dict[str, bool] = {"proactive_request": False}

    def fake_self_thought(root, *, checked_at, trigger, min_interval_seconds):
        return {
            "status": "held",
            "outcome": "research_handoff",
            "focus_kind": "research_collection_gap",
            "intention": "collect_sources",
            "candidate_enabled": False,
            "research_needed": True,
            "research_route": "source_search_provider",
        }

    def fake_proactive_request(root, *, evaluated_at, delivery_level):
        calls["proactive_request"] = True
        return {}

    monkeypatch.setattr("xinyu_core_bridge.run_self_thought_loop", fake_self_thought)
    monkeypatch.setattr("xinyu_core_bridge.run_proactive_request_loop", fake_proactive_request)

    notes = runtime._run_autonomous_self_thought_sidecars(checked_at="2026-05-01T23:00:00+08:00")

    assert calls["proactive_request"] is False
    assert "self_thought:held/research_handoff/research_collection_gap/collect_sources" in notes
    assert "self_thought_research:source_search_provider" in notes
