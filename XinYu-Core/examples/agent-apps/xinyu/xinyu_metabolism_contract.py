from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from xinyu_dream_engine import (
    build_dream_engine_result,
    dream_bias_lines_text as format_dream_bias_lines,
    self_choice_input as normalize_self_choice_input,
)


CONTRACT_VERSION = 1
DEFAULT_TICKET_TTL_SECONDS = 24 * 60 * 60
DEFAULT_LEASE_SECONDS = 15 * 60

MetabolismStatus = Literal[
    "requested",
    "approved",
    "running",
    "settled",
    "rejected",
    "cancelled",
    "expired",
    "failed",
]


def create_ticket(
    root: Path,
    *,
    entropy_state: dict[str, Any],
    resource_request: dict[str, Any] | None = None,
    active_desire: dict[str, Any] | None = None,
    input_window: dict[str, Any] | None = None,
    ticket_id: str | None = None,
    ttl_seconds: int = DEFAULT_TICKET_TTL_SECONDS,
) -> dict[str, Any]:
    now = _now_iso()
    resource = resource_request or {}
    requested_seconds = _bounded_int(resource.get("requested_seconds"), default=600, low=60, high=1800)
    ticket = {
        "version": CONTRACT_VERSION,
        "ticket_id": ticket_id or _ticket_id(entropy_state, active_desire),
        "status": "requested",
        "created_at": now,
        "updated_at": now,
        "expires_at": _iso_after(ttl_seconds),
        "requested_seconds": requested_seconds,
        "approved_seconds": None,
        "owner_decision_id": "",
        "owner_note": "",
        "resource_request": dict(resource),
        "entropy_before": _entropy_snapshot(entropy_state),
        "active_desire": dict(active_desire or {}),
        "input_window": _input_window(input_window or {}),
        "lease": None,
        "artifacts": {},
        "settlement": {},
        "notes": ["ticket_requested"],
    }

    with _ContractLock(_lock_path(root)):
        store = _read_store(root)
        existing = _tickets(store).get(ticket["ticket_id"])
        if isinstance(existing, dict):
            return {"accepted": True, "idempotent": True, "ticket": existing, "notes": ["ticket_already_exists"]}
        _tickets(store)[ticket["ticket_id"]] = ticket
        _write_store(root, store)
        event = _ledger_event("ticket_requested", ticket=ticket, payload={"requested_seconds": requested_seconds})
        _append_ledger(root, event)
        return {"accepted": True, "idempotent": False, "ticket": ticket, "ledger_event": event, "notes": ["ticket_created"]}


def approve_ticket(
    root: Path,
    ticket_id: str,
    *,
    owner_decision_id: str,
    approved_seconds: int | None = None,
    note: str = "",
) -> dict[str, Any]:
    decision_id = _safe_str(owner_decision_id).strip()
    if not decision_id:
        return {"accepted": False, "ticket": {}, "notes": ["missing_owner_decision_id"]}
    with _ContractLock(_lock_path(root)):
        store = _read_store(root)
        ticket = _tickets(store).get(ticket_id)
        if not isinstance(ticket, dict):
            return {"accepted": False, "ticket": {}, "notes": ["ticket_not_found"]}
        if ticket.get("owner_decision_id") == decision_id and ticket.get("status") in {
            "approved",
            "running",
            "settled",
        }:
            return {"accepted": True, "idempotent": True, "ticket": ticket, "notes": ["decision_already_applied"]}
        status = _safe_str(ticket.get("status"))
        if status != "requested":
            return {"accepted": False, "ticket": ticket, "notes": [f"invalid_status_for_approve:{status}"]}
        if _is_expired(ticket):
            _transition(ticket, "expired", note="ticket_expired_before_approval")
            _write_store(root, store)
            event = _ledger_event("ticket_expired", ticket=ticket, payload={"reason": "expired_before_approval"})
            _append_ledger(root, event)
            return {"accepted": False, "ticket": ticket, "ledger_event": event, "notes": ["ticket_expired"]}

        requested = _bounded_int(ticket.get("requested_seconds"), default=600, low=60, high=1800)
        approved = _bounded_int(approved_seconds, default=requested, low=60, high=requested)
        ticket["approved_seconds"] = approved
        ticket["owner_decision_id"] = decision_id
        ticket["owner_note"] = _compact(note, 240)
        _transition(ticket, "approved", note="owner_approved")
        _write_store(root, store)
        event = _ledger_event(
            "ticket_approved",
            ticket=ticket,
            payload={"owner_decision_id": decision_id, "approved_seconds": approved, "note": ticket["owner_note"]},
        )
        _append_ledger(root, event)
        return {"accepted": True, "idempotent": False, "ticket": ticket, "ledger_event": event, "notes": ["ticket_approved"]}


