from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CORE_URL = "http://127.0.0.1:8765"
DEFAULT_WINDOW_MINUTES = 120
REQUIRED_CHECKS = {
    "runtime_status",
    "private_input",
    "dispatch_started",
    "visible_reply_sent",
    "qq_ack",
    "visible_send_shadow_guard",
}


@dataclass(frozen=True)
class ReportCheck:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _row_time(row: dict[str, Any]) -> datetime | None:
    for key in ("recorded_at", "observed_at", "acked_at", "created_at", "sent_at"):
        timestamp = _parse_timestamp(row.get(key))
        if timestamp is not None:
            return timestamp
    return None


def _age_minutes(timestamp: datetime | None, now: datetime) -> float | None:
    if timestamp is None:
        return None
    compare_now = now
    compare_timestamp = timestamp
    if timestamp.tzinfo is not None and now.tzinfo is not None:
        compare_now = now.astimezone(timestamp.tzinfo)
    elif timestamp.tzinfo is not None and now.tzinfo is None:
        compare_now = now.replace(tzinfo=timestamp.tzinfo)
    elif timestamp.tzinfo is None and now.tzinfo is not None:
        compare_timestamp = timestamp.replace(tzinfo=now.tzinfo)
    return max(0.0, (compare_now - compare_timestamp).total_seconds() / 60.0)


