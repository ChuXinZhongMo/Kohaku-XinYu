from __future__ import annotations

from typing import Any


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _sentences(items: list[Any], *, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for item in items[:limit]:
        text = _safe_str(item).strip()
        if text:
            lines.append(text.rstrip("。.!！"))
    return lines


def _state_is_tight(snapshot: dict[str, Any] | None) -> bool:
    if not isinstance(snapshot, dict):
        return False
    band = snapshot.get("affect_band")
    if not isinstance(band, dict):
        return False
    return _safe_str(band.get("fatigue")) in {"tired", "spent"} or _safe_str(band.get("closure")) == "withdrawn"


def _has_report(outcome: dict[str, Any]) -> bool:
    return bool(_safe_str(outcome.get("report_path")).strip())


def action_diagnosis(outcome: dict[str, Any]) -> dict[str, Any]:
    direct = outcome.get("diagnosis")
    if isinstance(direct, dict):
        return direct
    load = outcome.get("load") if isinstance(outcome.get("load"), dict) else {}
    value = load.get("diagnosis")
    return value if isinstance(value, dict) else {}


def diagnosis_issue_phrase(diagnosis: dict[str, Any], *, compact: bool = False) -> str:
    kind = _safe_str(diagnosis.get("kind"), "unknown")
    evidence = [_safe_str(item) for item in diagnosis.get("evidence", [])[:3] if _safe_str(item)] if isinstance(diagnosis.get("evidence"), list) else []
    if kind == "java_out_of_memory":
        if compact:
            return "Java 堆炸了"
        return "Java 堆炸了。日志里有 OutOfMemoryError，像是 JVM 内存给少了、模组泄漏，或者区块加载压得太狠"
    if kind == "auth_token_mismatch":
        if compact:
            return "鉴权没对上"
        return "鉴权没对上。核心返回 401 或 token 要求，先看 bridge token 和调用方请求头"
    if kind == "websocket_handshake_failed":
        if compact:
            return "WebSocket 握手没接上"
        return "WebSocket 握手没接上。先看连接地址、协议路径、服务是不是刚重启，还有鉴权"
    if kind == "connection_refused":
        if compact:
            return "目标端口没接住"
        return "目标端口没接住。对应服务大概率没在监听，先看进程还活不活"
    if kind == "timeout":
        if compact:
            return "请求超时"
        return "请求超时。像是服务卡住了，或者下游响应太慢"
    if kind == "runtime_exception":
        if compact:
            return "运行时异常"
        clue = f"最近一行是 {evidence[-1]}" if evidence else "需要看报告里的堆栈"
        return f"运行时异常。{clue}"
    if kind == "missing_path":
        if compact:
            return "路径没对上"
        return "路径没对上。先检查登记目录和实际日志位置"
    if kind == "no_recent_errors":
        return "最近 tail 里没看到明显错误"
    if kind == "warning_noise":
        return "主要是警告和失败关键词，还得看报告确认有没有实际影响"
    summary = _safe_str(diagnosis.get("summary")).strip().rstrip("。")
    for prefix in ("初步判断是", "初步看是", "主要是"):
        if summary.startswith(prefix):
            summary = summary[len(prefix):].lstrip()
            break
    return summary or "日志里有错误关键词，但还不能稳定归因"


def _log_scan_count_phrase(outcome: dict[str, Any], summary: list[str]) -> str:
    load = outcome.get("load") if isinstance(outcome.get("load"), dict) else {}
    try:
        error_lines = int(load.get("error_lines") or 0)
    except (TypeError, ValueError):
        error_lines = 0
    try:
        files_scanned = int(load.get("files_scanned") or 0)
    except (TypeError, ValueError):
        files_scanned = 0
    if error_lines > 0:
        return f"扫到 {error_lines} 条错误线，{files_scanned} 个文件"
    if files_scanned > 0:
        return f"扫了 {files_scanned} 个文件，最近 tail 没看到明显错误"
    for item in summary:
        if "发现" in item or "扫了" in item:
            return item
    return ""


def compose_action_reply(
    outcome: dict[str, Any],
    *,
    frame: dict[str, Any] | None = None,
    self_choice_public: dict[str, Any] | None = None,
    owner_urgency: str = "",
) -> str:
    tool = _safe_str(outcome.get("tool"))
    result = _safe_str(outcome.get("result"), "success")
    summary = _sentences(list(outcome.get("summary", [])), limit=3)
    tight = _state_is_tight(self_choice_public) and owner_urgency != "high"

    if result == "blocked_by_boundary":
        base = summary[0] if summary else "这个目标还没登记清楚，我先不动工具"
        return base.rstrip("。") + "。"

    if tool == "status_probe":
        parts = summary[:2] if tight else summary[:3]
        body = "；".join(part.rstrip("。") for part in parts if part)
        return (body or "我在线").rstrip("。") + "。"

    if not outcome.get("ok"):
        base = summary[0] if summary else "这次没有跑顺"
        if _has_report(outcome):
            return f"{base}。报告在 Outbox。"
        return base.rstrip("。") + "。"

    if tool == "external_plugin_call":
        base = summary[0] if summary else "external plugin completed"
        return base.rstrip(".!?") + "."

    if tool == "log_scan":
        diagnosis = action_diagnosis(outcome)
        issue = diagnosis_issue_phrase(diagnosis, compact=tight) if diagnosis else ""
        count = _log_scan_count_phrase(outcome, summary)
        boundary = "没碰未登记目录"
        tail = "报告丢到 Outbox 了。" if _has_report(outcome) else ""
        if issue:
            if tight:
                body = "；".join(part for part in (count, boundary) if part)
                residue = "先给结论。"
                return "".join(
                    part for part in ("扫完了。", issue.rstrip("。"), "。", body, "。" if body else "", tail, residue) if part
                )
            detail = "；".join(part for part in (count, boundary) if part)
            return "".join(
                part
                for part in (
                    "扫完了。",
                    issue.rstrip("。"),
                    "。",
                    detail,
                    "。" if detail else "",
                    tail,
                )
                if part
            )
        body = "；".join(summary[:2] if tight else summary[:3])
        tail = "报告丢到 Outbox 了。" if _has_report(outcome) else ""
        residue = "先给结论。" if tight else ""
        return "".join(part for part in ("扫完了。", body, "。" if body else "", tail, residue) if part)

    if tool == "codex_delegate":
        if _has_report(outcome):
            return "开了，我让 Codex 在专门窗口里查。报告会写到 Outbox。"
        return "开了，我让 Codex 在专门窗口里查。"

    body = "；".join(summary[:2] if tight else summary[:3])
    if body:
        return f"做完了。{body}。"
    return "做完了。"
