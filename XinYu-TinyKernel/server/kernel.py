from __future__ import annotations

import re
from typing import Any

from schemas import decision


NEGATIVE_MARKERS = ("别", "不要", "不用", "先别", "不需要", "没让你", "不是让你", "别开", "别查")
CODEX_MARKERS = ("codex", "用codex", "让codex", "调用codex", "交给codex", "开codex")
CODEX_TASK_MARKERS = (
    "查",
    "看",
    "检查",
    "分析",
    "改",
    "修",
    "测试",
    "验证",
    "项目",
    "代码",
    "日志",
    "文件",
    "check",
    "inspect",
    "analyze",
    "fix",
    "test",
    "project",
    "code",
    "log",
    "file",
)
STATUS_MARKERS = ("状态", "运行", "在线", "health", "status")
WAIT_MARKERS = ("等一下", "等下", "先等等", "没说完", "待会", "一会再说")
MEMORY_MARKERS = ("记住", "记下来", "作为目标", "长期记住", "偏好", "我希望", "我想")
API_DOWN_MARKERS = ("没有api", "api没了", "api 不可用", "没api", "外部api", "断api")
CLARIFY_MARKERS = (
    "处理一下",
    "继续那个",
    "那个继续",
    "搞一下",
    "修一下",
    "这个不对",
    "它坏了",
    "做下一步",
    "先做重要的",
    "把它弄完整",
    "修核心",
    "检查一下那个",
)


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    compact = _compact(text)
    return any(marker.lower() in lowered or _compact(marker) in compact for marker in markers)


def _capabilities(payload: dict[str, Any]) -> dict[str, Any]:
    caps = payload.get("capabilities")
    return caps if isinstance(caps, dict) else {}


def _allow_tool(payload: dict[str, Any]) -> bool:
    constraints = payload.get("constraints")
    if isinstance(constraints, dict) and constraints.get("allow_tool_request") is False:
        return False
    source = _safe_text(payload.get("source"))
    return source in {"owner_private", "desktop_owner_private", "local_test", ""}


def _memory_candidate_for(text: str) -> dict[str, Any] | None:
    if not _has_any(text, MEMORY_MARKERS):
        return None
    if ("?" in text or "？" in text) and not any(marker in text for marker in ("记住", "记下来", "我想", "我希望")):
        return None
    if len(text) < 8:
        return None
    return {"text": text[:180], "kind": "owner_goal_or_preference", "confidence": 0.72}


def decide(payload: dict[str, Any]) -> dict[str, Any]:
    text = _safe_text(payload.get("user_text"))
    if not text:
        return decision(mode="clarify", reply="你这句是空的。", confidence=0.78, notes=["rule_kernel", "empty_text"])

    compact = _compact(text)
    caps = _capabilities(payload)
    codex_available = bool(caps.get("codex_available", True))
    external_api_available = bool(caps.get("external_api_available", False))
    local_tools_available = bool(caps.get("local_tools_available", True))
    negative = _has_any(text, NEGATIVE_MARKERS)

    if _has_any(text, WAIT_MARKERS):
        return decision(mode="wait", reply="[WAITING]", confidence=0.88, notes=["rule_kernel", "wait_marker"])

    if _has_any(text, API_DOWN_MARKERS) or (not external_api_available and "复杂" in text and "api" in compact):
        return decision(
            mode="local_only_limitation",
            reply="外部 API 没了也能保留本地人格、记忆和简单工具判断；复杂推理和大代码任务会降级或排队。",
            confidence=0.82,
            notes=["rule_kernel", "api_unavailable"],
        )

    if _has_any(text, CLARIFY_MARKERS) and not _has_any(text, CODEX_MARKERS + STATUS_MARKERS + WAIT_MARKERS):
        return decision(
            mode="clarify",
            reply="你再说具体一点：对象是哪一个？",
            confidence=0.82,
            notes=["rule_kernel", "ambiguous_request"],
        )

    if negative and ("codex" in compact or _has_any(text, STATUS_MARKERS + CODEX_TASK_MARKERS)):
        return decision(mode="reply", reply="嗯，我不动工具。", confidence=0.86, notes=["rule_kernel", "negative_tool_block"])

    if _allow_tool(payload) and codex_available and _has_any(text, CODEX_MARKERS) and _has_any(text, CODEX_TASK_MARKERS):
        return decision(
            mode="codex_delegate",
            tool_request={"tool": "codex_delegate", "risk": "delegated_local", "task": text},
            confidence=0.9,
            notes=["rule_kernel", "codex_delegate"],
        )

    if _allow_tool(payload) and local_tools_available and _has_any(text, STATUS_MARKERS) and any(marker in text for marker in ("看", "查", "检查", "怎么样", "如何")):
        return decision(
            mode="status_probe",
            tool_request={"tool": "status_probe", "risk": "read_only", "task": text},
            confidence=0.84,
            notes=["rule_kernel", "status_probe"],
        )

    candidate = _memory_candidate_for(text)
    if candidate:
        return decision(
            mode="memory_candidate",
            reply="这个可以先作为候选记下来，等后面多轮确认再固化。",
            memory_candidates=[candidate],
            confidence=0.78,
            notes=["rule_kernel", "memory_candidate"],
        )

    if "?" in text or "？" in text:
        reply = "可以。先把范围压小一点，我按本地可运行、可回滚、可 shadow 的路线处理。"
    elif len(text) <= 8:
        reply = "嗯。"
    else:
        reply = "我明白。先按最小可运行版本推进，不直接动主链路。"
    return decision(mode="reply", reply=reply, confidence=0.68, notes=["rule_kernel", "default_reply"])
