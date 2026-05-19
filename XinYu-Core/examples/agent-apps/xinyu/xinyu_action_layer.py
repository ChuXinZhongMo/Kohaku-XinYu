from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_action_reply_composer import compose_action_reply
from xinyu_local_scope import default_local_scope_root, ensure_local_scope, resolve_local_scope_path
from xinyu_tool_intent_router import RouteDecision, ToolIntentRouter
from xinyu_tool_protocol import (
    ALLOWED_TOOLS,
    DELEGATED_LOCAL_RISK,
    EXTERNAL_RUNTIME_RISK,
    READ_ONLY_RISK,
    ActionOutcome,
    ToolRequest,
)
from xinyu_tool_targets import TargetRegistry, TargetRegistryError


MAX_LOG_FILES = 8
MAX_LOG_TAIL_BYTES = 256 * 1024
MAX_LOG_TOTAL_BYTES = 1024 * 1024
INTERESTING_LOG_RE = re.compile(
    r"(error|exception|traceback|timeout|timed out|failed|fatal|warn|错误|异常|报错|超时|失败|断开|崩)",
    re.IGNORECASE,
)


LOG_DIAGNOSIS_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "java_out_of_memory",
        re.compile(r"(outofmemoryerror|java\s+heap\s+space|gc\s+overhead\s+limit)", re.IGNORECASE),
        "初步判断是 Java 内存溢出，优先检查 JVM 内存参数、模组内存泄漏或区块加载压力",
    ),
    (
        "auth_token_mismatch",
        re.compile(r"(http\s*401|unauthori[sz]ed|requires[_-]?bridge[_-]?token|invalid\s+token)", re.IGNORECASE),
        "初步判断是鉴权/token 没对上，优先检查 bridge token 和调用方请求头",
    ),
    (
        "websocket_handshake_failed",
        re.compile(r"(opening\s+handshake\s+failed|websocket.*handshake|handshake.*websocket)", re.IGNORECASE),
        "初步判断是 WebSocket 握手失败，优先检查连接地址、服务是否刚重启、协议路径或鉴权",
    ),
    (
        "connection_refused",
        re.compile(r"(econnrefused|connection\s+refused|actively\s+refused|tcp\s+connect.*failed|端口.*拒绝)", re.IGNORECASE),
        "初步判断是目标服务或端口没在监听，优先检查对应进程是否还活着",
    ),
    (
        "timeout",
        re.compile(r"(timeout|timed\s+out|超时)", re.IGNORECASE),
        "初步判断是请求超时，优先看服务是否卡住或下游响应太慢",
    ),
    (
        "runtime_exception",
        re.compile(r"(traceback|exception|fatal|uncaught|异常)", re.IGNORECASE),
        "初步判断是运行时异常，需要看报告里的最近堆栈或异常行",
    ),
    (
        "missing_path",
        re.compile(r"(enoent|no\s+such\s+file|file\s+not\s+found|找不到|不存在)", re.IGNORECASE),
        "初步判断是路径或文件缺失，优先检查配置里的登记路径",
    ),
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _is_owner_private(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    message_type = _safe_str(payload.get("message_type")).lower()
    group_id = _safe_str(payload.get("group_id")).strip()
    return bool(metadata.get("is_owner_user")) and (message_type.startswith("private") or not group_id)


def _shorten(text: str, limit: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."


def _rel_label(path: Path, roots: list[Path]) -> str:
    for root in roots:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
    return path.name


def _read_tail(path: Path, limit: int) -> tuple[str, int]:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > limit:
            handle.seek(-limit, 2)
        data = handle.read(limit)
    return data.decode("utf-8", errors="replace"), min(size, limit)


def _diagnose_log_lines(interesting: list[dict[str, str]], *, error_lines: int) -> dict[str, Any]:
    if error_lines <= 0:
        return {
            "kind": "no_recent_errors",
            "confidence": 0.72,
            "summary": "最近 tail 里没有看到明显 ERROR/Traceback/超时关键词",
            "evidence": [],
        }
    recent_texts = [_safe_str(item.get("text")) for item in interesting[-12:] if _safe_str(item.get("text"))]
    all_text = "\n".join(recent_texts)
    for kind, pattern, summary in LOG_DIAGNOSIS_RULES:
        evidence = [text for text in recent_texts if pattern.search(text)]
        if evidence:
            confidence = 0.78 if len(evidence) >= 2 else 0.68
            return {
                "kind": kind,
                "confidence": confidence,
                "summary": summary,
                "evidence": evidence[:3],
            }
    if re.search(r"(warn|warning|警告)", all_text, re.IGNORECASE):
        return {
            "kind": "warning_noise",
            "confidence": 0.55,
            "summary": "主要是警告/失败关键词，需要看报告确认是否真的影响运行",
            "evidence": recent_texts[-3:],
        }
    return {
        "kind": "generic_error_lines",
        "confidence": 0.5,
        "summary": "日志里有错误关键词，但第一层规则还不能稳定归因，需要看报告里的最近片段",
        "evidence": recent_texts[-3:],
    }


class XinyuActionLayer:
    def __init__(self, root: Path, *, registry: TargetRegistry | None = None) -> None:
        self.root = root.resolve()
        self.registry = registry or TargetRegistry.load(self.root)
        self.router = ToolIntentRouter(self.registry)

    def route(self, payload: dict[str, Any], text: str, *, turn_id: str = "") -> RouteDecision:
        return self.router.route(text, payload, turn_id=turn_id)

    def execute(
        self,
        request: ToolRequest | dict[str, Any],
        payload: dict[str, Any],
        *,
        bridge_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        req = request if isinstance(request, ToolRequest) else ToolRequest.from_dict(request)
        started = time.perf_counter()
        blocked = self.validate(req, payload)
        if blocked is not None:
            blocked.duration_ms = int((time.perf_counter() - started) * 1000)
            return blocked.to_dict()
        try:
            if req.tool == "status_probe":
                outcome = self._execute_status_probe(req, bridge_snapshot=bridge_snapshot)
            elif req.tool == "log_scan":
                outcome = self._execute_log_scan(req)
            elif req.tool == "codex_delegate":
                outcome = ActionOutcome.failed(
                    tool=req.tool,
                    summary="codex_delegate must be executed by Core Bridge runtime",
                    error_code="external_executor_required",
                    risk=DELEGATED_LOCAL_RISK,
                )
            elif req.tool == "external_plugin_call":
                outcome = ActionOutcome.failed(
                    tool=req.tool,
                    summary="external_plugin_call must be executed by Core Bridge runtime",
                    error_code="external_executor_required",
                    risk=EXTERNAL_RUNTIME_RISK,
                )
            else:
                outcome = ActionOutcome.blocked(
                    tool=req.tool,
                    summary=f"工具 {req.tool} 不在第一版白名单里。",
                    error_code="tool_not_whitelisted",
                    risk=req.risk,
                )
        except Exception as exc:
            outcome = ActionOutcome.failed(
                tool=req.tool,
                target_alias=req.target.alias,
                summary=f"{req.tool} 没有跑顺：{type(exc).__name__}",
                error_code=type(exc).__name__,
                risk=req.risk,
                notes=["executor_exception"],
            )
        outcome.duration_ms = int((time.perf_counter() - started) * 1000)
        return outcome.to_dict()

    def validate(self, request: ToolRequest, payload: dict[str, Any]) -> ActionOutcome | None:
        if request.protocol != "xinyu.tool.v1":
            return ActionOutcome.blocked(
                tool=request.tool,
                summary="工具请求协议不对，我先不执行。",
                error_code="invalid_protocol",
                risk=request.risk,
            )
        if not _is_owner_private(payload):
            return ActionOutcome.blocked(
                tool=request.tool,
                summary="这类本机行动只接受 owner 私聊触发。",
                error_code="not_owner_private",
                risk=request.risk,
            )
        if request.tool not in ALLOWED_TOOLS:
            return ActionOutcome.blocked(
                tool=request.tool,
                summary=f"工具 {request.tool} 不在第一版白名单里。",
                error_code="tool_not_whitelisted",
                risk=request.risk,
            )
        if request.risk not in {READ_ONLY_RISK, DELEGATED_LOCAL_RISK, EXTERNAL_RUNTIME_RISK}:
            return ActionOutcome.blocked(
                tool=request.tool,
                summary="这个风险等级第一版不接。",
                error_code="risk_not_allowed",
                risk=request.risk,
            )
        if request.tool == "log_scan":
            alias = request.target.alias
            try:
                self.registry.resolve_read_roots(alias)
            except TargetRegistryError as exc:
                return ActionOutcome.blocked(
                    tool=request.tool,
                    target_alias=alias,
                    summary=self._registry_block_reply(alias, exc),
                    error_code=self._registry_error_code(exc),
                    risk=request.risk,
                    notes=["target_registry_blocked"],
                )
        return None

    def _registry_error_code(self, exc: TargetRegistryError) -> str:
        text = str(exc)
        if "not registered" in text:
            return "target_not_registered"
        if "owner setup" in text or "no registered read roots" in text:
            return "target_setup_required"
        return "target_not_available"

    def _registry_block_reply(self, alias: str, exc: TargetRegistryError) -> str:
        code = self._registry_error_code(exc)
        if code == "target_not_registered":
            return f"{alias or '这个目标'} 还没登记，我先不乱扫。你把目录给我一次，之后我再认。"
        if code == "target_setup_required":
            return f"{alias or '这个目标'} 的日志目录还没登记，我先不乱扫。你把目录给我一次，之后我就认得了。"
        return f"{alias or '这个目标'} 现在不可用，我先不碰未确认路径。"

    def _execute_status_probe(self, request: ToolRequest, *, bridge_snapshot: dict[str, Any] | None) -> ActionOutcome:
        from xinyu_status import check_ports, check_qq_gateway_config, check_state, status_fields

        checks = []
        reply_style = _safe_str(request.params.get("reply_style"), "casual_status")
        technical_reply = reply_style == "technical_status"
        if bridge_snapshot:
            core_ok = bool(bridge_snapshot.get("ok")) and not bool(bridge_snapshot.get("closed"))
            version = _safe_str(bridge_snapshot.get("version"), "unknown")
            sessions = _safe_str(bridge_snapshot.get("sessions"), "unknown")
            if technical_reply:
                core_summary = f"Core Bridge 在线，version={version}，sessions={sessions}"
            else:
                core_summary = "我在线，core 正常" if core_ok else "core 现在还不稳"
        else:
            core_ok = True
            version = "unknown"
            sessions = "unknown"
            core_summary = "Core Bridge 源码可读" if technical_reply else "我在线，core 源码可读"
        checks.extend(check_ports())
        checks.extend(check_qq_gateway_config(self.root, self.root / "xinyu_qq_gateway.config.json"))
        checks.extend(check_state(self.root))
        warn = [check for check in checks if not check.ok and check.name != "dispatch_state"]
        port_warn_names = {"xinyu_qq_gateway_6199", "napcat_webui_6099", "napcat_to_xinyu_qq_gateway_ws"}
        port_warn = [check for check in warn if check.name in port_warn_names]
        other_warn_count = len([check for check in warn if check.name not in port_warn_names])
        fields = status_fields(self.root)
        if technical_reply:
            qq_line = "QQ gateway 和 NapCat 连接正常" if not warn else f"发现 {len(warn)} 个状态警告"
        elif port_warn:
            qq_line = "QQ/NapCat 这台机器现在没接"
            if other_warn_count:
                qq_line += f"，另外 {other_warn_count} 个状态警告"
        elif other_warn_count:
            qq_line = f"发现 {other_warn_count} 个状态警告"
        else:
            qq_line = "QQ/NapCat 连接正常"
        queued = fields.get("qq_outbox_queued", "missing")
        failed = fields.get("qq_outbox_failed", "missing")
        outbox_line = (
            f"QQ outbox queued={queued} failed={failed}"
            if technical_reply
            else f"待发队列 {queued}，失败 {failed}"
        )
        summary = [core_summary, qq_line, outbox_line]
        return ActionOutcome(
            ok=core_ok and not warn,
            tool=request.tool,
            summary=summary,
            risk=READ_ONLY_RISK,
            result="success" if core_ok and not warn else "failure",
            load={
                "checks": len(checks) + 1,
                "warnings": len(warn),
                "timeout": False,
                "reply_style": reply_style,
                "core_version": version,
                "sessions": sessions,
            },
            notes=["status_probe_read_only", f"status_reply_style:{reply_style}"],
        )

    def _execute_log_scan(self, request: ToolRequest) -> ActionOutcome:
        alias = request.target.alias
        resolved = self.registry.resolve_read_roots(alias)
        roots = list(resolved.roots)
        files = self.registry.iter_log_files(alias, max_files=MAX_LOG_FILES)
        if not files:
            return ActionOutcome(
                ok=True,
                tool=request.tool,
                target_alias=alias,
                summary=[f"{alias} 已登记，但没有找到匹配的日志文件。"],
                risk=READ_ONLY_RISK,
                result="success",
                load={"files_scanned": 0, "bytes_scanned": 0, "error_lines": 0, "timeout": False},
                notes=["log_scan_no_files"],
            )

        interesting: list[dict[str, str]] = []
        bytes_scanned = 0
        files_scanned = 0
        for file_path in files:
            if bytes_scanned >= MAX_LOG_TOTAL_BYTES:
                break
            try:
                tail, read_bytes = _read_tail(file_path, min(MAX_LOG_TAIL_BYTES, MAX_LOG_TOTAL_BYTES - bytes_scanned))
            except OSError:
                continue
            bytes_scanned += read_bytes
            files_scanned += 1
            label = _rel_label(file_path, roots)
            for line_no, line in enumerate(tail.splitlines(), start=1):
                if INTERESTING_LOG_RE.search(line):
                    interesting.append({"file": label, "line": str(line_no), "text": _shorten(line, 260)})
                    if len(interesting) >= 40:
                        break
            if len(interesting) >= 40:
                break

        error_lines = len(interesting)
        diagnosis = _diagnose_log_lines(interesting, error_lines=error_lines)
        report_path = self._write_log_report(
            alias,
            roots,
            files[:files_scanned],
            interesting,
            bytes_scanned,
            diagnosis=diagnosis,
        )
        if error_lines:
            first = interesting[-1]["text"] if interesting else ""
            summary = [
                _safe_str(diagnosis.get("summary")) or "初步判断还不稳定",
                f"发现 {error_lines} 条错误/异常/超时关键词，涉及 {files_scanned} 个文件",
                f"最近片段：{first}" if first else "最近片段已写入报告",
            ]
        else:
            summary = [
                _safe_str(diagnosis.get("summary")) or "最近 tail 里没有看到明显错误",
                f"扫了 {files_scanned} 个登记日志文件",
            ]
        summary.append("没有扫描未登记目录")
        return ActionOutcome(
            ok=True,
            tool=request.tool,
            target_alias=alias,
            summary=summary,
            report_path=str(report_path),
            risk=READ_ONLY_RISK,
            result="success",
            load={
                "files_scanned": files_scanned,
                "bytes_scanned": bytes_scanned,
                "error_lines": error_lines,
                "timeout": False,
                "diagnosis": diagnosis,
            },
            notes=["log_scan_read_only", "registered_target_only"],
        )

    def _write_log_report(
        self,
        alias: str,
        roots: list[Path],
        files: list[Path],
        interesting: list[dict[str, str]],
        bytes_scanned: int,
        *,
        diagnosis: dict[str, Any],
    ) -> Path:
        scope = ensure_local_scope(default_local_scope_root(self.root))
        outbox = resolve_local_scope_path(scope, "Outbox")
        stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
        report_path = outbox / f"action-log-scan-{alias}-{stamp}.md"
        file_lines = "\n".join(f"- {_rel_label(path, roots)}" for path in files) or "- none"
        if interesting:
            interesting_lines = "\n".join(
                f"- `{item['file']}:{item['line']}` {item['text']}" for item in interesting[:24]
            )
        else:
            interesting_lines = "- none"
        diagnosis_evidence = diagnosis.get("evidence") if isinstance(diagnosis.get("evidence"), list) else []
        evidence_lines = "\n".join(f"- {text}" for text in diagnosis_evidence[:3]) or "- none"
        text = f"""---
title: XinYu Action Log Scan Report
request_type: action_layer_log_scan
target_alias: {alias}
created_at: {datetime.now().astimezone().isoformat(timespec="seconds")}
---

# XinYu Action Log Scan Report

## Boundary

- target_alias: {alias}
- read_policy: registered_target_tail_only
- bytes_scanned: {bytes_scanned}
- raw_stdout_stderr_in_memory: false

## Files

{file_lines}

## Diagnosis

- kind: {_safe_str(diagnosis.get("kind"), "unknown")}
- confidence: {_safe_str(diagnosis.get("confidence"), "0")}
- summary: {_safe_str(diagnosis.get("summary"), "none")}

## Diagnosis Evidence

{evidence_lines}

## Interesting Lines

{interesting_lines}
"""
        report_path.write_text(text, encoding="utf-8")
        return report_path


def codex_response_to_outcome(response: dict[str, Any], request: ToolRequest | dict[str, Any]) -> dict[str, Any]:
    req = request if isinstance(request, ToolRequest) else ToolRequest.from_dict(request)
    accepted = bool(response.get("accepted"))
    report_path = _safe_str(response.get("report_path"))
    summary = [_safe_str(response.get("reply"), "Codex 委派已提交").strip() or "Codex 委派已提交"]
    if report_path:
        summary.append("报告路径已由 Codex delegate 预留")
    return ActionOutcome(
        ok=accepted,
        tool="codex_delegate",
        target_alias=req.target.alias,
        summary=summary,
        report_path=report_path,
        risk=DELEGATED_LOCAL_RISK,
        result="success" if accepted else "failure",
        load={
            "scheduled": accepted,
            "codex_exit_code": response.get("codex_exit_code"),
            "timeout": bool(response.get("codex_timed_out")),
        },
        error_code="" if accepted else "codex_delegate_rejected",
        notes=[_safe_str(note) for note in response.get("notes", [])[:6]],
    ).to_dict()


def external_response_to_outcome(response: dict[str, Any], request: ToolRequest | dict[str, Any]) -> dict[str, Any]:
    req = request if isinstance(request, ToolRequest) else ToolRequest.from_dict(request)
    accepted = bool(response.get("accepted") or response.get("ok"))
    plugin_id = _safe_str(response.get("plugin_id"), req.target.alias or "external")
    capability = _safe_str(response.get("capability"), "unknown")
    summary_value = response.get("summary")
    if isinstance(summary_value, list):
        summary = [_safe_str(item) for item in summary_value if _safe_str(item)]
    else:
        summary = []
    if not summary:
        if accepted:
            summary = [f"{plugin_id}:{capability} completed"]
        else:
            reason = _safe_str(response.get("error_code") or response.get("result"), "external_plugin_failed")
            summary = [f"{plugin_id}:{capability} failed: {reason}"]
    result = _safe_str(response.get("result"), "success" if accepted else "failure")
    return ActionOutcome(
        ok=accepted,
        tool="external_plugin_call",
        target_alias=plugin_id,
        summary=summary,
        risk=_safe_str(req.risk, EXTERNAL_RUNTIME_RISK),
        result=result,
        load={
            "plugin_id": plugin_id,
            "capability": capability,
            "prepared": response.get("prepared") if isinstance(response.get("prepared"), dict) else {},
            "execution": response.get("execution") if isinstance(response.get("execution"), dict) else {},
        },
        error_code="" if accepted else _safe_str(response.get("error_code"), "external_plugin_failed"),
        notes=[_safe_str(note) for note in response.get("notes", [])[:8]],
    ).to_dict()


def compose_reply_for_outcome(
    outcome: dict[str, Any],
    *,
    frame: dict[str, Any] | None = None,
    self_choice_public: dict[str, Any] | None = None,
) -> str:
    return compose_action_reply(outcome, frame=frame, self_choice_public=self_choice_public)
