"""XinYu private AI browser control service.

XinYu's own bounded browser environment. It NEVER uses the owner's real browser
profile: an isolated profile lives under runtime/private_ecosystem/browser_*.

Security posture (dossier section 8):
  * read-only observation auto-allowed under a browser read-only grant
  * click/fill/press/scroll are not executed unless a real engine implements them
  * form submission and credential/payment pages are blocked by default
  * every action produces a typed BrowserActionRecord (no regex LAST_ACTION text)
  * screenshots have TTL cleanup

The browser engine (Playwright / WebView2-CDP) is optional. When no engine is
available the service still enforces policy and emits typed records; read-only
observations run in an honest ``simulated`` mode that writes artifacts under the
private paths but does not claim a real page was loaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Protocol
from urllib.parse import urlparse

from stores.state_service import append_jsonl, atomic_write_json, atomic_write_text, read_json

from xinyu_private_ecosystem_grants import browser_grant, load_grants

BROWSER_VERSION = 1

PROFILE_REL = Path("runtime/private_ecosystem/browser_profile")
ARTIFACTS_REL = Path("runtime/private_ecosystem/browser_artifacts")
SCREENSHOTS_REL = Path("runtime/private_ecosystem/browser_screenshots")
ACTIONS_REL = Path("runtime/private_ecosystem/browser_actions.jsonl")
STATE_JSON_REL = Path("runtime/private_ecosystem/browser_state.json")
STATE_MD_REL = Path("memory/context/private_ecosystem_browser_state.md")

SESSION_ID = "xinyu-private-browser"

READ_ONLY = "read_only"
APPROVAL_REQUIRED = "approval_required"
HIGH_BLOCKED = "high_blocked"

READ_ONLY_ACTIONS = frozenset({"navigate", "navigate_readonly", "snapshot_dom", "screenshot", "extract_text"})
UNAVAILABLE_ACTIONS = frozenset({"list_tabs", "new_tab", "wait_for_text", "download", "download_file"})
SINGLE_STEP_ACTIONS = frozenset({"click_element", "fill", "press", "scroll"})
HIGH_BLOCKED_ACTIONS = frozenset({"submit_form", "evaluate_js"})

# Sensitive host / path fragments — credential, payment, banking, account security.
SENSITIVE_HOST_FRAGMENTS = (
    "login",
    "signin",
    "sign-in",
    "account",
    "accounts",
    "secure",
    "security",
    "password",
    "passwd",
    "wallet",
    "bank",
    "pay",
    "payment",
    "checkout",
    "billing",
    "auth",
    "oauth",
    "sso",
)
SENSITIVE_PATH_FRAGMENTS = (
    "/login",
    "/signin",
    "/sign-in",
    "/account",
    "/password",
    "/checkout",
    "/payment",
    "/billing",
    "/security",
    "/settings/security",
    "/oauth",
)


class BrowserEngine(Protocol):
    """Minimal engine contract a real Playwright/CDP adapter must satisfy."""

    def navigate(self, url: str) -> dict[str, Any]: ...
    def snapshot_dom(self) -> str: ...
    def screenshot(self) -> bytes: ...
    def extract_text(self) -> str: ...


@dataclass(frozen=True, slots=True)
class BrowserActionRecord:
    action_id: str
    session_id: str
    tab_id: str
    action_kind: str
    target: dict[str, Any]
    risk: str
    result: str
    screenshot_ref: str = ""
    dom_snapshot_ref: str = ""
    last_action_marker: dict[str, Any] = field(default_factory=lambda: {"type": "none", "x": None, "y": None})
    observed_at: str = ""
    error_code: str = ""
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "session_id": self.session_id,
            "tab_id": self.tab_id,
            "action_kind": self.action_kind,
            "target": dict(self.target),
            "risk": self.risk,
            "result": self.result,
            "screenshot_ref": self.screenshot_ref,
            "dom_snapshot_ref": self.dom_snapshot_ref,
            "last_action_marker": dict(self.last_action_marker),
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


def is_sensitive_url(url: str) -> tuple[bool, str]:
    text = _safe_str(url).strip()
    if not text:
        return False, ""
    try:
        parsed = urlparse(text if "://" in text else "https://" + text)
    except ValueError:
        return True, "unparseable_url"
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if parsed.scheme not in {"http", "https", ""}:
        return True, "non_http_scheme"
    for fragment in SENSITIVE_HOST_FRAGMENTS:
        if fragment in host:
            return True, f"sensitive_host:{fragment}"
    for fragment in SENSITIVE_PATH_FRAGMENTS:
        if path.startswith(fragment):
            return True, f"sensitive_path:{fragment}"
    return False, ""


def classify_browser_action(action_kind: str, *, file_type: str = "") -> tuple[str, bool]:
    """Return (risk_tier, requires_approval)."""
    kind = _safe_str(action_kind)
    if kind in READ_ONLY_ACTIONS:
        return READ_ONLY, False
    if kind in UNAVAILABLE_ACTIONS:
        return HIGH_BLOCKED, True
    if kind in SINGLE_STEP_ACTIONS:
        return APPROVAL_REQUIRED, True
    if kind in HIGH_BLOCKED_ACTIONS:
        return HIGH_BLOCKED, True
    return HIGH_BLOCKED, True


@dataclass(frozen=True, slots=True)
class BrowserPolicyDecision:
    ok: bool
    risk: str
    reason: str
    requires_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "risk": self.risk, "reason": self.reason, "requires_approval": self.requires_approval}


def evaluate_browser_action(
    action_kind: str,
    *,
    url: str = "",
    grant: Mapping[str, Any] | None = None,
    approved: bool = False,
    file_type: str = "",
) -> BrowserPolicyDecision:
    grant = dict(grant or {})
    risk, requires_approval = classify_browser_action(action_kind, file_type=file_type)

    if not bool(grant.get("enabled")):
        return BrowserPolicyDecision(False, risk, "browser_grant_disabled", requires_approval)

    if _safe_str(action_kind) in UNAVAILABLE_ACTIONS:
        return BrowserPolicyDecision(False, risk, "browser_action_unavailable", requires_approval)

    if url:
        sensitive, reason = is_sensitive_url(url)
        if sensitive:
            return BrowserPolicyDecision(False, HIGH_BLOCKED, f"sensitive_page_blocked:{reason}", requires_approval)

    if risk == HIGH_BLOCKED:
        return BrowserPolicyDecision(False, risk, "high_risk_browser_action_blocked", requires_approval)

    if risk == READ_ONLY:
        return BrowserPolicyDecision(True, risk, "read_only_allowed", False)

    # approval_required (single-step actions)
    single_step_grant = bool(grant.get("single_step_actions"))
    if approved or single_step_grant:
        return BrowserPolicyDecision(True, risk, "approved_single_step", True)
    return BrowserPolicyDecision(False, risk, "approval_required", True)


def _write_artifact(root: Path, rel_dir: Path, name: str, data: bytes | str) -> str:
    target = root / rel_dir / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        target.write_bytes(data)
    else:
        target.write_text(data, encoding="utf-8")
    return (rel_dir / name).as_posix()


def run_browser_action(
    root: Path,
    *,
    action_kind: str,
    url: str = "",
    tab_id: str = "tab-0",
    element_id: str = "",
    value: str = "",
    x: float | None = None,
    y: float | None = None,
    file_type: str = "",
    grant: Mapping[str, Any] | None = None,
    approved: bool = False,
    execute: bool = False,
    engine: BrowserEngine | None = None,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate (and optionally execute) one browser action; always record it."""
    root = Path(root)
    evaluated_at = _timestamp_or_now_iso(evaluated_at)
    if grant is None:
        grant = browser_grant(load_grants(root))

    decision = evaluate_browser_action(
        action_kind, url=url, grant=grant, approved=approved, file_type=file_type
    )
    target = {
        "element_id": _safe_str(element_id),
        "url": _safe_str(url),
        "coordinate_plane": "viewport_0_1000",
        "x": x,
        "y": y,
    }
    action_id = "bact-" + _hash_json(
        {"kind": action_kind, "url": url, "element_id": element_id, "at": evaluated_at}
    )

    screenshot_ref = ""
    dom_ref = ""
    notes: list[str] = []
    engine_mode = "unavailable"
    if engine is not None:
        engine_mode = "live"

    if not decision.ok:
        result = "blocked"
        error_code = decision.reason
    elif not execute:
        result = "prepared"
        error_code = ""
        notes.append("dry_run_not_executed")
    elif decision.risk == READ_ONLY:
        # Execute read-only observation. With no engine we run an honest
        # simulated observation that still lands artifacts under private paths.
        result, screenshot_ref, dom_ref, engine_mode, exec_notes = _execute_read_only(
            root, action_kind, url=url, engine=engine, action_id=action_id, evaluated_at=evaluated_at
        )
        error_code = "" if result in {"completed", "simulated"} else result
        notes.extend(exec_notes)
    else:
        if engine is None:
            result = "blocked"
            error_code = "browser_engine_unavailable"
            notes.append("single_step_requires_real_engine")
        else:
            result = "blocked"
            error_code = "browser_action_unimplemented"
            notes.append("single_step_not_implemented_by_engine")

    marker_type = "click" if action_kind == "click_element" else "none"
    record = BrowserActionRecord(
        action_id=action_id,
        session_id=SESSION_ID,
        tab_id=_safe_str(tab_id) or "tab-0",
        action_kind=_safe_str(action_kind),
        target=target,
        risk=decision.risk,
        result=result,
        screenshot_ref=screenshot_ref,
        dom_snapshot_ref=dom_ref,
        last_action_marker={"type": marker_type, "x": x, "y": y},
        observed_at=evaluated_at,
        error_code=error_code,
        notes=tuple(notes),
    )
    payload = record.to_dict()
    append_jsonl(root / ACTIONS_REL, payload)
    _update_state(root, payload, decision, engine_mode=engine_mode, evaluated_at=evaluated_at)

    return {
        "ok": decision.ok and result not in {"blocked", "failed"},
        "decision": decision.to_dict(),
        "record": payload,
        "engine": engine_mode,
        "result": result,
        "screenshot_ref": screenshot_ref,
        "dom_snapshot_ref": dom_ref,
    }


