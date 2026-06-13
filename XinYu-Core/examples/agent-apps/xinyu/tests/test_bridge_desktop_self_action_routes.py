from __future__ import annotations

import xinyu_bridge_desktop_self_action_routes as routes


def test_self_action_goal_and_action_labels_cover_known_and_fallback_values() -> None:
    assert routes.self_action_goal_label("continue_bounded_work") == "继续打磨心玉自己的本地能力"
    assert routes.self_action_goal_label("unknown") == ""
    assert routes.self_action_action_label("self_code_patch_request") == "代码补丁请求"
    assert routes.self_action_action_label("stable_memory_change_request") == "稳定记忆变更请求"
    assert routes.self_action_action_label("") == ""


def test_self_action_intent_and_reason_labels_project_request_context() -> None:
    assert "自选目标 -> 自行动作 -> 结果观察" in routes.self_action_intent_label(
        "self_code_patch_request",
        "continue_bounded_work",
        {},
    )
    assert routes.self_action_intent_label(
        "stable_memory_change_request",
        "absorb_feedback_repair",
        {},
    ) == "把「吸收反馈并修正记忆或表达方式」整理成可审的记忆或表达方式修正草案。"
    assert routes.self_action_intent_label("custom_action", "", {"label": "  自定义动作  "}) == "自定义动作"
    assert routes.self_action_reason_label(
        "self_code_patch_request",
        "curate_failure_replay",
        {},
    ) == "我想把失败回放或测试材料变成更稳定的本地验证。"
    assert routes.self_action_reason_label("custom_action", "", {"reason": ""}) == "这件事需要你的显式确认。"


def test_self_action_scope_boundary_effect_and_goal_labels_preserve_copy() -> None:
    assert (
        routes.self_action_scope_label("focused_xinyu_app_patch", "")
        == "只限 XinYu 应用内的一小块 Python 代码和相关测试。"
    )
    assert (
        routes.self_action_scope_label("", "owner_message_draft_request")
        == "只生成草稿，不直接推送或发送。"
    )
    assert (
        routes.self_action_boundary_label("self_code_patch_request")
        == "不会自动变成长期授权；不会碰密钥、系统外目录或破坏性文件操作。"
    )
    assert (
        routes.self_action_approval_effect_label("owner_message_draft_request")
        == "我只会生成一条草稿，不会直接发出去。"
    )
    assert routes.self_action_ecology_context_label("quiet_presence", "") == "「保持安静存在的边界」"
    assert routes.self_action_ecology_context_label("", "owner_private_message_draft") == (
        "「把想说的话先写成草稿，而不是直接打扰你」"
    )
    assert "自选目标生态" in routes.self_action_patch_goal_label("continue_bounded_work", "")
    assert "失败回放" in routes.self_action_patch_goal_label("", "replay_fixture_or_test_patch")
