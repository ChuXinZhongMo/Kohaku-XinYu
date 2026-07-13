"""Tests for kernel governance status builder."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from kernel.owner_grants import grant_owner_scope
from kernel.runtime_self import persist_runtime_self
from kernel.self import Self
from xinyu_bridge_kernel_status import build_kernel_governance_status


def test_build_kernel_governance_status_exposes_meta_threshold():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        meta_path = root / "memory" / "kernel" / "reorg_meta_state.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(
            json.dumps(
                {
                    "slow_escalation_threshold": 2,
                    "recommendation": "consider_lower_slow_escalation_threshold",
                    "fast_impact_rate": 0.5,
                    "slow_impact_rate": 0.0,
                }
            ),
            encoding="utf-8",
        )
        persist_runtime_self(Self(self_id="xinyu_runtime_self"), root)
        grant_owner_scope(root, "belief", note="owner grant")

        status = build_kernel_governance_status(root)
        assert status["available"] is True
        assert status["slow_escalation_threshold"] == 2
        assert status["reorg_recommendation"] == "consider_lower_slow_escalation_threshold"
        assert "belief" in status["granted_scopes"]