from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from xinyu_tool_protocol import DELEGATED_LOCAL_RISK, READ_ONLY_RISK, ToolIntent, ToolRequest, ToolTarget, new_turn_id
from xinyu_tool_targets import TargetRegistry


NEGATIVE_MARKERS = (
    "别",
    "不要",
    "不用",
    "先别",
    "不需要",
    "没让你",
    "不是让你",
    "不是叫你",
    "别扫",
    "别查",
    "不要扫",
    "不要查",
)
STATUS_ACTION_MARKERS = ("看", "查", "检查", "看看", "状态", "status")
STATUS_OBJECT_MARKERS = ("状态", "运行", "在线", "health", "status")
LOG_ACTION_MARKERS = ("扫", "查", "看", "检查", "分析", "找", "整理", "scan")
LOG_OBJECT_MARKERS = ("日志", "log", "logs", "报错", "错误", "异常", "error", "traceback", "crash")
CODEX_MARKERS = ("codex", "Codex", "用 Codex", "让 Codex", "交给 Codex", "调用 Codex")


READABLE_NEGATIVE_MARKERS = (
    "别",
    "不要",
    "不用",
    "先别",
    "不需要",
    "没让你",
    "不是让你",
    "不是叫你",
)
CODEX_META_DISCUSSION_MARKERS = (
    "说起来你运行codex",
    "运行codex好像",
    "codex好像",
    "codex每次都没成功",
    "codex没成功",
    "没成功的样子",
    "没跑顺",
    "怎么直接就开codex",
    "直接就开codex",
    "直接开codex",
    "怎么开codex",
    "为什么开codex",
    "为啥开codex",
    "开codex了",
    "开了codex",
    "又开codex",
    "又开了codex",
    "自动开codex",
    "自动开了codex",
    "误触发",
    "不是让你开codex",
    "没让你启动codex",
    "没让你开codex",
    "没让你用codex",
    "不是提到codex",
    "固定模板",
    "标准ai报告腔",
    "报告腔",
)
CODEX_DELEGATION_VERB_MARKERS = (
    "用codex",
    "用一下codex",
    "调用codex",
    "让codex",
    "叫codex",
    "交给codex",
    "开codex查",
    "开codex看",
    "开codex改",
    "启动codex查",
    "启动codex看",
    "codex查",
    "codex看",
    "codex检查",
    "codex分析",
    "codex改",
    "codex修",
    "codex跑",
    "codex测",
    "codex搜",
    "codex处理",
    "usecodex",
    "runcodex",
    "askcodex",
)
CODEX_CONCRETE_TASK_MARKERS = (
    "查",
    "看",
    "检查",
    "分析",
    "改",
    "修",
    "调试",
    "测试",
    "验证",
    "搜",
    "搜索",
    "读",
    "整理",
    "处理",
    "代码",
    "日志",
    "文件",
    "项目",
    "报错",
    "问题",
    "配置",
    "脚本",
    "启动问题",
) + LOG_ACTION_MARKERS + LOG_OBJECT_MARKERS


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker.lower() in text.lower() for marker in markers)


def _has_compact_any(compact: str, markers: tuple[str, ...]) -> bool:
    return any(_compact(marker) in compact for marker in markers if marker)


def _is_owner_private(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = bool(metadata.get("is_owner_user"))
    message_type = _safe_str(payload.get("message_type")).lower()
    group_id = _safe_str(payload.get("group_id")).strip()
    return is_owner and (message_type.startswith("private") or not group_id)


@dataclass
class RouteDecision:
    kind: str
    request: ToolRequest | None = None
    notes: list[str] = field(default_factory=list)
    reply_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "request": self.request.to_dict() if self.request else None,
            "notes": list(self.notes),
            "reply_hint": self.reply_hint,
        }


