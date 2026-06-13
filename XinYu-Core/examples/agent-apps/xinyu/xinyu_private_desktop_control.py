"""XinYu private ISOLATED desktop control service (policy + typed records).

XinYu's own isolated desktop session (a local Linux container/VM). This is
NEVER the owner's host Windows desktop:

  * it does not control the owner's current Windows desktop;
  * it does not capture the owner's screen;
  * it does not move the owner's physical mouse;
  * it does not enable the existing ``computer_control`` shortcut.

Security posture (see CLAUDE-TASK-XINYU-ISOLATED-DESKTOP-CONTROL-2026-06-03.md):
  * read-only status/live-view/screenshot/observe allowed under an isolated
    desktop grant (``private_desktop.enabled``);
  * propose_* records a proposal only and never executes;
  * click/type/hotkey/scroll/move/clipboard require approval or a single-step
    grant, and are blocked while ``observe_only`` is set;
  * shell/download/upload/install/network/multi-step/arbitrary are HIGH-risk and
    blocked in this first landing regardless of grant;
  * every action produces a typed ``DesktopActionRecord`` appended to
    ``actions.jsonl``; marker coordinates clamp to the 0..1000 plane;
  * executed actions capture an after-frame when the backend supports it.

The backend (docker_xfce_vnc) is optional. With no live backend, the service
still enforces policy and records honestly in ``simulated`` mode; it never
claims a live isolated desktop it does not have.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Protocol

from stores.state_service import append_jsonl, atomic_write_json, atomic_write_text, read_json

from xinyu_private_ecosystem_grants import desktop_grant, load_grants

DESKTOP_VERSION = 1

WORKSPACE_REL = Path("runtime/private_ecosystem/desktop_workspace")
STATE_JSON_REL = WORKSPACE_REL / "state.json"
EVENTS_REL = WORKSPACE_REL / "events.jsonl"
ACTIONS_REL = WORKSPACE_REL / "actions.jsonl"
FRAMES_REL = WORKSPACE_REL / "frames"
LATEST_FRAME_REL = WORKSPACE_REL / "latest_frame.png"
STATE_MD_REL = Path("memory/context/private_ecosystem_desktop_state.md")

SESSION_ID = "xinyu-private-desktop"
COORDINATE_PLANE = "desktop_0_1000"
COORDINATE_MAX = 1000

READ_ONLY = "read_only"
PROPOSAL = "proposal"
APPROVAL_REQUIRED = "approval_required"
HIGH_BLOCKED = "high_blocked"

READ_ONLY_ACTIONS = frozenset({"status", "live_view", "screenshot", "list_windows", "observe_text"})
PROPOSAL_ACTIONS = frozenset({"propose_click", "propose_type", "propose_hotkey"})
SINGLE_STEP_ACTIONS = frozenset(
    {"click", "double_click", "move_mouse", "scroll", "type_text", "hotkey", "clipboard_set"}
)
HIGH_BLOCKED_ACTIONS = frozenset(
    {"shell", "download", "upload", "install_package", "network_open_external", "multi_step_task", "arbitrary_keyboard_mouse"}
)


class PrivateDesktopBackend(Protocol):
    """Contract a real isolated-desktop backend (docker_xfce_vnc) satisfies.

    A backend NEVER touches the owner's host desktop; it only drives XinYu's own
    isolated session. ``mode`` is ``"live"`` for a real backend and
    ``"simulated"`` for the honest test/fallback backend.
    """

    mode: str

    def status(self) -> dict[str, Any]: ...
    def ensure_started(self) -> dict[str, Any]: ...
    def stop(self) -> dict[str, Any]: ...
    def screenshot(self) -> bytes: ...
    def click(self, x: int, y: int, button: str = "left") -> dict[str, Any]: ...
    def double_click(self, x: int, y: int, button: str = "left") -> dict[str, Any]: ...
    def move_mouse(self, x: int, y: int) -> dict[str, Any]: ...
    def scroll(self, x: int, y: int, delta: int) -> dict[str, Any]: ...
    def type_text(self, text: str) -> dict[str, Any]: ...
    def hotkey(self, keys: list[str]) -> dict[str, Any]: ...
    def clipboard_set(self, text: str) -> dict[str, Any]: ...


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = "" if value is None else str(value).strip()
    if not text or text.lower() in {"none", "null", "unknown"}:
        return _now_iso()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def _hash_json(value: Any, *, length: int = 16) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()[:length]


def _clamp_marker(value: Any) -> int | None:
    """Clamp a marker coordinate into the 0..1000 isolated-desktop plane."""
    if value is None:
        return None
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(COORDINATE_MAX, number))


def classify_desktop_action(action_kind: str) -> tuple[str, bool]:
    """Return (risk_tier, requires_approval)."""
    kind = _safe_str(action_kind)
    if kind in READ_ONLY_ACTIONS:
        return READ_ONLY, False
    if kind in PROPOSAL_ACTIONS:
        return PROPOSAL, False
    if kind in SINGLE_STEP_ACTIONS:
        return APPROVAL_REQUIRED, True
    if kind in HIGH_BLOCKED_ACTIONS:
        return HIGH_BLOCKED, True
    return HIGH_BLOCKED, True


@dataclass(frozen=True, slots=True)
class DesktopPolicyDecision:
    ok: bool
    risk: str
    reason: str
    requires_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "risk": self.risk, "reason": self.reason, "requires_approval": self.requires_approval}


def evaluate_desktop_action(
    action_kind: str,
    *,
    grant: Mapping[str, Any] | None = None,
    approved: bool = False,
) -> DesktopPolicyDecision:
    grant = dict(grant or {})
    risk, requires_approval = classify_desktop_action(action_kind)

    if not bool(grant.get("enabled")):
        return DesktopPolicyDecision(False, risk, "desktop_grant_disabled", requires_approval)

    if risk == HIGH_BLOCKED:
        # shell/download/upload/install/network/multi-step/arbitrary stay blocked
        # in this first landing, regardless of grant.
        return DesktopPolicyDecision(False, risk, "high_risk_blocked_first_landing", requires_approval)

    if risk == READ_ONLY:
        return DesktopPolicyDecision(True, risk, "read_only_allowed", False)

    if risk == PROPOSAL:
        # Proposal-only: recorded, never executed.
        return DesktopPolicyDecision(True, risk, "proposal_recorded", False)

    # approval_required (single-step)
    if bool(grant.get("observe_only", True)):
        return DesktopPolicyDecision(False, risk, "observe_only_blocks_actions", True)
    if approved or bool(grant.get("single_step_actions")):
        return DesktopPolicyDecision(True, risk, "approved_single_step", True)
    return DesktopPolicyDecision(False, risk, "approval_required", True)


@dataclass(frozen=True, slots=True)
class DesktopActionRecord:
    action_id: str
    session_id: str
    action_kind: str
    risk: str
    result: str
    coordinate_plane: str
    target: dict[str, Any]
    last_action_marker: dict[str, Any] = field(default_factory=lambda: {"type": "none", "x": None, "y": None})
    frame_ref: str = ""
    observed_at: str = ""
    error_code: str = ""
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "session_id": self.session_id,
            "action_kind": self.action_kind,
            "risk": self.risk,
            "result": self.result,
            "coordinate_plane": self.coordinate_plane,
            "target": dict(self.target),
            "last_action_marker": dict(self.last_action_marker),
            "frame_ref": self.frame_ref,
            "observed_at": self.observed_at,
            "error_code": self.error_code,
            "notes": list(self.notes),
        }


def _write_frame(root: Path, name: str, data: bytes) -> str:
    """Write a frame under the workspace and refresh latest_frame.png. Returns a
    private-ecosystem-relative posix path (never an absolute/host path)."""
    target = root / FRAMES_REL / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    latest = root / LATEST_FRAME_REL
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_bytes(data)
    return (FRAMES_REL / name).as_posix()


def _backend_act(backend: PrivateDesktopBackend, action_kind: str, *, x, y, button, delta, text, keys) -> dict[str, Any]:
    if action_kind == "click":
        return backend.click(x, y, button=button)
    if action_kind == "double_click":
        return backend.double_click(x, y, button=button)
    if action_kind == "move_mouse":
        return backend.move_mouse(x, y)
    if action_kind == "scroll":
        return backend.scroll(x, y, delta)
    if action_kind == "type_text":
        return backend.type_text(text)
    if action_kind == "hotkey":
        return backend.hotkey([k.strip() for k in keys.split("+") if k.strip()])
    if action_kind == "clipboard_set":
        return backend.clipboard_set(text)
    return {"ok": False, "error_code": "unsupported_single_step"}


def run_desktop_action(
    root: Path,
    *,
    action_kind: str,
    x: float | None = None,
    y: float | None = None,
    button: str = "left",
    delta: int = 0,
    text: str = "",
    keys: str = "",
    window_title: str = "",
    grant: Mapping[str, Any] | None = None,
    approved: bool = False,
    execute: bool = False,
    backend: PrivateDesktopBackend | None = None,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate (and optionally execute) one isolated-desktop action; always record it."""
    root = Path(root)
    evaluated_at = _timestamp_or_now_iso(evaluated_at)
    if grant is None:
        grant = desktop_grant(load_grants(root))

    decision = evaluate_desktop_action(action_kind, grant=grant, approved=approved)
    mx, my = _clamp_marker(x), _clamp_marker(y)
    target = {
        "coordinate_plane": COORDINATE_PLANE,
        "x": mx,
        "y": my,
        "button": _safe_str(button) or "left",
        "window_title": _safe_str(window_title),
        "text_len": len(_safe_str(text)),
        "keys": _safe_str(keys),
    }
    action_id = "dact-" + _hash_json(
        {"kind": action_kind, "x": mx, "y": my, "keys": keys, "at": evaluated_at}
    )

    frame_ref = ""
    notes: list[str] = []
    backend_mode = "unavailable" if backend is None else _safe_str(getattr(backend, "mode", "live")) or "live"
    error_code = ""

    if not decision.ok:
        result = "blocked"
        error_code = decision.reason
    elif not execute:
        result = "prepared"
        notes.append("dry_run_not_executed")
    elif decision.risk == PROPOSAL:
        result = "proposed"
        notes.append("proposal_only_never_executes")
    elif decision.risk == READ_ONLY:
        result, frame_ref, backend_mode, read_notes = _execute_read_only(
            root, action_kind, backend=backend, action_id=action_id
        )
        error_code = "" if result in {"completed", "simulated"} else result
        notes.extend(read_notes)
    else:
        # approved single-step action
        if backend is None:
            result = "blocked"
            error_code = "desktop_backend_unavailable"
            notes.append("single_step_requires_backend")
        else:
            outcome = _backend_act(
                backend, action_kind, x=mx, y=my, button=target["button"], delta=int(delta or 0), text=text, keys=keys
            )
            if bool(outcome.get("ok")):
                result = "completed" if backend_mode == "live" else "simulated"
                try:
                    frame_ref = _write_frame(root, f"{action_id}-after.png", backend.screenshot())
                except Exception:
                    notes.append("after_frame_failed")
            else:
                result = "failed"
                error_code = _safe_str(outcome.get("error_code")) or "single_step_failed"

    marker_type = {
        "click": "click",
        "double_click": "double_click",
        "move_mouse": "move",
        "scroll": "scroll",
        "propose_click": "proposed_click",
    }.get(action_kind, "none")
    record = DesktopActionRecord(
        action_id=action_id,
        session_id=SESSION_ID,
        action_kind=_safe_str(action_kind),
        risk=decision.risk,
        result=result,
        coordinate_plane=COORDINATE_PLANE,
        target=target,
        last_action_marker={"type": marker_type, "x": mx, "y": my},
        frame_ref=frame_ref,
        observed_at=evaluated_at,
        error_code=error_code,
        notes=tuple(notes),
    )
    payload = record.to_dict()
    append_jsonl(root / ACTIONS_REL, payload)
    _update_state(root, payload, decision, backend_mode=backend_mode, evaluated_at=evaluated_at)

    return {
        "ok": decision.ok and result not in {"blocked", "failed"},
        "decision": decision.to_dict(),
        "record": payload,
        "backend": backend_mode,
        "result": result,
        "frame_ref": frame_ref,
        "error_code": error_code,
    }


