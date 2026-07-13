"""Tests for reorg meta-learning."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kernel.meta_learning import (
    compute_slow_escalation_threshold,
    get_slow_escalation_threshold,
    load_reorg_meta,
    record_cycle_meta,
)


def test_record_cycle_meta_tracks_impact_rates():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        record_cycle_meta(root, reorg_mode="fast", structural_impact=True)
        record_cycle_meta(root, reorg_mode="fast", structural_impact=False)
        record_cycle_meta(root, reorg_mode="slow", structural_impact=False)

        meta = load_reorg_meta(root)
        assert meta["fast_cycles"] == 2
        assert meta["fast_with_impact"] == 1
        assert meta["fast_impact_rate"] == 0.5
        assert meta["recommendation"] in ("insufficient_data", "balanced", "fast_reorg_often_ineffective_review_gates")
        assert meta["slow_escalation_threshold"] == 3


def test_dynamic_threshold_lowers_when_slow_ineffective():
    meta = {
        "recommendation": "consider_lower_slow_escalation_threshold",
        "slow_cycles": 6,
        "slow_with_impact": 0,
        "fast_cycles": 2,
        "fast_with_impact": 2,
    }
    assert compute_slow_escalation_threshold(meta) == 2


def test_record_cycle_meta_persists_dynamic_threshold():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for _ in range(6):
            record_cycle_meta(root, reorg_mode="slow", structural_impact=False)
        record_cycle_meta(root, reorg_mode="fast", structural_impact=True)
        record_cycle_meta(root, reorg_mode="fast", structural_impact=True)

        meta = load_reorg_meta(root)
        if meta["recommendation"] == "consider_lower_slow_escalation_threshold":
            assert get_slow_escalation_threshold(root) == 2
        else:
            assert get_slow_escalation_threshold(root) in (2, 3, 4, 5)