class ToolIntentRouter:
    def __init__(self, registry: TargetRegistry) -> None:
        self.registry = registry

    def route(self, text: str, payload: dict[str, Any], *, turn_id: str = "") -> RouteDecision:
        user_text = _safe_str(text).strip()
        if not user_text:
            return RouteDecision("no_action", notes=["empty_text"])
        if not _is_owner_private(payload):
            return RouteDecision("no_action", notes=["not_owner_private"])

        compact = _compact(user_text)
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        negative = any(marker in compact for marker in (_compact(item) for item in NEGATIVE_MARKERS + READABLE_NEGATIVE_MARKERS))
        if negative and (_has_any(user_text, LOG_ACTION_MARKERS + STATUS_ACTION_MARKERS) or "codex" in compact):
            return RouteDecision("blocked", notes=["negative_marker_blocked_tool_route"], reply_hint="好，我不动工具。")

        routed_turn_id = turn_id or new_turn_id()
        if bool(metadata.get("desktop_codex_mode")):
            return RouteDecision(
                "action_request",
                request=ToolRequest(
                    turn_id=routed_turn_id,
                    source="desktop_owner_private",
                    intent=ToolIntent("codex_delegate", 0.96, ["desktop_codex_mode", "owner_delegate_request"]),
                    tool="codex_delegate",
                    risk=DELEGATED_LOCAL_RISK,
                    params={"task_text": user_text},
                ),
                notes=["desktop_codex_mode"],
            )
        if compact.startswith("/status") or compact in {"status", "状态"}:
            return RouteDecision(
                "action_request",
                request=ToolRequest(
                    turn_id=routed_turn_id,
                    source="qq_owner_private",
                    intent=ToolIntent("status_probe", 0.99, ["explicit_status_command"]),
                    tool="status_probe",
                    risk=READ_ONLY_RISK,
                ),
                notes=["explicit_status"],
            )

        if self._looks_like_status_request(user_text):
            return RouteDecision(
                "action_request",
                request=ToolRequest(
                    turn_id=routed_turn_id,
                    source="qq_owner_private",
                    intent=ToolIntent("status_probe", 0.82, ["status_object", "owner_action_verb"]),
                    tool="status_probe",
                    risk=READ_ONLY_RISK,
                ),
                notes=["natural_status"],
            )

        codex_task = self._extract_codex_task(user_text)
        if codex_task:
            return RouteDecision(
                "action_request",
                request=ToolRequest(
                    turn_id=routed_turn_id,
                    source="qq_owner_private",
                    intent=ToolIntent("codex_delegate", 0.9, ["codex_marker", "owner_delegate_request"]),
                    tool="codex_delegate",
                    risk=DELEGATED_LOCAL_RISK,
                    params={"task_text": codex_task},
                ),
                notes=["codex_delegate"],
            )

        alias = self._registered_alias_in_text(user_text)
        if alias and _has_any(user_text, LOG_ACTION_MARKERS) and _has_any(user_text, LOG_OBJECT_MARKERS):
            return RouteDecision(
                "action_request",
                request=ToolRequest(
                    turn_id=routed_turn_id,
                    source="qq_owner_private",
                    intent=ToolIntent("local_inspect", 0.86, ["registered_alias", "log_object", "owner_action_verb"]),
                    tool="log_scan",
                    target=ToolTarget(alias=alias, time_hint="recent"),
                    risk=READ_ONLY_RISK,
                ),
                notes=["log_scan_alias"],
            )

        return RouteDecision("no_action", notes=["no_deterministic_tool_intent"])

    def _registered_alias_in_text(self, text: str) -> str:
        lowered = text.lower()
        for alias in sorted(self.registry.aliases(), key=len, reverse=True):
            if alias.lower() in lowered:
                return alias
        return ""

    def _looks_like_status_request(self, text: str) -> bool:
        return _has_any(text, STATUS_OBJECT_MARKERS) and _has_any(text, STATUS_ACTION_MARKERS)

    def _extract_codex_task(self, text: str) -> str:
        stripped = text.strip()
        compact = _compact(stripped)
        if compact.startswith("/codex"):
            return re.sub(r"(?is)^/codex", "", stripped, count=1).strip() or "检查当前本地任务"
        if "codex" not in compact:
            return ""
        if _has_compact_any(compact, CODEX_META_DISCUSSION_MARKERS):
            return ""
        if not _has_any(stripped, CODEX_MARKERS):
            return ""
        if not _has_compact_any(compact, CODEX_DELEGATION_VERB_MARKERS):
            return ""
        if _has_compact_any(compact, CODEX_CONCRETE_TASK_MARKERS) or re.search(
            r"(?i)(?:[a-z]:[\\/]|\\\\|https?://)",
            stripped,
        ):
            return stripped
        if not _has_any(stripped, ("检查", "查", "看", "分析", "构建", "失败", "项目", "代码", "日志", "运行", "测试", "修")):
            return ""
        return stripped