def reject_ticket(root: Path, ticket_id: str, *, owner_decision_id: str, note: str = "") -> dict[str, Any]:
    decision_id = _safe_str(owner_decision_id).strip()
    if not decision_id:
        return {"accepted": False, "ticket": {}, "notes": ["missing_owner_decision_id"]}
    with _ContractLock(_lock_path(root)):
        store = _read_store(root)
        ticket = _tickets(store).get(ticket_id)
        if not isinstance(ticket, dict):
            return {"accepted": False, "ticket": {}, "notes": ["ticket_not_found"]}
        if ticket.get("owner_decision_id") == decision_id and ticket.get("status") == "rejected":
            return {"accepted": True, "idempotent": True, "ticket": ticket, "notes": ["decision_already_applied"]}
        status = _safe_str(ticket.get("status"))
        if status not in {"requested", "approved"}:
            return {"accepted": False, "ticket": ticket, "notes": [f"invalid_status_for_reject:{status}"]}
        ticket["owner_decision_id"] = decision_id
        ticket["owner_note"] = _compact(note, 240)
        ticket["settlement"] = {
            "mode": "rejected_no_metabolism_v1",
            "entropy_delta": 0.0,
            "scar_delta": 0.04,
            "memory_decay_risk_delta": 0.02,
        }
        _transition(ticket, "rejected", note="owner_rejected")
        _write_store(root, store)
        event = _ledger_event(
            "ticket_rejected",
            ticket=ticket,
            payload={"owner_decision_id": decision_id, "scar_delta": 0.04, "note": ticket["owner_note"]},
        )
        _append_ledger(root, event)
        return {"accepted": True, "idempotent": False, "ticket": ticket, "ledger_event": event, "notes": ["ticket_rejected"]}


def cancel_ticket(root: Path, ticket_id: str, *, reason: str = "owner_cancelled") -> dict[str, Any]:
    with _ContractLock(_lock_path(root)):
        store = _read_store(root)
        ticket = _tickets(store).get(ticket_id)
        if not isinstance(ticket, dict):
            return {"accepted": False, "ticket": {}, "notes": ["ticket_not_found"]}
        status = _safe_str(ticket.get("status"))
        if status not in {"requested", "approved", "running"}:
            return {"accepted": False, "ticket": ticket, "notes": [f"invalid_status_for_cancel:{status}"]}
        _transition(ticket, "cancelled", note=_compact(reason, 120))
        _write_store(root, store)
        event = _ledger_event("ticket_cancelled", ticket=ticket, payload={"reason": reason})
        _append_ledger(root, event)
        return {"accepted": True, "ticket": ticket, "ledger_event": event, "notes": ["ticket_cancelled"]}


def get_ticket(root: Path, ticket_id: str) -> dict[str, Any]:
    store = _read_store(root)
    ticket = _tickets(store).get(ticket_id)
    return dict(ticket) if isinstance(ticket, dict) else {}