def _execute_read_only(
    root: Path,
    action_kind: str,
    *,
    backend: PrivateDesktopBackend | None,
    action_id: str,
) -> tuple[str, str, str, list[str]]:
    if backend is None:
        return "simulated", "", "simulated", ["no_backend_simulated_observation"]
    mode = _safe_str(getattr(backend, "mode", "live")) or "live"
    done = "completed" if mode == "live" else "simulated"
    if action_kind == "screenshot":
        try:
            frame = backend.screenshot()
        except Exception:
            return "failed", "", mode, ["backend_screenshot_failed"]
        return done, _write_frame(root, f"{action_id}.png", frame), mode, []
    if action_kind == "live_view":
        existing = LATEST_FRAME_REL.as_posix() if (root / LATEST_FRAME_REL).exists() else ""
        return done, existing, mode, []
    # status / list_windows / observe_text — no frame capture required
    return done, "", mode, []


def _count_files(root: Path, rel_dir: Path) -> int:
    directory = root / rel_dir
    if not directory.exists():
        return 0
    return sum(1 for entry in directory.iterdir() if entry.is_file())


def _read_actions(root: Path, *, limit: int = 10) -> list[dict[str, Any]]:
    path = root / ACTIONS_REL
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            out.append(data)
    return out[-limit:]


