from __future__ import annotations

from pathlib import Path

from xinyu_action_reply_composer import compose_action_reply
from xinyu_tool_intent_router import ToolIntentRouter
from xinyu_tool_targets import TargetRegistry


OWNER_PAYLOAD = {"message_type": "private_text", "metadata": {"is_owner_user": True}}


def test_personal_state_questions_do_not_route_to_status_probe(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    for text in (
        "状态如何，丫头",
        "你现在什么状态",
        "看看你现在什么状态",
        "你感觉怎么样",
        "你现在怎么样",
        "你还在线吗",
        "丫头你还好吗",
        "心情怎么样",
    ):
        decision = router.route(text, OWNER_PAYLOAD, turn_id="turn-status")

        assert decision.kind == "no_action", text


def test_runtime_status_request_uses_casual_reply_style(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    for text in ("运行状态怎么样", "core 和 QQ/NapCat 状态如何", "QQ/NapCat 连接正常吗", "查一下状态"):
        decision = router.route(text, OWNER_PAYLOAD, turn_id="turn-status")

        assert decision.kind == "action_request", text
        assert decision.request is not None
        assert decision.request.tool == "status_probe"
        assert decision.request.params["reply_style"] == "casual_status"


def test_explicit_status_command_keeps_technical_reply_style(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    decision = router.route("/status", OWNER_PAYLOAD, turn_id="turn-status")

    assert decision.kind == "action_request"
    assert decision.request is not None
    assert decision.request.tool == "status_probe"
    assert decision.request.params["reply_style"] == "technical_status"


def test_explicit_kohaku_command_routes_to_external_plugin(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    decision = router.route("/kohaku main kohaku hello from xinyu", OWNER_PAYLOAD, turn_id="turn-kohaku")

    assert decision.kind == "action_request"
    assert decision.request is not None
    assert decision.request.tool == "external_plugin_call"
    assert decision.request.target.alias == "kohaku_terrarium"
    assert decision.request.params["plugin_id"] == "kohaku_terrarium"
    assert decision.request.params["capability"] == "chat_creature"
    assert decision.request.params["args"] == {
        "session_id": "main",
        "creature_id": "kohaku",
        "message": "hello from xinyu",
    }


def test_codex_delegate_requires_explicit_task_after_directive(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    for text in (
        "/codex 核查当前架构",
        "启动codex查查？",
        "你群聊逻辑爆炸了，调用codex自主修复一下群聊逻辑",
        "用codex搜索 consciousness is useful philosophy",
    ):
        decision = router.route(text, OWNER_PAYLOAD, turn_id="turn-codex")

        assert decision.kind == "action_request", text
        assert decision.request is not None
        assert decision.request.tool == "codex_delegate"
        assert decision.request.params["task_text"]


def test_codex_observations_and_meta_questions_do_not_launch(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    for text in (
        "丫头刚刚在想什么？看见你调用codex了",
        "心玉为什么不能调用codex进行搜索",
        "说起来你运行codex好像每次都没成功的样子",
        "怎么直接就开codex",
        "codex查完了没",
    ):
        decision = router.route(text, OWNER_PAYLOAD, turn_id="turn-codex-meta")

        assert decision.kind == "no_action", text


def test_status_reply_surfaces_offline_qq_without_core_version_noise() -> None:
    reply = compose_action_reply(
        {
            "ok": False,
            "tool": "status_probe",
            "result": "failure",
            "summary": [
                "我在线，core 正常",
                "QQ/NapCat 这台机器现在没接",
                "待发队列 0，失败 0",
            ],
        }
    )

    assert reply == "我在线，core 正常；QQ/NapCat 这台机器现在没接；待发队列 0，失败 0。"
    assert "version=" not in reply
    assert "sessions=" not in reply
