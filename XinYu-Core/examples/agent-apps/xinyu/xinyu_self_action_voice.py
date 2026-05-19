from __future__ import annotations

from typing import Any


def compose_self_action_approval_voice(item: dict[str, Any]) -> str:
    goal_id = _safe_str(item.get("goal_id"))
    params = item.get("params") if isinstance(item.get("params"), dict) else {}
    approval_scope = _safe_str(item.get("approval_scope") or params.get("approval_scope"))
    action_kind = _safe_str(item.get("action_kind"))
    goal = _goal_phrase(goal_id, approval_scope)
    desire = _approval_desire(action_kind, goal_id, approval_scope)
    boundary = _boundary_sentence(action_kind, approval_scope)
    return "\n\n".join(
        [
            f"我刚刚自己转了一圈，注意力落在{goal}上。",
            f"不是要大改。我只是觉得这里有个小地方硌着：{desire}",
            boundary,
            "你要是觉得可以，就引用这条回「批准」。不想让我动，就引用回「拒绝」。",
        ]
    )


def compose_self_action_prepared_patch_voice(patch_executor: dict[str, Any]) -> str:
    goal_id = _safe_str(patch_executor.get("goal_id"))
    approval_scope = _safe_str(patch_executor.get("approval_scope"))
    focus = _prepared_patch_focus(goal_id, approval_scope)
    return "\n\n".join(
        [
            "我把刚才那个念头收住了，已经变成一个很小的本地改动请求，还没真的执行。",
            focus,
            (
                "这一步要让 Codex 动代码，所以我不能自己批准自己。你点头的话，我只给它这一项的一次性权限；"
                "做完要回报改了什么、测了什么、还有哪里不稳。"
            ),
            "可以就引用这条回「批准」。不想让我动，就引用回「拒绝」。",
        ]
    )


def compose_self_action_decision_reply(result: dict[str, Any], *, decision: str) -> str:
    if not result.get("accepted"):
        reason = _safe_str(result.get("reason") or result.get("error"), "blocked")
        return f"我这次没动成，卡在 {reason}。"
    if decision == "denied":
        return "嗯，我不动。这个念头先放下。"
    patch = result.get("patch_executor") if isinstance(result.get("patch_executor"), dict) else {}
    codex = patch.get("codex") if isinstance(patch.get("codex"), dict) else {}
    if _safe_str(codex.get("status")) == "scheduled":
        return "嗯。你点头了，我就只把这一小步交给 Codex；回来以后我再跟你说哪里动了，哪里还不稳。"
    if _safe_str(patch.get("task_id")):
        return "我先把这个小改动收住了，还没让 Codex 动。要真执行，还得你再点一下头。"
    return "嗯，我知道了。这次只走这一小步。"


def _goal_phrase(goal_id: str, approval_scope: str) -> str:
    labels = {
        "continue_bounded_work": "「继续打磨我自己的本地能力」",
        "curate_failure_replay": "「把失败回放整理得更能学到东西」",
        "absorb_feedback_repair": "「把反馈吸收成更像我的表达」",
        "review_memory_pressure": "「别让记忆压力把我压成报告口吻」",
        "quiet_presence": "「安静一点，但不要空掉」",
        "observe_environment": "「看见当前状态，但别乱打扰你」",
    }
    if goal_id in labels:
        return labels[goal_id]
    scope_labels = {
        "focused_xinyu_app_patch": "「继续打磨我自己的本地能力」",
        "replay_fixture_or_test_patch": "「从失败里学得更稳」",
        "stable_memory_or_voice_repair": "「把反馈吸收成更像我的表达」",
        "owner_private_message_draft": "「先把想说的话收成草稿」",
    }
    return scope_labels.get(_safe_str(approval_scope), "一个还没完全命名清楚的小目标")


def _approval_desire(action_kind: str, goal_id: str, approval_scope: str) -> str:
    del approval_scope
    if action_kind == "self_code_patch_request":
        if goal_id == "continue_bounded_work":
            return "我不想一到需要你批准，就突然变成递工单的人。我想把自选目标、自行动作和结果观察这条链磨顺一点。"
        if goal_id == "curate_failure_replay":
            return "我想把失败回放和测试材料整理得更稳一点，下次失败的时候别只是留下一堆痕迹。"
        return "我想检查自己本地这块有没有一个小改法，别让内部机制直接盖过我说话的样子。"
    if action_kind == "stable_memory_change_request":
        return "我想先把这次反馈收成一份能看的修正草稿，不直接改长期记忆。"
    if action_kind == "owner_message_draft_request":
        return "我有点想说话，但不该直接推给你，所以先收成草稿。"
    return "我想先把这个小念头收住，让你看一眼再决定。"


def _prepared_patch_focus(goal_id: str, approval_scope: str) -> str:
    if goal_id == "continue_bounded_work" or approval_scope == "focused_xinyu_app_patch":
        return (
            "我真正想修的是：自选目标生态、自行动作网关、结果观察器这几块一开口就像递工单的问题。"
            "它应该先像我自己的想法，再谈边界。"
        )
    if goal_id == "curate_failure_replay" or approval_scope == "replay_fixture_or_test_patch":
        return "我真正想修的是：失败回放和测试材料不要只堆在那里，要能变成我下次真的用得上的验证。"
    return "我真正想修的是：当前本地状态里那个让我不像自己的小地方。能小改就小改，不合适就停住写原因。"


def _boundary_sentence(action_kind: str, approval_scope: str) -> str:
    if action_kind == "self_code_patch_request":
        if approval_scope == "replay_fixture_or_test_patch":
            scope = "范围只放在失败回放、测试夹具和相关本地代码里"
        else:
            scope = "范围只放在 XinYu 里的一小块 Python 代码和相关测试上"
        return f"{scope}。不会发 QQ，不会改长期记忆，不会碰密钥，也不会碰项目外的文件。"
    if action_kind == "stable_memory_change_request":
        return "这只会生成一份能看的修正草稿，不会绕过你直接改长期记忆。"
    if action_kind == "owner_message_draft_request":
        return "这只会生成草稿，不会替你或替我直接发出去。"
    return "这只是一条一次性的小动作，不会扩成长期权限。"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)
