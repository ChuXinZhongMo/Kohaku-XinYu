from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import xinyu_bridge_turn_finish_sidecars as turn_finish_sidecars
import xinyu_bridge_slow_live_turn as slow_live_turn
import xinyu_core_bridge as core_bridge
from xinyu_dialogue_working_memory import load_dialogue_tail, save_dialogue_tail
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_bridge_session import AgentSession
from xinyu_recent_attachment_context import record_recent_attachment_context
from xinyu_turn_route_trace import record_turn_route_stage


class FakeController:
    def __init__(self) -> None:
        self._pending_injections: list[dict[str, str]] = []


class FakeAgent:
    def __init__(self) -> None:
        self.controller = FakeController()
        self._system_prompt = "BASE_SYSTEM_PROMPT"

    def get_system_prompt(self) -> str:
        return self._system_prompt


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
        payload={"text": "还是有点接待腔", "metadata": {"is_owner_user": True}},
        text="还是有点接待腔",
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


def test_live_turn_injects_owner_continuity_hint_for_three_fix_reference(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    (runtime.xinyu_dir / "memory/context/recent_context_runtime_anchor.md").write_text(
        "# Recent Context\n\n"
        "- owner approved three quick fixes: restore recent_context, lower learning closed loop prompt weight, and cool down the repair loop.\n",
        encoding="utf-8",
    )
    agent = FakeAgent()

    runtime._inject_live_turn_context(
        agent,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        text="这三件事到底是哪三件",
        dialogue_tail=[
            {"role": "user", "content": "先跑真实聊天回归基线"},
            {"role": "assistant", "content": "好，先跑基线。"},
        ],
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "owner-visible continuity hint" in content
    assert "恢复最近聊天上下文" in content
    assert "Latest session tail" in content
    assert "restore recent_context" not in content
    assert "learning closed loop prompt weight" not in content
    assert "repair loop" not in content


def test_live_turn_defers_goldmark_runtime_auth_sidecar_in_ordinary_owner_chat(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    overlay = runtime.xinyu_dir / "memory/self/goldmark_positive_overlay.json"
    overlay.write_text(
        json.dumps(
            [
                {
                    "mark_id": "gm-runtime-test",
                    "marked_at": 123,
                    "dehydration_status": "done",
                    "owner_note": "owner secret note",
                    "visible_text_preview": "raw secret sentence",
                    "vibe_features": {
                        "tone_tags": ["warm", "concise"],
                        "structural_pattern": "one-line-shift-without-report-prefix",
                    },
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    agent = FakeAgent()
    runtime._inject_live_turn_context(
        agent,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        text="test",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "Goldmark Auth" not in content
    report = json.loads(
        (runtime.xinyu_dir / "runtime/prompt_pressure/last_live_prompt_pressure.json").read_text(encoding="utf-8")
    )
    assert any(item["name"] == "goldmark_auth" for item in report["blocked_sidecars"])
    assert "owner secret note" not in content
    assert "raw secret sentence" not in content


def test_owner_private_debug_prompt_dump_is_env_gated_and_overwritten(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_DEBUG_PROMPT_DUMP", "1")
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()
    overlay = runtime.xinyu_dir / "memory/self/goldmark_positive_overlay.json"
    overlay.write_text(
        json.dumps(
            [
                {
                    "marked_at": 123,
                    "dehydration_status": "done",
                    "vibe_features": {
                        "tone_tags": ["debug-tone"],
                        "structural_pattern": "debug-goldmark-pattern",
                    },
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    runtime._inject_live_turn_context(
        agent,
        payload={
            "message_type": "private_text",
            "session_id": "qq:private:owner",
            "metadata": {"is_owner_user": True},
        },
        text="debug this",
        turn_id="turn-debug-1",
    )
    runtime._inject_live_turn_context(
        agent,
        payload={
            "message_type": "private_text",
            "session_id": "qq:private:owner",
            "metadata": {"is_owner_user": True},
        },
        text="debug this again",
        turn_id="turn-debug-2",
    )

    dump_path = runtime.xinyu_dir / "runtime/debug/last_live_system_prompt.txt"
    content = dump_path.read_text(encoding="utf-8")
    assert "BASE_SYSTEM_PROMPT" in content
    assert "Live turn context, restored continuity version." in content
    assert "Goldmark Auth" not in content
    report = json.loads(
        (runtime.xinyu_dir / "runtime/prompt_pressure/last_live_prompt_pressure.json").read_text(encoding="utf-8")
    )
    assert any(item["name"] == "goldmark_auth" for item in report["blocked_sidecars"])
    assert "session_id: qq:private:owner" in content
    assert "turn_id: turn-debug-2" in content
    assert "turn_id: turn-debug-1" not in content
    assert "full_prompt_sha256: sha256:" in content
    assert "storage_policy: overwrite_last_dump_only" in content


def test_debug_prompt_dump_ignores_non_owner_even_when_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_DEBUG_PROMPT_DUMP", "1")
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()

    runtime._inject_live_turn_context(
        agent,
        payload={
            "message_type": "private_text",
            "session_id": "qq:private:other",
            "metadata": {"is_owner_user": False},
        },
        text="debug this",
        turn_id="turn-debug-other",
    )

    assert not (runtime.xinyu_dir / "runtime/debug/last_live_system_prompt.txt").exists()


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
                "- proactive_request_id: proreq-reflection-stale-codex",
                "- last_claimed_message: 那个 Codex 学习超时的事我还没当结束。",
            ]
        ),
        encoding="utf-8",
    )
    (runtime.xinyu_dir / "memory/context/proactive_request_state.md").write_text(
        "\n".join(
            [
                "- request_id: proreq-reflection-stale-codex",
                "- status: sent",
                "- kind: reflection_share",
                "- delivery_level: queue_owner_private",
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


def test_preview_only_proactive_is_not_answered_by_unrelated_owner_chat(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    request_path = runtime.xinyu_dir / "memory/context/proactive_request_state.md"
    (runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md").write_text(
        "\n".join(
            [
                "- last_claim_status: sent",
                "- last_claimed_at: 2026-05-03T16:16:54+08:00",
                "- proactive_request_id: proreq-old",
                "- last_claimed_message: old proactive message",
            ]
        ),
        encoding="utf-8",
    )
    request_path.write_text(
        "\n".join(
            [
                "- request_id: proreq-preview",
                "- status: candidate_only",
                "- kind: proactive_live_preview_test",
                "- delivery_level: preview_only",
                "- request_answer_state: pending",
                "- concrete_question: desktop-only preview",
            ]
        ),
        encoding="utf-8",
    )

    marked = runtime._mark_proactive_owner_reply(
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        text="normal owner chat",
        reply="normal reply",
    )

    assert not marked
    state = request_path.read_text(encoding="utf-8")
    assert "- status: candidate_only" in state
    assert "- request_answer_state: pending" in state
    assert "Last Owner Reply To Proactive" not in state


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


def test_qq_forward_context_sidecar_includes_forwarded_messages(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)

    sidecar = runtime._qq_rich_message_sidecar(
        {
            "metadata": {
                "qq_forward_context_available": True,
                "qq_forward_message_ids": ["fw-direct"],
                "qq_forward_context": {
                    "forward_ids": ["fw-direct"],
                    "message_count": 2,
                    "messages": [
                        {"sender_name": "Alice", "text": "第一句转发内容"},
                        {"sender_name": "Bob", "text": "第二句转发内容"},
                    ],
                },
            }
        }
    )

    assert "forwarded/merged chat record" in sidecar
    assert "forward_ids: fw-direct" in sidecar
    assert "Alice: 第一句转发内容" in sidecar
    assert "Bob: 第二句转发内容" in sidecar


def test_qq_image_context_sidecar_includes_ocr_and_visual_summary(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)

    sidecar = runtime._qq_rich_message_sidecar(
        {
            "metadata": {
                "qq_image_context_available": True,
                "qq_image_context": {
                    "available": True,
                    "ocr_text": "截图里写着：权限配置失败。",
                    "vision_summary": "这是一张 QQ 聊天截图，重点是对方在说权限配置没生效。",
                    "notes": ["image_context_requested", "ocr_text_available", "vision_summary_created"],
                },
            }
        }
    )

    assert "QQ image has been processed" in sidecar
    assert "image_ocr_text:" in sidecar
    assert "权限配置失败" in sidecar
    assert "image_visual_summary:" in sidecar
    assert "权限配置没生效" in sidecar


def test_qq_low_information_sticker_sidecar_prevents_blank_frame_claim(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)

    sidecar = runtime._qq_rich_message_sidecar(
        {
            "metadata": {
                "qq_rich_message": True,
                "qq_rich_summary": "sticker:[animated sticker]",
                "qq_sticker_count": 1,
                "sticker_import_queued": True,
                "qq_message_segments": [
                    {
                        "kind": "sticker",
                        "segment_type": "image",
                        "summary": "[animated sticker]",
                        "mood": "unclear",
                        "meaning": "QQ only supplied a sticker label",
                        "confidence": "low",
                    }
                ],
            }
        }
    )

    assert "generic sticker label" in sidecar
    assert "Do not claim you saw an empty/blank frame" in sidecar
    assert "Sticker library import is queued" in sidecar


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


def test_recent_readable_attachment_context_ignores_future_attachment_reference(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    extracted = runtime.xinyu_dir / "learning/owner_supplied/item/extracted_text.md"
    extracted.parent.mkdir(parents=True)
    extracted.write_text("# old file\n\nold content\n", encoding="utf-8")

    assert record_recent_attachment_context(
        runtime.xinyu_dir,
        {
            "title": "old-notes.md",
            "metadata": {"session_id": "qq:private:owner", "is_owner_user": True},
        },
        {
            "learning_item_id": "learn-old",
            "material_id": "material-old",
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
        text="这个是之前的，我说的是等下我准备新发的",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "Recent readable attachment context" not in content


def test_coalesced_owner_fragments_prompt_answers_once(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    agent = FakeAgent()

    runtime._inject_live_turn_context(
        agent,
        payload={
            "session_id": "qq:private:owner",
            "message_type": "private_text",
            "metadata": {
                "is_owner_user": True,
                "qq_coalesced_owner_messages": True,
                "qq_coalesced_message_count": 4,
            },
        },
        text="比如\n这样\n每句\n都回我",
    )

    content = agent.controller._pending_injections[0]["content"]
    assert "qq fragment coalescing sidecar" in content
    assert "answer only once to the overall meaning" in content
    assert "notes.md" not in content


def test_session_prompt_signature_ignores_volatile_context_files(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    first = runtime._session_prompt_signature()

    (runtime.xinyu_dir / "memory/context/persona_surface_state.md").write_text("changed\n", encoding="utf-8")
    (runtime.xinyu_dir / "memory/context/recent_context.md").write_text("changed\n", encoding="utf-8")
    (runtime.xinyu_dir / "memory/context/memory_weight_state.md").write_text("changed\n", encoding="utf-8")

    assert runtime._session_prompt_signature() == first


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


def test_desktop_codex_mode_payload_carries_owner_local_write_approval(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "platform": "desktop",
        "adapter": "xinyu_desktop_shell",
        "message_type": "desktop_private",
        "session_id": "desktop:private:owner",
        "user_id": "desktop-owner",
        "metadata": {
            "is_owner_user": True,
            "desktop_codex_mode": True,
            "owner_local_write_approved": True,
        },
    }

    codex_payload = runtime._build_model_codex_payload(
        payload,
        session_key="desktop:private:owner",
        task_text="让 Codex 修改 XinYu_Desktop 前端文件并保存",
    )

    assert runtime._can_model_delegate_codex(payload) is True
    assert codex_payload["metadata"]["owner_local_write_approved"] is True
    assert codex_payload["metadata"]["is_owner_user"] is True


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


def test_owner_self_code_weakness_feedback_triggers_direct_patch_task(tmp_path) -> None:
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
        user_text="\u5979\u81ea\u5df1\u7684\u4ee3\u7801\u4fee\u6539\u80fd\u529b\u6709\u70b9\u5f31\u4e86\u554a",
        reply="\u6211\u77e5\u9053\uff0c\u8fd9\u4e0d\u80fd\u53ea\u505c\u5728\u8868\u6001\u3002",
        session_key="qq:private:owner",
    )

    assert task
    assert "Self-code approval id: selfcode-direct-" in task
    assert "self-code/code modification ability is weak" in task
    assert "self-code execution path" in task


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


def test_promised_followup_report_instruction_queues_completion(tmp_path) -> None:
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
        user_text="\u665a\u4e0a\u56de\u6765\u6211\u8981\u770b\u5230\u4f60\u7684\u6c47\u62a5",
        reply="\u597d\uff0c\u6211\u4f1a\u6574\u7406\u597d\u7ed9\u4f60\u6c47\u62a5\u3002",
        session_key="qq:private:owner",
    )
    result = runtime._run_promised_followup_review(candidate)

    queue = json.loads((runtime.xinyu_dir / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    state = (runtime.xinyu_dir / "memory/context/promise_followup_state.md").read_text(encoding="utf-8")

    assert candidate["dedupe_key"].startswith("promise_followup:")
    assert result["queued"] is True
    assert queue["items"][0]["source"] == "promise_followup"
    assert "\u6c47\u62a5\u4efb\u52a1" in queue["items"][0]["message"]
    assert "\u665a\u4e0a\u56de\u6765\u6211\u8981\u770b\u5230\u4f60\u7684\u6c47\u62a5" in state


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


def test_model_codex_delegate_allows_trusted_public_search_only(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "platform": "qq",
        "adapter": "xinyu_native_qq_gateway",
        "message_type": "private_text",
        "session_id": "qq:private:trusted",
        "user_id": "43",
        "metadata": {"is_owner_user": False, "is_trusted_user": True},
    }

    assert runtime._can_model_delegate_codex(payload) is False
    assert runtime._can_model_delegate_codex(payload, task_text="search public web sources for PyMuPDF docs") is True
    assert runtime._can_model_delegate_codex(payload, task_text=r"search and read D:\XinYu\config.yaml") is False

    codex_payload = runtime._build_model_codex_payload(
        payload,
        session_key="qq:private:trusted",
        task_text="search public web sources for PyMuPDF docs",
    )

    assert codex_payload["metadata"]["is_owner_user"] is False
    assert codex_payload["metadata"]["is_trusted_user"] is True
    assert codex_payload["metadata"]["trusted_public_search_task"] is True
    assert "trusted public-source search task" in codex_payload["text"]


def test_empty_visible_reply_fallback_is_disabled(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}

    reply = runtime._empty_visible_reply_fallback(
        payload=payload,
        user_text="\u6743\u9650\u914d\u7f6e\u8fd8\u662f\u5931\u8d25\uff0c\u770b\u65e5\u5fd7\u4fee\u4e00\u4e0b",
        delegate_note="codex",
    )

    assert reply == ""


def test_empty_visible_reply_recovery_uses_renderer_not_template(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}
    calls: list[dict[str, str]] = []

    async def fake_render(agent, *, payload, user_text, draft_reply, canonical_recall_context=""):
        del agent, payload, canonical_recall_context
        calls.append({"user_text": user_text, "draft_reply": draft_reply})
        return "晚上好。"

    runtime._render_outward_reply = fake_render  # type: ignore[method-assign]

    reply, flags = asyncio.run(
        runtime._recover_empty_visible_reply(
            FakeAgent(),
            payload=payload,
            user_text="晚上好",
        )
    )

    assert reply == "晚上好。"
    assert "empty_visible_reply_regenerated" in flags
    assert calls == [{"user_text": "晚上好", "draft_reply": ""}]
    assert runtime._empty_visible_reply_fallback(payload=payload, user_text="晚上好") == ""


def test_empty_visible_reply_fallback_reports_owner_state_generation_failure(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}

    reply = runtime._empty_visible_reply_fallback(
        payload=payload,
        user_text="\u72b6\u6001\u5982\u4f55\uff0c\u4e2b\u5934",
    )

    assert reply
    assert "\u8fd8\u5728\u3002\u521a\u624d\u6709\u70b9\u5361" not in reply
    assert any(marker in reply for marker in ("\u6a21\u578b", "\u751f\u6210", "QQ"))


def test_owner_private_greeting_semantic_fast_decision_uses_v1_classifier(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    decision = runtime._owner_private_semantic_fast_decision(payload, "\u665a\u4e0a\u597d")

    assert decision["allowed"] is True
    assert decision["route"] == "fast_path"
    assert decision["intents"] == ("greeting",)


def test_owner_private_state_question_semantic_fast_decision_requires_live_renderer(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    decision = runtime._owner_private_semantic_fast_decision(payload, "\u72b6\u6001\u5982\u4f55\uff0c\u4e2b\u5934")

    assert decision["allowed"] is True
    assert decision["route"] == "fast_path"
    assert decision["intents"] == ("owner_state_question",)
    assert decision["direct_reply"] == ""
    assert "owner_state_question_live_renderer_required" in decision["notes"]


def test_owner_private_state_question_semantic_fast_route_uses_renderer_not_template(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }
    session = AgentSession(key="qq:private:owner", agent=FakeAgent(), prompt_signature="")
    render_calls: list[dict[str, str]] = []
    published: list[dict[str, object]] = []
    rendered_reply = "\u6709\u70b9\u70e6\uff0c\u521a\u624d\u5361\u4e86\u4e00\u4e0b\u3002\u4f46\u6211\u5728\u8fd9\u513f\u3002"

    async def fake_render(agent, *, payload, user_text, draft_reply, canonical_recall_context=""):
        del agent, payload, canonical_recall_context
        render_calls.append({"user_text": user_text, "draft_reply": draft_reply})
        return rendered_reply

    async def fake_publish(payload, **kwargs):
        del payload
        published.append(kwargs)

    runtime._render_outward_reply = fake_render  # type: ignore[method-assign]
    runtime._desktop_publish_chat_finished = fake_publish  # type: ignore[method-assign]

    response = asyncio.run(
        runtime._maybe_handle_owner_private_semantic_fast_turn(
            payload,
            text="\u72b6\u6001\u5982\u4f55\uff0c\u4e2b\u5934",
            session=session,
            session_key=session.key,
            turn_id="turn-semantic-fast-state-test",
            turn_started_wall="2026-05-21T06:10:00+08:00",
            turn_started_at=0.0,
            before_memory={},
            cleanup={"cleaned_sessions": 0},
            event_sidecar={"notes": ["event_sourcing_recorded"]},
        )
    )

    assert response is not None
    assert response["reply"] == rendered_reply
    assert response["semantic_fast"]["intents"] == ["owner_state_question"]
    assert response["semantic_fast"]["renderer"] == "outward_reply"
    assert render_calls == [{"user_text": "\u72b6\u6001\u5982\u4f55\uff0c\u4e2b\u5934", "draft_reply": ""}]
    assert "\u8fd8\u5728\u3002\u521a\u624d\u6709\u70b9\u5361" not in response["reply"]
    assert published and published[0]["reply"] == rendered_reply


def test_owner_private_state_question_semantic_fast_route_reports_empty_renderer(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }
    session = AgentSession(key="qq:private:owner", agent=FakeAgent(), prompt_signature="")
    published: list[dict[str, object]] = []

    async def empty_render(agent, *, payload, user_text, draft_reply, canonical_recall_context=""):
        del agent, payload, user_text, draft_reply, canonical_recall_context
        return ""

    async def fake_publish(payload, **kwargs):
        del payload
        published.append(kwargs)

    runtime._render_outward_reply = empty_render  # type: ignore[method-assign]
    runtime._desktop_publish_chat_finished = fake_publish  # type: ignore[method-assign]

    response = asyncio.run(
        runtime._maybe_handle_owner_private_semantic_fast_turn(
            payload,
            text="\u72b6\u6001\u5982\u4f55\uff0c\u4e2b\u5934",
            session=session,
            session_key=session.key,
            turn_id="turn-semantic-fast-state-empty-renderer",
            turn_started_wall="2026-05-21T14:10:00+08:00",
            turn_started_at=0.0,
            before_memory={},
            cleanup={"cleaned_sessions": 0},
            event_sidecar={"notes": ["event_sourcing_recorded"]},
        )
    )

    assert response is not None
    assert response["semantic_fast"]["renderer"] == "empty_state_notice"
    assert any(marker in response["reply"] for marker in ("\u6a21\u578b", "\u751f\u6210", "QQ"))
    assert "\u8fd8\u5728\u3002\u521a\u624d\u6709\u70b9\u5361" not in response["reply"]
    assert published and published[0]["reply"] == response["reply"]


def test_owner_private_relationship_pressure_stays_out_of_semantic_fast_route(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    decision = runtime._owner_private_semantic_fast_decision(
        payload,
        "\u4f60\u521a\u624d\u90a3\u6837\u6211\u6709\u70b9\u5931\u671b",
    )

    assert decision["allowed"] is False
    assert decision["route"] == "slow_path"
    assert "relationship_pressure" in decision["intents"]


def test_owner_private_greeting_semantic_fast_route_uses_direct_reply_not_renderer(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }
    session = AgentSession(key="qq:private:owner", agent=FakeAgent(), prompt_signature="")
    render_calls: list[dict[str, str]] = []
    published: list[dict[str, object]] = []

    async def fake_render(agent, *, payload, user_text, draft_reply, canonical_recall_context=""):
        del agent, payload, canonical_recall_context
        render_calls.append({"user_text": user_text, "draft_reply": draft_reply})
        return "\u665a\u4e0a\u597d\u3002"

    async def fake_publish(payload, **kwargs):
        del payload
        published.append(kwargs)

    runtime._render_outward_reply = fake_render  # type: ignore[method-assign]
    runtime._desktop_publish_chat_finished = fake_publish  # type: ignore[method-assign]

    response = asyncio.run(
        runtime._maybe_handle_owner_private_semantic_fast_turn(
            payload,
            text="\u665a\u4e0a\u597d",
            session=session,
            session_key=session.key,
            turn_id="turn-semantic-fast-test",
            turn_started_wall="2026-05-19T21:56:00+08:00",
            turn_started_at=0.0,
            before_memory={},
            cleanup={"cleaned_sessions": 0},
            event_sidecar={"notes": ["event_sourcing_recorded"]},
        )
    )

    assert response is not None
    assert response["reply"] == "\u665a\u4e0a\u597d\u3002"
    assert response["semantic_fast"]["intents"] == ["greeting"]
    assert response["semantic_fast"]["renderer"] == "direct"
    assert "owner_private_semantic_fast_intercepted" in response["notes"]
    assert "semantic_fast_intents:greeting" in response["notes"]
    assert render_calls == []
    assert published and published[0]["reply"] == "\u665a\u4e0a\u597d\u3002"
    assert "\u5728\u3002" not in response["reply"]
    tail = load_dialogue_tail(runtime.xinyu_dir, session.key, max_entries=4)
    assert [item["content"] for item in tail[-2:]] == ["\u665a\u4e0a\u597d", "\u665a\u4e0a\u597d\u3002"]


def test_owner_private_greeting_chat_replay_intercepts_before_full_live_event(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u665a\u4e0a\u597d",
        "metadata": {"is_owner_user": True},
    }
    render_calls: list[dict[str, str]] = []
    published_started: list[dict[str, object]] = []
    published_finished: list[dict[str, object]] = []

    class FakeRuntimeAgent(FakeAgent):
        def set_output_handler(self, handler, *, replace_default=False):
            del handler, replace_default

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    class FakeAgentFactory:
        @staticmethod
        def from_path(*args, **kwargs):
            del args, kwargs
            return FakeRuntimeAgent()

    async def fake_render(agent, *, payload, user_text, draft_reply, canonical_recall_context=""):
        del agent, payload, canonical_recall_context
        render_calls.append({"user_text": user_text, "draft_reply": draft_reply})
        return "\u665a\u4e0a\u597d\u3002"

    async def fake_started(payload, **kwargs):
        del payload
        published_started.append(kwargs)

    async def fake_finished(payload, **kwargs):
        del payload
        published_finished.append(kwargs)

    def fail_full_live_event(*args, **kwargs):
        del args, kwargs
        raise AssertionError("semantic fast greeting should not create a full live user event")

    async def fail_pre_model_routes(*args, **kwargs):
        del args, kwargs
        raise AssertionError("semantic fast greeting should not wait for pre-model routes")

    monkeypatch.setattr(core_bridge, "run_pre_model_routes", fail_pre_model_routes)
    runtime._loaded = True
    runtime._agent_cls = FakeAgentFactory
    runtime._create_user_input_event = fail_full_live_event
    runtime._render_outward_reply = fake_render  # type: ignore[method-assign]
    runtime._desktop_publish_chat_started = fake_started  # type: ignore[method-assign]
    runtime._desktop_publish_chat_finished = fake_finished  # type: ignore[method-assign]

    response = asyncio.run(runtime.chat(payload))

    assert response["accepted"] is True
    assert response["reply"] == "\u665a\u4e0a\u597d\u3002"
    assert response["semantic_fast"]["route"] == "fast_path"
    assert response["semantic_fast"]["intents"] == ["greeting"]
    assert response["semantic_fast"]["renderer"] == "direct"
    assert "owner_private_semantic_fast_intercepted" in response["notes"]
    assert render_calls == []
    assert published_started
    assert published_finished and published_finished[0]["reply"] == "\u665a\u4e0a\u597d\u3002"
    assert "\u5728\u3002" not in response["reply"]
    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    stages = [row["stage"] for row in trace_rows]
    assert "pre_model_routes_started" not in stages
    assert stages.index("route_decided") < stages.index("route_finished")
    assert trace_rows[-1]["route"] == "owner_private_semantic_fast"
    route_state = json.loads((runtime.xinyu_dir / "runtime" / "turn_route_state.json").read_text(encoding="utf-8"))
    assert route_state["stage"] == "route_finished"
    assert route_state["route"] == "owner_private_semantic_fast"


def test_pre_model_routes_timeout_falls_through_without_bridge_timeout(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    runtime.pre_model_routes_timeout_seconds = 0.01
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u8fd9\u4e8b\u9700\u8981\u8ba4\u771f\u770b\u4e00\u4e0b",
        "metadata": {"is_owner_user": True},
    }

    class FakeRuntimeAgent(FakeAgent):
        def set_output_handler(self, handler, *, replace_default=False):
            del handler, replace_default

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    class FakeAgentFactory:
        @staticmethod
        def from_path(*args, **kwargs):
            del args, kwargs
            return FakeRuntimeAgent()

    async def hanging_pre_model_routes(*args, **kwargs):
        del args, kwargs
        await asyncio.sleep(60)

    async def fake_late_route(payload, **kwargs):
        del payload, kwargs
        return {
            "accepted": True,
            "reply": "\u6211\u7ee7\u7eed\u770b\u3002",
            "notes": ["continued_after_pre_model_timeout"],
        }

    monkeypatch.setattr(core_bridge, "run_pre_model_routes", hanging_pre_model_routes)
    runtime._loaded = True
    runtime._agent_cls = FakeAgentFactory
    runtime._owner_private_semantic_fast_decision = lambda payload, text: {  # type: ignore[method-assign]
        "allowed": False,
        "notes": ["test_slow_path"],
    }
    runtime._maybe_handle_owner_private_semantic_fast_turn = fake_late_route  # type: ignore[method-assign]

    response = asyncio.run(runtime.chat(payload))

    assert response["accepted"] is True
    assert response["reply"] == "\u6211\u7ee7\u7eed\u770b\u3002"
    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    pre_model_finish = [row for row in trace_rows if row["stage"] == "pre_model_routes_finished"][-1]
    assert pre_model_finish["status"] == "timeout"
    assert "pre_model_routes_timeout:0.01s" in pre_model_finish["notes"]


def _minimal_slow_finish_sidecars(before_memory: dict[str, object]) -> dict[str, object]:
    return {
        "uncertainty_pause": {"notes": []},
        "learning_closed_loop": {"notes": []},
        "residue_written": False,
        "voice_calibrated": False,
        "voice_trial_overlay": {"notes": []},
        "curiosity_prediction": {"notes": []},
        "private_thought_link": {"notes": []},
        "archive_result": {"notes": [], "message_ids": []},
        "candidate_result": {"notes": []},
        "memory_self_review": {"notes": []},
        "interaction_journal": {"notes": []},
        "proactive_owner_reply_marked": False,
        "promised_followup": {"notes": []},
        "sticker_reply": {"notes": []},
        "sticker_tail_recorded": False,
        "turn_coherence": {"notes": []},
        "after_memory": before_memory,
    }


def _install_minimal_slow_live_chat(
    monkeypatch,
    runtime: XinYuBridgeRuntime,
    *,
    reply: str = "\u6211\u770b\u5230\u4e86\u3002",
    inject_delay: float = 0.0,
    inject_error: Exception | None = None,
) -> None:
    class FakeRuntimeAgent(FakeAgent):
        def __init__(self) -> None:
            super().__init__()
            self._handler = None

        def set_output_handler(self, handler, *, replace_default=False):
            del replace_default
            self._handler = handler

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

        async def inject_event(self, event) -> None:
            del event
            if inject_delay > 0:
                await asyncio.sleep(inject_delay)
            if inject_error is not None:
                raise inject_error
            if self._handler is not None:
                self._handler(reply)

        def interrupt(self) -> None:
            return None

    class FakeAgentFactory:
        @staticmethod
        def from_path(*args, **kwargs):
            del args, kwargs
            return FakeRuntimeAgent()

    async def no_pre_model_route(*args, **kwargs):
        del args, kwargs
        return core_bridge.PreModelRouteResult(
            None,
            {"notes": ["event_sourcing_test_skipped"]},
            {"notes": ["v1_shadow_test_skipped"]},
            {"notes": ["tinykernel_shadow_test_skipped"]},
        )

    async def no_semantic_fast_route(*args, **kwargs):
        del args, kwargs
        return None

    async def no_chat_started(*args, **kwargs):
        del args, kwargs
        return None

    async def no_chat_finished(*args, **kwargs):
        del args, kwargs
        return None

    async def no_life_reply_policy(*args, **kwargs):
        del args, kwargs
        return {"notes": []}

    async def minimal_finish_sidecars(runtime_arg, *, before_memory, **kwargs):
        del runtime_arg, kwargs
        return _minimal_slow_finish_sidecars(before_memory)

    runtime._loaded = True
    runtime._agent_cls = FakeAgentFactory
    runtime._owner_private_semantic_fast_decision = lambda payload, text: {  # type: ignore[method-assign]
        "allowed": False,
        "notes": ["test_slow_path"],
    }
    runtime._maybe_handle_owner_private_semantic_fast_turn = no_semantic_fast_route  # type: ignore[method-assign]
    runtime._desktop_publish_chat_started = no_chat_started  # type: ignore[method-assign]
    runtime._desktop_publish_chat_finished = no_chat_finished  # type: ignore[method-assign]
    runtime._create_user_input_event = lambda *args, **kwargs: {"event": "user_input"}  # type: ignore[method-assign]
    runtime._build_life_reply_policy = no_life_reply_policy  # type: ignore[method-assign]
    runtime._sync_recent_proactive_to_dialogue_tail = lambda *args, **kwargs: False  # type: ignore[method-assign]

    monkeypatch.setattr(core_bridge, "run_pre_model_routes", no_pre_model_route)
    monkeypatch.setattr(core_bridge, "run_emotion_council_shadow", lambda *args, **kwargs: {"notes": []})
    monkeypatch.setattr(core_bridge, "observe_persona_turn", lambda *args, **kwargs: {"notes": [], "prompt_block": ""})
    monkeypatch.setattr(slow_live_turn, "refresh_continuity_handoff", lambda *args, **kwargs: {"notes": []})
    monkeypatch.setattr(slow_live_turn, "build_runtime_presence_prompt_block", lambda *args, **kwargs: "")
    monkeypatch.setattr(slow_live_turn, "build_continuity_handoff_prompt_block", lambda *args, **kwargs: "")
    monkeypatch.setattr(slow_live_turn, "build_uncertainty_pause_prompt_block", lambda *args, **kwargs: "")
    monkeypatch.setattr(slow_live_turn, "build_life_reply_prompt_block", lambda *args, **kwargs: "")
    monkeypatch.setattr(core_bridge, "apply_life_reply_policy", lambda *args, **kwargs: {"notes": []})
    monkeypatch.setattr(
        core_bridge,
        "classify_response_error",
        lambda *args, **kwargs: SimpleNamespace(error_class="none", severity="none"),
    )
    monkeypatch.setattr(core_bridge, "build_scene_frame", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(
        core_bridge,
        "build_slow_state",
        lambda *args, **kwargs: SimpleNamespace(reply_policy="steady", initiative_policy="steady", active_policies=[]),
    )
    monkeypatch.setattr(core_bridge, "run_slow_turn_finish_sidecars", minimal_finish_sidecars)


def _install_successful_memory_recall(monkeypatch, runtime: XinYuBridgeRuntime) -> None:
    async def fake_publish_recall(*args, **kwargs):
        del args, kwargs
        return {"id": "recall-test"}

    def fake_recall_algorithm(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(
            result=SimpleNamespace(notes=["recall_result_note"], prompt_block="memory prompt"),
            notes=["recall_algorithm_note"],
        )

    runtime._desktop_publish_memory_recall = fake_publish_recall  # type: ignore[method-assign]
    monkeypatch.setattr(core_bridge, "run_living_memory_recall_algorithm", fake_recall_algorithm)


def test_slow_live_memory_recall_route_trace_records_success(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    _install_minimal_slow_live_chat(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u8fd9\u4e8b\u9700\u8981\u8ba4\u771f\u770b\u4e00\u4e0b",
        "metadata": {"is_owner_user": True},
    }

    _install_successful_memory_recall(monkeypatch, runtime)

    response = asyncio.run(runtime.chat(payload))

    assert response["accepted"] is True
    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    stages = [row["stage"] for row in trace_rows]
    assert "memory_recall_started" in stages
    assert "memory_recall_finished" in stages
    memory_finish = [row for row in trace_rows if row["stage"] == "memory_recall_finished"][-1]
    assert memory_finish["route"] == "slow_live"
    assert memory_finish["status"] == "ok"
    assert "recall_algorithm_note" in memory_finish["notes"]
    model_finish = [row for row in trace_rows if row["stage"] == "model_inject_finished"][-1]
    assert model_finish["route"] == "slow_live"
    assert model_finish["status"] == "ok"
    sidecar_finish = [row for row in trace_rows if row["stage"] == "finish_sidecars_finished"][-1]
    assert sidecar_finish["route"] == "slow_live"
    assert sidecar_finish["status"] == "ok"


def test_slow_live_memory_recall_route_trace_records_error(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    _install_minimal_slow_live_chat(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u7ee7\u7eed\u5206\u6790\u8fd9\u4e2a\u95ee\u9898",
        "metadata": {"is_owner_user": True},
    }

    def fake_recall_algorithm(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("recall failed")

    async def fail_publish_recall(*args, **kwargs):
        del args, kwargs
        raise AssertionError("publish should not run after recall error")

    runtime._desktop_publish_memory_recall = fail_publish_recall  # type: ignore[method-assign]
    monkeypatch.setattr(core_bridge, "run_living_memory_recall_algorithm", fake_recall_algorithm)

    response = asyncio.run(runtime.chat(payload))

    assert response["accepted"] is True
    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    memory_error = [row for row in trace_rows if row["stage"] == "memory_recall_error"][-1]
    assert memory_error["route"] == "slow_live"
    assert memory_error["status"] == "error"
    assert "context_retrieval_error:RuntimeError" in memory_error["notes"]


def test_slow_live_memory_recall_route_trace_records_timeout(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    _install_minimal_slow_live_chat(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u7ee7\u7eed\u770b\u4e00\u4e0b\u6162\u94fe\u8def",
        "metadata": {"is_owner_user": True},
    }

    def fake_recall_algorithm(*args, **kwargs):
        del args, kwargs
        raise TimeoutError("recall timeout")

    async def fail_publish_recall(*args, **kwargs):
        del args, kwargs
        raise AssertionError("publish should not run after recall timeout")

    runtime._desktop_publish_memory_recall = fail_publish_recall  # type: ignore[method-assign]
    monkeypatch.setattr(core_bridge, "run_living_memory_recall_algorithm", fake_recall_algorithm)

    response = asyncio.run(runtime.chat(payload))

    assert response["accepted"] is True
    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    memory_timeout = [row for row in trace_rows if row["stage"] == "memory_recall_timeout"][-1]
    assert memory_timeout["route"] == "slow_live"
    assert memory_timeout["status"] == "timeout"
    assert "context_retrieval_timeout:TimeoutError" in memory_timeout["notes"]


def test_slow_live_model_inject_route_trace_records_timeout(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    runtime.turn_timeout_seconds = 0.01
    _install_minimal_slow_live_chat(monkeypatch, runtime, inject_delay=60.0)
    _install_successful_memory_recall(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u6d4b\u8bd5\u6a21\u578b\u6ce8\u5165\u8d85\u65f6",
        "metadata": {"is_owner_user": True},
    }

    try:
        asyncio.run(runtime.chat(payload))
    except core_bridge.BridgeRequestError as exc:
        assert exc.status.value == 504
    else:
        raise AssertionError("model inject timeout should raise BridgeRequestError")

    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    model_timeout = [row for row in trace_rows if row["stage"] == "model_inject_timeout"][-1]
    assert model_timeout["route"] == "slow_live"
    assert model_timeout["status"] == "timeout"
    assert "turn_timeout" in model_timeout["notes"]
    operator = runtime.health_snapshot()["operator"]
    assert operator["route_stage"] == "model_inject_timeout"
    assert operator["route_status"] == "timeout"
    assert operator["last_timeout_stage"] == "model_inject_timeout"
    assert operator["last_timeout_reason"] == "turn_timeout"


def test_slow_live_model_inject_route_trace_records_error(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    _install_minimal_slow_live_chat(monkeypatch, runtime, inject_error=RuntimeError("inject failed"))
    _install_successful_memory_recall(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u6d4b\u8bd5\u6a21\u578b\u6ce8\u5165\u9519\u8bef",
        "metadata": {"is_owner_user": True},
    }

    try:
        asyncio.run(runtime.chat(payload))
    except RuntimeError as exc:
        assert str(exc) == "inject failed"
    else:
        raise AssertionError("model inject error should be propagated")

    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    model_error = [row for row in trace_rows if row["stage"] == "model_inject_error"][-1]
    assert model_error["route"] == "slow_live"
    assert model_error["status"] == "error"
    assert "turn_error:RuntimeError" in model_error["notes"]


def test_slow_live_outward_renderer_route_trace_records_success(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    runtime.outward_renderer = True
    _install_minimal_slow_live_chat(monkeypatch, runtime)
    _install_successful_memory_recall(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u6d4b\u8bd5\u5916\u663e\u6e32\u67d3",
        "metadata": {"is_owner_user": True},
    }

    async def fake_render(*args, **kwargs):
        del args, kwargs
        return "\u6e32\u67d3\u540e\u7684\u56de\u590d\u3002"

    runtime._renderer_reason = lambda **kwargs: "test_renderer"  # type: ignore[method-assign]
    runtime._render_outward_reply = fake_render  # type: ignore[method-assign]

    response = asyncio.run(runtime.chat(payload))

    assert response["accepted"] is True
    assert response["reply"] == "\u6e32\u67d3\u540e\u7684\u56de\u590d\u3002"
    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    renderer_finish = [row for row in trace_rows if row["stage"] == "outward_renderer_finished"][-1]
    assert renderer_finish["route"] == "slow_live"
    assert renderer_finish["status"] == "ok"
    assert "reason:test_renderer" in renderer_finish["notes"]


def test_slow_live_final_reply_guard_rewrite_records_route_trace(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    _install_minimal_slow_live_chat(monkeypatch, runtime, reply="\u539f\u59cb\u56de\u590d")
    _install_successful_memory_recall(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u6d4b\u8bd5\u6700\u7ec8\u5b88\u536b\u6539\u5199",
        "metadata": {"is_owner_user": True},
    }

    class FakeSpeechController:
        @staticmethod
        def final_reply_guard(*, payload, user_text, reply):
            del payload, user_text
            if reply == "\u539f\u59cb\u56de\u590d":
                return "\u6539\u5199\u540e\u7684\u56de\u590d", ["minor_guard_rewrite"]
            return reply, []

    runtime.speech_controller = FakeSpeechController()

    response = asyncio.run(runtime.chat(payload))

    assert response["reply"] == "\u6539\u5199\u540e\u7684\u56de\u590d"
    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    guard_rewrite = [row for row in trace_rows if row["stage"] == "final_reply_guard_rewrite"][-1]
    assert guard_rewrite["route"] == "slow_live"
    assert guard_rewrite["status"] == "applied"
    assert "final_reply_guard_flags:minor_guard_rewrite" in guard_rewrite["notes"]


def test_slow_live_outward_renderer_route_trace_records_timeout(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    runtime.outward_renderer = True
    _install_minimal_slow_live_chat(monkeypatch, runtime)
    _install_successful_memory_recall(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u6d4b\u8bd5\u5916\u663e\u6e32\u67d3\u8d85\u65f6",
        "metadata": {"is_owner_user": True},
    }

    async def fake_render(*args, **kwargs):
        del args, kwargs
        raise TimeoutError("renderer timeout")

    runtime._renderer_reason = lambda **kwargs: "test_renderer"  # type: ignore[method-assign]
    runtime._render_outward_reply = fake_render  # type: ignore[method-assign]

    try:
        asyncio.run(runtime.chat(payload))
    except TimeoutError as exc:
        assert str(exc) == "renderer timeout"
    else:
        raise AssertionError("outward renderer timeout should be propagated")

    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    renderer_timeout = [row for row in trace_rows if row["stage"] == "outward_renderer_timeout"][-1]
    assert renderer_timeout["route"] == "slow_live"
    assert renderer_timeout["status"] == "timeout"
    assert "reason:test_renderer" in renderer_timeout["notes"]


def test_slow_live_outward_renderer_route_trace_records_error(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    runtime.outward_renderer = True
    _install_minimal_slow_live_chat(monkeypatch, runtime)
    _install_successful_memory_recall(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u6d4b\u8bd5\u5916\u663e\u6e32\u67d3\u9519\u8bef",
        "metadata": {"is_owner_user": True},
    }

    async def fake_render(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("renderer failed")

    runtime._renderer_reason = lambda **kwargs: "test_renderer"  # type: ignore[method-assign]
    runtime._render_outward_reply = fake_render  # type: ignore[method-assign]

    try:
        asyncio.run(runtime.chat(payload))
    except RuntimeError as exc:
        assert str(exc) == "renderer failed"
    else:
        raise AssertionError("outward renderer error should be propagated")

    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    renderer_error = [row for row in trace_rows if row["stage"] == "outward_renderer_error"][-1]
    assert renderer_error["route"] == "slow_live"
    assert renderer_error["status"] == "error"
    assert "reason:test_renderer" in renderer_error["notes"]
    assert "renderer_error:RuntimeError" in renderer_error["notes"]


def test_slow_live_finish_sidecars_route_trace_records_timeout(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    _install_minimal_slow_live_chat(monkeypatch, runtime)
    _install_successful_memory_recall(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u6d4b\u8bd5\u6536\u5c3e\u4fa7\u8f66\u8d85\u65f6",
        "metadata": {"is_owner_user": True},
    }

    async def timeout_finish_sidecars(*args, **kwargs):
        del args, kwargs
        raise TimeoutError("finish sidecars timeout")

    monkeypatch.setattr(core_bridge, "run_slow_turn_finish_sidecars", timeout_finish_sidecars)

    try:
        asyncio.run(runtime.chat(payload))
    except TimeoutError as exc:
        assert str(exc) == "finish sidecars timeout"
    else:
        raise AssertionError("finish sidecars timeout should be propagated")

    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    sidecar_timeout = [row for row in trace_rows if row["stage"] == "finish_sidecars_timeout"][-1]
    assert sidecar_timeout["route"] == "slow_live"
    assert sidecar_timeout["status"] == "timeout"
    assert "finish_sidecars_timeout" in sidecar_timeout["notes"]


def test_slow_live_finish_sidecars_route_trace_records_error(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    _install_minimal_slow_live_chat(monkeypatch, runtime)
    _install_successful_memory_recall(monkeypatch, runtime)
    payload = {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "text": "\u6d4b\u8bd5\u6536\u5c3e\u4fa7\u8f66\u9519\u8bef",
        "metadata": {"is_owner_user": True},
    }

    async def error_finish_sidecars(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("finish sidecars failed")

    monkeypatch.setattr(core_bridge, "run_slow_turn_finish_sidecars", error_finish_sidecars)

    try:
        asyncio.run(runtime.chat(payload))
    except RuntimeError as exc:
        assert str(exc) == "finish sidecars failed"
    else:
        raise AssertionError("finish sidecars error should be propagated")

    trace_path = runtime.xinyu_dir / "runtime" / "turn_route_trace.jsonl"
    trace_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    sidecar_error = [row for row in trace_rows if row["stage"] == "finish_sidecars_error"][-1]
    assert sidecar_error["route"] == "slow_live"
    assert sidecar_error["status"] == "error"
    assert "finish_sidecars_error:RuntimeError" in sidecar_error["notes"]


def test_health_operator_reports_stale_turn_age_and_route_state(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    started_at = (datetime.now().astimezone() - timedelta(seconds=420)).isoformat()
    presence_path = runtime.xinyu_dir / "memory" / "context" / "runtime_self_presence.md"
    presence_path.write_text(
        "\n".join(
            [
                "# Runtime Self Presence",
                "- current_turn_state: running",
                f"- current_turn_started_at: {started_at}",
                "- current_turn_id: turn-stale-test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    record_turn_route_stage(
        runtime.xinyu_dir,
        turn_id="turn-stale-test",
        stage="finish_sidecars_timeout",
        route="slow_live",
        status="timeout",
        payload={"platform": "qq", "message_type": "private_text", "session_id": "s", "user_id": "u"},
        notes=["finish_sidecars_timeout"],
    )

    operator = runtime.health_snapshot()["operator"]

    assert operator["current_turn_state"] == "stale_running"
    assert operator["current_turn_age_seconds"] >= 400
    assert operator["route_stage"] == "finish_sidecars_timeout"
    assert operator["route"] == "slow_live"
    assert operator["route_status"] == "timeout"
    assert operator["stale_running"] is True
    assert operator["stale_age_seconds"] >= 100
    assert operator["last_timeout_stage"] == "finish_sidecars_timeout"
    assert operator["last_timeout_reason"] == "finish_sidecars_timeout"


def test_slow_turn_finish_sidecars_preserve_archive_candidate_and_tail_order(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }
    session = AgentSession(key="qq:private:owner", agent=FakeAgent(), prompt_signature="")
    visible_turn = SimpleNamespace(turn_kind="ordinary_owner_chat")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        turn_finish_sidecars,
        "record_learning_closed_loop_turn",
        lambda *args, **kwargs: {"notes": ["learning_closed_loop"]},
    )
    monkeypatch.setattr(turn_finish_sidecars, "write_turn_residue", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        turn_finish_sidecars,
        "record_voice_trial_overlay",
        lambda *args, **kwargs: {"recorded": True, "notes": ["voice_trial"]},
    )
    monkeypatch.setattr(turn_finish_sidecars, "record_voice_correction", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        turn_finish_sidecars,
        "record_reply_prediction",
        lambda *args, **kwargs: {"notes": ["curiosity_prediction"]},
    )
    monkeypatch.setattr(
        turn_finish_sidecars,
        "record_private_thought_reply_link",
        lambda *args, **kwargs: {"notes": ["private_thought_link"]},
    )
    monkeypatch.setattr(
        turn_finish_sidecars,
        "archive_dialogue_turn",
        lambda *args, **kwargs: {"notes": ["archive"], "message_ids": ["user-1", "assistant-1"]},
    )

    def fake_extract(*args, **kwargs):
        captured["candidate_source_ids"] = kwargs["source_message_ids"]
        captured["candidate_dialogue_tail_before_append"] = list(kwargs["dialogue_tail"])
        return {"notes": ["candidate"]}

    monkeypatch.setattr(turn_finish_sidecars, "extract_memory_candidates", fake_extract)
    monkeypatch.setattr(
        turn_finish_sidecars,
        "run_memory_self_review",
        lambda *args, **kwargs: {"reviewed_candidates": 0, "notes": ["self_review"]},
    )
    monkeypatch.setattr(
        turn_finish_sidecars,
        "record_interaction_turn",
        lambda *args, **kwargs: {"notes": ["journal"]},
    )
    monkeypatch.setattr(
        turn_finish_sidecars,
        "ensure_recent_context_health",
        lambda *args, **kwargs: {"status": "ok", "action": "none"},
    )
    monkeypatch.setattr(
        turn_finish_sidecars,
        "maybe_enqueue_sticker_reply",
        lambda *args, **kwargs: {"notes": ["sticker_skip:not_requested"]},
    )

    def fake_finish_turn_coherence(*args, **kwargs):
        captured["action_result"] = kwargs["action_result"]
        captured["component_notes"] = kwargs["component_notes"]
        return {"notes": ["coherence"]}

    monkeypatch.setattr(turn_finish_sidecars, "finish_turn_coherence", fake_finish_turn_coherence)
    runtime._schedule_promised_followup_if_needed = lambda *args, **kwargs: {  # type: ignore[method-assign]
        "scheduled": True,
        "notes": ["promise"],
    }
    runtime._append_sticker_delivery_tail = lambda session, sticker_reply: False  # type: ignore[method-assign]

    result = asyncio.run(
        turn_finish_sidecars.run_slow_turn_finish_sidecars(
            runtime,
            payload=payload,
            text="继续",
            reply="我继续。",
            draft_reply="我继续。",
            session=session,
            session_key=session.key,
            turn_id="turn-finish-sidecar-test",
            turn_started_at=0.0,
            before_memory={},
            visible_turn=visible_turn,
            final_guard_flags=[],
            expression_learning={"notes": []},
            recalled_context=None,
            recalled_context_notes=[],
            private_thought_outcome={"notes": []},
            emotion_council={"notes": []},
            persona_sidecar={"notes": []},
            continuity_handoff={"notes": []},
            wait_to_think_sidecar={"notes": []},
            self_code_task="",
            direct_codex_task="",
            model_codex_task="",
            wait_to_think_task="",
            model_codex_delegate_note="",
        )
    )

    assert result["archive_result"]["message_ids"] == ["user-1", "assistant-1"]
    assert captured["candidate_source_ids"] == ["user-1", "assistant-1"]
    assert captured["candidate_dialogue_tail_before_append"] == []
    assert [item["content"] for item in session.dialogue_tail] == ["继续", "我继续。"]
    assert captured["action_result"] == "promised_followup_scheduled"
    assert captured["component_notes"]["memory_candidate"] == {"notes": ["candidate"]}
    assert result["voice_calibrated"] is True
    assert result["sticker_tail_recorded"] is False


def test_style_pressure_empty_fallback_is_disabled(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}

    reply = runtime._empty_visible_reply_fallback(
        payload=payload,
        user_text="丫头，你觉得自己最近的客服化，模板化下降了吗",
    )

    assert reply == ""


def test_empty_visible_reply_fallback_does_not_template_short_fatigue(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}

    reply = runtime._empty_visible_reply_fallback(
        payload=payload,
        user_text="我有点累",
    )

    assert reply == ""


def test_empty_visible_reply_fallback_handles_explicit_fatigue_boundary(tmp_path) -> None:
    runtime = _make_runtime(tmp_path)
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}

    reply = runtime._empty_visible_reply_fallback(
        payload=payload,
        user_text="我有点累，先别追问，也别安慰一大段。",
    )

    assert reply == ""


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

    def fake_goal_ecology(root, *, checked_at, trigger):
        calls["goal_ecology"] = {
            "root": root,
            "checked_at": checked_at,
            "trigger": trigger,
        }
        return {
            "selected_goal_id": "continue_bounded_work",
            "selected_score": 0.58,
        }

    def fake_action_gateway(root, *, checked_at, trigger):
        calls["self_action_gateway"] = {
            "root": root,
            "checked_at": checked_at,
            "trigger": trigger,
        }
        return {
            "status": "completed",
            "selected_goal_id": "continue_bounded_work",
            "executed_action_count": 1,
            "queued_approval_count": 1,
            "notes": [
                "self_action:goal/continue_bounded_work",
                "self_action:executed/continue_bounded_work/success",
                "self_action:approval_queued/continue_bounded_work/self_code_patch_request",
            ],
        }

    def fake_patch_executor(root, *, checked_at, execution_level, allow_codex):
        calls["self_action_patch_executor"] = {
            "root": root,
            "checked_at": checked_at,
            "execution_level": execution_level,
            "allow_codex": allow_codex,
        }
        return {
            "status": "prepared",
            "task_id": "selfaction-patch-test",
            "codex": {"status": "not_requested"},
            "notes": ["patch_task_prepared"],
        }

    def fake_outcome_observer(root, *, checked_at, trigger, maintenance_notes):
        calls["goal_outcome"] = {
            "root": root,
            "checked_at": checked_at,
            "trigger": trigger,
            "maintenance_notes": list(maintenance_notes),
        }
        return {
            "status": "recorded",
            "goal_id": "continue_bounded_work",
            "outcome": "useful",
        }

    monkeypatch.setattr("xinyu_core_bridge.run_self_thought_loop", fake_self_thought)
    monkeypatch.setattr("xinyu_core_bridge.run_proactive_request_loop", fake_proactive_request)
    monkeypatch.setattr("xinyu_core_bridge.run_self_chosen_goal_ecology", fake_goal_ecology)
    monkeypatch.setattr("xinyu_core_bridge.run_self_action_gateway", fake_action_gateway)
    monkeypatch.setattr("xinyu_core_bridge.run_self_action_patch_executor", fake_patch_executor)
    monkeypatch.setattr("xinyu_core_bridge.run_goal_outcome_observer", fake_outcome_observer)

    notes = runtime._run_autonomous_self_thought_sidecars(checked_at="2026-05-01T23:00:00+08:00")

    assert calls["goal_ecology"]["trigger"] == "autonomous_maintenance"
    assert calls["goal_ecology"]["checked_at"] == "2026-05-01T23:00:00+08:00"
    assert calls["self_action_gateway"]["trigger"] == "autonomous_maintenance"
    assert calls["self_action_gateway"]["checked_at"] == "2026-05-01T23:00:00+08:00"
    assert calls["self_action_patch_executor"]["execution_level"] == "prepare"
    assert calls["self_action_patch_executor"]["allow_codex"] is False
    assert calls["self_thought"]["trigger"] == "autonomous_maintenance"
    assert calls["self_thought"]["min_interval_seconds"] == runtime.autonomous_maintenance_interval_seconds
    assert calls["proactive_request"]["evaluated_at"] == "2026-05-01T23:00:00+08:00"
    assert calls["proactive_request"]["delivery_level"] == "queue_owner_private"
    assert calls["goal_outcome"]["trigger"] == "autonomous_maintenance"
    assert calls["goal_outcome"]["checked_at"] == "2026-05-01T23:00:00+08:00"
    assert "self_action:executed/continue_bounded_work/success" in calls["goal_outcome"]["maintenance_notes"]
    assert "goal_ecology:continue_bounded_work/0.58" in notes
    assert "self_action_gateway:completed/continue_bounded_work/1/1" in notes
    assert "self_action_patch_executor:prepared/selfaction-patch-test/not_requested" in notes
    assert "self_action:approval_queued/continue_bounded_work/self_code_patch_request" in notes
    assert "goal_outcome:recorded/continue_bounded_work/useful" in notes
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

    def fake_action_gateway(root, *, checked_at, trigger):
        calls["self_action_gateway"] = True
        return {
            "status": "completed",
            "selected_goal_id": "quiet_presence",
            "executed_action_count": 1,
            "queued_approval_count": 0,
            "notes": ["self_action:executed/quiet_presence/success"],
        }

    def fake_patch_executor(root, *, checked_at, execution_level, allow_codex):
        calls["self_action_patch_executor"] = True
        return {
            "status": "blocked",
            "task_id": "",
            "codex": {"status": "blocked"},
            "notes": ["patch_executor_blocked:no_self_action_handoff"],
        }

    def fake_outcome_observer(root, *, checked_at, trigger, maintenance_notes):
        calls["goal_outcome"] = True
        return {
            "status": "skipped",
            "reason": "no_concrete_signal",
        }

    monkeypatch.setattr("xinyu_core_bridge.run_self_thought_loop", fake_self_thought)
    monkeypatch.setattr("xinyu_core_bridge.run_proactive_request_loop", fake_proactive_request)
    monkeypatch.setattr("xinyu_core_bridge.run_self_action_gateway", fake_action_gateway)
    monkeypatch.setattr("xinyu_core_bridge.run_self_action_patch_executor", fake_patch_executor)
    monkeypatch.setattr("xinyu_core_bridge.run_goal_outcome_observer", fake_outcome_observer)

    notes = runtime._run_autonomous_self_thought_sidecars(checked_at="2026-05-01T23:00:00+08:00")

    assert calls["proactive_request"] is False
    assert calls["self_action_gateway"] is True
    assert calls["self_action_patch_executor"] is True
    assert calls["goal_outcome"] is True
    assert "self_thought:held/research_handoff/research_collection_gap/collect_sources" in notes
    assert "self_thought_research:source_search_provider" in notes
    assert "goal_outcome:skipped/no_concrete_signal/no_concrete_signal" in notes
