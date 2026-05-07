from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_APP_REL = Path("XinYu-Core/examples/agent-apps/xinyu")
EXCEPTION_RE = re.compile(r"(?i)(traceback|exception|error|failed)")
NO_ERROR_VALUES = frozenset({"", "0", "false", "none", "null", "ok", "no_error"})
BENIGN_TEXT_EXCEPTION_MARKERS = (
    "websockets.exceptions.InvalidMessage: did not receive a valid HTTP request",
    "websockets.exceptions.ConnectionClosedError: no close frame received or sent",
    "EOFError: connection closed while reading HTTP request line",
    "EOFError: stream ends after 0 bytes, before end of line",
)


@dataclass
class HealthSignal:
    name: str
    status: str
    detail: str


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read_text(path: Path, limit: int = 512 * 1024) -> str:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _meaningful_error(value: Any) -> bool:
    if value is None or value is False:
        return False
    text = str(value).strip().lower()
    return text not in NO_ERROR_VALUES


def _jsonl_exception_hits(text: str) -> int:
    hits = 0
    for line in text.splitlines()[-500:]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            hits += len(EXCEPTION_RE.findall(line))
            continue
        if not isinstance(row, dict):
            continue
        if row.get("accepted") is False:
            hits += 1
            continue
        if any(_meaningful_error(row.get(key)) for key in ("error", "error_message", "exception", "traceback")):
            hits += 1
            continue
    return hits


def _text_exception_hits(text: str) -> int:
    hits = 0
    for block in re.split(r"(?=Traceback \(most recent call last\):|opening handshake failed)", text):
        if any(marker in block for marker in BENIGN_TEXT_EXCEPTION_MARKERS):
            continue
        hits += len(EXCEPTION_RE.findall(block))
    return hits


def _extract_assignment(path: Path, name: str) -> str:
    text = _read_text(path)
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1).strip() if match else "unknown"


def _tcp_connect(host: str, port: int, timeout: float = 0.75) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _websocket_probe(host: str, port: int, path: str = "/", timeout: float = 0.75) -> bool:
    request = (
        f"GET {path or '/'} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(request.encode("ascii"))
            response = sock.recv(256)
            if b" 101 " in response or response.startswith(b"HTTP/1.1 101"):
                try:
                    sock.sendall(b"\x88\x80\x00\x00\x00\x00")
                    sock.recv(256)
                except OSError:
                    pass
            return response.startswith(b"HTTP/")
    except OSError:
        return False


def _http_json(url: str, timeout: float = 2.0) -> tuple[bool, dict[str, Any] | str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
            return True, data if isinstance(data, dict) else {"value": data}
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _git_status(workspace: Path) -> tuple[str, str]:
    try:
        completed = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=str(workspace),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception as exc:
        return "unknown", f"{type(exc).__name__}: {exc}"
    output = completed.stdout.strip()
    if completed.returncode != 0:
        return "error", (completed.stderr.strip() or output or f"exit={completed.returncode}")[:240]
    dirty_lines = [line for line in output.splitlines()[1:] if line.strip()]
    return ("dirty" if dirty_lines else "clean"), f"{len(dirty_lines)} dirty entries"


def _outbox_backlog(app_root: Path) -> tuple[str, str]:
    data = _read_json(app_root / "memory/context/qq_outbox_queue.json")
    items = data.get("items")
    if not isinstance(items, list):
        return "unknown", "queue missing or unreadable"
    pending = [
        item
        for item in items
        if isinstance(item, dict) and str(item.get("status") or "queued").lower() in {"queued", "pending", "claimed"}
    ]
    status = "ok" if len(pending) < 20 else "warn"
    return status, f"pending={len(pending)} total={len(items)}"


def _recent_exception_count(app_root: Path) -> tuple[str, str]:
    candidates: list[Path] = []
    for folder in (app_root / "logs", app_root / "runtime"):
        if folder.exists():
            for path in folder.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in {".log", ".txt", ".jsonl"}:
                    continue
                try:
                    rel = path.relative_to(app_root)
                except ValueError:
                    rel = path
                rel_parts = rel.parts
                if len(rel_parts) >= 2 and rel_parts[:2] == ("runtime", "diagnostics"):
                    continue
                if rel_parts == ("runtime", "v1_shadow_trace.jsonl"):
                    continue
                candidates.append(path)
    hits = 0
    scanned = 0
    file_hits: list[tuple[int, str]] = []
    for path in sorted(candidates, key=lambda item: item.stat().st_mtime if item.exists() else 0, reverse=True)[:30]:
        text = _read_text(path, limit=64 * 1024)
        if not text:
            continue
        scanned += 1
        if path.suffix.lower() == ".jsonl":
            path_hits = _jsonl_exception_hits(text)
        else:
            path_hits = _text_exception_hits(text[-64 * 1024 :])
        hits += path_hits
        if path_hits:
            try:
                rel = str(path.relative_to(app_root))
            except ValueError:
                rel = str(path)
            file_hits.append((path_hits, rel))
    status = "ok" if hits == 0 else ("warn" if hits < 20 else "critical")
    top = ",".join(f"{rel}:{count}" for count, rel in sorted(file_hits, reverse=True)[:3]) or "none"
    return status, f"hits={hits} scanned_files={scanned} top={top}"


def _v1_shadow_errors(app_root: Path) -> tuple[str, str]:
    path = app_root / "runtime/v1_shadow_trace.jsonl"
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[-200:]
    except OSError:
        return "unknown", "trace missing"
    failures = 0
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and (row.get("accepted") is False or _meaningful_error(row.get("error"))):
            failures += 1
    status = "ok" if failures == 0 else "warn"
    return status, f"errors={failures} window={len(lines)}"


def _disk_space(workspace: Path) -> tuple[str, str]:
    usage = shutil.disk_usage(workspace)
    free_gb = usage.free / (1024**3)
    status = "ok" if free_gb >= 5 else ("warn" if free_gb >= 1 else "critical")
    return status, f"free_gb={free_gb:.1f}"


def _default_ledger_path(workspace: Path) -> Path:
    return workspace.resolve() / DEFAULT_APP_REL / "runtime/diagnostics/xinyu_health_history.jsonl"


def _append_health_ledger(report: dict[str, Any], ledger_path: Path, *, kind: str) -> dict[str, Any]:
    row = {
        "kind": kind,
        "checked_at": report.get("checked_at"),
        "status": report.get("status"),
        "workspace": report.get("workspace"),
        "app_root": report.get("app_root"),
        "signals": {
            str(item.get("name")): str(item.get("status"))
            for item in report.get("signals", [])
            if isinstance(item, dict) and item.get("name")
        },
        "degraded": [
            {
                "name": item.get("name"),
                "status": item.get("status"),
                "detail": item.get("detail"),
            }
            for item in report.get("signals", [])
            if isinstance(item, dict) and str(item.get("status")) != "ok"
        ],
    }
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str) + "\n")
    return {
        "written": True,
        "kind": kind,
        "path": str(ledger_path),
    }


