from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_action_reply_composer import diagnosis_issue_phrase
from xinyu_visible_text_sanitizer import (
    sanitize_visible_text,
    visible_action_pressure_label,
    visible_action_result_label,
    visible_action_theme_label,
)


RESIDUE_REL = Path("runtime/life_kernel/action_experience_residue.jsonl")
RECENT_ACTION_REL = Path("runtime/life_kernel/recent_action_experience.jsonl")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _bounded_float(value: Any, *, default: float = 0.0, floor: float = 0.0, ceiling: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(min(ceiling, max(floor, number)), 3)


def _band(score: float) -> str:
    if score < 0.25:
        return "low"
    if score < 0.65:
        return "medium"
    return "high"


def _result_from_outcome(outcome: dict[str, Any]) -> str:
    result = _safe_str(outcome.get("result")).strip()
    if result:
        return result
    return "success" if outcome.get("ok") else "failure"


def _pressure(outcome: dict[str, Any]) -> dict[str, Any]:
    load = outcome.get("load") if isinstance(outcome.get("load"), dict) else {}
    result = _result_from_outcome(outcome)
    reasons: list[str] = ["owner_requested_action"]
    score = 0.12
    if result == "blocked_by_boundary":
        score = 0.22
        reasons.append("boundary_held")
    elif not outcome.get("ok"):
        score = 0.44
        reasons.append("tool_failed")

    error_lines = int(load.get("error_lines") or 0)
    if error_lines:
        score += min(0.25, error_lines / 80.0)
        reasons.append("error_lines")
    files_scanned = int(load.get("files_scanned") or 0)
    if files_scanned > 4:
        score += 0.04
        reasons.append("multi_file_scan")
    if bool(load.get("timeout")):
        score += 0.32
        reasons.append("timeout")
    duration_ms = int(outcome.get("duration_ms") or 0)
    if duration_ms > 30000:
        score += 0.16
        reasons.append("long_action")
    score = _bounded_float(score)
    return {"score": score, "band": _band(score), "reasons": reasons}


def _affect_impulse(result: str, pressure: dict[str, Any]) -> dict[str, Any]:
    band = _safe_str(pressure.get("band"), "low")
    reasons = set(pressure.get("reasons") if isinstance(pressure.get("reasons"), list) else [])
    if result == "blocked_by_boundary":
        return {"fatigue_delta": 0.0, "closure_delta": 0.015, "urge_delta": 0.01, "cue": "boundary_held"}
    if "timeout" in reasons:
        return {"fatigue_delta": 0.075, "closure_delta": 0.04, "urge_delta": 0.0, "cue": "stalled_in_action"}
    if result != "success":
        return {"fatigue_delta": 0.05, "closure_delta": 0.035, "urge_delta": 0.0, "cue": "task_failed_residue"}
    if band == "low":
        return {"fatigue_delta": 0.01, "closure_delta": -0.01, "urge_delta": 0.0, "cue": "small_task_finished"}
    if band == "medium":
        return {"fatigue_delta": 0.035, "closure_delta": 0.008, "urge_delta": 0.008, "cue": "worked_through_noise"}
    return {"fatigue_delta": 0.06, "closure_delta": 0.02, "urge_delta": 0.004, "cue": "worked_through_noise"}


def _memory_candidates(request: dict[str, Any], outcome: dict[str, Any], result: str) -> list[str]:
    tool = _safe_str(outcome.get("tool") or request.get("tool"))
    target_alias = _safe_str(outcome.get("target_alias") or (request.get("target") or {}).get("alias"))
    summary = [str(item) for item in outcome.get("summary", [])[:2]]
    candidates: list[str] = []
    if tool == "status_probe" and result == "success":
        candidates.append("owner asked XinYu to inspect local runtime status")
    elif tool == "log_scan" and result == "success":
        candidates.append(f"owner asked XinYu to inspect registered logs: {target_alias or 'unknown'}")
    elif result == "blocked_by_boundary":
        candidates.append(f"XinYu held a tool boundary for target: {target_alias or 'unknown'}")
    elif tool == "codex_delegate":
        candidates.append("owner delegated a bounded local task to Codex through XinYu")
    for item in summary:
        cleaned = item.replace("\\", "/")
        if len(cleaned) > 160:
            cleaned = cleaned[:157] + "..."
        candidates.append(cleaned)
    return candidates[:4]


class ExperienceReducer:
    def reduce(self, request: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
        result = _result_from_outcome(outcome)
        pressure = _pressure(outcome)
        tool = _safe_str(outcome.get("tool") or request.get("tool"))
        target = request.get("target") if isinstance(request.get("target"), dict) else {}
        target_alias = _safe_str(outcome.get("target_alias") or target.get("alias"))
        salience = 0.25 + pressure["score"] * 0.6
        if tool in {"log_scan", "codex_delegate"}:
            salience += 0.08
        if result in {"failure", "blocked_by_boundary"}:
            salience += 0.08
        salience = _bounded_float(salience)
        load = outcome.get("load") if isinstance(outcome.get("load"), dict) else {}
        return {
            "experience_id": f"exp-{uuid.uuid4().hex[:16]}",
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_turn_id": _safe_str(request.get("turn_id")),
            "action_id": _safe_str(outcome.get("action_id")),
            "tool": tool,
            "target_alias": target_alias,
            "result": result,
            "risk": _safe_str(outcome.get("risk"), "read_only"),
            "duration_ms": int(outcome.get("duration_ms") or 0),
            "load": dict(load),
            "pressure": pressure,
            "salience": salience,
            "memory_candidates": _memory_candidates(request, outcome, result),
            "affect_impulse": _affect_impulse(result, pressure),
            "notes": ["experience_frame_v1", "no_direct_stable_memory_write"],
        }


def build_experience_frame(request: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    return ExperienceReducer().reduce(request, outcome)


def write_action_experience_residue(
    root: Path,
    frame: dict[str, Any],
    outcome: dict[str, Any],
    *,
    salience_threshold: float = 0.6,
) -> dict[str, Any]:
    salience = _bounded_float(frame.get("salience"))
    if salience < salience_threshold:
        return {"written": False, "notes": ["action_residue_low_salience"]}
    path = root / RESIDUE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "experience_id": _safe_str(frame.get("experience_id")),
        "created_at": _safe_str(frame.get("created_at")),
        "tool": _safe_str(frame.get("tool")),
        "target_alias": _safe_str(frame.get("target_alias")),
        "result": _safe_str(frame.get("result")),
        "pressure": frame.get("pressure") if isinstance(frame.get("pressure"), dict) else {},
        "salience": salience,
        "memory_candidates": list(frame.get("memory_candidates", [])[:3]),
        "outcome_summary": list(outcome.get("summary", [])[:3]),
        "notes": ["dream_reflection_residue_candidate", "stdout_stderr_not_included"],
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {"written": True, "path": str(path), "notes": ["action_residue_written"]}


def write_recent_action_experience(
    root: Path,
    frame: dict[str, Any],
    outcome: dict[str, Any],
    *,
    max_rows: int = 12,
) -> dict[str, Any]:
    path = root / RECENT_ACTION_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _load_recent_rows(path)
    row = {
        "experience_id": _safe_str(frame.get("experience_id")),
        "created_at": _safe_str(frame.get("created_at")),
        "source_turn_id": _safe_str(frame.get("source_turn_id")),
        "tool": _safe_str(frame.get("tool")),
        "target_alias": _safe_str(frame.get("target_alias")),
        "result": _safe_str(frame.get("result")),
        "risk": _safe_str(frame.get("risk")),
        "pressure": frame.get("pressure") if isinstance(frame.get("pressure"), dict) else {},
        "salience": _bounded_float(frame.get("salience")),
        "load": _compact_recent_load(outcome),
        "summary": [_safe_str(item) for item in outcome.get("summary", [])[:3] if _safe_str(item)],
        "diagnosis": _outcome_diagnosis(outcome),
        "report_available": bool(_safe_str(outcome.get("report_path")).strip()),
        "memory_candidates": [_safe_str(item) for item in frame.get("memory_candidates", [])[:3] if _safe_str(item)],
        "notes": ["recent_action_experience_v1", "prompt_callback_context"],
    }
    rows.append(row)
    rows = rows[-max(1, max_rows):]
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in rows),
        encoding="utf-8",
    )
    return {"written": True, "path": str(path), "notes": ["recent_action_experience_written"]}


def read_recent_action_context(root: Path, *, limit: int = 3) -> str:
    path = root / RECENT_ACTION_REL
    rows = _load_recent_rows(path)
    if not rows:
        return ""
    recent = rows[-max(1, limit):]
    lines = [
        "recent action sidecar:",
        (
            "These are XinYu's most recent bounded local actions. If the owner asks "
            "what you just saw, what the main problem was, whether it finished, or "
            "uses 刚才/刚刚/主要问题/怎么样, answer from this sidecar before older recalled context."
        ),
    ]
    for row in reversed(recent):
        tool = _safe_str(row.get("tool"), "unknown")
        target = _safe_str(row.get("target_alias")) or "none"
        action_label = visible_action_theme_label(f"local action pressure after {tool}:{target}")
        result = visible_action_result_label(row.get("result"))
        pressure = row.get("pressure") if isinstance(row.get("pressure"), dict) else {}
        pressure_band = visible_action_pressure_label(pressure.get("band"))
        diagnosis = row.get("diagnosis") if isinstance(row.get("diagnosis"), dict) else {}
        diagnosis_text = sanitize_visible_text(_safe_str(diagnosis.get("summary")).strip())
        summary = [
            sanitize_visible_text(item)
            for item in row.get("summary", [])[:3]
            if _safe_str(item) and sanitize_visible_text(item) != diagnosis_text
        ][:2]
        summary_text = " | ".join(summary) if summary else "no visible summary"
        if diagnosis_text:
            summary_text = f"{diagnosis_text} | {summary_text}"
        report = " report=Outbox" if row.get("report_available") else ""
        lines.append(f"- 行动={action_label} 结果={result} 负载={pressure_band}{report}; summary={summary_text}")
    return "\n".join(lines)


def compose_recent_action_followup(
    root: Path,
    text: str,
    *,
    max_age_seconds: int = 15 * 60,
) -> dict[str, Any] | None:
    mode = _recent_action_followup_mode(text)
    if not mode:
        return None
    row = _select_recent_action_row(root / RECENT_ACTION_REL, mode=mode, max_age_seconds=max_age_seconds)
    if not row:
        return None

    tool = _safe_str(row.get("tool"), "unknown")
    target = _safe_str(row.get("target_alias"))
    result = _safe_str(row.get("result"), "unknown")
    summary = [_safe_str(item) for item in row.get("summary", []) if _safe_str(item)]
    diagnosis = row.get("diagnosis") if isinstance(row.get("diagnosis"), dict) else {}
    diagnosis_summary = _safe_str(diagnosis.get("summary")).strip()
    report_available = bool(row.get("report_available"))
    summary_text = "；".join(summary[:3]) if summary else "刚才那次没有留下可见摘要"

    if result == "blocked_by_boundary":
        target_text = target or "那个目标"
        reply = f"刚才是边界拦住了：{target_text} 还没登记，我没有乱扫。"
    elif tool == "status_probe":
        if mode == "main_issue":
            reply = f"主要没看到异常。刚才看的是运行状态：{summary_text}。"
        else:
            reply = f"刚才看的是运行状态：{summary_text}。"
    elif tool == "log_scan":
        target_text = target or "日志"
        if mode == "main_issue":
            if diagnosis:
                issue = diagnosis_issue_phrase(diagnosis, compact=False)
                spacer = " " if issue[:1].isascii() and issue[:1].isalnum() else ""
                reply = f"主要是{spacer}{issue.rstrip('。')}"
                detail = _recent_log_count_phrase(row, target_text)
                if not detail:
                    detail = next((item for item in summary if item != diagnosis_summary), "")
                if detail:
                    reply += f"。{detail}"
                reply += "。"
            elif diagnosis_summary:
                issue = _main_issue_phrase(diagnosis_summary)
                spacer = " " if issue[:1].isascii() and issue[:1].isalnum() else ""
                reply = f"主要是{spacer}{issue}"
                detail = next((item for item in summary if item != diagnosis_summary), "")
                if detail:
                    reply += f"；{target_text} 里{detail}"
                reply += "。"
            elif summary:
                reply = f"主要是 {target_text} 里{summary[0]}"
                if len(summary) > 1:
                    reply += f"；{summary[1]}"
                reply += "。"
            else:
                reply = f"主要问题在 {target_text} 的日志扫描结果里，但这次没有留下摘要。"
        else:
            reply = f"刚才扫的是 {target_text}：{summary_text}。"
        if report_available and "报告" not in reply:
            reply += "报告丢到 Outbox 了。"
    elif tool == "codex_delegate":
        if mode == "main_issue":
            reply = f"主要是 Codex 那次委派的结果：{summary_text}。"
        else:
            reply = f"刚才看到的是 Codex 委派结果：{summary_text}。"
    else:
        reply = f"刚才那次本地动作是 {tool}"
        if target:
            reply += f":{target}"
        reply += f"，结果是 {result}：{summary_text}。"

    return {
        "reply": reply,
        "row": row,
        "mode": mode,
        "notes": [
            "recent_action_followup_matched",
            f"recent_action_followup_mode:{mode}",
            f"recent_action_followup_tool:{tool}",
        ],
    }


def _load_recent_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def _compact_recent_load(outcome: dict[str, Any]) -> dict[str, Any]:
    load = outcome.get("load") if isinstance(outcome.get("load"), dict) else {}
    compact: dict[str, Any] = {}
    for key in ("files_scanned", "error_lines", "timeout"):
        if key in load:
            compact[key] = load.get(key)
    return compact


def _recent_log_count_phrase(row: dict[str, Any], target_text: str) -> str:
    load = row.get("load") if isinstance(row.get("load"), dict) else {}
    try:
        error_lines = int(load.get("error_lines") or 0)
    except (TypeError, ValueError):
        error_lines = 0
    try:
        files_scanned = int(load.get("files_scanned") or 0)
    except (TypeError, ValueError):
        files_scanned = 0
    if error_lines > 0:
        return f"{target_text} 扫到 {error_lines} 条错误线，{files_scanned} 个文件"
    if files_scanned > 0:
        return f"{target_text} 扫了 {files_scanned} 个文件，最近 tail 没看到明显错误"
    return ""


def _outcome_diagnosis(outcome: dict[str, Any]) -> dict[str, Any]:
    direct = outcome.get("diagnosis")
    if isinstance(direct, dict):
        return {
            "kind": _safe_str(direct.get("kind"), "unknown"),
            "confidence": _bounded_float(direct.get("confidence"), default=0.0),
            "summary": _safe_str(direct.get("summary")),
            "evidence": [_safe_str(item) for item in direct.get("evidence", [])[:3] if _safe_str(item)]
            if isinstance(direct.get("evidence"), list)
            else [],
        }
    load = outcome.get("load") if isinstance(outcome.get("load"), dict) else {}
    value = load.get("diagnosis")
    if not isinstance(value, dict):
        return {}
    return {
        "kind": _safe_str(value.get("kind"), "unknown"),
        "confidence": _bounded_float(value.get("confidence"), default=0.0),
        "summary": _safe_str(value.get("summary")),
        "evidence": [_safe_str(item) for item in value.get("evidence", [])[:3] if _safe_str(item)]
        if isinstance(value.get("evidence"), list)
        else [],
    }


def _main_issue_phrase(text: str) -> str:
    cleaned = _safe_str(text).strip().rstrip("。")
    for prefix in ("初步判断是", "初步看是", "主要是"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip()
            break
    return cleaned or "刚才那次日志扫描结果"


def _recent_action_followup_mode(text: str) -> str:
    compact = re.sub(r"\s+", "", _safe_str(text)).lower()
    if not compact:
        return ""
    main_issue_markers = (
        "主要问题",
        "问题是什么",
        "什么问题",
        "哪里有问题",
        "哪有问题",
        "报错是什么",
        "什么报错",
        "错误是什么",
        "异常是什么",
    )
    if any(marker in compact for marker in main_issue_markers):
        return "main_issue"
    if "所以" in compact and any(marker in compact for marker in ("问题", "报错", "错误", "异常")):
        return "main_issue"
    if any(marker in compact for marker in ("有没有报错", "有没有错误", "有没有异常")):
        return "main_issue"

    what_markers = (
        "刚刚看到什么",
        "刚才看到什么",
        "刚看到什么",
        "看到了什么",
        "看到啥",
        "发现什么",
        "扫到什么",
        "查到什么",
    )
    if any(marker in compact for marker in what_markers):
        return "what_saw"

    status_markers = (
        "结果呢",
        "结果是什么",
        "怎么样",
        "咋样",
        "完成了吗",
        "跑完了吗",
        "扫完了吗",
        "看完了吗",
    )
    if any(marker in compact for marker in status_markers) and any(
        marker in compact for marker in ("刚", "刚才", "刚刚", "扫", "查", "看", "结果", "完成", "跑完")
    ):
        return "result"
    return ""


def _select_recent_action_row(path: Path, *, mode: str, max_age_seconds: int) -> dict[str, Any] | None:
    rows = _load_recent_rows(path)
    if not rows:
        return None
    now = datetime.now().astimezone()
    fresh: list[dict[str, Any]] = []
    for row in rows:
        created_at = _safe_str(row.get("created_at"))
        try:
            created = datetime.fromisoformat(created_at)
        except ValueError:
            continue
        if created.tzinfo is None:
            created = created.astimezone()
        age_seconds = (now - created).total_seconds()
        if 0 <= age_seconds <= max_age_seconds:
            fresh.append(row)
    if not fresh:
        return None
    if mode == "main_issue":
        for row in reversed(fresh):
            if _safe_str(row.get("tool")) in {"log_scan", "codex_delegate"}:
                return row
    return fresh[-1]
