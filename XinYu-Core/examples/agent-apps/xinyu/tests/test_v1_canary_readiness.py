from __future__ import annotations

import json
from pathlib import Path

from xinyu_v1_canary_readiness import record_v1_shadow_observation


def _write_owner_config(root: Path, owner_id: str = "123456789") -> None:
    (root / "xinyu_qq_gateway.config.json").write_text(
        json.dumps({"owner_user_ids": [owner_id], "whitelist_user_ids": [owner_id]}),
        encoding="utf-8",
    )


def _queue_items(root: Path) -> list[dict[str, object]]:
    path = root / "memory/context/qq_outbox_queue.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    items = data.get("items", [])
    return items if isinstance(items, list) else []


def test_v1_canary_collects_before_threshold(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_V1_CANARY_MIN_SHADOW_TURNS", "3")
    monkeypatch.setenv("XINYU_V1_CANARY_MAX_ERROR_RATE", "0")
    monkeypatch.setenv("XINYU_V1_CANARY_MIN_ROUTE_DIVERSITY", "1")

    result = record_v1_shadow_observation(
        tmp_path,
        accepted=True,
        route="fast_path",
        trace_id="tr-1",
        elapsed_ms=12,
        observed_at="2026-05-03T00:00:00+08:00",
    )

    state = (tmp_path / "memory/context/v1_canary_readiness_state.md").read_text(encoding="utf-8")
    assert result["readiness_decision"] == "collecting_shadow_sample"
    assert "- proposal_status: not_due" in state
    assert "- auto_full_switch: false" in state
    assert _queue_items(tmp_path) == []


def test_v1_canary_ready_is_review_only_by_default_without_qq_outbox(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_V1_CANARY_MIN_SHADOW_TURNS", "3")
    monkeypatch.setenv("XINYU_V1_CANARY_MAX_ERROR_RATE", "0")
    monkeypatch.setenv("XINYU_V1_CANARY_MIN_ROUTE_DIVERSITY", "1")
    monkeypatch.setenv("XINYU_V1_CANARY_PROPOSAL_COOLDOWN_SECONDS", "0")
    monkeypatch.delenv("XINYU_V1_CANARY_QQ_PROPOSAL_ENABLED", raising=False)
    _write_owner_config(tmp_path)

    result: dict[str, object] = {}
    for index in range(3):
        result = record_v1_shadow_observation(
            tmp_path,
            accepted=True,
            route="fast_path",
            trace_id=f"tr-default-{index}",
            elapsed_ms=10 + index,
            observed_at=f"2026-05-03T00:01:0{index}+08:00",
        )

    state = (tmp_path / "memory/context/v1_canary_readiness_state.md").read_text(encoding="utf-8")
    trace = (tmp_path / "runtime/v1_shadow_trace.jsonl").read_text(encoding="utf-8")

    assert result["readiness_decision"] == "ready_for_owner_canary_request"
    assert result["proposal_status"] == "held_review_only"
    assert "- proposal_qq_outbox_enabled: false" in state
    assert "- proposal_status: held_review_only" in state
    assert "- next_action: review_readiness_locally_no_outbox" in state
    assert "v1_canary_owner_proposal_queued" not in trace
    assert _queue_items(tmp_path) == []


def test_v1_canary_ready_queues_owner_proposal_without_switching(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_V1_CANARY_MIN_SHADOW_TURNS", "3")
    monkeypatch.setenv("XINYU_V1_CANARY_MAX_ERROR_RATE", "0")
    monkeypatch.setenv("XINYU_V1_CANARY_MIN_ROUTE_DIVERSITY", "1")
    monkeypatch.setenv("XINYU_V1_CANARY_PROPOSAL_COOLDOWN_SECONDS", "0")
    monkeypatch.setenv("XINYU_V1_CANARY_QQ_PROPOSAL_ENABLED", "true")
    _write_owner_config(tmp_path)

    result: dict[str, object] = {}
    for index in range(3):
        result = record_v1_shadow_observation(
            tmp_path,
            accepted=True,
            route="fast_path",
            trace_id=f"tr-{index}",
            elapsed_ms=10 + index,
            observed_at=f"2026-05-03T00:00:0{index}+08:00",
        )

    state = (tmp_path / "memory/context/v1_canary_readiness_state.md").read_text(encoding="utf-8")
    items = _queue_items(tmp_path)

    assert result["readiness_decision"] == "ready_for_owner_canary_request"
    assert result["proposal_status"] == "queued"
    assert "- switch_permission: owner_approval_required" in state
    assert "- auto_full_switch: false" in state
    assert "- canary_scope: owner_private_simple_messages_only" in state
    assert "XINYU_V1_ENABLED" not in state
    assert len(items) == 1
    assert items[0]["source"] == "v1_canary_readiness"
    assert items[0]["dedupe_key"] == "v1-canary-owner-proposal-20260503"
    assert items[0]["target"]["user_id"] == "123456789"
    assert "不会自己全量切" in str(items[0]["message"])


def test_v1_canary_shadow_errors_block_owner_proposal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_V1_CANARY_MIN_SHADOW_TURNS", "2")
    monkeypatch.setenv("XINYU_V1_CANARY_MAX_ERROR_RATE", "0")
    monkeypatch.setenv("XINYU_V1_CANARY_MIN_ROUTE_DIVERSITY", "1")
    _write_owner_config(tmp_path)

    record_v1_shadow_observation(
        tmp_path,
        accepted=True,
        route="fast_path",
        trace_id="tr-ok",
        elapsed_ms=10,
        observed_at="2026-05-03T00:00:00+08:00",
    )
    result = record_v1_shadow_observation(
        tmp_path,
        accepted=False,
        route="",
        trace_id="",
        elapsed_ms=3000,
        error="TimeoutError: v1 shadow exceeded budget",
        observed_at="2026-05-03T00:00:01+08:00",
    )

    state = (tmp_path / "memory/context/v1_canary_readiness_state.md").read_text(encoding="utf-8")
    assert result["readiness_decision"] == "blocked_shadow_errors"
    assert "- proposal_status: not_due" in state
    assert _queue_items(tmp_path) == []
