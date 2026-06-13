from __future__ import annotations

import asyncio
import copy
import json
import math
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SELF_CHOICE_VERSION = 1
STATE_REL = Path("runtime/life_kernel/self_choice_state.json")
LOCK_REL = Path("runtime/life_kernel/.self_choice_state.lock")
LEDGER_REL = Path("runtime/life_kernel/entropy_ledger.jsonl")

HIBERNATION_GAP_HOURS = 24.0
IDLE_GAP_HOURS = 2.0
IDLE_DECAY_CAP_HOURS = 2.0
FLUSH_INTERVAL_SECONDS = 10.0

URGE_TAU_HOURS = 10.0
CLOSURE_TAU_HOURS = 18.0
FATIGUE_TAU_HOURS = 8.0

RUNTIME_DEFAULTS = {
    "urge_to_express": 0.42,
    "self_closure": 0.36,
    "fatigue": 0.18,
    "last_choice": "",
    "last_choice_at": "",
}
SEDIMENT_DEFAULTS = {
    "baseline_urge": 0.38,
    "baseline_closure": 0.32,
    "rejection_scar": 0.0,
    "repair_trust": 0.2,
    "motif_biases": {},
}
RECOVERY_RUNTIME_DEFAULTS = {
    "urge_to_express": 0.36,
    "self_closure": 0.42,
    "fatigue": 0.22,
    "last_choice": "",
    "last_choice_at": "",
}
RECOVERY_SEDIMENT_DEFAULTS = {
    "baseline_urge": 0.36,
    "baseline_closure": 0.34,
    "rejection_scar": 0.0,
    "repair_trust": 0.2,
    "motif_biases": {},
}