def collect_health(workspace: Path, core_url: str) -> dict[str, Any]:
    workspace = workspace.resolve()
    app_root = workspace / DEFAULT_APP_REL
    signals: list[HealthSignal] = []

    signals.append(
        HealthSignal(
            "app_root",
            "ok" if app_root.exists() else "critical",
            "present" if app_root.exists() else "missing",
        )
    )
    bridge_version = _extract_assignment(app_root / "xinyu_core_bridge.py", "BRIDGE_VERSION")
    gateway_version = _extract_assignment(app_root / "xinyu_qq_gateway.py", "GATEWAY_VERSION")
    signals.append(HealthSignal("bridge_source", "ok" if bridge_version != "unknown" else "warn", f"version={bridge_version}"))
    signals.append(HealthSignal("qq_gateway_source", "ok" if gateway_version != "unknown" else "warn", f"version={gateway_version}"))

    ok, core = _http_json(core_url.rstrip("/") + "/health")
    core_status = "ok" if ok and isinstance(core, dict) and core.get("ok") else "warn"
    core_detail = f"version={core.get('version', 'unknown')} sessions={core.get('sessions', 'unknown')}" if isinstance(core, dict) else str(core)
    signals.append(HealthSignal("bridge_alive", core_status, core_detail))
    signals.append(
        HealthSignal(
            "desktop_ws_alive",
            "ok" if _websocket_probe("127.0.0.1", 8766, "/desktop/events") else "warn",
            "websocket 127.0.0.1:8766/desktop/events",
        )
    )
    signals.append(
        HealthSignal(
            "qq_gateway_alive",
            "ok" if _websocket_probe("127.0.0.1", 6199) else "warn",
            "websocket 127.0.0.1:6199",
        )
    )
    signals.append(
        HealthSignal(
            "napcat_reachable",
            "ok" if _websocket_probe("127.0.0.1", 6099) else "warn",
            "websocket 127.0.0.1:6099",
        )
    )

    status, detail = _outbox_backlog(app_root)
    signals.append(HealthSignal("outbox_backlog", status, detail))
    status, detail = _recent_exception_count(app_root)
    signals.append(HealthSignal("recent_exceptions", status, detail))
    status, detail = _v1_shadow_errors(app_root)
    signals.append(HealthSignal("v1_shadow_errors", status, detail))
    status, detail = _disk_space(workspace)
    signals.append(HealthSignal("disk_space", status, detail))
    status, detail = _git_status(workspace)
    signals.append(HealthSignal("git_state", status, detail))

    severity = {"ok": 0, "unknown": 1, "warn": 2, "dirty": 2, "error": 3, "critical": 4}
    worst = max((severity.get(item.status, 2) for item in signals), default=0)
    overall = "ok" if worst <= 1 else ("warn" if worst <= 2 else "critical")
    return {
        "ok": overall == "ok",
        "status": overall,
        "checked_at": _now_iso(),
        "workspace": str(workspace),
        "app_root": str(app_root),
        "signals": [asdict(item) for item in signals],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="XinYu long-run health diagnostic. Default mode is read-only.")
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--core-url", default="http://127.0.0.1:8765")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warn or critical status.")
    parser.add_argument(
        "--write-ledger",
        action="store_true",
        help="Append a compact health row to the runtime diagnostics JSONL ledger.",
    )
    parser.add_argument(
        "--checkpoint",
        action="store_true",
        help="Mark the ledger row as a checkpoint entry. Requires --write-ledger.",
    )
    parser.add_argument(
        "--ledger-path",
        type=Path,
        default=None,
        help="Override the default runtime diagnostics ledger path.",
    )
    args = parser.parse_args()
    if args.checkpoint and not args.write_ledger:
        parser.error("--checkpoint requires --write-ledger")

    report = collect_health(args.workspace, args.core_url)
    if args.write_ledger:
        ledger_path = args.ledger_path or _default_ledger_path(args.workspace)
        try:
            report["ledger"] = _append_health_ledger(
                report,
                ledger_path.resolve(),
                kind="checkpoint" if args.checkpoint else "heartbeat",
            )
        except OSError as exc:
            print(f"Failed to write health ledger: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"XinYu health: {report['status']}")
        for item in report["signals"]:
            print(f"{item['status'].upper()} {item['name']}: {item['detail']}")
        ledger = report.get("ledger")
        if isinstance(ledger, dict) and ledger.get("written"):
            print(f"LEDGER {ledger.get('kind')}: {ledger.get('path')}")
    if args.strict and report["status"] != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