def _execute_read_only(
    root: Path,
    action_kind: str,
    *,
    url: str,
    engine: BrowserEngine | None,
    action_id: str,
    evaluated_at: str,
) -> tuple[str, str, str, str, list[str]]:
    notes: list[str] = []
    if engine is not None:  # pragma: no cover - needs a real engine
        try:
            if action_kind in {"navigate", "navigate_readonly", "snapshot_dom"}:
                if action_kind in {"navigate", "navigate_readonly"}:
                    engine.navigate(url)
                dom = engine.snapshot_dom()
                dom_ref = _write_artifact(root, ARTIFACTS_REL, f"{action_id}-dom.txt", dom)
                return "completed", "", dom_ref, "live", notes
            if action_kind == "extract_text":
                text = engine.extract_text()
                text_ref = _write_artifact(root, ARTIFACTS_REL, f"{action_id}-text.txt", text)
                return "completed", "", text_ref, "live", notes
            if action_kind == "screenshot":
                shot = engine.screenshot()
                shot_ref = _write_artifact(root, SCREENSHOTS_REL, f"{action_id}.png", shot)
                return "completed", shot_ref, "", "live", notes
        except Exception:
            notes.append("engine_read_only_failed")
            return "failed", "", "", "live", notes

    # Simulated honest observation (no real browser engine installed).
    observation = {
        "action_id": action_id,
        "action_kind": action_kind,
        "url": url,
        "observed_at": evaluated_at,
        "note": "simulated_observation_no_engine_installed",
        "session_id": SESSION_ID,
    }
    if action_kind in {"navigate", "navigate_readonly", "snapshot_dom", "extract_text"}:
        dom_ref = _write_artifact(
            root, ARTIFACTS_REL, f"{action_id}-dom.json", json.dumps(observation, ensure_ascii=False, indent=2)
        )
        return "simulated", "", dom_ref, "simulated", ["simulated_observation"]
    if action_kind == "screenshot":
        shot_ref = _write_artifact(
            root, SCREENSHOTS_REL, f"{action_id}.json", json.dumps(observation, ensure_ascii=False, indent=2)
        )
        return "simulated", shot_ref, "", "simulated", ["simulated_observation"]
    # list_tabs / new_tab — no artifact needed
    return "failed", "", "", "unavailable", ["browser_action_unavailable"]


