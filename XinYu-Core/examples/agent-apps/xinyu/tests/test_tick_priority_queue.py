from __future__ import annotations

from xinyu_tick_priority_queue import (
    TickCandidate,
    plan_from_device_gate,
    plan_tick_queue,
    resource_pressure_from_device_metrics,
    should_run_kind,
)


def test_live_chat_preempts() -> None:
    plan = plan_tick_queue(
        [
            TickCandidate(kind="tech_scout", ready=True),
            TickCandidate(kind="live_chat", ready=True),
            TickCandidate(kind="maintenance", ready=True),
        ],
        device_allowed=True,
        max_allowed=2,
    )
    assert plan.allowed[0].kind == "live_chat"
    assert should_run_kind(plan, "live_chat")


def test_device_blocks_heavy_scout() -> None:
    plan = plan_tick_queue(
        [
            TickCandidate(kind="tech_scout", ready=True),
            TickCandidate(kind="maintenance", ready=True),
            TickCandidate(kind="heartbeat", ready=True),
        ],
        device_allowed=False,
        device_reason="cpu_high",
        resource_pressure=0.9,
        max_allowed=3,
    )
    assert not should_run_kind(plan, "tech_scout")
    kinds_allowed = {d.kind for d in plan.allowed}
    assert "tech_scout" not in kinds_allowed


def test_proactive_without_finding_not_allowed() -> None:
    plan = plan_tick_queue(
        [
            TickCandidate(kind="proactive", ready=True, has_finding=False, concrete=True),
            TickCandidate(kind="maintenance", ready=True),
        ],
        max_allowed=2,
    )
    assert not should_run_kind(plan, "proactive")


def test_high_pe_proactive_with_finding_ranks_above_scout() -> None:
    plan = plan_tick_queue(
        [
            TickCandidate(
                kind="proactive",
                ready=True,
                has_finding=True,
                concrete=True,
                pe_stress=0.9,
                predicted_deviation=0.8,
            ),
            TickCandidate(kind="tech_scout", ready=True),
        ],
        device_allowed=True,
        resource_pressure=0.2,
        max_allowed=2,
    )
    assert should_run_kind(plan, "proactive")
    # Proactive should rank better (lower score) than scout.
    scores = {d.kind: d.score for d in plan.ordered}
    assert scores["proactive"] < scores["tech_scout"]


def test_plan_from_device_gate_object() -> None:
    class _D:
        allowed = True
        reason = "ok"
        metrics = {"cpu_percent": 20.0, "ram_free_gb": 8.0, "disk_free_gb": 100.0}

    plan = plan_from_device_gate(
        [TickCandidate(kind="tech_scout", ready=True)],
        _D(),
    )
    assert plan.device_allowed is True
    assert should_run_kind(plan, "tech_scout")


def test_resource_pressure_tts() -> None:
    p = resource_pressure_from_device_metrics({"tts_busy": True, "cpu_percent": 10})
    assert p >= 0.55
