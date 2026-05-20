from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xinyu_answer_discipline_visible_guard import evaluate_visible_reply_for_answer_discipline
from xinyu_bridge_semantic_fast_routes import owner_private_semantic_fast_decision
from xinyu_prompt_pressure import PromptSidecar, select_prompt_sidecars
from xinyu_tool_intent_router import ToolIntentRouter
from xinyu_tool_targets import TargetRegistry
from xinyu_turn_triage_gate import ACTIVE_TASK_LANE, ORDINARY_LANE, REST_LANE, RUNTIME_FIX_LANE, triage_turn
from xinyu_visible_reply_guard import dedupe_visible_reply


OWNER_PAYLOAD = {"message_type": "private_text", "metadata": {"is_owner_user": True}}


class FakeRuntime:
    owner_private_semantic_fast_route = True

    def __init__(self, *, decision: object) -> None:
        self.xinyu_dir = "."
        self._v1_app = SimpleNamespace(
            normalizer=SimpleNamespace(normalize=lambda payload: payload),
            router=SimpleNamespace(decide=lambda turn: decision),
        )

    def _owner_private_payload_matches(self, payload: dict) -> bool:
        del payload
        return True


def _decision(*, route: str, intents: list[str], needs_model: bool = False, needs_memory: bool = False):
    return SimpleNamespace(
        route=SimpleNamespace(value=route),
        reasons=("test",),
        classification=SimpleNamespace(
            intents=intents,
            needs_model=needs_model,
            needs_memory=needs_memory,
        ),
    )


def _visible(turn_kind: str = "ordinary_owner_chat") -> SimpleNamespace:
    return SimpleNamespace(
        turn_kind=turn_kind,
        technical_work=False,
        owner_style_pressure=False,
        owner_no_change_pressure=False,
        relationship_pressure=False,
        rest_silence=False,
    )


def _sidecar(name: str, admission: str) -> PromptSidecar:
    return PromptSidecar.from_parts(name, [f"{name} block"], admission=admission)


def test_personal_state_questions_stay_in_conversation_lane(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    for text in ("状态如何，丫头", "你现在什么状态", "现在感觉如何", "你感觉怎么样"):
        route = router.route(text, OWNER_PAYLOAD, turn_id="turn-owner-regression")
        triage = triage_turn(tmp_path, user_text=text, payload=OWNER_PAYLOAD)
        pressure = select_prompt_sidecars(
            [_sidecar("memory_braid", "core"), _sidecar("runtime_presence", "status")],
            payload=OWNER_PAYLOAD,
            user_text=text,
            visible_turn=_visible(),
        )
        admitted = {sidecar.name for sidecar in pressure.admitted}
        blocked = {decision.sidecar.name for decision in pressure.blocked}

        assert route.kind == "no_action", text
        assert route.request is None
        assert triage.primary_lane not in {RUNTIME_FIX_LANE, ACTIVE_TASK_LANE}, text
        assert triage.primary_lane in {ORDINARY_LANE, REST_LANE}, text
        assert pressure.status_reference is False, text
        assert "memory_braid" in admitted
        assert "runtime_presence" in blocked


def test_runtime_status_requests_keep_runtime_status_context(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    for text in ("运行状态怎么样", "core 和 QQ/NapCat 状态如何", "查一下状态", "/status"):
        route = router.route(text, OWNER_PAYLOAD, turn_id="turn-owner-regression")
        pressure = select_prompt_sidecars(
            [_sidecar("runtime_presence", "status"), _sidecar("goldmark_auth", "background")],
            payload=OWNER_PAYLOAD,
            user_text=text,
            visible_turn=_visible(),
        )
        admitted = {sidecar.name for sidecar in pressure.admitted}
        blocked = {decision.sidecar.name for decision in pressure.blocked}

        assert route.kind == "action_request", text
        assert route.request is not None
        assert route.request.tool == "status_probe"
        assert pressure.status_reference is True, text
        assert "runtime_presence" in admitted
        assert "goldmark_auth" in blocked


def test_semantic_fast_keeps_greetings_direct_but_defers_personal_state() -> None:
    greeting = owner_private_semantic_fast_decision(
        FakeRuntime(decision=_decision(route="fast_path", intents=["greeting"])),
        OWNER_PAYLOAD,
        "晚上好",
    )
    personal_state = owner_private_semantic_fast_decision(
        FakeRuntime(decision=_decision(route="slow_path", intents=["ordinary_chat"], needs_model=True)),
        OWNER_PAYLOAD,
        "现在感觉如何",
    )

    assert greeting["allowed"] is True
    assert greeting["direct_reply"] == "晚上好。"
    assert personal_state["allowed"] is False
    assert "semantic_fast_not_low_risk" in personal_state["notes"]


def test_visible_reply_guard_handles_recent_short_loop_without_flattening() -> None:
    loop = dedupe_visible_reply("困，但还没睡。你呢？困，但还没睡。你呢？")
    expressive = dedupe_visible_reply("嗯。嗯。")

    assert loop.text == "困，但还没睡。你呢？"
    assert loop.changed is True
    assert "visible_reply_duplicate_sentence_removed" in loop.notes
    assert expressive.text == "嗯。嗯。"
    assert expressive.changed is False


def test_answer_discipline_blocks_template_repair_in_plain_chat() -> None:
    template = evaluate_visible_reply_for_answer_discipline(
        "I cannot verify the previous dialogue, so I can only answer the current message.",
        {"retrieval_pressure": "none", "evidence_sufficiency": "usable"},
    )
    natural = evaluate_visible_reply_for_answer_discipline(
        "困，但还没睡。你呢？",
        {"retrieval_pressure": "none", "evidence_sufficiency": "usable"},
    )

    assert template.passed is False
    assert template.flags["template_like_casual_reply"] is True
    assert natural.passed is True