def _update_state(
    root: Path,
    record: Mapping[str, Any],
    decision: DesktopPolicyDecision,
    *,
    backend_mode: str,
    evaluated_at: str,
) -> None:
    state = read_json(root / STATE_JSON_REL, default={})
    if not isinstance(state, dict):
        state = {}
    counters = state.get("counters") if isinstance(state.get("counters"), dict) else {}
    counters["actions_total"] = int(counters.get("actions_total", 0)) + 1
    if record.get("result") in {"completed", "simulated", "proposed"}:
        counters["actions_executed"] = int(counters.get("actions_executed", 0)) + 1
    if record.get("result") in {"blocked", "failed"}:
        counters["actions_blocked"] = int(counters.get("actions_blocked", 0)) + 1
    state.update(
        {
            "version": DESKTOP_VERSION,
            "updated_at": evaluated_at,
            "session_id": SESSION_ID,
            "backend": backend_mode,
            "last_action_kind": record.get("action_kind"),
            "last_result": record.get("result"),
            "last_risk": decision.risk,
            "last_reason": decision.reason,
            "counters": counters,
            "frame_count": _count_files(root, FRAMES_REL),
            "boundaries": boundaries_dict(),
        }
    )
    atomic_write_json(root / STATE_JSON_REL, state)
    _write_state_markdown(root, state)


