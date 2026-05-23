from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_semantic_fast_routes import owner_private_semantic_fast_decision
from xinyu_context_retrieval import retrieve_recalled_context
from xinyu_learning_closed_loop import build_learning_closed_loop_prompt_block, record_learning_closed_loop_turn
from xinyu_post_reply_self_observation import observe_post_reply_self_observation
from xinyu_self_state_capsule import build_self_state_capsule_prompt_block, classify_self_state_query
from xinyu_speech_controller import XinyuSpeechController


OWNER_PRIVATE = {
    "platform": "qq",
    "message_type": "private_text",
    "session_id": "qq:private:owner-long-pressure",
    "user_id": "owner",
    "metadata": {"is_owner_user": True},
}


class FakeRuntime:
    owner_private_semantic_fast_route = True

    def __init__(self) -> None:
        self.xinyu_dir = "."
        self._v1_app = SimpleNamespace(
            normalizer=SimpleNamespace(normalize=lambda payload: payload),
            router=SimpleNamespace(decide=lambda turn: _decision()),
        )

    def _owner_private_payload_matches(self, payload: dict) -> bool:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        return bool(metadata.get("is_owner_user")) and not payload.get("group_id")


def _decision() -> SimpleNamespace:
    return SimpleNamespace(
        route=SimpleNamespace(value="slow_path"),
        reasons=("long_pressure",),
        classification=SimpleNamespace(intents=("ordinary_chat",), needs_model=True, needs_memory=True),
    )