class SelfChoiceStore:
    def __init__(self, root: Path, *, state_path: Path | None = None) -> None:
        self.root = root
        self.state_path = state_path or root / STATE_REL
        self.lock_path = root / LOCK_REL
        self.ledger_path = root / LEDGER_REL
        self._lock = asyncio.Lock()
        self._state: dict[str, Any] = _default_state(_now())
        self._loaded = False
        self._dirty = False
        self._last_error = ""
        self._last_flush_monotonic = 0.0
        self._last_decay: dict[str, Any] = {}
        self._last_recovery_at = ""

    async def load_or_recover(self, *, now: datetime | None = None) -> dict[str, Any]:
        now_dt = _coerce_now(now)
        async with self._lock:
            if self._loaded:
                return self.health_snapshot()
            recovered = False
            recovered_reason = ""
            state: dict[str, Any] | None = None
            flush_after_load = False
            try:
                with _FileLock(self.lock_path):
                    if not self.state_path.exists():
                        state = _default_state(now_dt)
                        self._dirty = True
                    else:
                        try:
                            loaded = json.loads(self.state_path.read_text(encoding="utf-8-sig"))
                            if not isinstance(loaded, dict):
                                raise ValueError("self choice state root must be an object")
                            state = _normalize_state(loaded, now_dt=now_dt, recovery=False)
                        except Exception as exc:
                            recovered = True
                            recovered_reason = f"{type(exc).__name__}: {exc}"
                            self._backup_corrupt_locked(now_dt)
                            state = _default_state(now_dt, recovery=True)
                            _add_cue(state, "recovered_from_corrupt_state", snapshots=2)
                            self._dirty = True
                    self._state = state
                    self._loaded = True
                    self._last_error = ""
                    if recovered:
                        self._last_recovery_at = _iso(now_dt)
                        self._append_ledger_locked(
                            "self_choice_state_recovered",
                            now_dt=now_dt,
                            payload={
                                "state_path": _rel_path(self.root, self.state_path),
                                "reason": recovered_reason,
                            },
                        )
                    if self._dirty:
                        flush_after_load = True
                if flush_after_load:
                    self._flush_locked(now_dt=now_dt)
            except Exception as exc:
                self._state = _default_state(now_dt, recovery=True)
                _add_cue(self._state, "recovered_from_corrupt_state", snapshots=2)
                self._loaded = True
                self._dirty = True
                self._last_error = f"{type(exc).__name__}: {exc}"
            return self.health_snapshot()

    async def apply_time_decay(self, *, now: datetime | None = None) -> dict[str, Any]:
        await self._ensure_loaded(now=now)
        now_dt = _coerce_now(now)
        async with self._lock:
            result = self._apply_time_decay_locked(now_dt)
            if result.get("dirty"):
                self._flush_if_due_locked(now_dt=now_dt)
            return dict(result)

    async def apply_event_impulse(
        self,
        event: str,
        *,
        now: datetime | None = None,
        flush: bool = True,
    ) -> dict[str, Any]:
        await self._ensure_loaded(now=now)
        now_dt = _coerce_now(now)
        async with self._lock:
            self._apply_time_decay_locked(now_dt)
            applied = self._apply_event_impulse_locked(event, now_dt=now_dt)
            if applied:
                self._append_ledger_locked(
                    "self_choice_event_impulse",
                    now_dt=now_dt,
                    payload={"source_event": event, "affect_band": _affect_band(self._state)},
                )
            if flush and self._dirty:
                self._flush_locked(now_dt=now_dt)
            return self._public_snapshot_locked(consume_cues=False)

    async def apply_experience_impulse(
        self,
        frame: dict[str, Any],
        *,
        now: datetime | None = None,
        flush: bool = True,
    ) -> dict[str, Any]:
        await self._ensure_loaded(now=now)
        now_dt = _coerce_now(now)
        async with self._lock:
            self._apply_time_decay_locked(now_dt)
            applied = self._apply_experience_impulse_locked(frame, now_dt=now_dt)
            if applied:
                impulse = frame.get("affect_impulse") if isinstance(frame.get("affect_impulse"), dict) else {}
                self._append_ledger_locked(
                    "self_choice_experience_impulse",
                    now_dt=now_dt,
                    payload={
                        "experience_id": _safe_str(frame.get("experience_id")),
                        "tool": _safe_str(frame.get("tool")),
                        "result": _safe_str(frame.get("result")),
                        "pressure_band": _safe_str(
                            (frame.get("pressure") if isinstance(frame.get("pressure"), dict) else {}).get("band")
                        ),
                        "cue": _safe_str(impulse.get("cue")),
                        "affect_band": _affect_band(self._state),
                    },
                )
            if flush and self._dirty:
                self._flush_locked(now_dt=now_dt)
            return self._public_snapshot_locked(consume_cues=False)

    async def record_life_choice(
        self,
        choice: str,
        *,
        now: datetime | None = None,
        flush: bool = False,
    ) -> None:
        await self._ensure_loaded(now=now)
        now_dt = _coerce_now(now)
        choice_text = _safe_str(choice).strip()
        async with self._lock:
            runtime = _runtime(self._state)
            if choice_text and runtime.get("last_choice") != choice_text:
                runtime["last_choice"] = choice_text
                runtime["last_choice_at"] = _iso(now_dt)
                self._touch_locked(now_dt)
            if flush and self._dirty:
                self._flush_locked(now_dt=now_dt)
            else:
                self._flush_if_due_locked(now_dt=now_dt)

    async def snapshot_public(self, *, consume_cues: bool = True) -> dict[str, Any]:
        await self._ensure_loaded()
        async with self._lock:
            snapshot = self._public_snapshot_locked(consume_cues=consume_cues)
            if consume_cues and self._dirty:
                self._flush_if_due_locked(now_dt=_now())
            return snapshot

    async def snapshot_private(self) -> dict[str, Any]:
        await self._ensure_loaded()
        async with self._lock:
            return copy.deepcopy(self._state)

    async def dream_bias_snapshot(self) -> dict[str, Any]:
        await self._ensure_loaded()
        async with self._lock:
            hibernation = _hibernation(self._state)
            pending = hibernation.get("pending_wake_residue")
            return {
                "version": SELF_CHOICE_VERSION,
                "affect_band": _affect_band(self._state),
                "physical_cues": _cue_strings(self._state),
                "hibernation": {
                    "pending_wake_residue": isinstance(pending, dict),
                    "last_wake_at": _safe_str(hibernation.get("last_wake_at")),
                    "last_offline_hours": _bounded_float(hibernation.get("last_offline_hours"), default=0.0),
                    "first_metabolism_after_hibernation": isinstance(pending, dict)
                    and not _safe_str(pending.get("consumed_at")),
                },
                "notes": ["self_choice_dream_bias_v1"],
            }

    async def consume_hibernation_residue_for_metabolism(self, *, now: datetime | None = None) -> None:
        await self._ensure_loaded(now=now)
        now_dt = _coerce_now(now)
        async with self._lock:
            hibernation = _hibernation(self._state)
            pending = hibernation.get("pending_wake_residue")
            if isinstance(pending, dict):
                pending["consumed_at"] = _iso(now_dt)
                hibernation["pending_wake_residue"] = None
                self._touch_locked(now_dt)
                self._flush_locked(now_dt=now_dt)

    async def flush(self) -> None:
        await self._ensure_loaded()
        async with self._lock:
            if self._dirty:
                self._flush_locked(now_dt=_now())

    async def shutdown(self) -> None:
        await self.flush()

    def health_snapshot(self) -> dict[str, Any]:
        state = self._state if isinstance(self._state, dict) else _default_state(_now())
        hibernation = _hibernation(state)
        pending = hibernation.get("pending_wake_residue")
        return {
            "loaded": self._loaded,
            "state_path": str(self.state_path),
            "dirty": self._dirty,
            "last_error": self._last_error,
            "last_recovery_at": self._last_recovery_at,
            "affect_band": _affect_band(state),
            "last_choice": _safe_str(_runtime(state).get("last_choice")),
            "hibernation": {
                "last_wake_at": _safe_str(hibernation.get("last_wake_at")),
                "last_offline_hours": _bounded_float(hibernation.get("last_offline_hours"), default=0.0),
                "pending_wake_residue": isinstance(pending, dict),
            },
            "notes": ["self_choice_store_v1"],
        }

    def boot_log_line(self) -> str:
        band = _affect_band(self._state)
        hibernation = _hibernation(self._state)
        pending = hibernation.get("pending_wake_residue")
        waking = isinstance(pending, dict) or self._last_decay.get("mode") == "hibernation_wake"
        if waking:
            offline = int(round(_bounded_float(hibernation.get("last_offline_hours"), default=0.0)))
            hibernation_text = f"{offline}h->single_wake_residue"
            state_text = "waking"
        else:
            hibernation_text = "none"
            state_text = band["closure"]
        affect = f"{band['urge']}/{band['closure']}"
        return (
            "[xinyu_life_kernel] "
            f"self_choice={state_text} affect={affect} "
            f"hibernation={hibernation_text} metabolism=idle ledger=ready"
        )

    async def _ensure_loaded(self, *, now: datetime | None = None) -> None:
        if not self._loaded:
            await self.load_or_recover(now=now)

    def _apply_time_decay_locked(self, now_dt: datetime) -> dict[str, Any]:
        state = self._state
        runtime = _runtime(state)
        sediment = _sediment(state)
        last_seen = _parse_time(state.get("last_seen_at")) or now_dt
        gap_hours = max(0.0, (now_dt - last_seen).total_seconds() / 3600.0)
        if gap_hours <= 0.0001:
            state["last_seen_at"] = _iso(now_dt)
            self._last_decay = {"mode": "none", "gap_hours": 0.0, "dirty": False}
            return dict(self._last_decay)

        if gap_hours >= HIBERNATION_GAP_HOURS:
            runtime["fatigue"] = push_up(runtime["fatigue"], 0.04)
            runtime["self_closure"] = push_up(runtime["self_closure"], 0.03)
            runtime["urge_to_express"] = push_up(runtime["urge_to_express"], 0.02)
            hibernation = _hibernation(state)
            hibernation["last_wake_at"] = _iso(now_dt)
            hibernation["last_offline_hours"] = round(gap_hours, 3)
            hibernation["pending_wake_residue"] = {
                "cue": "waking_from_hibernation",
                "offline_hours": round(gap_hours, 3),
                "applied_at": _iso(now_dt),
                "consumed_at": "",
            }
            _add_cue(state, "waking_from_hibernation", snapshots=2)
            self._append_ledger_locked(
                "self_choice_hibernation_wake",
                now_dt=now_dt,
                payload={
                    "offline_hours": round(gap_hours, 3),
                    "applied_as": "single_wake_residue",
                },
            )
            mode = "hibernation_wake"
        elif gap_hours >= IDLE_GAP_HOURS:
            decay_hours = min(gap_hours, IDLE_DECAY_CAP_HOURS)
            _decay_runtime_to_baseline(runtime, sediment, gap_hours=decay_hours)
            idle_ratio = min(1.0, gap_hours / HIBERNATION_GAP_HOURS)
            runtime["self_closure"] = push_up(runtime["self_closure"], 0.025 * idle_ratio)
            runtime["fatigue"] = push_up(runtime["fatigue"], 0.018 * idle_ratio)
            runtime["urge_to_express"] = pull_down(runtime["urge_to_express"], 0.018 * idle_ratio)
            mode = "idle_decay_capped"
        else:
            _decay_runtime_to_baseline(runtime, sediment, gap_hours=gap_hours)
            mode = "normal_decay"

        state["last_seen_at"] = _iso(now_dt)
        self._touch_locked(now_dt)
        self._last_decay = {"mode": mode, "gap_hours": round(gap_hours, 3), "dirty": True}
        return dict(self._last_decay)

    def _apply_event_impulse_locked(self, event: str, *, now_dt: datetime) -> bool:
        runtime = _runtime(self._state)
        sediment = _sediment(self._state)
        event_name = _safe_str(event).strip()
        cue = ""
        if event_name == "ticket_approved":
            runtime["self_closure"] = pull_down(runtime["self_closure"], 0.08)
            runtime["urge_to_express"] = push_up(runtime["urge_to_express"], 0.03)
            cue = "compute_yield_received"
        elif event_name == "ticket_rejected":
            runtime["self_closure"] = push_up(runtime["self_closure"], 0.18)
            runtime["fatigue"] = push_up(runtime["fatigue"], 0.06)
            runtime["urge_to_express"] = push_up(runtime["urge_to_express"], 0.04)
            sediment["rejection_scar"] = push_up(sediment["rejection_scar"], 0.04)
            cue = "boundary_hardened"
        elif event_name == "ticket_settled":
            runtime["fatigue"] = pull_down(runtime["fatigue"], 0.18)
            runtime["self_closure"] = pull_down(runtime["self_closure"], 0.05)
            sediment["repair_trust"] = push_up(sediment["repair_trust"], 0.04)
            cue = "metabolism_settled"
        elif event_name == "ticket_failed":
            runtime["fatigue"] = push_up(runtime["fatigue"], 0.08)
            runtime["self_closure"] = push_up(runtime["self_closure"], 0.05)
            cue = "metabolism_failed"
        elif event_name == "suppress_and_decay":
            runtime["self_closure"] = push_up(runtime["self_closure"], 0.10)
            runtime["urge_to_express"] = push_up(runtime["urge_to_express"], 0.06)
            runtime["fatigue"] = push_up(runtime["fatigue"], 0.03)
            runtime["last_choice"] = "suppress_and_wait"
            runtime["last_choice_at"] = _iso(now_dt)
            cue = "withheld"
        else:
            return False
        if cue:
            _add_cue(self._state, cue, snapshots=2)
        self._touch_locked(now_dt)
        return True

    def _apply_experience_impulse_locked(self, frame: dict[str, Any], *, now_dt: datetime) -> bool:
        if not isinstance(frame, dict):
            return False
        impulse = frame.get("affect_impulse")
        if not isinstance(impulse, dict):
            return False
        runtime = _runtime(self._state)
        fatigue_delta = _clamped_delta(impulse.get("fatigue_delta"), floor=-0.04, ceiling=0.08)
        closure_delta = _clamped_delta(impulse.get("closure_delta"), floor=-0.04, ceiling=0.06)
        urge_delta = _clamped_delta(impulse.get("urge_delta"), floor=-0.03, ceiling=0.04)
        if fatigue_delta:
            runtime["fatigue"] = _round(_bounded_float(runtime.get("fatigue"), default=0.0) + fatigue_delta)
        if closure_delta:
            runtime["self_closure"] = _round(_bounded_float(runtime.get("self_closure"), default=0.0) + closure_delta)
        if urge_delta:
            runtime["urge_to_express"] = _round(_bounded_float(runtime.get("urge_to_express"), default=0.0) + urge_delta)
        runtime["fatigue"] = _bounded_float(runtime.get("fatigue"), default=0.0)
        runtime["self_closure"] = _bounded_float(runtime.get("self_closure"), default=0.0)
        runtime["urge_to_express"] = _bounded_float(runtime.get("urge_to_express"), default=0.0)
        cue = _safe_str(impulse.get("cue")).strip()
        if cue:
            _add_cue(self._state, cue, snapshots=2)
        if fatigue_delta or closure_delta or urge_delta or cue:
            self._touch_locked(now_dt)
            return True
        return False

    def _public_snapshot_locked(self, *, consume_cues: bool) -> dict[str, Any]:
        cues = _cue_strings(self._state)
        snapshot = {
            "version": SELF_CHOICE_VERSION,
            "affect_band": _affect_band(self._state),
            "last_choice": _safe_str(_runtime(self._state).get("last_choice")),
            "physical_cues": cues,
            "notes": ["self_choice_snapshot_v1"],
        }
        if consume_cues and cues:
            remaining: list[dict[str, Any]] = []
            for item in _cues(self._state):
                item["remaining_snapshots"] = max(0, int(item.get("remaining_snapshots", 1)) - 1)
                if int(item.get("remaining_snapshots", 0)) > 0:
                    remaining.append(item)
            self._state["physical_cues"] = remaining
            self._touch_locked(_now())
        return snapshot

    def _touch_locked(self, now_dt: datetime) -> None:
        self._state["version"] = SELF_CHOICE_VERSION
        self._state["updated_at"] = _iso(now_dt)
        self._dirty = True

    def _flush_if_due_locked(self, *, now_dt: datetime) -> None:
        if not self._dirty:
            return
        if time.monotonic() - self._last_flush_monotonic >= FLUSH_INTERVAL_SECONDS:
            self._flush_locked(now_dt=now_dt)

    def _flush_locked(self, *, now_dt: datetime) -> None:
        self._state = _normalize_state(self._state, now_dt=now_dt, recovery=False)
        self._state["updated_at"] = _iso(now_dt)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with _FileLock(self.lock_path):
            _write_json_atomic(self.state_path, self._state)
        self._dirty = False
        self._last_flush_monotonic = time.monotonic()
        self._last_error = ""

    def _backup_corrupt_locked(self, now_dt: datetime) -> None:
        if not self.state_path.exists():
            return
        stamp = now_dt.strftime("%Y%m%d-%H%M%S")
        backup = self.state_path.with_name(f"{self.state_path.name}.corrupt-{stamp}")
        if backup.exists():
            backup = self.state_path.with_name(f"{self.state_path.name}.corrupt-{stamp}-{uuid.uuid4().hex[:6]}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        os.replace(self.state_path, backup)

    def _append_ledger_locked(self, event: str, *, now_dt: datetime, payload: dict[str, Any]) -> None:
        ledger_event = {
            "version": SELF_CHOICE_VERSION,
            "event_id": f"ledger:{uuid.uuid4().hex[:16]}",
            "event": event,
            "created_at": _iso(now_dt),
            "payload": payload,
        }
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(ledger_event, ensure_ascii=False, separators=(",", ":")) + "\n")