def boundaries_dict() -> dict[str, Any]:
    return {
        "host_windows_desktop_controlled": False,
        "host_screen_captured": False,
        "owner_mouse_moved": False,
        "computer_control_enabled": False,
        "workspace": "isolated_desktop",
        "loopback_only": True,
    }


def _write_state_markdown(root: Path, state: Mapping[str, Any]) -> None:
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    lines = [
        "---",
        "memory_type: private_ecosystem_desktop_state",
        "protected: true",
        "source: xinyu_private_desktop_control",
        f"updated_at: {state.get('updated_at', '')}",
        "status: active",
        "tags: [private_ecosystem, isolated_desktop, sanitized]",
        "---",
        "",
        "# XinYu Private Isolated Desktop State",
        "",
        f"- session_id: {state.get('session_id', SESSION_ID)}",
        f"- backend: {state.get('backend', 'unavailable')}",
        f"- last_action_kind: {state.get('last_action_kind', 'none')}",
        f"- last_result: {state.get('last_result', 'none')}",
        f"- last_risk: {state.get('last_risk', 'none')}",
        f"- actions_total: {counters.get('actions_total', 0)}",
        f"- actions_executed: {counters.get('actions_executed', 0)}",
        f"- actions_blocked: {counters.get('actions_blocked', 0)}",
        f"- frame_count: {state.get('frame_count', 0)}",
        "",
        "## Boundaries",
        "",
        "- isolated Linux desktop session only; never the owner's host Windows desktop.",
        "- owner host screen not captured; owner physical mouse not moved.",
        "- computer_control stays off; all ports bind 127.0.0.1 only.",
        "- read-only observe auto-allowed; click/type need approval or single-step grant.",
        "- shell/download/install/network/multi-step blocked in this landing.",
    ]
    atomic_write_text(root / STATE_MD_REL, "\n".join(lines))