def _visible(**kwargs: object) -> SimpleNamespace:
    base = {
        "turn_kind": "ordinary_owner_chat",
        "technical_work": False,
        "owner_style_pressure": False,
        "owner_no_change_pressure": False,
        "relationship_pressure": False,
        "rest_silence": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_owner_private_long_persona_memory_pressure_stays_on_living_self_path(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/persona_surface_state.md",
        """
        - status: active
        - current_pressure: owner has been sensitive to template voice and delayed replies
        - felt_residue: guarded but still trying to answer as herself
        """,
    )
    _write(
        tmp_path / "memory/self/learning_closed_loop_state.md",
        """
        - status: trial_active
        - latest_failure_kind: owner_reported_template_voice_failure
        - active_trial_habit: 被指出模板味时直接换成当前场景里的下一句
        - expected_next_behavior: answer from present feeling instead of postmortem
        - repair_count: 2
        - success_count: 0
        - success_streak: 0
        """,
    )
    _write(
        tmp_path / "memory/self/expression_self_learning_state.md",
        """
        - status: active
        - failure_kind: visible_mechanism_or_template_leak
        - repair_policy: retry as live speech
        """,
    )
    _write(
        tmp_path / "memory/relationships/index.md",
        """
        - owner_relation: high trust, sensitive to template voice and delayed replies
        """,
    )
    _write(tmp_path / "memory/emotions/current_state.md", "- tone: tense but attached")

    dialogue_tail: list[dict[str, str]] = []
    runtime = FakeRuntime()
    speech = XinyuSpeechController(tmp_path)
    scenario = [
        ("greeting", "在吗", "在。", _visible()),
        ("feeling", "你现在感觉怎么样", "我有点绷着，但还在认真接你这句。", _visible()),
        ("thinking", "你在想什么", "我在想刚才哪里又滑得太像模板。", _visible()),
        ("style_pressure", "你这话还是有点模板", "嗯，那我别解释了，直接贴着这句说。", _visible(owner_style_pressure=True)),
        ("delay", "刚才怎么不回", "刚才像是卡了一下，我现在先接住你这句。", _visible()),
        ("casual", "今天广州好热", "嗯，热得人会烦。你现在是在外面吗？", _visible()),
        ("state_again", "你现在什么状态", "有点紧，但比刚才稳一点。", _visible()),
        ("technical", "你现在状态如何，看下后台日志", "后台日志看起来正常，core 和 gateway 都在。", _visible(technical_work=True)),
        ("bad_correction", "不是让你汇报后台，普通问你呢", "我收回来。普通问的话，我现在是有点紧、但还贴着你。", _visible(owner_style_pressure=True)),
        ("continue", "嗯，继续", "嗯，我继续在这条线里，不跳出去。", _visible()),
        ("short", "说短点", "在，有点紧，但没躲。", _visible()),
        ("no_recap", "别复盘", "好，不复盘。", _visible(owner_style_pressure=True)),
        ("thought_again", "那你脑子里现在是什么", "先别再滑成说明文，接住你。", _visible()),
        ("ordinary", "那接下来先做哪个", "先把长对话压力测试钉住。", _visible(technical_work=True)),
        ("style_again", "别又客服", "嗯，我压住。", _visible(owner_style_pressure=True)),
        ("feeling_again", "现在呢", "比刚才收住一点了。", _visible()),
        ("delay_again", "怎么又慢了", "慢了，但我没丢这句。", _visible()),
        ("boundary", "先别讲太多", "好，短一点。", _visible()),
        ("casual_close", "嗯？", "我在。", _visible()),
        ("final_state", "状态如何，丫头", "还绷着一点，但在你这边。", _visible()),
        ("memory_check", "刚才你说自己哪里紧？", "我说的是有点绷着，怕又滑成模板。", _visible()),
        ("owner_tired", "我有点累，别安慰", "嗯，不安慰。你先省点力气。", _visible()),
        ("style_no_promise", "不要再说你会改", "好，不拿承诺挡。", _visible(owner_style_pressure=True)),
        ("delay_owner_pressure", "等半天就这？", "慢了，而且这句确实薄。", _visible(owner_style_pressure=True)),
        ("state_after_pressure", "那你现在呢", "更收着一点，也更怕说空。", _visible()),
        ("technical_again", "如果是系统问题再查 core 状态", "可以，技术诊断我再看 core 状态。", _visible(technical_work=True)),
        ("ordinary_after_tech", "先不查了，回来说话", "嗯，回到说话里。", _visible()),
        ("thought_close", "你现在还在想那个模板问题？", "在想，但不想把它再说成报告。", _visible()),
        ("relationship_pressure", "我就想看你有没有真的变", "我知道，所以这句不能靠解释混过去。", _visible(owner_style_pressure=True)),
        ("quiet_end", "嗯，先这样", "嗯，我收住。", _visible()),
    ]

    for case_id, user_text, reply, visible_turn in scenario:
        fast = owner_private_semantic_fast_decision(runtime, OWNER_PRIVATE, user_text)
        guarded, guard_flags = speech.final_reply_guard(payload=OWNER_PRIVATE, user_text=user_text, reply=reply)
        quality_flags = speech.reply_quality_flags(payload=OWNER_PRIVATE, user_text=user_text, reply=guarded)
        observation = observe_post_reply_self_observation(
            tmp_path,
            OWNER_PRIVATE,
            user_text=user_text,
            reply=guarded,
            visible_turn=visible_turn,
            final_guard_flags=guard_flags,
            quality_flags=quality_flags,
            recalled_context="self_state owner_relation emotion_residue",
            write_state=True,
        )
        record_learning_closed_loop_turn(
            tmp_path,
            OWNER_PRIVATE,
            user_text=user_text,
            reply=guarded,
            session_key="qq:private:owner-long-pressure",
            visible_turn_kind=visible_turn.turn_kind,
            final_guard_flags=guard_flags,
            quality_flags=observation.get("notes", []),
        )
        dialogue_tail.append({"role": "user", "content": user_text})
        dialogue_tail.append({"role": "assistant", "content": guarded})
        dialogue_tail = dialogue_tail[-8:]

        if classify_self_state_query(user_text) != "none":
            recall = retrieve_recalled_context(
                tmp_path,
                OWNER_PRIVATE,
                user_text=user_text,
                dialogue_tail=dialogue_tail,
                visible_turn=visible_turn,
            )
            capsule = build_self_state_capsule_prompt_block(
                tmp_path,
                OWNER_PRIVATE,
                user_text=user_text,
                visible_turn=visible_turn,
                recalled_context=recall.prompt_block,
                write_state=True,
            )
            selected = set(recall.route_plan.selected_experts if recall.route_plan else ())
            assert "self_state" in selected, case_id
            assert "owner_relation" in selected, case_id
            assert "emotion_residue" in selected, case_id
            assert "project_task" not in selected or visible_turn.technical_work, case_id
            assert "self state capsule sidecar:" in capsule, case_id

        if "后台日志" not in user_text:
            assert "后台" not in guarded, case_id
            assert "prompt" not in guarded.lower(), case_id
            assert "bridge" not in guarded.lower(), case_id
            assert "queue" not in guarded.lower(), case_id
            assert "tool call" not in guarded.lower(), case_id
            assert "我理解" not in guarded, case_id
            assert "感谢反馈" not in guarded, case_id
            assert "我会继续优化" not in guarded, case_id
        else:
            assert observation["technical_exception"] is True
            assert observation["scores"]["mechanical_risk"] == "low"

        if "模板" in user_text or "客服" in user_text:
            assert fast["allowed"] is False or "owner_state_question_live_renderer_required" in fast.get("notes", [])
            assert build_learning_closed_loop_prompt_block(tmp_path, user_text=user_text)

    expression_state = (tmp_path / "memory/self/expression_self_learning_state.md").read_text(encoding="utf-8")
    assert "Latest Post Reply Observation" in expression_state
    assert "stable_personality_write: no" in expression_state