def push_up(value: Any, amount: float, ceiling: float = 1.0) -> float:
    current = _bounded_float(value, default=0.0)
    return _round(current + (ceiling - current) * max(0.0, amount))


def pull_down(value: Any, amount: float, floor: float = 0.0) -> float:
    current = _bounded_float(value, default=0.0)
    return _round(current - (current - floor) * max(0.0, amount))


def _clamped_delta(value: Any, *, floor: float, ceiling: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(floor, min(ceiling, number)), 3)


def public_affect_band_from_state(state: dict[str, Any]) -> dict[str, str]:
    return _affect_band(_normalize_state(state, now_dt=_now(), recovery=False))


def _default_state(now_dt: datetime, *, recovery: bool = False) -> dict[str, Any]:
    runtime = dict(RECOVERY_RUNTIME_DEFAULTS if recovery else RUNTIME_DEFAULTS)
    sediment = dict(RECOVERY_SEDIMENT_DEFAULTS if recovery else SEDIMENT_DEFAULTS)
    return {
        "version": SELF_CHOICE_VERSION,
        "updated_at": _iso(now_dt),
        "last_seen_at": _iso(now_dt),
        "runtime_affect": runtime,
        "affective_sediment": sediment,
        "hibernation": {
            "last_wake_at": "",
            "last_offline_hours": 0.0,
            "pending_wake_residue": None,
        },
        "physical_cues": [],
        "notes": ["self_choice_state_v1"],
    }


