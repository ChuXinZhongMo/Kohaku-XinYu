from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import json
import py_compile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from xinyu_self_choice_store import SelfChoiceStore


def _ledger_events(root: Path) -> list[dict]:
    path = root / "runtime/life_kernel/entropy_ledger.jsonl"
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def _write_state(root: Path, state: dict) -> None:
    path = root / "runtime/life_kernel/self_choice_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def _smoke() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-self-choice-store-") as tmp:
        root = Path(tmp)
        now = datetime.now().astimezone().replace(microsecond=0)
        store = SelfChoiceStore(root)
        await store.load_or_recover(now=now)
        initial = await store.snapshot_private()
        runtime = initial.get("runtime_affect") if isinstance(initial.get("runtime_affect"), dict) else {}
        if initial.get("version") != 1:
            failures.append(f"default state version mismatch: {initial}")
        for key in ("urge_to_express", "self_closure", "fatigue"):
            if not isinstance(runtime.get(key), float):
                failures.append(f"default runtime affect missing float {key}: {runtime}")

        await store.flush()
        state_path = root / "runtime/life_kernel/self_choice_state.json"
        if not state_path.is_file():
            failures.append("flush did not write self_choice_state.json")
        else:
            try:
                json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(f"flush wrote invalid JSON: {exc}")

        before_reject = await store.snapshot_private()
        await store.apply_event_impulse("ticket_rejected", now=now + timedelta(minutes=1))
        after_reject = await store.snapshot_private()
        before_runtime = before_reject["runtime_affect"]
        after_runtime = after_reject["runtime_affect"]
        before_sediment = before_reject["affective_sediment"]
        after_sediment = after_reject["affective_sediment"]
        if after_runtime["self_closure"] <= before_runtime["self_closure"]:
            failures.append("ticket_rejected did not raise closure")
        if after_runtime["fatigue"] <= before_runtime["fatigue"]:
            failures.append("ticket_rejected did not raise fatigue")
        if after_runtime["urge_to_express"] <= before_runtime["urge_to_express"]:
            failures.append("ticket_rejected did not raise urge")
        if after_sediment["rejection_scar"] <= before_sediment["rejection_scar"]:
            failures.append("ticket_rejected did not raise rejection scar")
        await store.flush()

        reloaded = SelfChoiceStore(root)
        await reloaded.load_or_recover(now=now + timedelta(minutes=2))
        reloaded_state = await reloaded.snapshot_private()
        if reloaded_state["runtime_affect"]["self_closure"] != after_runtime["self_closure"]:
            failures.append("reload did not preserve flushed closure")

        decay_state = await reloaded.snapshot_private()
        decay_state["last_seen_at"] = (now - timedelta(hours=1)).isoformat()
        decay_state["runtime_affect"]["urge_to_express"] = 0.9
        decay_state["runtime_affect"]["self_closure"] = 0.8
        decay_state["runtime_affect"]["fatigue"] = 0.7
        decay_state["affective_sediment"]["baseline_urge"] = 0.4
        decay_state["affective_sediment"]["baseline_closure"] = 0.3
        _write_state(root, decay_state)
        decay_store = SelfChoiceStore(root)
        await decay_store.load_or_recover(now=now)
        decay_result = await decay_store.apply_time_decay(now=now)
        decayed = (await decay_store.snapshot_private())["runtime_affect"]
        if decay_result.get("mode") != "normal_decay":
            failures.append(f"one-hour gap should use normal decay: {decay_result}")
        if not (0.4 < decayed["urge_to_express"] < 0.9):
            failures.append(f"urge did not decay toward baseline: {decayed}")
        if not (0.3 < decayed["self_closure"] < 0.8):
            failures.append(f"closure did not decay toward baseline: {decayed}")
        if not (0.0 <= decayed["fatigue"] < 0.7):
            failures.append(f"fatigue did not decay toward clear baseline: {decayed}")

        hibernation_state = await decay_store.snapshot_private()
        hibernation_state["last_seen_at"] = (now - timedelta(hours=168)).isoformat()
        hibernation_state["runtime_affect"]["urge_to_express"] = 0.36
        hibernation_state["runtime_affect"]["self_closure"] = 0.34
        hibernation_state["runtime_affect"]["fatigue"] = 0.2
        hibernation_state["physical_cues"] = []
        hibernation_state["hibernation"]["pending_wake_residue"] = None
        _write_state(root, hibernation_state)
        hibernation_store = SelfChoiceStore(root)
        await hibernation_store.load_or_recover(now=now)
        wake = await hibernation_store.apply_time_decay(now=now)
        if wake.get("mode") != "hibernation_wake":
            failures.append(f"long offline gap should be hibernation wake: {wake}")
        public_wake = await hibernation_store.snapshot_public()
        if "waking_from_hibernation" not in public_wake.get("physical_cues", []):
            failures.append(f"hibernation cue missing from public snapshot: {public_wake}")
        second = await hibernation_store.apply_time_decay(now=now + timedelta(minutes=1))
        if second.get("mode") == "hibernation_wake":
            failures.append("hibernation wake residue duplicated on second decay")
        wake_events = [event for event in _ledger_events(root) if event.get("event") == "self_choice_hibernation_wake"]
        if len(wake_events) != 1:
            failures.append(f"hibernation wake should write one ledger event: {wake_events}")

        impulse_store = SelfChoiceStore(root)
        await impulse_store.load_or_recover(now=now + timedelta(minutes=3))
        before_approve = await impulse_store.snapshot_private()
        await impulse_store.apply_event_impulse("ticket_approved", now=now + timedelta(minutes=4))
        approved = await impulse_store.snapshot_private()
        if approved["runtime_affect"]["self_closure"] >= before_approve["runtime_affect"]["self_closure"]:
            failures.append("ticket_approved did not lower closure")
        if approved["runtime_affect"]["urge_to_express"] <= before_approve["runtime_affect"]["urge_to_express"]:
            failures.append("ticket_approved did not raise urge")

        before_settle = await impulse_store.snapshot_private()
        await impulse_store.apply_event_impulse("ticket_settled", now=now + timedelta(minutes=5))
        settled = await impulse_store.snapshot_private()
        if settled["runtime_affect"]["fatigue"] >= before_settle["runtime_affect"]["fatigue"]:
            failures.append("ticket_settled did not lower fatigue")
        if settled["affective_sediment"]["repair_trust"] <= before_settle["affective_sediment"]["repair_trust"]:
            failures.append("ticket_settled did not raise repair trust")

        public = await impulse_store.snapshot_public()
        public_text = json.dumps(public, ensure_ascii=False)
        for forbidden in ("urge_to_express", "self_closure", "baseline_urge", "baseline_closure"):
            if forbidden in public_text:
                failures.append(f"public snapshot leaked raw field {forbidden}: {public}")
        band = public.get("affect_band") if isinstance(public.get("affect_band"), dict) else {}
        if sorted(band) != ["closure", "fatigue", "urge"]:
            failures.append(f"public snapshot missing affect bands: {public}")

        corrupt_root = root / "corrupt-case"
        corrupt_path = corrupt_root / "runtime/life_kernel/self_choice_state.json"
        corrupt_path.parent.mkdir(parents=True, exist_ok=True)
        corrupt_path.write_text("{bad json", encoding="utf-8")
        corrupt_store = SelfChoiceStore(corrupt_root)
        await corrupt_store.load_or_recover(now=now)
        corrupt_public = await corrupt_store.snapshot_public()
        if "recovered_from_corrupt_state" not in corrupt_public.get("physical_cues", []):
            failures.append(f"corrupt recovery cue missing: {corrupt_public}")
        if not list(corrupt_path.parent.glob("self_choice_state.json.corrupt-*")):
            failures.append("corrupt state was not backed up")
        recovered_events = [
            event for event in _ledger_events(corrupt_root) if event.get("event") == "self_choice_state_recovered"
        ]
        if not recovered_events:
            failures.append("corrupt recovery did not write ledger event")

        module_path = ROOT / "xinyu_self_choice_store.py"
        try:
            py_compile.compile(str(module_path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"py_compile failed for xinyu_self_choice_store.py: {exc}")
    return failures


def main() -> int:
    failures = asyncio.run(_smoke())
    if failures:
        print("XinYu self choice store smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu self choice store smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
