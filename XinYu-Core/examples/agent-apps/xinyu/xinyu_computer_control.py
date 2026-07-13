"""XinYu computer control service (observe-first body surface).

Computer control is a body surface, not the first milestone (dossier section 9).
Clean-room implementation; no Super-Agent-Party code. Useful patterns adapted
conceptually only: normalized 0..1000 coordinates, region-scoped screenshots,
grid overlays, screenshot-after-action, structured action-feedback markers, and
single-step observe/action/observe loops.

Capability tiers:
  observe-only      screenshot / region_screenshot / grid_overlay  (grant enabled)
  proposal-only     propose_click / propose_type / propose_hotkey  (record, never runs)
  single-step       click / type_text / hotkey  (approval or single-step grant)
  blocked           arbitrary_keyboard_mouse / multi_step

A real capture/automation backend is optional and must be injected. Without one
the service runs honest ``simulated`` observation (metadata artifact, no real
pixels) and never executes input. It never targets payment, credential,
account-security, or owner-private apps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Protocol

from stores.state_service import append_jsonl, atomic_write_json, atomic_write_text, read_json

from xinyu_private_ecosystem_grants import computer_grant, load_grants

COMPUTER_VERSION = 1

SCREENSHOTS_REL = Path("runtime/private_ecosystem/computer_screenshots")
ACTIONS_REL = Path("runtime/private_ecosystem/computer_actions.jsonl")
STATE_JSON_REL = Path("runtime/private_ecosystem/computer_state.json")
STATE_MD_REL = Path("memory/context/private_ecosystem_computer_state.md")

COORD_PLANE = "viewport_0_1000"

READ_ONLY = "read_only"
APPROVAL_REQUIRED = "approval_required"
HIGH_BLOCKED = "high_blocked"

OBSERVE_ACTIONS = frozenset({"screenshot", "region_screenshot", "grid_overlay"})
PROPOSAL_ACTIONS = frozenset({"propose_click", "propose_type", "propose_hotkey"})
SINGLE_STEP_ACTIONS = frozenset({"click", "type_text", "hotkey"})
HIGH_BLOCKED_ACTIONS = frozenset({"arbitrary_keyboard_mouse", "multi_step", "drag_drop_macro"})

SENSITIVE_WINDOW_FRAGMENTS = (
    "bank",
    "pay",
    "payment",
    "wallet",
    "password",
    "keychain",
    "keepass",
    "1password",
    "bitwarden",
    "login",
    "sign in",
    "account security",
    "two-factor",
    "authenticator",
    "wechat pay",
    "alipay",
    "支付",
    "银行",
    "密码",
    "钱包",
)


class CaptureBackend(Protocol):
    def screenshot(self, region: dict[str, Any] | None = None) -> bytes: ...


@dataclass(frozen=True, slots=True)
class ComputerActionRecord:
    action_id: str
    action_kind: str
    risk: str
    result: str
    coordinate_plane: str
    target: dict[str, Any]
    last_action_marker: dict[str, Any]
    screenshot_ref: str = ""
    observed_at: str = ""
    error_code: str = ""
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_kind": self.action_kind,
            "risk": self.risk,
            "result": self.result,
            "coordinate_plane": self.coordinate_plane,
            "target": dict(self.target),
            "last_action_marker": dict(self.last_action_marker),
            "screenshot_ref": self.screenshot_ref,
            "observed_at": self.observed_at,
            "error_code": self.error_code,
            "notes": list(self.notes),
        }


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


def _clamp_coord(value: Any) -> int | None:
    if value is None:
        return None
    try:
        num = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(1000, num))


def is_sensitive_window(window_title: str) -> tuple[bool, str]:
    text = _safe_str(window_title).lower()
    if not text:
        return False, ""
    for fragment in SENSITIVE_WINDOW_FRAGMENTS:
        if fragment in text:
            return True, f"sensitive_window:{fragment}"
    return False, ""


def classify_computer_action(action_kind: str) -> tuple[str, bool]:
    kind = _safe_str(action_kind)
    if kind in OBSERVE_ACTIONS:
        return READ_ONLY, False
    if kind in PROPOSAL_ACTIONS:
        return READ_ONLY, False
    if kind in SINGLE_STEP_ACTIONS:
        return APPROVAL_REQUIRED, True
    if kind in HIGH_BLOCKED_ACTIONS:
        return HIGH_BLOCKED, True
    return HIGH_BLOCKED, True


@dataclass(frozen=True, slots=True)
class ComputerPolicyDecision:
    ok: bool
    risk: str
    reason: str
    requires_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "risk": self.risk, "reason": self.reason, "requires_approval": self.requires_approval}


def evaluate_computer_action(
    action_kind: str,
    *,
    window_title: str = "",
    grant: Mapping[str, Any] | None = None,
    approved: bool = False,
) -> ComputerPolicyDecision:
    grant = dict(grant or {})
    risk, requires_approval = classify_computer_action(action_kind)
    is_proposal = _safe_str(action_kind) in PROPOSAL_ACTIONS

    if not bool(grant.get("enabled")):
        return ComputerPolicyDecision(False, risk, "computer_control_grant_disabled", requires_approval)

    sensitive, reason = is_sensitive_window(window_title)
    if sensitive and not is_proposal:
        return ComputerPolicyDecision(False, HIGH_BLOCKED, f"sensitive_window_blocked:{reason}", requires_approval)

    if risk == HIGH_BLOCKED:
        return ComputerPolicyDecision(False, risk, "high_risk_computer_action_blocked", requires_approval)

    if risk == READ_ONLY:
        # observe-only and proposal-only both run without an execution grant
        return ComputerPolicyDecision(True, risk, "observe_or_proposal_allowed", False)

    # single-step execution
    single_step_grant = bool(grant.get("single_step_actions"))
    if approved or single_step_grant:
        return ComputerPolicyDecision(True, risk, "approved_single_step", True)
    return ComputerPolicyDecision(False, risk, "approval_required", True)


def _write_artifact(root: Path, rel_dir: Path, name: str, data: bytes | str) -> str:
    target = root / rel_dir / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        target.write_bytes(data)
    else:
        target.write_text(data, encoding="utf-8")
    return (rel_dir / name).as_posix()


def run_computer_action(
    root: Path,
    *,
    action_kind: str,
    window_title: str = "",
    region: dict[str, Any] | None = None,
    x: float | None = None,
    y: float | None = None,
    text: str = "",
    keys: str = "",
    grant: Mapping[str, Any] | None = None,
    approved: bool = False,
    execute: bool = False,
    backend: CaptureBackend | None = None,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    evaluated_at = _timestamp_or_now_iso(evaluated_at)
    if grant is None:
        grant = computer_grant(load_grants(root))

    decision = evaluate_computer_action(
        action_kind, window_title=window_title, grant=grant, approved=approved
    )
    nx, ny = _clamp_coord(x), _clamp_coord(y)
    target = {
        "window_title_hash": hashlib.sha256(_safe_str(window_title).encode("utf-8", "replace")).hexdigest()[:12]
        if window_title
        else "none",
        "region": dict(region) if isinstance(region, dict) else {},
        "x": nx,
        "y": ny,
        "has_text": bool(text),
        "keys": _safe_str(keys)[:40],
    }
    action_id = "cact-" + _hash_json({"kind": action_kind, "x": nx, "y": ny, "at": evaluated_at})

    screenshot_ref = ""
    notes: list[str] = []
    backend_mode = "live" if backend is not None else "unavailable"

    is_proposal = _safe_str(action_kind) in PROPOSAL_ACTIONS
    if not decision.ok:
        result = "blocked"
        error_code = decision.reason
    elif is_proposal:
        result = "proposed"
        error_code = ""
        notes.append("proposal_only_not_executed")
    elif not execute:
        result = "prepared"
        error_code = ""
        notes.append("dry_run_not_executed")
    elif decision.risk == READ_ONLY:
        result, screenshot_ref, backend_mode, exec_notes = _execute_observe(
            root, action_kind, region=region, backend=backend, action_id=action_id, evaluated_at=evaluated_at
        )
        error_code = "" if result in {"completed", "simulated"} else result
        notes.extend(exec_notes)
    else:
        # single-step execution requires a real backend; never simulated.
        if backend is None:
            result = "blocked"
            error_code = "computer_backend_unavailable"
            notes.append("single_step_requires_real_backend")
        else:  # pragma: no cover - real backend path
            result = "completed"
            error_code = ""
            try:
                shot = backend.screenshot(region)
                screenshot_ref = _write_artifact(root, SCREENSHOTS_REL, f"{action_id}-after.png", shot)
            except Exception:
                notes.append("screenshot_after_action_failed")

    marker_type = {
        "click": "click",
        "propose_click": "click",
        "type_text": "type",
        "hotkey": "key",
    }.get(_safe_str(action_kind), "none")
    record = ComputerActionRecord(
        action_id=action_id,
        action_kind=_safe_str(action_kind),
        risk=decision.risk,
        result=result,
        coordinate_plane=COORD_PLANE,
        target=target,
        last_action_marker={"type": marker_type, "x": nx, "y": ny},
        screenshot_ref=screenshot_ref,
        observed_at=evaluated_at,
        error_code=error_code,
        notes=tuple(notes),
    )
    payload = record.to_dict()
    append_jsonl(root / ACTIONS_REL, payload)
    _update_state(root, payload, decision, backend_mode=backend_mode, evaluated_at=evaluated_at)

    return {
        "ok": decision.ok,
        "decision": decision.to_dict(),
        "record": payload,
        "backend": backend_mode,
        "result": result,
        "screenshot_ref": screenshot_ref,
    }


def _execute_observe(
    root: Path,
    action_kind: str,
    *,
    region: dict[str, Any] | None,
    backend: CaptureBackend | None,
    action_id: str,
    evaluated_at: str,
) -> tuple[str, str, str, list[str]]:
    if backend is not None:  # pragma: no cover - real backend path
        try:
            shot = backend.screenshot(region)
            ref = _write_artifact(root, SCREENSHOTS_REL, f"{action_id}.png", shot)
            return "completed", ref, "live", []
        except Exception:
            return "failed", "", "live", ["backend_capture_failed"]
    observation = {
        "action_id": action_id,
        "action_kind": action_kind,
        "region": dict(region) if isinstance(region, dict) else {},
        "coordinate_plane": COORD_PLANE,
        "observed_at": evaluated_at,
        "note": "simulated_observation_no_capture_backend",
    }
    ref = _write_artifact(
        root, SCREENSHOTS_REL, f"{action_id}.json", json.dumps(observation, ensure_ascii=False, indent=2)
    )
    return "simulated", ref, "simulated", ["simulated_observation"]


def _read_actions(root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
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


def _count_files(root: Path, rel_dir: Path) -> int:
    directory = root / rel_dir
    if not directory.exists():
        return 0
    return sum(1 for entry in directory.iterdir() if entry.is_file())


def _update_state(
    root: Path,
    record: Mapping[str, Any],
    decision: ComputerPolicyDecision,
    *,
    backend_mode: str,
    evaluated_at: str,
) -> None:
    state = read_json(root / STATE_JSON_REL, default={})
    if not isinstance(state, dict):
        state = {}
    counters = state.get("counters") if isinstance(state.get("counters"), dict) else {}
    counters["actions_total"] = int(counters.get("actions_total", 0)) + 1
    if record.get("result") in {"completed", "simulated"}:
        counters["observed"] = int(counters.get("observed", 0)) + 1
    if record.get("result") == "proposed":
        counters["proposed"] = int(counters.get("proposed", 0)) + 1
    if record.get("result") == "blocked":
        counters["blocked"] = int(counters.get("blocked", 0)) + 1
    state.update(
        {
            "version": COMPUTER_VERSION,
            "updated_at": evaluated_at,
            "backend": backend_mode,
            "last_action_kind": record.get("action_kind"),
            "last_result": record.get("result"),
            "last_risk": decision.risk,
            "last_reason": decision.reason,
            "coordinate_plane": COORD_PLANE,
            "counters": counters,
            "screenshot_count": _count_files(root, SCREENSHOTS_REL),
            "boundaries": {
                "multi_step_arbitrary_control": "disabled",
                "targets_payment_credential_pages": False,
                "execution_requires_approval": True,
            },
        }
    )
    atomic_write_json(root / STATE_JSON_REL, state)
    _write_state_markdown(root, state)


def _write_state_markdown(root: Path, state: Mapping[str, Any]) -> None:
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    lines = [
        "---",
        "memory_type: private_ecosystem_computer_state",
        "protected: true",
        "source: xinyu_computer_control",
        f"updated_at: {state.get('updated_at', '')}",
        "status: active",
        "tags: [private_ecosystem, computer_control, sanitized]",
        "---",
        "",
        "# XinYu Computer Control State",
        "",
        f"- backend: {state.get('backend', 'unavailable')}",
        f"- coordinate_plane: {state.get('coordinate_plane', COORD_PLANE)}",
        f"- last_action_kind: {state.get('last_action_kind', 'none')}",
        f"- last_result: {state.get('last_result', 'none')}",
        f"- last_risk: {state.get('last_risk', 'none')}",
        f"- actions_total: {counters.get('actions_total', 0)}",
        f"- observed_count: {counters.get('observed', 0)}",
        f"- proposed_count: {counters.get('proposed', 0)}",
        f"- blocked_count: {counters.get('blocked', 0)}",
        f"- screenshot_count: {state.get('screenshot_count', 0)}",
        "- multi_step_arbitrary_control: disabled",
        "- execution_requires_approval: true",
        "",
        "## Boundaries",
        "",
        "- observe-only and proposal-only run without an execution grant.",
        "- click/type/hotkey need owner approval or a single-step grant.",
        "- multi-step arbitrary desktop control is disabled.",
        "- never targets payment, credential, or account-security windows.",
    ]
    atomic_write_text(root / STATE_MD_REL, "\n".join(lines))


def build_computer_snapshot(root: Path) -> dict[str, Any]:
    root = Path(root)
    state = read_json(root / STATE_JSON_REL, default={})
    if not isinstance(state, dict):
        state = {}
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    return {
        "backend": _safe_str(state.get("backend")) or "unavailable",
        "observed": bool(state),
        "coordinate_plane": _safe_str(state.get("coordinate_plane")) or COORD_PLANE,
        "updated_at": _safe_str(state.get("updated_at")),
        "last_action_kind": _safe_str(state.get("last_action_kind")) or "none",
        "last_result": _safe_str(state.get("last_result")) or "none",
        "last_risk": _safe_str(state.get("last_risk")) or "none",
        "actions_total": int(counters.get("actions_total", 0)),
        "observed_count": int(counters.get("observed", 0)),
        "proposed_count": int(counters.get("proposed", 0)),
        "blocked_count": int(counters.get("blocked", 0)),
        "screenshot_count": int(state.get("screenshot_count", 0)),
        "recent_actions": [
            {
                "action_kind": r.get("action_kind"),
                "risk": r.get("risk"),
                "result": r.get("result"),
                "observed_at": r.get("observed_at"),
            }
            for r in _read_actions(root, limit=10)
        ],
        "boundaries": state.get("boundaries", {
            "multi_step_arbitrary_control": "disabled",
            "targets_payment_credential_pages": False,
            "execution_requires_approval": True,
        }),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one XinYu computer-control action (policy-gated).")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--action", default="screenshot")
    parser.add_argument("--window-title", default="")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--real", action="store_true", help="Use the real mss capture backend (else simulated).")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.snapshot:
        result = build_computer_snapshot(root)
    else:
        backend = None
        if args.real:
            from xinyu_computer_capture_mss import MssCaptureBackend

            backend = MssCaptureBackend()
        result = run_computer_action(
            root,
            action_kind=args.action,
            window_title=args.window_title,
            execute=args.execute,
            approved=args.approved,
            backend=backend,
        )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result.get("decision", result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
