"""Tests for kernel review CLI."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kernel.self import Self
from kernel.runtime_self import persist_runtime_self
from xinyu_kernel_review_cli import apply_kernel_review, grant_kernel_scope, kernel_governance_status


def test_kernel_governance_status_empty_inbox():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        persist_runtime_self(Self(self_id="xinyu_runtime_self"), root)
        status = kernel_governance_status(root)
        assert status["ok"] is True
        assert status["pending_count"] == 0
        assert status["slow_escalation_threshold"] == 3


def test_kernel_governance_status_lists_pending_world_fact():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        s = Self(self_id="xinyu_runtime_self")
        s.world_model.add_fact("Owner expects direct replies.", confidence=0.9, review_status="review_only")
        persist_runtime_self(s, root)

        status = kernel_governance_status(root)
        assert status["pending_count"] >= 1
        assert status["world_model_count"] >= 1
        wm_items = [i for i in status["items"] if i["domain"] == "world_model"]
        assert wm_items


def test_apply_kernel_review_approves_world_fact():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        s = Self(self_id="xinyu_runtime_self")
        s.world_model.add_fact("Trust requires consistency.", confidence=0.88, review_status="review_only")
        pending = s.get_pending_world_facts()
        assert pending
        fid = pending[0]["fact_id"]
        persist_runtime_self(s, root)

        result = apply_kernel_review(root, domain="world_model", item_id=fid, action="approve")
        assert result["ok"] is True
        assert result["applied"] is True
        assert result["pending_count"] == 0


def test_grant_kernel_scope_updates_granted_scopes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        persist_runtime_self(Self(self_id="xinyu_runtime_self"), root)

        result = grant_kernel_scope(root, scope="world_model", note="desktop test")
        assert result["ok"] is True
        assert "world_model" in result["granted_scopes"]
        assert "world_model" not in result["grantable_scopes"]