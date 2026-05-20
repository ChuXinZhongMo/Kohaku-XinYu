from __future__ import annotations

import argparse
import json
import re
import socket
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from xinyu_runtime_presence import DEFAULT_RUNNING_STALE_SECONDS, read_runtime_presence_summary
from xinyu_turn_route_trace import read_turn_route_summary


DEFAULT_CORE_URL = "http://127.0.0.1:8765"
DEFAULT_DASHBOARD_REL = Path("runtime/local_inspector_dashboard.html")
ARCHIVE_REL = Path("runtime/dialogue_archive/dialogue.sqlite3")

_FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_LONG_ID_RE = re.compile(r"\b\d{6,}\b")
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def build_inspection(root: Path, *, route_limit: int = 12, include_network: bool = True) -> dict[str, Any]:
    root = root.resolve()
    presence = read_runtime_presence_summary(root)
    route = read_turn_route_summary(root)
    route_timeline = _read_route_timeline(root / "runtime/turn_route_trace.jsonl", limit=route_limit)
    proactive = _proactive_state(root)
    memory_candidates = _memory_candidate_counts(root)
    gateway = _gateway_state(root, include_network=include_network)
    stale = _stale_warnings(presence=presence, route=route, proactive=proactive, gateway=gateway, memory=memory_candidates)
    current_turn = {
        "state": _safe_str(presence.get("current_turn_state"), "unknown"),
        "turn_id": _safe_str(presence.get("current_turn_id")),
        "kind": _safe_str(presence.get("current_turn_kind")),
        "source": _safe_str(presence.get("current_turn_source")),
        "relation": _safe_str(presence.get("current_turn_relation")),
        "started_at": _safe_str(presence.get("current_turn_started_at")),
        "age_seconds": _safe_int(presence.get("current_turn_age_seconds"), 0),
        "stale_running": bool(presence.get("stale_running")),
    }
    return {
        "ok": not stale["critical"],
        "root": "<xinyu_dir>",
        "current_turn": current_turn,
        "operator": {
            "route_stage": _safe_str(route.get("last_stage"), "unknown"),
            "route": _safe_str(route.get("last_route"), "unknown"),
            "route_status": _safe_str(route.get("last_status"), "unknown"),
            "last_timeout_stage": _safe_str(route.get("last_timeout_stage")),
            "last_timeout_reason": _safe_str(route.get("last_timeout_reason")),
        },
        "route_timeline": route_timeline,
        "gateway": gateway,
        "proactive": proactive,
        "memory_candidates": memory_candidates,
        "warnings": stale,
    }


def render_text(summary: dict[str, Any]) -> str:
    current = summary["current_turn"]
    operator = summary["operator"]
    gateway = summary["gateway"]
    proactive = summary["proactive"]
    memory = summary["memory_candidates"]
    warnings = summary["warnings"]
    lines = [
        "XinYu Local Inspector",
        "",
        f"current_turn: {current['state']} age={current['age_seconds']}s kind={current['kind']} source={current['source']}",
        f"route: {operator['route']} stage={operator['route_stage']} status={operator['route_status']}",
        f"gateway: enabled={gateway['enabled']} core={gateway['core_chat_url']} port_open={gateway['onebot_port_open']} napcat_ws={gateway['napcat_ws_established']}",
        (
            "proactive: "
            f"request={proactive['request_status']} delivery={proactive['delivery_level']} "
            f"answer={proactive['request_answer_state']} claim={proactive['last_claim_status']} "
            f"ack={proactive['last_ack_status']}"
        ),
        (
            "memory_candidates: "
            f"pending={memory['pending']} approved={memory['approved']} rejected={memory['rejected']} "
            f"db={memory['db_state']}"
        ),
    ]
    if operator["last_timeout_reason"]:
        lines.append(f"last_timeout: {operator['last_timeout_stage']} {operator['last_timeout_reason']}")
    if summary["route_timeline"]:
        lines.extend(["", "route_timeline:"])
        for event in summary["route_timeline"]:
            lines.append(
                f"- {event['observed_at']} {event['stage']} {event['route']} {event['status']} {event['elapsed_ms']}ms"
            )
    if warnings["items"]:
        lines.extend(["", "warnings:"])
        lines.extend(f"- {item}" for item in warnings["items"])
    else:
        lines.extend(["", "warnings: none"])
    return "\n".join(lines)