def _normalize_state(value: dict[str, Any], *, now_dt: datetime, recovery: bool) -> dict[str, Any]:
    default = _default_state(now_dt, recovery=recovery)
    state = dict(value)
    state["version"] = SELF_CHOICE_VERSION
    state["updated_at"] = _safe_str(state.get("updated_at")) or default["updated_at"]
    state["last_seen_at"] = _safe_str(state.get("last_seen_at")) or _safe_str(state.get("updated_at")) or default[
        "last_seen_at"
    ]

    runtime_value = state.get("runtime_affect") if isinstance(state.get("runtime_affect"), dict) else {}
    runtime_defaults = default["runtime_affect"]
    state["runtime_affect"] = {
        "urge_to_express": _bounded_float(
            runtime_value.get("urge_to_express"), default=runtime_defaults["urge_to_express"]
        ),
        "self_closure": _bounded_float(runtime_value.get("self_closure"), default=runtime_defaults["self_closure"]),
        "fatigue": _bounded_float(runtime_value.get("fatigue"), default=runtime_defaults["fatigue"]),
        "last_choice": _safe_str(runtime_value.get("last_choice")),
        "last_choice_at": _safe_str(runtime_value.get("last_choice_at")),
    }

    sediment_value = state.get("affective_sediment") if isinstance(state.get("affective_sediment"), dict) else {}
    sediment_defaults = default["affective_sediment"]
    motif_biases = sediment_value.get("motif_biases")
    state["affective_sediment"] = {
        "baseline_urge": _bounded_float(
            sediment_value.get("baseline_urge"),
            default=sediment_defaults["baseline_urge"],
            low=0.18,
            high=0.78,
        ),
        "baseline_closure": _bounded_float(
            sediment_value.get("baseline_closure"),
            default=sediment_defaults["baseline_closure"],
            low=0.18,
            high=0.72,
        ),
        "rejection_scar": _bounded_float(sediment_value.get("rejection_scar"), default=0.0),
        "repair_trust": _bounded_float(sediment_value.get("repair_trust"), default=0.2),
        "motif_biases": motif_biases if isinstance(motif_biases, dict) else {},
    }

    hibernation_value = state.get("hibernation") if isinstance(state.get("hibernation"), dict) else {}
    pending = hibernation_value.get("pending_wake_residue")
    state["hibernation"] = {
        "last_wake_at": _safe_str(hibernation_value.get("last_wake_at")),
        "last_offline_hours": _bounded_float(hibernation_value.get("last_offline_hours"), default=0.0, high=100000.0),
        "pending_wake_residue": pending if isinstance(pending, dict) else None,
    }
    state["physical_cues"] = _normalize_cues(state.get("physical_cues"))
    notes = state.get("notes")
    state["notes"] = [str(item) for item in notes if str(item).strip()][:20] if isinstance(notes, list) else []
    if "self_choice_state_v1" not in state["notes"]:
        state["notes"].append("self_choice_state_v1")
    return state