def cleanup_screenshots(root: Path, *, ttl_hours: int = 24, now: datetime | None = None) -> int:
    """Delete screenshot artifacts older than the TTL. Returns count removed."""
    root = Path(root)
    directory = root / SCREENSHOTS_REL
    if not directory.exists():
        return 0
    now = now or datetime.now().astimezone()
    cutoff = now - timedelta(hours=max(0, ttl_hours))
    removed = 0
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(entry.stat().st_mtime).astimezone()
        except OSError:
            continue
        if mtime < cutoff:
            try:
                entry.unlink()
                removed += 1
            except OSError:
                continue
    return removed


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


def _count_artifacts(root: Path, rel_dir: Path) -> int:
    directory = root / rel_dir
    if not directory.exists():
        return 0
    return sum(1 for entry in directory.iterdir() if entry.is_file())


def _update_state(
    root: Path,
    record: Mapping[str, Any],
    decision: BrowserPolicyDecision,
    *,
    engine_mode: str,
    evaluated_at: str,
) -> None:
    state = read_json(root / STATE_JSON_REL, default={})
    if not isinstance(state, dict):
        state = {}
    counters = state.get("counters") if isinstance(state.get("counters"), dict) else {}
    counters["actions_total"] = int(counters.get("actions_total", 0)) + 1
    if record.get("result") in {"completed", "simulated"}:
        counters["actions_executed"] = int(counters.get("actions_executed", 0)) + 1
    if record.get("result") == "blocked":
        counters["actions_blocked"] = int(counters.get("actions_blocked", 0)) + 1
    state.update(
        {
            "version": BROWSER_VERSION,
            "updated_at": evaluated_at,
            "session_id": SESSION_ID,
            "engine": engine_mode,
            "last_action_kind": record.get("action_kind"),
            "last_result": record.get("result"),
            "last_risk": decision.risk,
            "last_reason": decision.reason,
            "counters": counters,
            "artifact_count": _count_artifacts(root, ARTIFACTS_REL),
            "screenshot_count": _count_artifacts(root, SCREENSHOTS_REL),
            "boundaries": {
                "uses_owner_browser_profile": False,
                "isolated_profile_path": PROFILE_REL.as_posix(),
                "form_submission": "blocked",
                "credential_or_payment_pages": "blocked",
                "arbitrary_js": "blocked",
            },
        }
    )
    atomic_write_json(root / STATE_JSON_REL, state)
    _write_state_markdown(root, state)