def _age_label(timestamp: datetime | None, now: datetime) -> str:
    age = _age_minutes(timestamp, now)
    if age is None:
        return "unknown"
    if age < 1:
        return "<1m"
    if age < 60:
        return f"{int(age)}m"
    hours = int(age // 60)
    minutes = int(age % 60)
    return f"{hours}h{minutes}m"


def _mask_id(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    parts: list[str] = []
    for part in text.split(","):
        part = part.strip()
        if len(part) <= 4:
            parts.append(part)
        else:
            parts.append(f"{part[:2]}***{part[-2:]}")
    return ",".join(parts)


def _split_ids(value: Any) -> set[str]:
    if value is None:
        return set()
    return {part.strip() for part in str(value).split(",") if part.strip()}


def _read_jsonl_tail(path: Path, max_lines: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max_lines:]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _latest(rows: list[dict[str, Any]], predicate) -> dict[str, Any] | None:
    for row in reversed(rows):
        if predicate(row):
            return row
    return None


def _within_window(row: dict[str, Any] | None, now: datetime, window_minutes: int) -> bool:
    if row is None:
        return False
    age = _age_minutes(_row_time(row), now)
    return age is not None and age <= window_minutes


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _same_input_anchor(row: dict[str, Any] | None, private_input: dict[str, Any] | None) -> bool:
    if not row or not private_input:
        return False
    input_ids = _split_ids(private_input.get("message_id"))
    row_ids = _split_ids(row.get("message_id"))
    if input_ids and row_ids and bool(input_ids & row_ids):
        return True
    if input_ids and row_ids:
        return False
    input_arrival = _coerce_int(private_input.get("arrival_seq"))
    row_arrival = _coerce_int(row.get("arrival_seq"))
    if not (input_arrival > 0 and row_arrival == input_arrival):
        return False
    row_time = _row_time(row)
    input_time = _row_time(private_input)
    if row_time is None or input_time is None:
        return True
    if row_time.tzinfo is not None and input_time.tzinfo is not None:
        input_time = input_time.astimezone(row_time.tzinfo)
    elif row_time.tzinfo is not None and input_time.tzinfo is None:
        input_time = input_time.replace(tzinfo=row_time.tzinfo)
    elif row_time.tzinfo is None and input_time.tzinfo is not None:
        row_time = row_time.replace(tzinfo=input_time.tzinfo)
    delta_minutes = (row_time - input_time).total_seconds() / 60.0
    return 0 <= delta_minutes <= 30


def _time_distance_minutes(left: dict[str, Any] | None, right: dict[str, Any] | None) -> float | None:
    if not left or not right:
        return None
    left_time = _row_time(left)
    right_time = _row_time(right)
    if left_time is None or right_time is None:
        return None
    compare_right = right_time
    if left_time.tzinfo is not None and right_time.tzinfo is not None:
        compare_right = right_time.astimezone(left_time.tzinfo)
    elif left_time.tzinfo is not None and right_time.tzinfo is None:
        compare_right = right_time.replace(tzinfo=left_time.tzinfo)
    elif left_time.tzinfo is None and right_time.tzinfo is not None:
        left_time = left_time.replace(tzinfo=right_time.tzinfo)
    return abs((left_time - compare_right).total_seconds()) / 60.0


def _near_row_time(row: dict[str, Any] | None, anchor: dict[str, Any] | None, max_minutes: int) -> bool:
    distance = _time_distance_minutes(row, anchor)
    return distance is not None and distance <= max_minutes


def _ack_matches_reply(ack: dict[str, Any] | None, reply: dict[str, Any] | None) -> bool:
    if not ack or not reply:
        return False
    reply_source_ids = _split_ids(reply.get("message_id"))
    ack_source_ids = _split_ids(ack.get("source_message_id"))
    return bool(reply_source_ids and ack_source_ids and reply_source_ids & ack_source_ids)


def _find_first_key(value: Any, target_key: str) -> Any:
    if isinstance(value, dict):
        if target_key in value:
            return value[target_key]
        for nested in value.values():
            found = _find_first_key(nested, target_key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_first_key(item, target_key)
            if found is not None:
                return found
    return None


def _status_check_ok(status_data: dict[str, Any] | None, name: str) -> bool:
    if not status_data:
        return False
    for check in status_data.get("checks", []):
        if isinstance(check, dict) and check.get("name") == name:
            return bool(check.get("ok"))
    return False


def _known_error_count(status_data: dict[str, Any] | None) -> str:
    value = _find_first_key(status_data, "known_error_count")
    if value is None:
        return "unknown"
    return str(value)


def _load_live_status(root: Path, core_url: str) -> tuple[dict[str, Any] | None, str]:
    status_path = root / "xinyu_status.py"
    if not status_path.exists():
        return None, f"missing_status_script:{status_path}"
    command = [
        sys.executable,
        str(status_path),
        "--json",
        "--root",
        str(root),
        "--core-url",
        core_url,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"status_error:{exc}"
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = completed.stderr.strip() or completed.stdout.strip()[:200] or "no_status_json"
        return None, f"status_json_error:{detail}"
    if not isinstance(data, dict):
        return None, "status_json_error:not_object"
    return data, ""


def _ack_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pending_by_key: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("key") or "")
        event = row.get("event")
        if event == "pending" and key:
            pending_by_key[key] = row
        elif event == "acked":
            pending = pending_by_key.get(key, {})
            payload = pending.get("payload") if isinstance(pending.get("payload"), dict) else {}
            records.append(
                {
                    "key": key,
                    "route": row.get("route") or payload.get("route") or "",
                    "acked_at": row.get("acked_at") or "",
                    "adapter_message_id": row.get("adapter_message_id") or payload.get("adapter_message_id") or "",
                    "source_message_id": payload.get("source_message_id") or "",
                    "turn_id": payload.get("turn_id") or "",
                    "message_type": payload.get("message_type") or "",
                }
            )
    return records


def _trace_summary(row: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    if row is None:
        return {"present": False}
    timestamp = _row_time(row)
    return {
        "present": True,
        "arrival_seq": row.get("arrival_seq"),
        "dispatch_seq": row.get("dispatch_seq"),
        "stage": row.get("stage") or "",
        "message_kind": row.get("message_kind") or "",
        "message_id": _mask_id(row.get("message_id")),
        "recorded_at": timestamp.isoformat() if timestamp else "",
        "age": _age_label(timestamp, now),
        "text_len": row.get("text_len"),
        "drop_reason": row.get("drop_reason") or "",
        "error": row.get("error") or "",
    }


def _shadow_summary(row: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    if row is None:
        return {"present": False}
    timestamp = _row_time(row)
    return {
        "present": True,
        "observed_at": timestamp.isoformat() if timestamp else "",
        "age": _age_label(timestamp, now),
        "passed": bool(row.get("passed")),
        "shadow_only": bool(row.get("shadow_only")),
        "raw_prompt_saved": bool(row.get("raw_prompt_saved")),
        "raw_reply_saved": bool(row.get("raw_reply_saved")),
        "send_blocked": bool(row.get("send_blocked")),
        "target_kind": row.get("target_kind") or "",
        "route": row.get("route") or "",
        "reply_hash": row.get("reply_hash") or "",
    }


def _ack_summary(row: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    if row is None:
        return {"present": False}
    timestamp = _parse_timestamp(row.get("acked_at"))
    return {
        "present": True,
        "acked_at": timestamp.isoformat() if timestamp else "",
        "age": _age_label(timestamp, now),
        "route": row.get("route") or "",
        "adapter_message_id": _mask_id(row.get("adapter_message_id")),
        "source_message_id": _mask_id(row.get("source_message_id")),
        "message_type": row.get("message_type") or "",
    }


def _check_detail(report: dict[str, Any], name: str) -> str:
    for check in report.get("checks", []):
        if check.get("name") == name:
            return str(check.get("detail") or "")
    return ""


def _check_ok(report: dict[str, Any], name: str) -> bool:
    for check in report.get("checks", []):
        if check.get("name") == name:
            return bool(check.get("ok"))
    return False


def _should_wait_for_inflight_reply(report: dict[str, Any]) -> bool:
    if report.get("ok"):
        return False
    return (
        _check_ok(report, "private_input")
        and _check_ok(report, "dispatch_started")
        and (not _check_ok(report, "visible_reply_sent") or not _check_ok(report, "qq_ack"))
    )


def build_report(
    root: Path,
    *,
    status_data: dict[str, Any] | None = None,
    status_error: str = "",
    now: datetime | None = None,
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> dict[str, Any]:
    root = root.resolve()
    now = now or datetime.now(timezone.utc)
    runtime = root / "runtime"
    trace_rows = _read_jsonl_tail(runtime / "qq_inbound_trace.jsonl", max_lines=800)
    shadow_rows = _read_jsonl_tail(runtime / "answer_discipline_visible_send_shadow.jsonl", max_lines=200)
    ack_rows = _read_jsonl_tail(runtime / "gateway_ack_spool.jsonl", max_lines=400)
    acked_rows = _ack_records(ack_rows)

    latest_private_input = _latest(
        trace_rows,
        lambda row: row.get("message_kind") == "private"
        and row.get("stage") in {"queued", "prepared", "coalesced_wait"},
    )
    latest_dispatch = _latest(
        trace_rows,
        lambda row: row.get("message_kind") == "private"
        and row.get("stage") == "dispatch_start"
        and _same_input_anchor(row, latest_private_input),
    )
    latest_reply = _latest(
        trace_rows,
        lambda row: row.get("message_kind") == "private"
        and row.get("stage") == "reply_sent"
        and _same_input_anchor(row, latest_private_input),
    )
    latest_stale_drop = _latest(trace_rows, lambda row: row.get("stage") == "stale_reply_dropped")
    latest_group_drop = _latest(
        trace_rows,
        lambda row: row.get("message_kind") == "group" and row.get("stage") == "dropped",
    )
    latest_shadow_any = _latest(
        shadow_rows,
        lambda row: row.get("target_kind") == "private" and row.get("source") == "direct_chat_pre_send",
    )
    latest_shadow = _latest(
        shadow_rows,
        lambda row: row.get("target_kind") == "private"
        and row.get("source") == "direct_chat_pre_send"
        and (latest_reply is None or _near_row_time(row, latest_reply, max_minutes=2)),
    )
    if latest_shadow is None:
        latest_shadow = latest_shadow_any
    latest_chat_ack_any = _latest(acked_rows, lambda row: row.get("route") == "chat")
    latest_chat_ack = _latest(
        acked_rows,
        lambda row: row.get("route") == "chat" and _ack_matches_reply(row, latest_reply),
    )
    if latest_chat_ack is None:
        latest_chat_ack = latest_chat_ack_any

    input_covered_by_reply = _same_input_anchor(latest_reply, latest_private_input)
    ack_matches_reply = _ack_matches_reply(latest_chat_ack, latest_reply)

    # Check infrastructure availability directly to avoid circular dependency:
    # xinyu_status.py returns ok=false when Stage12 itself is not ready, which
    # would permanently prevent Stage12 from evaluating its own live-loop evidence.
    # Infrastructure is considered up when core, gateway, and napcat_ws all pass.
    _core_ok = _status_check_ok(status_data, "core_bridge")
    _gateway_ok = _status_check_ok(status_data, "xinyu_qq_gateway_6199")
    _napcat_ws_ok = _status_check_ok(status_data, "napcat_to_xinyu_qq_gateway_ws")
    runtime_status_ok = bool(status_data and _core_ok and _gateway_ok and _napcat_ws_ok)
    status_detail = (
        "ok"
        if runtime_status_ok
        else status_error or "core/gateway/napcat_ws not all reachable"
    )
    if status_data:
        status_detail = (
            f"status_ok={str(status_data.get('ok')).lower()} "
            f"core={_core_ok} "
            f"gateway={_gateway_ok} "
            f"napcat_ws={_napcat_ws_ok} "
            f"known_errors={_known_error_count(status_data)}"
        )

    private_input_ok = _within_window(latest_private_input, now, window_minutes)
    dispatch_ok = _within_window(latest_dispatch, now, window_minutes)
    reply_ok = _within_window(latest_reply, now, window_minutes) and input_covered_by_reply
    ack_ok = _within_window(latest_chat_ack, now, window_minutes) and ack_matches_reply
    shadow_ok = bool(
        latest_shadow
        and _within_window(latest_shadow, now, window_minutes)
        and (latest_reply is None or _near_row_time(latest_shadow, latest_reply, max_minutes=2))
        and latest_shadow.get("passed") is True
        and latest_shadow.get("shadow_only") is True
        and latest_shadow.get("raw_prompt_saved") is False
        and latest_shadow.get("raw_reply_saved") is False
    )

    checks = [
        ReportCheck("runtime_status", runtime_status_ok, status_detail),
        ReportCheck(
            "private_input",
            private_input_ok,
            "recent private owner QQ input observed" if private_input_ok else "no recent private owner QQ input",
        ),
        ReportCheck(
            "dispatch_started",
            dispatch_ok,
            "core dispatch started for private input" if dispatch_ok else "no recent private dispatch_start",
        ),
        ReportCheck(
            "visible_reply_sent",
            reply_ok,
            (
                "latest private input is covered by a visible reply_sent trace"
                if reply_ok
                else "latest private input has no matching recent reply_sent trace"
            ),
        ),
        ReportCheck(
            "qq_ack",
            ack_ok,
            "matching QQ chat ack observed" if ack_ok else "no matching QQ chat ack for latest reply",
        ),
        ReportCheck(
            "visible_send_shadow_guard",
            shadow_ok,
            (
                "shadow guard passed; raw prompt/reply not saved"
                if shadow_ok
                else "shadow guard missing, failed, or saved raw prompt/reply"
            ),
        ),
        ReportCheck(
            "stale_reply_drop_guard",
            latest_stale_drop is not None,
            (
                "recent stale reply drop evidence exists"
                if latest_stale_drop
                else "not observed in recent tail; this only appears after rapid newer input"
            ),
            required=False,
        ),
        ReportCheck(
            "group_boundary",
            latest_group_drop is not None,
            (
                f"group drop observed: {latest_group_drop.get('drop_reason') or 'dropped'}"
                if latest_group_drop
                else "not observed in recent tail; private QQ is the verification path"
            ),
            required=False,
        ),
    ]

    report_checks = [check.__dict__ for check in checks]
    ok = all(check["ok"] for check in report_checks if check["name"] in REQUIRED_CHECKS)
    return {
        "ok": ok,
        "checked_at": now.isoformat(),
        "window_minutes": window_minutes,
        "root": str(root),
        "checks": report_checks,
        "evidence": {
            "latest_private_input": _trace_summary(latest_private_input, now),
            "latest_dispatch_start": _trace_summary(latest_dispatch, now),
            "latest_reply_sent": _trace_summary(latest_reply, now),
            "latest_chat_ack": _ack_summary(latest_chat_ack, now),
            "latest_shadow_guard": _shadow_summary(latest_shadow, now),
            "latest_stale_reply_drop": _trace_summary(latest_stale_drop, now),
            "latest_group_drop": _trace_summary(latest_group_drop, now),
        },
        "privacy": {
            "raw_user_text_included": False,
            "visible_reply_text_included": False,
            "raw_prompt_included": False,
            "raw_reply_included": False,
            "only_hashes_times_ids_and_counters": True,
        },
    }


def format_human_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("XinYu QQ 闭环验证报告")
    lines.append(f"结果: {'通过' if report.get('ok') else '需要检查'}")
    lines.append(f"检查时间: {report.get('checked_at')}")
    lines.append(f"时间窗口: 最近 {report.get('window_minutes')} 分钟")
    lines.append("")
    lines.append("核心检查")
    for check in report.get("checks", []):
        required = "" if check.get("required") else " optional"
        state = "OK" if check.get("ok") else "WARN"
        lines.append(f"{state:4} {check.get('name')}{required}: {check.get('detail')}")
    evidence = report.get("evidence", {})
    lines.append("")
    lines.append("闭环证据")
    for key in (
        "latest_private_input",
        "latest_dispatch_start",
        "latest_reply_sent",
        "latest_chat_ack",
        "latest_shadow_guard",
        "latest_stale_reply_drop",
        "latest_group_drop",
    ):
        value = evidence.get(key) or {"present": False}
        if not value.get("present"):
            lines.append(f"- {key}: none")
            continue
        if key == "latest_chat_ack":
            lines.append(
                "- "
                f"{key}: route={value.get('route')} source={value.get('source_message_id')} "
                f"adapter={value.get('adapter_message_id')} age={value.get('age')}"
            )
        elif key == "latest_shadow_guard":
            lines.append(
                "- "
                f"{key}: passed={value.get('passed')} shadow_only={value.get('shadow_only')} "
                f"raw_prompt_saved={value.get('raw_prompt_saved')} "
                f"raw_reply_saved={value.get('raw_reply_saved')} age={value.get('age')}"
            )
        else:
            drop_reason = value.get("drop_reason")
            suffix = f" drop_reason={drop_reason}" if drop_reason else ""
            lines.append(
                "- "
                f"{key}: seq={value.get('arrival_seq')} stage={value.get('stage')} "
                f"msg={value.get('message_id')} age={value.get('age')}{suffix}"
            )
    lines.append("")
    lines.append("隐私边界: 本报告不输出 QQ 原文、可见回复正文、prompt 原文或 reply 原文。")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only XinYu QQ live loop verification report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--core-url", default=DEFAULT_CORE_URL)
    parser.add_argument("--window-minutes", type=int, default=DEFAULT_WINDOW_MINUTES)
    parser.add_argument("--wait-seconds", type=int, default=0)
    parser.add_argument("--poll-seconds", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--no-status", action="store_true", help="Skip xinyu_status.py live status call.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    root = args.root.resolve()
    report: dict[str, Any]
    deadline = time.monotonic() + max(0, args.wait_seconds)
    while True:
        status_data: dict[str, Any] | None = None
        status_error = ""
        if not args.no_status:
            status_data, status_error = _load_live_status(root, args.core_url)
        report = build_report(
            root,
            status_data=status_data,
            status_error=status_error,
            window_minutes=max(1, args.window_minutes),
        )
        if not _should_wait_for_inflight_reply(report) or time.monotonic() >= deadline:
            break
        remaining = max(0.0, deadline - time.monotonic())
        time.sleep(min(max(1, args.poll_seconds), remaining))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human_report(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