def build_desktop_snapshot(root: Path, *, backend_status: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = Path(root)
    grant = desktop_grant(load_grants(root))
    state = read_json(root / STATE_JSON_REL, default={})
    if not isinstance(state, dict):
        state = {}
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    status = dict(backend_status or {})
    return {
        "session_id": _safe_str(state.get("session_id")) or SESSION_ID,
        "backend": _safe_str(status.get("backend") or state.get("backend")) or "unavailable",
        "session_state": _safe_str(status.get("session_state")) or "stopped",
        "display_size": _safe_str(status.get("display_size")),
        "live_view_url": _safe_str(status.get("live_view_url")),
        "frame_age_seconds": status.get("frame_age_seconds"),
        "max_frame_rate": int(grant.get("max_frame_rate", 10) or 10),
        "observed": bool(state),
        "updated_at": _safe_str(state.get("updated_at")),
        "last_action_kind": _safe_str(state.get("last_action_kind")) or "none",
        "last_result": _safe_str(state.get("last_result")) or "none",
        "last_risk": _safe_str(state.get("last_risk")) or "none",
        "actions_total": int(counters.get("actions_total", 0)),
        "actions_executed": int(counters.get("actions_executed", 0)),
        "actions_blocked": int(counters.get("actions_blocked", 0)),
        "frame_count": int(state.get("frame_count", 0)),
        "has_latest_frame": (root / LATEST_FRAME_REL).exists(),
        "grant": {
            "enabled": bool(grant.get("enabled")),
            "observe_only": bool(grant.get("observe_only", True)),
            "single_step_actions": bool(grant.get("single_step_actions")),
            "shell_enabled": bool(grant.get("shell_enabled")),
            "network_enabled": bool(grant.get("network_enabled")),
        },
        "boundaries": boundaries_dict(),
        "recent_actions": [
            {
                "action_kind": r.get("action_kind"),
                "risk": r.get("risk"),
                "result": r.get("result"),
                "observed_at": r.get("observed_at"),
            }
            for r in _read_actions(root, limit=10)
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one XinYu private isolated-desktop action (policy-gated).")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--action", default="status")
    parser.add_argument("--x", type=int, default=None)
    parser.add_argument("--y", type=int, default=None)
    parser.add_argument("--text", default="")
    parser.add_argument("--keys", default="")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.snapshot:
        result: Any = build_desktop_snapshot(root)
    else:
        result = run_desktop_action(
            root,
            action_kind=args.action,
            x=args.x,
            y=args.y,
            text=args.text,
            keys=args.keys,
            execute=args.execute,
            approved=args.approved,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