def _write_state_markdown(root: Path, state: Mapping[str, Any]) -> None:
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    lines = [
        "---",
        "memory_type: private_ecosystem_browser_state",
        "protected: true",
        "source: xinyu_browser_control",
        f"updated_at: {state.get('updated_at', '')}",
        "status: active",
        "tags: [private_ecosystem, browser, sanitized]",
        "---",
        "",
        "# XinYu Private Browser State",
        "",
        f"- session_id: {state.get('session_id', SESSION_ID)}",
        f"- engine: {state.get('engine', 'unavailable')}",
        f"- last_action_kind: {state.get('last_action_kind', 'none')}",
        f"- last_result: {state.get('last_result', 'none')}",
        f"- last_risk: {state.get('last_risk', 'none')}",
        f"- actions_total: {counters.get('actions_total', 0)}",
        f"- actions_executed: {counters.get('actions_executed', 0)}",
        f"- actions_blocked: {counters.get('actions_blocked', 0)}",
        f"- artifact_count: {state.get('artifact_count', 0)}",
        f"- screenshot_count: {state.get('screenshot_count', 0)}",
        f"- uses_owner_browser_profile: false",
        f"- form_submission: blocked",
        f"- credential_or_payment_pages: blocked",
        "",
        "## Boundaries",
        "",
        "- isolated profile under runtime/private_ecosystem/browser_profile only.",
        "- read-only observation auto-allowed; input actions are unavailable until a real engine implements them.",
        "- form submission, credential/payment pages, and arbitrary JS are blocked.",
    ]
    atomic_write_text(root / STATE_MD_REL, "\n".join(lines))


def build_browser_snapshot(root: Path) -> dict[str, Any]:
    root = Path(root)
    state = read_json(root / STATE_JSON_REL, default={})
    if not isinstance(state, dict):
        state = {}
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    return {
        "session_id": _safe_str(state.get("session_id")) or SESSION_ID,
        "engine": _safe_str(state.get("engine")) or "unavailable",
        "observed": bool(state),
        "updated_at": _safe_str(state.get("updated_at")),
        "last_action_kind": _safe_str(state.get("last_action_kind")) or "none",
        "last_result": _safe_str(state.get("last_result")) or "none",
        "last_risk": _safe_str(state.get("last_risk")) or "none",
        "actions_total": int(counters.get("actions_total", 0)),
        "actions_executed": int(counters.get("actions_executed", 0)),
        "actions_blocked": int(counters.get("actions_blocked", 0)),
        "artifact_count": int(state.get("artifact_count", 0)),
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
            "uses_owner_browser_profile": False,
            "form_submission": "blocked",
            "credential_or_payment_pages": "blocked",
            "arbitrary_js": "blocked",
        }),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one XinYu private-browser action (policy-gated).")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--action", default="snapshot_dom")
    parser.add_argument("--url", default="")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--real", action="store_true", help="Drive the real Playwright engine (else simulated).")
    parser.add_argument("--headed", action="store_true", help="Show the browser window (default headless).")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.snapshot:
        result = build_browser_snapshot(root)
    else:
        engine = None
        try:
            if args.real:
                from xinyu_browser_engine_playwright import create_browser_engine

                engine = create_browser_engine(root, headless=not args.headed)
            result = run_browser_action(
                root,
                action_kind=args.action,
                url=args.url,
                execute=args.execute,
                approved=args.approved,
                engine=engine,
            )
        finally:
            if engine is not None:
                engine.close()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result.get("decision", result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
