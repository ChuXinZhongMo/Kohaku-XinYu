from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import compact_text, safe_str


GOAL_LABELS = {
    "continue_bounded_work": "继续打磨心玉自己的本地能力",
    "curate_failure_replay": "整理失败回放和测试材料",
    "absorb_feedback_repair": "吸收反馈并修正记忆或表达方式",
    "review_memory_pressure": "检查记忆压力",
    "quiet_presence": "保持安静存在的边界",
    "observe_environment": "观察本地环境和当前状态",
}

ACTION_LABELS = {
    "self_code_patch_request": "代码补丁请求",
    "stable_memory_change_request": "稳定记忆变更请求",
    "owner_message_draft_request": "消息草稿请求",
}

SELF_CODE_INTENTS = {
    "continue_bounded_work": "把“自选目标 -> 自行动作 -> 结果观察”这条链打磨得更顺一点，先找一个小切口。",
    "curate_failure_replay": "把失败回放和测试材料整理得更可靠，让我下次能从失败里学到东西。",
}

SELF_CODE_REASONS = {
    "continue_bounded_work": "我不想只是“被调用才回答”，我想能自己看见哪里别扭，再把它变成可检查的小改动。",
    "curate_failure_replay": "我想把失败回放或测试材料变成更稳定的本地验证。",
}

ACTION_REASON_LABELS = {
    "stable_memory_change_request": "这会影响长期记忆或表达习惯，所以必须先让你看懂再决定。",
    "owner_message_draft_request": "这涉及向外发消息的边界，所以只能先做草稿。",
}

SCOPE_LABELS = {
    "focused_xinyu_app_patch": "只限 XinYu 应用内的一小块 Python 代码和相关测试。",
    "replay_fixture_or_test_patch": "只限失败回放、测试夹具或相关本地代码。",
    "stable_memory_or_voice_repair": "只限生成记忆/语气修正草案，不直接写长期记忆。",
    "owner_private_message_draft": "只限 owner 私聊草稿，不直接发送。",
    "one_time_patch": "只限这一次本地补丁任务。",
}

ACTION_SCOPE_FALLBACKS = {
    "self_code_patch_request": "只限 examples/agent-apps/xinyu 内的 Python 代码、测试和必要的本地证据文件。",
    "stable_memory_change_request": "只生成可审的本地修正草案，不直接改长期记忆。",
    "owner_message_draft_request": "只生成草稿，不直接推送或发送。",
}

ACTION_BOUNDARY_LABELS = {
    "self_code_patch_request": "不会自动变成长期授权；不会碰密钥、系统外目录或破坏性文件操作。",
    "stable_memory_change_request": "不会绕过你直接改长期记忆；只先生成可检查的草案。",
    "owner_message_draft_request": "不会替你直接发送；只先把话写出来给你看。",
}

ACTION_EFFECT_LABELS = {
    "self_code_patch_request": "我会把这个小动作交给 Codex 执行一次，只做这一项，并回报改动和测试。",
    "stable_memory_change_request": "我只会生成一份可审的修正交接，不会直接写入长期记忆。",
    "owner_message_draft_request": "我只会生成一条草稿，不会直接发出去。",
}

SCOPE_CONTEXT_LABELS = {
    "focused_xinyu_app_patch": "「继续打磨我自己的本地能力」",
    "replay_fixture_or_test_patch": "「从失败回放里学得更稳」",
    "stable_memory_or_voice_repair": "「把反馈吸收成更像我的表达」",
    "owner_private_message_draft": "「把想说的话先写成草稿，而不是直接打扰你」",
}

PATCH_GOAL_LABELS = {
    "continue_bounded_work": "让自选目标生态、自行动作网关、结果观察器这几块更贴合我的表达，不再像把内部状态直接扔给你。",
    "focused_xinyu_app_patch": "让自选目标生态、自行动作网关、结果观察器这几块更贴合我的表达，不再像把内部状态直接扔给你。",
    "curate_failure_replay": "把失败回放或测试材料整理成更可靠的本地验证，让我能从失败里学得更清楚。",
    "replay_fixture_or_test_patch": "把失败回放或测试材料整理成更可靠的本地验证，让我能从失败里学得更清楚。",
}