def _runtime(state: dict[str, Any]) -> dict[str, Any]:
    runtime = state.get("runtime_affect")
    if not isinstance(runtime, dict):
        runtime = dict(RUNTIME_DEFAULTS)
        state["runtime_affect"] = runtime
    return runtime


def _sediment(state: dict[str, Any]) -> dict[str, Any]:
    sediment = state.get("affective_sediment")
    if not isinstance(sediment, dict):
        sediment = dict(SEDIMENT_DEFAULTS)
        state["affective_sediment"] = sediment
    return sediment


def _hibernation(state: dict[str, Any]) -> dict[str, Any]:
    hibernation = state.get("hibernation")
    if not isinstance(hibernation, dict):
        hibernation = {
            "last_wake_at": "",
            "last_offline_hours": 0.0,
            "pending_wake_residue": None,
        }
        state["hibernation"] = hibernation
    return hibernation


def _cues(state: dict[str, Any]) -> list[dict[str, Any]]:
    cues = state.get("physical_cues")
    if not isinstance(cues, list):
        cues = []
        state["physical_cues"] = cues
    normalized = _normalize_cues(cues)
    state["physical_cues"] = normalized
    return normalized


def _normalize_cues(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, str):
            cue = item.strip()
            remaining = 1
            created_at = ""
        elif isinstance(item, dict):
            cue = _safe_str(item.get("cue") or item.get("name")).strip()
            remaining = _bounded_int(item.get("remaining_snapshots"), default=1, low=0, high=5)
            created_at = _safe_str(item.get("created_at"))
        else:
            continue
        if not cue or remaining <= 0 or cue in seen:
            continue
        seen.add(cue)
        result.append({"cue": cue, "remaining_snapshots": remaining, "created_at": created_at})
    return result[-8:]


