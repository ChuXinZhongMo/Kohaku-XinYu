from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from xinyu_self_choice_store import SelfChoiceStore


STATE_REL = Path("runtime/life_kernel/self_choice_state.json")
LEDGER_REL = Path("runtime/life_kernel/entropy_ledger.jsonl")


def _now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def _state_path(root: Path) -> Path:
    return root / STATE_REL


def _ledger_events(root: Path) -> list[dict[str, object]]:
    path = root / LEDGER_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _write_state(root: Path, state: dict[str, object]) -> None:
    path = _state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def test_self_choice_store_loads_default_state(tmp_path: Path) -> None:
    now = _now()
    store = SelfChoiceStore(tmp_path)

    health = await store.load_or_recover(now=now)
    private = await store.snapshot_private()

    assert health["loaded"] is True
    assert health["last_error"] == ""
    assert _state_path(tmp_path).is_file()
    assert private["version"] == 1
    assert private["last_seen_at"] == now.isoformat()
    assert set(private["runtime_affect"]) == {
        "urge_to_express",
        "self_closure",
        "fatigue",
        "last_choice",
        "last_choice_at",
    }
    for key in ("urge_to_express", "self_closure", "fatigue"):
        assert isinstance(private["runtime_affect"][key], float)
    assert isinstance(private["affective_sediment"]["baseline_urge"], float)
    assert private["hibernation"]["pending_wake_residue"] is None


async def test_self_choice_store_flushes_and_reloads_state(tmp_path: Path) -> None:
    now = _now()
    store = SelfChoiceStore(tmp_path)
    await store.load_or_recover(now=now)

    before = await store.snapshot_private()
    await store.apply_event_impulse("ticket_rejected", now=now + timedelta(minutes=1))
    after = await store.snapshot_private()
    await store.flush()

    state_path = _state_path(tmp_path)
    assert state_path.is_file()
    assert json.loads(state_path.read_text(encoding="utf-8"))["runtime_affect"] == after["runtime_affect"]
    assert after["runtime_affect"]["self_closure"] > before["runtime_affect"]["self_closure"]

    reloaded = SelfChoiceStore(tmp_path)
    await reloaded.load_or_recover(now=now + timedelta(minutes=2))

    assert (await reloaded.snapshot_private())["runtime_affect"] == after["runtime_affect"]


async def test_self_choice_store_recovers_corrupt_state_with_backup_and_ledger(tmp_path: Path) -> None:
    now = _now()
    state_path = _state_path(tmp_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{bad json", encoding="utf-8")

    store = SelfChoiceStore(tmp_path)
    health = await store.load_or_recover(now=now)
    public = await store.snapshot_public()

    assert health["last_error"] == ""
    assert health["last_recovery_at"] == now.isoformat()
    assert "recovered_from_corrupt_state" in public["physical_cues"]
    assert list(state_path.parent.glob("self_choice_state.json.corrupt-*"))
    recovered_events = [event for event in _ledger_events(tmp_path) if event.get("event") == "self_choice_state_recovered"]
    assert len(recovered_events) == 1
    assert recovered_events[0]["payload"]["state_path"] == STATE_REL.as_posix()


async def test_self_choice_store_public_snapshot_does_not_expose_raw_private_fields(tmp_path: Path) -> None:
    store = SelfChoiceStore(tmp_path)
    await store.load_or_recover(now=_now())
    await store.apply_event_impulse("ticket_rejected")

    public = await store.snapshot_public()
    public_text = json.dumps(public, ensure_ascii=False)

    assert sorted(public["affect_band"]) == ["closure", "fatigue", "urge"]
    assert "self_choice_snapshot_v1" in public["notes"]
    for forbidden in (
        "runtime_affect",
        "affective_sediment",
        "urge_to_express",
        "self_closure",
        "baseline_urge",
        "baseline_closure",
        "rejection_scar",
        "repair_trust",
        "pending_wake_residue",
    ):
        assert forbidden not in public_text


async def test_self_choice_store_applies_known_event_impulses_and_ignores_unknown_events(tmp_path: Path) -> None:
    now = _now()
    store = SelfChoiceStore(tmp_path)
    await store.load_or_recover(now=now)

    before = await store.snapshot_private()
    await store.apply_event_impulse("ticket_approved", now=now)
    approved = await store.snapshot_private()
    await store.apply_event_impulse("unknown_event", now=now)
    unknown = await store.snapshot_private()

    assert approved["runtime_affect"]["self_closure"] < before["runtime_affect"]["self_closure"]
    assert approved["runtime_affect"]["urge_to_express"] > before["runtime_affect"]["urge_to_express"]
    assert unknown == approved
    events = [event for event in _ledger_events(tmp_path) if event.get("event") == "self_choice_event_impulse"]
    assert [event["payload"]["source_event"] for event in events] == ["ticket_approved"]


async def test_self_choice_store_consumes_hibernation_residue_only_once(tmp_path: Path) -> None:
    now = _now()
    store = SelfChoiceStore(tmp_path)
    await store.load_or_recover(now=now)
    state = await store.snapshot_private()
    state["last_seen_at"] = (now - timedelta(hours=168)).isoformat()
    state["hibernation"]["pending_wake_residue"] = None
    state["physical_cues"] = []
    _write_state(tmp_path, state)

    hibernation_store = SelfChoiceStore(tmp_path)
    await hibernation_store.load_or_recover(now=now)
    wake = await hibernation_store.apply_time_decay(now=now)

    assert wake["mode"] == "hibernation_wake"
    assert (await hibernation_store.dream_bias_snapshot())["hibernation"]["first_metabolism_after_hibernation"] is True

    await hibernation_store.consume_hibernation_residue_for_metabolism(now=now + timedelta(minutes=1))
    after_first = await hibernation_store.snapshot_private()
    await hibernation_store.consume_hibernation_residue_for_metabolism(now=now + timedelta(minutes=2))
    after_second = await hibernation_store.snapshot_private()

    assert after_first["hibernation"]["pending_wake_residue"] is None
    assert after_second == after_first
    wake_events = [event for event in _ledger_events(tmp_path) if event.get("event") == "self_choice_hibernation_wake"]
    assert len(wake_events) == 1
