from __future__ import annotations

from pathlib import Path

from run_heavy_maintenance import LOCK_REL, _acquire_lock, _release_lock, run_heavy_maintenance
from xinyu_bridge_heavy_maintenance import heavy_maintenance_subprocess_enabled
from xinyu_dialogue_archive import store_memory_candidate, update_memory_candidate_status
from xinyu_skill_library import list_skills


def _seed_corroborated(root: Path) -> None:
    claim = "owner_turn: 我喜欢简洁直接的回答方式"
    for cid in ("c1", "c2"):
        store_memory_candidate(
            root,
            candidate_id=cid,
            candidate_type="owner_preference",
            source_message_ids=[1],
            source_turn_id=f"t{cid}",
            candidate_text=claim,
            confidence_score=70,
            target_gate="g",
            target_memory_layer="memory/people/owner.md",
            reason="durable preference",
        )
        update_memory_candidate_status(root, candidate_id=cid, status="owner_review_required")


def test_worker_runs_lanes_and_synthesizes_skill(tmp_path: Path) -> None:
    (tmp_path / "memory" / "dreams").mkdir(parents=True)
    _seed_corroborated(tmp_path)
    result = run_heavy_maintenance(tmp_path)
    assert result["status"] == "ok"
    assert set(result["lanes"]) == {"candidate_maintenance", "skill_synthesis", "consolidation", "dream"}
    assert result["lanes"]["skill_synthesis"]["created"] == 1
    assert len(list_skills(tmp_path)) == 1


def test_worker_is_idempotent(tmp_path: Path) -> None:
    (tmp_path / "memory" / "dreams").mkdir(parents=True)
    _seed_corroborated(tmp_path)
    run_heavy_maintenance(tmp_path)
    again = run_heavy_maintenance(tmp_path)
    assert again["lanes"]["skill_synthesis"]["created"] == 0
    assert again["lanes"]["skill_synthesis"]["updated"] >= 1
    assert len(list_skills(tmp_path)) == 1


def test_single_flight_lock_blocks_concurrent_pass(tmp_path: Path) -> None:
    (tmp_path / "runtime").mkdir(parents=True)
    held = _acquire_lock(tmp_path)
    assert held is not None
    try:
        # a second pass while the lock is held must skip rather than run
        result = run_heavy_maintenance(tmp_path)
        assert result["status"] == "skipped_locked"
    finally:
        _release_lock(held)
    assert not (tmp_path / LOCK_REL).exists()
    # once released, a pass runs normally again
    (tmp_path / "memory" / "dreams").mkdir(parents=True)
    assert run_heavy_maintenance(tmp_path)["status"] == "ok"


def test_unknown_lane_is_isolated(tmp_path: Path) -> None:
    result = run_heavy_maintenance(tmp_path, lanes=("skill_synthesis", "bogus_lane"))
    assert result["lanes"]["bogus_lane"] == {"error": "unknown_lane"}
    assert "skill_synthesis" in result["lanes"]


def test_subprocess_flag_default_on_with_off_escape(monkeypatch) -> None:
    monkeypatch.delenv("XINYU_HEAVY_MAINTENANCE_SUBPROCESS", raising=False)
    assert heavy_maintenance_subprocess_enabled() is True
    monkeypatch.setenv("XINYU_HEAVY_MAINTENANCE_SUBPROCESS", "0")
    assert heavy_maintenance_subprocess_enabled() is False
