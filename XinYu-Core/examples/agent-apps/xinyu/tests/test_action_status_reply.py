from __future__ import annotations

from pathlib import Path

from xinyu_action_reply_composer import compose_action_reply
from xinyu_tool_intent_router import ToolIntentRouter
from xinyu_tool_targets import TargetRegistry


OWNER_PAYLOAD = {"message_type": "private_text", "metadata": {"is_owner_user": True}}


def test_natural_status_request_uses_casual_reply_style(tmp_path: Path) -> None:
    router = ToolIntentRouter(TargetRegistry(tmp_path))

    decision = router.route("你现在什么状态", OWNER_PAYLOAD, turn_id="turn-status")

    assert decision.kind == "action_request"
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