def _add_cue(state: dict[str, Any], cue: str, *, snapshots: int = 2) -> None:
    cue_text = _safe_str(cue).strip()
    if not cue_text:
        return
    cues = [item for item in _cues(state) if item.get("cue") != cue_text]
    cues.append({"cue": cue_text, "remaining_snapshots": max(1, snapshots), "created_at": _iso(_now())})
    state["physical_cues"] = cues[-8:]


def _cue_strings(state: dict[str, Any]) -> list[str]:
    return [_safe_str(item.get("cue")) for item in _cues(state) if _safe_str(item.get("cue"))]


def _affect_band(state: dict[str, Any]) -> dict[str, str]:
    runtime = _runtime(state)
    return {
        "urge": _urge_band(_bounded_float(runtime.get("urge_to_express"), default=0.0)),
        "closure": _closure_band(_bounded_float(runtime.get("self_closure"), default=0.0)),
        "fatigue": _fatigue_band(_bounded_float(runtime.get("fatigue"), default=0.0)),
    }


def _urge_band(value: float) -> str:
    if value < 0.34:
        return "low"
    if value < 0.67:
        return "warm"
    return "high"


def _closure_band(value: float) -> str:
    if value < 0.34:
        return "open"
    if value < 0.67:
        return "guarded"
    return "withdrawn"