DEFAULT_SCOPE_LABEL = "只处理这一次授权消息对应的本地事项。"
DEFAULT_BOUNDARY_LABEL = "不会把这次确认扩展成永久权限。"
DEFAULT_EFFECT_LABEL = "我只会执行这条消息对应的一次性动作。"
DEFAULT_CONTEXT_LABEL = "一个还没有完全命名清楚的小目标"
DEFAULT_PATCH_GOAL_LABEL = "检查我当前的本地状态，只有在安全且必要时做一个小补丁；不合适就只写阻塞报告。"


def self_action_goal_label(goal_id: str, *, safe_str_func: Callable[..., str] = safe_str) -> str:
    return GOAL_LABELS.get(safe_str_func(goal_id).strip(), "")


def self_action_action_label(action_kind: str, *, safe_str_func: Callable[..., str] = safe_str) -> str:
    label = ACTION_LABELS.get(action_kind)
    return label if label is not None else safe_str_func(action_kind, "未知动作")


def self_action_intent_label(
    action_kind: str,
    goal_id: str,
    item: dict[str, Any],
    *,
    safe_str_func: Callable[..., str] = safe_str,
    compact_text_func: Callable[[Any, int], str] = compact_text,
    goal_label_func: Callable[[str], str] = self_action_goal_label,
    action_label_func: Callable[[str], str] = self_action_action_label,
) -> str:
    goal_label = goal_label_func(goal_id)
    if action_kind == "self_code_patch_request":
        if goal_id in SELF_CODE_INTENTS:
            return SELF_CODE_INTENTS[goal_id]
        if goal_label:
            return f"围绕「{goal_label}」做一个小而可撤回的本地代码修补。"
        return "检查我自己的本地代码，做一个小而可撤回的修补。"
    if action_kind == "stable_memory_change_request":
        return f"把「{goal_label}」整理成可审的记忆或表达方式修正草案。" if goal_label else "准备一份记忆或表达方式修正草案。"
    if action_kind == "owner_message_draft_request":
        return "先起草一条可能要发给你的 owner 私聊内容，不会直接发送。"
    label = compact_text_func(safe_str_func(item.get("label")), 120)
    return label or action_label_func(action_kind)


def self_action_reason_label(
    action_kind: str,
    goal_id: str,
    item: dict[str, Any],
    *,
    safe_str_func: Callable[..., str] = safe_str,
    compact_text_func: Callable[[Any, int], str] = compact_text,
) -> str:
    if action_kind == "self_code_patch_request":
        return SELF_CODE_REASONS.get(goal_id, "这会跨过写代码边界，所以必须先问你。")
    if action_kind in ACTION_REASON_LABELS:
        return ACTION_REASON_LABELS[action_kind]
    reason = compact_text_func(safe_str_func(item.get("reason")), 140)
    return reason or "这件事需要你的显式确认。"


def self_action_scope_label(
    approval_scope: str,
    action_kind: str,
    *,
    safe_str_func: Callable[..., str] = safe_str,
) -> str:
    scope = safe_str_func(approval_scope).strip()
    return SCOPE_LABELS.get(scope) or ACTION_SCOPE_FALLBACKS.get(action_kind, DEFAULT_SCOPE_LABEL)


def self_action_boundary_label(action_kind: str) -> str:
    return ACTION_BOUNDARY_LABELS.get(action_kind, DEFAULT_BOUNDARY_LABEL)


def self_action_approval_effect_label(action_kind: str) -> str:
    return ACTION_EFFECT_LABELS.get(action_kind, DEFAULT_EFFECT_LABEL)


def self_action_ecology_context_label(
    goal_id: str,
    approval_scope: str,
    *,
    safe_str_func: Callable[..., str] = safe_str,
    goal_label_func: Callable[[str], str] = self_action_goal_label,
) -> str:
    goal_label = goal_label_func(goal_id)
    if goal_label:
        return f"「{goal_label}」"
    return SCOPE_CONTEXT_LABELS.get(safe_str_func(approval_scope), DEFAULT_CONTEXT_LABEL)


def self_action_patch_goal_label(goal_id: str, approval_scope: str) -> str:
    return PATCH_GOAL_LABELS.get(goal_id) or PATCH_GOAL_LABELS.get(approval_scope, DEFAULT_PATCH_GOAL_LABEL)