def write_dashboard(root: Path, summary: dict[str, Any], output: Path | None = None) -> Path:
    target = output or (root / DEFAULT_DASHBOARD_REL)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(summary, ensure_ascii=False, indent=2)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>XinYu Local Inspector</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #222; background: #f7f7f4; }}
    main {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ font-size: 24px; margin: 0 0 16px; }}
    section {{ margin: 14px 0; padding: 14px; border: 1px solid #d8d8d2; background: #fff; border-radius: 6px; }}
    h2 {{ font-size: 15px; margin: 0 0 8px; }}
    pre {{ white-space: pre-wrap; font-size: 13px; line-height: 1.45; }}
    .warn {{ color: #9b3d00; }}
    .ok {{ color: #17663a; }}
  </style>
</head>
<body>
<main>
  <h1>XinYu Local Inspector</h1>
  <section><h2>Status</h2><pre>{_html_escape(render_text(summary))}</pre></section>
  <section><h2>Sanitized JSON</h2><pre>{_html_escape(data)}</pre></section>
</main>
</body>
</html>
"""
    target.write_text(html, encoding="utf-8")
    return target


def call_intervention(
    *,
    core_url: str,
    action: str,
    token: str = "",
    payload: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    route = {
        "current": ("GET", "/turn/current"),
        "status-message": ("POST", "/turn/status-message"),
        "cancel": ("POST", "/turn/cancel"),
        "retry-lightweight": ("POST", "/turn/retry-lightweight"),
        "skip-sidecar": ("POST", "/turn/skip-sidecar"),
        "continue": ("POST", "/turn/continue"),
    }.get(action)
    if route is None:
        raise ValueError(f"unknown intervention action: {action}")
    method, path = route
    url = core_url.rstrip("/") + path
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method == "POST":
        data = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _NO_PROXY.open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else {"ok": True, "value": parsed}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return {"ok": False, "http_status": exc.code, "error": body[:400]}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _proactive_state(root: Path) -> dict[str, Any]:
    request = _read_text(root / "memory/context/proactive_request_state.md")
    dispatch = _read_text(root / "memory/context/proactive_qq_dispatch_state.md")
    latest = _read_last_jsonl(root / "runtime/proactive_request_trace.jsonl")
    return {
        "request_status": _field(request, "status", "missing"),
        "kind": _field(request, "kind", "missing"),
        "reason": _field(request, "reason", "missing"),
        "urgency": _field(request, "urgency", "missing"),
        "risk": _field(request, "risk", "missing"),
        "owner_relevance": _field(request, "owner_relevance", "missing"),
        "channel": _field(request, "channel", "missing"),
        "delivery_level": _field(request, "delivery_level", "missing"),
        "request_answer_state": _field(request, "request_answer_state", "missing"),
        "last_claim_status": _field(dispatch, "last_claim_status", "missing"),
        "last_ack_status": _field(dispatch, "last_ack_status", "missing"),
        "adapter_error": _scrub(_field(dispatch, "adapter_error", "")),
        "latest_event": _safe_event(latest),
    }


def _gateway_state(root: Path, *, include_network: bool) -> dict[str, Any]:
    cfg = _load_json(root / "xinyu_qq_gateway.config.json")
    port = _safe_int(cfg.get("onebot_port"), 6199)
    return {
        "enabled": bool(cfg.get("enabled")) if cfg else False,
        "core_chat_url": _scrub(_safe_str(cfg.get("core_chat_url"), "missing")) if cfg else "missing",
        "onebot_port": port,
        "send_replies": bool(cfg.get("send_replies")) if cfg else False,
        "qq_outbox_enabled": bool(cfg.get("qq_outbox_enabled")) if cfg else False,
        "onebot_port_open": _tcp_connect("127.0.0.1", port) if include_network and port > 0 else False,
        "napcat_ws_established": _has_established_local(port) if include_network and port > 0 else False,
        "owner_count": len(cfg.get("owner_user_ids")) if isinstance(cfg.get("owner_user_ids"), list) else 0,
        "whitelist_count": len(cfg.get("whitelist_user_ids")) if isinstance(cfg.get("whitelist_user_ids"), list) else 0,
    }


def _memory_candidate_counts(root: Path) -> dict[str, Any]:
    path = root / ARCHIVE_REL
    result = {"db_state": "missing", "pending": 0, "approved": 0, "rejected": 0, "other": 0}
    if not path.exists():
        return result
    try:
        with sqlite3.connect(path) as conn:
            rows = conn.execute("SELECT status, COUNT(*) FROM memory_candidates GROUP BY status").fetchall()
    except sqlite3.Error:
        result["db_state"] = "unreadable"
        return result
    result["db_state"] = "ok"
    for status, count in rows:
        key = _safe_str(status, "other")
        if key not in result:
            key = "other"
        result[key] = _safe_int(count, 0) + _safe_int(result.get(key), 0)
    return result


def _stale_warnings(
    *,
    presence: dict[str, Any],
    route: dict[str, Any],
    proactive: dict[str, Any],
    gateway: dict[str, Any],
    memory: dict[str, Any],
) -> dict[str, Any]:
    items: list[str] = []
    critical: list[str] = []
    age = _safe_int(presence.get("current_turn_age_seconds"), 0)
    if bool(presence.get("stale_running")) or (
        _safe_str(presence.get("current_turn_state")) == "running" and age > DEFAULT_RUNNING_STALE_SECONDS
    ):
        item = f"turn_stale_running:{age}s"
        items.append(item)
        critical.append(item)
    if _safe_str(route.get("last_status")) == "timeout" or _safe_str(route.get("last_timeout_reason")):
        items.append(f"route_timeout:{_safe_str(route.get('last_timeout_stage'), 'unknown')}")
    if proactive.get("last_ack_status") == "failed":
        items.append("proactive_last_ack_failed")
    if proactive.get("request_status") in {"claimed", "sent"} and proactive.get("request_answer_state") == "pending":
        items.append("proactive_thread_waiting_owner_reply")
    if gateway.get("enabled") and not gateway.get("onebot_port_open"):
        items.append("qq_gateway_port_not_open")
    if _safe_int(memory.get("pending"), 0) >= 20:
        items.append(f"memory_candidate_backlog:{memory.get('pending')}")
    return {"items": items, "critical": critical}


def _read_route_timeline(path: Path, *, limit: int) -> list[dict[str, Any]]:
    rows = _read_jsonl_tail(path, limit=max(1, limit))
    result = []
    for row in rows:
        result.append(
            {
                "observed_at": _safe_str(row.get("observed_at")),
                "turn_id": _scrub(_safe_str(row.get("turn_id"))),
                "stage": _safe_str(row.get("stage"), "unknown"),
                "route": _safe_str(row.get("route"), "unknown"),
                "status": _safe_str(row.get("status"), "unknown"),
                "elapsed_ms": _safe_int(row.get("elapsed_ms"), 0),
                "notes": [_scrub(note) for note in row.get("notes", [])[:4]] if isinstance(row.get("notes"), list) else [],
            }
        )
    return result


def _read_jsonl_tail(path: Path, *, limit: int) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _read_last_jsonl(path: Path) -> dict[str, Any]:
    rows = _read_jsonl_tail(path, limit=50)
    return rows[-1] if rows else {}


def _safe_event(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        return {}
    allowed = (
        "event_kind",
        "event_time",
        "request_id",
        "status",
        "delivery_level",
        "claim_status",
        "ack_status",
        "adapter_status",
        "notes",
    )
    return {key: _scrub(event.get(key)) for key in allowed if key in event}


def _field(text: str, field: str, default: str = "unknown") -> str:
    for match in _FIELD_RE.finditer(text or ""):
        if match.group(1) == field:
            return _scrub(match.group(2)) or default
    return default


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _tcp_connect(host: str, port: int, *, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _has_established_local(port: int) -> bool:
    try:
        import subprocess

        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
        )
    except Exception:
        return False
    needle = f":{port}"
    return any(needle in line and "ESTABLISHED" in line and "127.0.0.1" in line for line in result.stdout.splitlines())


def _html_escape(value: Any) -> str:
    text = _safe_str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _scrub(value: Any) -> str:
    text = _safe_str(value)
    text = _LOCAL_PATH_RE.sub("<local_path>", text)
    text = _LONG_ID_RE.sub(lambda match: match.group(0)[:2] + "***" + match.group(0)[-2:], text)
    return " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())[:240]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Privacy-preserving local XinYu operator inspector.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--core-url", default=DEFAULT_CORE_URL)
    parser.add_argument("--token", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-network", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("summary", help="Print the local inspector summary.")
    dash = sub.add_parser("dashboard", help="Write a minimal local dashboard HTML file.")
    dash.add_argument("--output", type=Path, default=None)
    intervention = sub.add_parser("intervene", help="Call an existing /turn intervention route.")
    intervention.add_argument(
        "action",
        choices=("current", "status-message", "cancel", "retry-lightweight", "skip-sidecar", "continue"),
    )
    intervention.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    command = args.command or "summary"
    root = args.root.resolve()
    if command == "intervene":
        result = call_intervention(
            core_url=args.core_url,
            action=args.action,
            token=args.token,
            payload={"force": bool(args.force)},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render_intervention_text(result))
        return 0 if result.get("ok", result.get("accepted", False)) else 1
    summary = build_inspection(root, include_network=not args.no_network)
    if command == "dashboard":
        path = write_dashboard(root, summary, output=args.output)
        if args.json:
            print(json.dumps({"ok": True, "dashboard": str(path)}, ensure_ascii=False, indent=2))
        else:
            print(f"dashboard: {path}")
        return 0
    print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json else render_text(summary))
    return 0 if summary.get("ok") else 1


def render_intervention_text(result: dict[str, Any]) -> str:
    if "message" in result:
        return _safe_str(result.get("message"))
    if result.get("ok") is False:
        return f"intervention failed: {_safe_str(result.get('reason') or result.get('error'))}"
    parts = [f"ok={result.get('ok', result.get('accepted', False))}"]
    for key in ("applied", "turn_id", "action", "reason"):
        if key in result:
            parts.append(f"{key}={_scrub(result.get(key))}")
    return " ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