def _fatigue_band(value: float) -> str:
    if value < 0.34:
        return "clear"
    if value < 0.67:
        return "tired"
    return "spent"


def _decay_runtime_to_baseline(runtime: dict[str, Any], sediment: dict[str, Any], *, gap_hours: float) -> None:
    runtime["urge_to_express"] = _decay(
        runtime.get("urge_to_express"),
        baseline=sediment.get("baseline_urge"),
        gap_hours=gap_hours,
        tau_hours=URGE_TAU_HOURS,
    )
    runtime["self_closure"] = _decay(
        runtime.get("self_closure"),
        baseline=sediment.get("baseline_closure"),
        gap_hours=gap_hours,
        tau_hours=CLOSURE_TAU_HOURS,
    )
    runtime["fatigue"] = _decay(
        runtime.get("fatigue"),
        baseline=0.0,
        gap_hours=gap_hours,
        tau_hours=FATIGUE_TAU_HOURS,
    )


def _decay(value: Any, *, baseline: Any, gap_hours: float, tau_hours: float) -> float:
    current = _bounded_float(value, default=0.0)
    base = _bounded_float(baseline, default=0.0)
    factor = math.exp(-max(0.0, gap_hours) / max(0.001, tau_hours))
    return _round(base + (current - base) * factor)


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _rel_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _coerce_now(value: datetime | None) -> datetime:
    if value is None:
        return _now()
    if value.tzinfo is None:
        return value.astimezone()
    return value.astimezone()


def _now() -> datetime:
    return datetime.now().astimezone()


def _iso(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="seconds")


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(_safe_str(value))
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed.astimezone()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _bounded_float(value: Any, *, default: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return _round(min(high, max(low, number)))


def _bounded_int(value: Any, *, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(high, max(low, number))


def _round(value: float) -> float:
    return round(min(1.0, max(0.0, float(value))), 3)


@dataclass
class _FileLock:
    path: Path
    timeout_seconds: float = 3.0
    stale_seconds: float = 30.0

    _fd: int | None = None

    def __enter__(self) -> "_FileLock":
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
                    raise TimeoutError(f"self choice state lock timed out: {self.path}")
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