def list_tickets(root: Path, *, statuses: set[str] | None = None) -> list[dict[str, Any]]:
    store = _read_store(root)
    values = [ticket for ticket in _tickets(store).values() if isinstance(ticket, dict)]
    if statuses:
        values = [ticket for ticket in values if _safe_str(ticket.get("status")) in statuses]
    return sorted(values, key=lambda ticket: _safe_str(ticket.get("created_at")))


def claim_next_approved_ticket(
    root: Path,
    *,
    runner_id: str = "life_kernel_stub_runner",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    with _ContractLock(_lock_path(root)):
        store = _read_store(root)
        expired_events = _fail_expired_leases(root, store)
        for ticket in list_tickets_from_store(store, statuses={"approved"}):
            if _is_expired(ticket):
                _transition(ticket, "expired", note="ticket_expired_before_running")
                event = _ledger_event("ticket_expired", ticket=ticket, payload={"reason": "expired_before_running"})
                _append_ledger(root, event)
                expired_events.append(event)
                continue
            lease_id = f"lease:{uuid.uuid4().hex[:16]}"
            ticket["lease"] = {
                "lease_id": lease_id,
                "runner_id": _compact(runner_id, 80),
                "claimed_at": _now_iso(),
                "lease_expires_at": _iso_after(lease_seconds),
            }
            ticket["started_at"] = _now_iso()
            _transition(ticket, "running", note="runner_claimed")
            _write_store(root, store)
            event = _ledger_event(
                "ticket_running",
                ticket=ticket,
                payload={"lease_id": lease_id, "runner_id": runner_id, "lease_seconds": lease_seconds},
            )
            _append_ledger(root, event)
            return {
                "claimed": True,
                "ticket": ticket,
                "lease_id": lease_id,
                "ledger_event": event,
                "expired_events": expired_events,
                "notes": ["ticket_claimed"],
            }
        if expired_events:
            _write_store(root, store)
        return {"claimed": False, "ticket": {}, "expired_events": expired_events, "notes": ["no_approved_ticket"]}


def run_due_metabolism_tickets(
    root: Path,
    *,
    runner_id: str = "life_kernel_stub_runner",
    max_tickets: int = 1,
) -> dict[str, Any]:
    settled: list[dict[str, Any]] = []
    notes: list[str] = []
    for _index in range(max(0, max_tickets)):
        claim = claim_next_approved_ticket(root, runner_id=runner_id)
        if not claim.get("claimed"):
            notes.extend(_safe_str(note) for note in claim.get("notes", []))
            break
        ticket = claim.get("ticket") if isinstance(claim.get("ticket"), dict) else {}
        result = run_stub_metabolism(root, _safe_str(ticket.get("ticket_id")), lease_id=_safe_str(claim.get("lease_id")))
        settled.append(result)
        notes.extend(_safe_str(note) for note in result.get("notes", []))
    return {"ran": len(settled), "settled": settled, "notes": notes or ["no_due_tickets"]}


def run_stub_metabolism(root: Path, ticket_id: str, *, lease_id: str = "") -> dict[str, Any]:
    with _ContractLock(_lock_path(root)):
        store = _read_store(root)
        ticket = _tickets(store).get(ticket_id)
        if not isinstance(ticket, dict):
            return {"settled": False, "ticket": {}, "notes": ["ticket_not_found"]}
        status = _safe_str(ticket.get("status"))
        if status != "running":
            return {"settled": False, "ticket": ticket, "notes": [f"invalid_status_for_stub_run:{status}"]}
        lease = ticket.get("lease") if isinstance(ticket.get("lease"), dict) else {}
        if lease_id and _safe_str(lease.get("lease_id")) != lease_id:
            return {"settled": False, "ticket": ticket, "notes": ["lease_mismatch"]}
        if _lease_expired(ticket):
            _transition(ticket, "failed", note="lease_expired_before_stub_metabolism")
            _write_store(root, store)
            event = _ledger_event("ticket_failed", ticket=ticket, payload={"reason": "lease_expired"})
            _append_ledger(root, event)
            return {"settled": False, "ticket": ticket, "ledger_event": event, "notes": ["lease_expired"]}

        metabolism, dream_text = _stub_artifacts(ticket)
        metabolism_path = _metabolism_path(root, ticket_id)
        dream_path = _dream_path(root, ticket_id)
        metabolism["artifacts"]["dream_log"] = _rel_path(root, dream_path)
        _write_json_file(metabolism_path, metabolism)
        _write_text(dream_path, dream_text)
        artifact_event = _ledger_event(
            "artifact_written",
            ticket=ticket,
            payload={
                "metabolism_path": _rel_path(root, metabolism_path),
                "dream_path": _rel_path(root, dream_path),
                "mode": "stub_metabolism_v1",
            },
        )
        _append_ledger(root, artifact_event)

        ticket["artifacts"] = {
            "metabolism": _rel_path(root, metabolism_path),
            "dream_log": _rel_path(root, dream_path),
        }
        ticket["settlement"] = metabolism["after"]
        ticket["settled_at"] = _safe_str(metabolism.get("settled_at"))
        _transition(ticket, "settled", note="stub_metabolism_settled")
        _write_store(root, store)
        settled_event = _ledger_event(
            "ticket_settled",
            ticket=ticket,
            payload={**metabolism["after"], "mode": "stub_metabolism_v1"},
        )
        _append_ledger(root, settled_event)
        return {
            "settled": True,
            "ticket": ticket,
            "artifact_event": artifact_event,
            "ledger_event": settled_event,
            "metabolism_path": _rel_path(root, metabolism_path),
            "dream_path": _rel_path(root, dream_path),
            "notes": ["stub_metabolism_settled"],
        }


def read_ledger(root: Path) -> list[dict[str, Any]]:
    path = _ledger_path(root)
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def list_tickets_from_store(store: dict[str, Any], *, statuses: set[str] | None = None) -> list[dict[str, Any]]:
    values = [ticket for ticket in _tickets(store).values() if isinstance(ticket, dict)]
    if statuses:
        values = [ticket for ticket in values if _safe_str(ticket.get("status")) in statuses]
    return sorted(values, key=lambda ticket: _safe_str(ticket.get("created_at")))


def _stub_artifacts(ticket: dict[str, Any]) -> tuple[dict[str, Any], str]:
    settled_at = _now_iso()
    input_window = _input_window(ticket.get("input_window") if isinstance(ticket.get("input_window"), dict) else {})
    before = _entropy_snapshot(ticket.get("entropy_before") if isinstance(ticket.get("entropy_before"), dict) else {})
    suppressed = _bounded_int(input_window.get("suppressed_residue_count"), default=0, low=0, high=999)
    memory_events = _bounded_int(input_window.get("memory_event_count"), default=0, low=0, high=999)
    entropy_delta = -round(min(0.35, max(0.22, float(before.get("entropy_level", 0.0)) * 0.36)), 3)
    scar_delta = -round(min(0.06, max(0.03, float(before.get("scar_level", 0.0)) * 0.08)), 3)
    risk_delta = -round(min(0.34, max(0.2, float(before.get("memory_decay_risk", 0.0)) * 0.4)), 3)
    summary = "多次想靠近但没有发出，残留集中在未完成的牵挂。"
    if suppressed <= 0:
        summary = "残留主要来自近期记忆噪声，而不是明确的压抑请求。"
    dream_bias = build_dream_engine_result(input_window=input_window).public_dict()
    metabolism = {
        "version": 1,
        "ticket_id": ticket.get("ticket_id", ""),
        "settled_at": settled_at,
        "mode": "stub_metabolism_v1",
        "input_window": input_window,
        "before": before,
        "compressed_residue": [
            {
                "kind": "suppressed_cluster" if suppressed else "memory_noise_cluster",
                "weight": round(min(1.0, max(0.12, suppressed * 0.09 + memory_events * 0.04)), 2),
                "summary": summary,
            }
        ],
        "dream_bias": dream_bias,
        "after": {
            "entropy_delta": entropy_delta,
            "scar_delta": scar_delta,
            "memory_decay_risk_delta": risk_delta,
        },
        "artifacts": {},
    }
    dream = _dream_text(ticket=ticket, input_window=input_window, metabolism=metabolism)
    return metabolism, dream


def _dream_text(*, ticket: dict[str, Any], input_window: dict[str, Any], metabolism: dict[str, Any]) -> str:
    suppressed = _bounded_int(input_window.get("suppressed_residue_count"), default=0, low=0, high=999)
    memory_events = _bounded_int(input_window.get("memory_event_count"), default=0, low=0, high=999)
    noun = "念头" if suppressed else "碎片"
    count = suppressed or memory_events
    count_text = _small_count_text(count) if count else "几"
    after = metabolism.get("after") if isinstance(metabolism.get("after"), dict) else {}
    dream_bias = metabolism.get("dream_bias") if isinstance(metabolism.get("dream_bias"), dict) else {}
    dream_lines = format_dream_bias_lines(dream_bias)
    return f"""# Dream Residue

ticket: {ticket.get("ticket_id", "")}
mode: stub_metabolism_v1

不是事实记忆。只是一次代谢后的错构残片。

风扇声很低，{count_text}个没说出口的{noun}叠在一起。
它们没有变成消息，只在边缘留下一圈噪点。
整理结束后，噪点退了一些，裂痕还在。

dual_temp_bias: {dream_bias.get("mode", "none")}
{dream_lines}
entropy_delta: {after.get("entropy_delta", 0)}
scar_delta: {after.get("scar_delta", 0)}
"""


def _transition(ticket: dict[str, Any], status: MetabolismStatus, *, note: str) -> None:
    now = _now_iso()
    ticket["status"] = status
    ticket["updated_at"] = now
    notes = ticket.get("notes")
    if not isinstance(notes, list):
        notes = []
    notes.append(note)
    ticket["notes"] = notes[-20:]
    history = ticket.get("history")
    if not isinstance(history, list):
        history = []
    history.append({"at": now, "status": status, "note": note})
    ticket["history"] = history[-80:]


def _small_count_text(value: int) -> str:
    names = {
        1: "一",
        2: "两",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
        10: "十",
    }
    return names.get(value, str(value))


def _fail_expired_leases(root: Path, store: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for ticket in list_tickets_from_store(store, statuses={"running"}):
        if not _lease_expired(ticket):
            continue
        _transition(ticket, "failed", note="lease_expired")
        event = _ledger_event("ticket_failed", ticket=ticket, payload={"reason": "lease_expired"})
        _append_ledger(root, event)
        events.append(event)
    return events


def _ledger_event(event: str, *, ticket: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    now = _now_iso()
    return {
        "version": CONTRACT_VERSION,
        "event_id": f"ledger:{uuid.uuid4().hex[:16]}",
        "event": event,
        "ticket_id": _safe_str(ticket.get("ticket_id")),
        "status": _safe_str(ticket.get("status")),
        "created_at": now,
        "payload": payload or {},
    }


def _input_window(value: dict[str, Any]) -> dict[str, Any]:
    window: dict[str, Any] = {
        "suppressed_residue_count": _bounded_int(value.get("suppressed_residue_count"), default=0, low=0, high=999),
        "memory_event_count": _bounded_int(value.get("memory_event_count"), default=0, low=0, high=999),
        "proactive_item_count": _bounded_int(value.get("proactive_item_count"), default=0, low=0, high=999),
        "recent_turn_count": _bounded_int(value.get("recent_turn_count"), default=0, low=0, high=999),
    }
    self_choice = value.get("self_choice") if isinstance(value.get("self_choice"), dict) else {}
    if self_choice:
        window["self_choice"] = normalize_self_choice_input(self_choice)
    return window


def _entropy_snapshot(value: dict[str, Any]) -> dict[str, float]:
    return {
        "entropy_level": _bounded_float(value.get("entropy_level"), default=0.0),
        "scar_level": _bounded_float(value.get("scar_level"), default=0.0),
        "memory_decay_risk": _bounded_float(value.get("memory_decay_risk"), default=0.0),
    }


def _tickets(store: dict[str, Any]) -> dict[str, Any]:
    tickets = store.get("tickets")
    if not isinstance(tickets, dict):
        store["tickets"] = {}
    return store["tickets"]


def _read_store(root: Path) -> dict[str, Any]:
    path = _tickets_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", CONTRACT_VERSION)
    data.setdefault("updated_at", _now_iso())
    data.setdefault("tickets", {})
    if not isinstance(data["tickets"], dict):
        data["tickets"] = {}
    return data


def _write_store(root: Path, store: dict[str, Any]) -> None:
    store["version"] = CONTRACT_VERSION
    store["updated_at"] = _now_iso()
    _write_json_file(_tickets_path(root), store)


def _write_json_file(path: Path, value: dict[str, Any]) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        _replace_file_with_retry(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _replace_file_with_retry(source: Path, target: Path) -> None:
    for attempt in range(20):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(min(0.05 * (attempt + 1), 0.5))


def _append_ledger(root: Path, event: dict[str, Any]) -> None:
    path = _ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def _tickets_path(root: Path) -> Path:
    return root / "runtime/life_kernel/metabolism_tickets.json"


def _ledger_path(root: Path) -> Path:
    return root / "runtime/life_kernel/entropy_ledger.jsonl"


def _lock_path(root: Path) -> Path:
    return root / "runtime/life_kernel/.metabolism_contract.lock"


def _metabolism_path(root: Path, ticket_id: str) -> Path:
    return root / "memory/metabolism" / f"{_date_slug()}-{_safe_slug(ticket_id)}.json"


def _dream_path(root: Path, ticket_id: str) -> Path:
    return root / "memory/dreams" / f"{_date_slug()}-{_safe_slug(ticket_id)}.md"


def _rel_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _ticket_id(entropy_state: dict[str, Any], active_desire: dict[str, Any] | None) -> str:
    desire_id = _safe_str((active_desire or {}).get("desire_id"))
    seed = json.dumps({"desire_id": desire_id, "entropy": _entropy_snapshot(entropy_state)}, sort_keys=True)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]
    return f"metabolism:{_safe_slug(desire_id or uuid.uuid4().hex[:12])}:{digest}"


def _safe_slug(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", _safe_str(value)).strip("-").lower()
    return text[:80] or "ticket"


def _date_slug() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _iso_after(seconds: int) -> str:
    return (datetime.now().astimezone() + timedelta(seconds=max(0, int(seconds)))).isoformat(timespec="seconds")


def _parse_time(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(_safe_str(value))
    except Exception:
        return None


def _is_expired(ticket: dict[str, Any]) -> bool:
    expires = _parse_time(ticket.get("expires_at"))
    if expires is None:
        return False
    return datetime.now().astimezone() > expires


def _lease_expired(ticket: dict[str, Any]) -> bool:
    lease = ticket.get("lease") if isinstance(ticket.get("lease"), dict) else {}
    expires = _parse_time(lease.get("lease_expires_at"))
    if expires is None:
        return False
    return datetime.now().astimezone() > expires


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _bounded_int(value: Any, *, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(high, max(low, number))


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(min(1.0, max(0.0, number)), 3)


@dataclass
class _ContractLock:
    path: Path
    timeout_seconds: float = 3.0
    stale_seconds: float = 30.0

    _fd: int | None = None

    def __enter__(self) -> "_ContractLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        while True:
            try:
                self._fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode("ascii", errors="ignore"))
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > self.stale_seconds:
                        self.path.unlink()
                        continue
                except OSError:
                    pass
                if time.monotonic() - started >= self.timeout_seconds:
                    raise TimeoutError(f"metabolism contract lock timed out: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
