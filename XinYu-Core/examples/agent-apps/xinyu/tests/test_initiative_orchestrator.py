from __future__ import annotations

import json
from pathlib import Path

import xinyu_bridge_desktop_proactive_routes
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_initiative_orchestrator import (
    record_initiative_feedback,
    run_initiative_orchestrator,
)


def _seed_proactive_request(
    root: Path,
    *,
    request_id: str = "proreq-test",
    question: str = "I found a grounded follow-up worth showing owner.",
    status: str = "ready",
) -> None:
    path = root / "memory/context/proactive_request_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "title: Proactive Request State",
                "updated_at: 2026-05-13T01:00:00+08:00",
                "---",
                "",
                "# Proactive Request State",
                "",
                "## Current Request",
                f"- request_id: {request_id}",
                "- created_at: 2026-05-13T01:00:00+08:00",
                f"- status: {status}",
                "- kind: reflection_question",
                "- source: self_thought",
                "- focus_kind: reflection",
                "- focus_label: grounded owner follow-up",
                "- evidence_label: owner_relevant fresh",
                "- evidence_hash: sha256:test",
                f"- concrete_question: {question}",
                "- requested_action: owner_review",
                "- request_answer_state: pending",
                "- delivery_level: queue_owner_private",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_dream_output(
    root: Path,
    *,
    dream_id: str = "dream-test",
    surface: str = "A quiet dream residue asks for later review.",
) -> None:
    path = root / "memory/dreams/dream_output_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "title: Dream Output State",
                "updated_at: 2026-05-13T01:00:00+08:00",
                "---",
                "",
                "# Dream Output State",
                "",
                f"- dream_id: {dream_id}",
                "- produced_at: 2026-05-13T01:00:00+08:00",
                "- theme: dream residue",
                f"- dream_surface: {surface}",
                "- emotional_weight: 60",
                "- confidence_score: 72",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_context_gate(
    root: Path,
    *,
    scene: str = "casual_chat",
    posture: str = "quiet_by_default",
    recall_count: int = 0,
    next_action: str = "answer_naturally",
) -> None:
    state_path = root / "memory/context/contextual_self_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        "\n".join(
            [
                "- evaluated_at: 2026-05-13T01:30:00+08:00",
                "- last_trigger: test",
                f"- current_scene: {scene}",
                "- working_context_budget: short",
                "- forgetting_posture: test_posture",
                "- retrieval_intents: test",
                "- working_self: test_self",
                f"- initiative_posture: {posture}",
                f"- next_action_bias: {next_action}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    recall_path = root / "memory/context/contextual_recall_state.md"
    recall_path.write_text(
        "\n".join(
            [
                "- evaluated_at: 2026-05-13T01:31:00+08:00",
                f"- current_scene: {scene}",
                "- retrieval_intents: test",
                f"- admitted_recall_count: {recall_count}",
                "- suppressed_recall_count: 0",
                f"- source_count: {1 if recall_count else 0}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_owner_long_idle(root: Path, *, minutes: int = 360) -> None:
    path = root / "memory/context/interaction_journal_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "- updated_at: 2026-05-13T01:30:00+08:00",
                "- last_owner_private_at: 2026-05-12T19:30:00+08:00",
                f"- minutes_since_last_owner_private: {minutes}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_runtime_program_awareness(
    root: Path,
    *,
    watched_source_error: bool = False,
    codex_delegate_status: str = "",
) -> None:
    path = root / "memory/context/runtime_program_awareness.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Runtime Program Awareness",
        "",
        "## Subsystems",
        "- bridge_core: bridge_process=running current_turn_state=finished last_turn_status=ok",
    ]
    if codex_delegate_status:
        lines.extend(
            [
                "",
                "## Programs",
                f"- codex_delegate: status={codex_delegate_status} task_id=test-delegate",
            ]
        )
    if watched_source_error:
        lines.extend(
            [
                "",
                "## Traces",
                "- watched_source: age_seconds=654 size_bytes=190479 last_status=error last_notes=fetch_error_connecttimeout",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _events(root: Path) -> list[dict[str, object]]:
    path = root / "runtime/initiative_lifecycle_events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _make_runtime(tmp_path: Path) -> XinYuBridgeRuntime:
    root = tmp_path / "xinyu"
    (root / "memory/context").mkdir(parents=True)
    (root / "memory/self").mkdir(parents=True)
    (root / "memory/relationships").mkdir(parents=True)
    (root / "memory/people").mkdir(parents=True)
    (root / "prompts").mkdir(parents=True)
    (root / "config.yaml").write_text("name: xinyu\n", encoding="utf-8")
    (root / "prompts/system.md").write_text("# system\n", encoding="utf-8")
    (root / "prompts/output.md").write_text("# output\n", encoding="utf-8")
    (root / "prompts/live_voice_card.md").write_text("# card\n", encoding="utf-8")
    (root / "memory/self/core.md").write_text("core\n", encoding="utf-8")
    (root / "memory/self/personality_profile.md").write_text("profile\n", encoding="utf-8")
    (root / "memory/self/narrative.md").write_text("narrative\n", encoding="utf-8")
    (root / "memory/context/persona_surface_state.md").write_text("surface\n", encoding="utf-8")
    (root / "memory/context/recent_context.md").write_text("recent\n", encoding="utf-8")
    (root / "memory/context/memory_weight_state.md").write_text("weights\n", encoding="utf-8")
    return XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=3,
        max_text_chars=8000,
        settle_seconds=0,
        outward_renderer=False,
    )


def test_no_candidates_writes_safe_state(tmp_path: Path) -> None:
    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
        dry_run=True,
    )

    state = (tmp_path / "memory/context/initiative_lifecycle_state.md").read_text(encoding="utf-8")
    events = _events(tmp_path)

    assert result["status"] == "no_candidates"
    assert result["desktop_item"] == {}
    assert "selected_candidate_id: none" in state
    assert events[-1]["status"] == "no_candidates"


def test_high_scoring_candidate_creates_local_only_desktop_item(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
    )

    desktop_item = result["desktop_item"]
    event = _events(tmp_path)[-1]

    assert result["status"] == "desktop_inbox"
    assert desktop_item["source"] == "initiative_orchestrator"
    assert desktop_item["deliveryLevel"] == "state_only"
    assert desktop_item["claimable"] is False
    assert event["delivery"]["level"] == "desktop_inbox"
    assert event["delivery"]["claimable"] is False
    assert event["feedback"]["status"] == "pending"
    assert event["feedback"]["requires_owner_feedback"] is True
    metrics = json.loads((tmp_path / "runtime/initiative_metrics.json").read_text(encoding="utf-8"))
    assert metrics["pending_feedback_count"] == 1


def test_context_gate_quiet_by_default_holds_ordinary_initiative(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)
    _seed_context_gate(tmp_path, scene="casual_chat", posture="quiet_by_default", recall_count=0)

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
    )
    event = _events(tmp_path)[-1]
    state = (tmp_path / "memory/context/initiative_lifecycle_state.md").read_text(encoding="utf-8")

    assert result["status"] == "hold_private"
    assert result["desktop_item"] == {}
    assert result["context_gate"]["current_scene"] == "casual_chat"
    assert "context_gate_quiet_by_default" in result["reasons_negative"]
    assert event["context_gate"]["initiative_posture"] == "quiet_by_default"
    assert event["delivery"]["level"] == "private_bias"
    assert event["feedback"]["status"] == "private_only"
    assert event["feedback"]["requires_owner_feedback"] is False
    assert "context_scene: casual_chat" in state
    metrics = json.loads((tmp_path / "runtime/initiative_metrics.json").read_text(encoding="utf-8"))
    assert metrics["pending_feedback_count"] == 0


def test_owner_long_idle_surfaces_gentle_presence_in_quiet_context(tmp_path: Path) -> None:
    _seed_owner_long_idle(tmp_path, minutes=360)
    _seed_context_gate(tmp_path, scene="casual_chat", posture="quiet_by_default", recall_count=0)

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T01:30:00+08:00",
        trigger="test",
    )
    event = _events(tmp_path)[-1]
    state = (tmp_path / "memory/context/initiative_lifecycle_state.md").read_text(encoding="utf-8")

    assert result["status"] == "desktop_inbox"
    assert result["source_type"] == "owner_long_idle"
    assert result["desktop_item"]["claimable"] is False
    assert "qq_send_disabled_for_owner_long_idle_v0" in result["hard_blocks"]
    assert "qq_send_disabled_for_owner_long_idle_v0" in result["notes"]
    assert "context_gate_passed" in result["notes"]
    assert "context_gate_quiet_by_default" not in result["reasons_negative"]
    assert event["delivery"]["level"] == "desktop_inbox"
    assert event["delivery"]["claimable"] is False
    assert "- selected_decision: desktop_inbox" in state


def test_context_gate_allows_substantive_task_done_in_quiet_context(tmp_path: Path) -> None:
    _seed_runtime_program_awareness(tmp_path, codex_delegate_status="finished")
    _seed_context_gate(tmp_path, scene="casual_chat", posture="quiet_by_default", recall_count=0)

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
    )
    event = _events(tmp_path)[-1]

    assert result["status"] == "desktop_inbox"
    assert result["source_type"] == "task_done"
    assert result["desktop_item"]["deliveryLevel"] == "state_only"
    assert "context_gate_passed" in result["notes"]
    assert "context_gate_quiet_by_default" not in result["reasons_negative"]
    assert event["delivery"]["level"] == "desktop_inbox"
    assert "context_gate_passed" in event["gate"]["notes"]


def test_context_gate_feedback_scene_with_recall_allows_desktop_candidate(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)
    _seed_context_gate(
        tmp_path,
        scene="initiative_feedback",
        posture="feedback_shaped",
        recall_count=2,
        next_action="adjust_bias_before_action",
    )

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
    )
    event = _events(tmp_path)[-1]

    assert result["status"] == "desktop_inbox"
    assert result["desktop_item"]["claimable"] is False
    assert result["context_gate"]["recall_support"] is True
    assert "context_gate_passed" in result["notes"]
    assert event["context_gate"]["admitted_recall_count"] == 2
    assert "context_gate_passed" in event["gate"]["notes"]


def test_watched_source_runtime_error_stays_internal(tmp_path: Path) -> None:
    _seed_runtime_program_awareness(tmp_path, watched_source_error=True)
    _seed_context_gate(tmp_path, scene="casual_chat", posture="quiet_by_default", recall_count=2)

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T19:30:01+08:00",
        trigger="test",
    )

    assert result["status"] == "no_candidates"
    assert result["desktop_item"] == {}


def test_desktop_focus_label_does_not_expose_score_reasons(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)
    _seed_context_gate(
        tmp_path,
        scene="initiative_feedback",
        posture="feedback_shaped",
        recall_count=2,
        next_action="adjust_bias_before_action",
    )

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
    )
    desktop_item = result["desktop_item"]

    assert desktop_item["focusLabel"] == "想法待确认"
    assert "utility_score" not in desktop_item["focusLabel"]
    assert "urgency_score" not in desktop_item["focusLabel"]


def test_dry_run_records_decision_without_desktop_item(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
        dry_run=True,
    )

    assert result["desktop_item"] == {}
    event = _events(tmp_path)[-1]
    assert event["delivery"]["level"] == "dry_run"
    assert event["feedback"]["status"] == "not_requested"
    assert event["feedback"]["requires_owner_feedback"] is False
    metrics = json.loads((tmp_path / "runtime/initiative_metrics.json").read_text(encoding="utf-8"))
    assert metrics["pending_feedback_count"] == 0


def test_expired_desktop_candidate_no_longer_counts_as_pending_feedback(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)

    first = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
    )
    assert first["delivery_level"] == "desktop_inbox"

    run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-15T02:00:00+08:00",
        trigger="test",
    )

    metrics = json.loads((tmp_path / "runtime/initiative_metrics.json").read_text(encoding="utf-8"))
    state = (tmp_path / "memory/context/initiative_lifecycle_state.md").read_text(encoding="utf-8")
    assert metrics["pending_feedback_count"] == 0
    assert "pending_feedback_count: 0" in state


def test_internal_marker_candidate_is_blocked(tmp_path: Path) -> None:
    _seed_proactive_request(
        tmp_path,
        question="authorization: bearer-secret-token-value should never be surfaced",
    )

    result = run_initiative_orchestrator(
        tmp_path,
        checked_at="2026-05-13T02:00:00+08:00",
        trigger="test",
    )
    event = _events(tmp_path)[-1]

    assert result["status"] == "blocked"
    assert result["desktop_item"] == {}
    assert "owner_visible_text_redacted_sensitive" in event["gate"]["blocked_by"]


def test_repeated_candidate_gets_repetition_penalty(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)

    first = run_initiative_orchestrator(tmp_path, checked_at="2026-05-13T02:00:00+08:00", trigger="test")
    second = run_initiative_orchestrator(tmp_path, checked_at="2026-05-13T02:01:00+08:00", trigger="test")

    assert second["total_score"] < first["total_score"]
    assert "repetition_penalty" in second["reasons_negative"]


def test_dismiss_feedback_holds_same_future_candidate(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)
    first = run_initiative_orchestrator(tmp_path, checked_at="2026-05-13T02:00:00+08:00", trigger="test")

    feedback = record_initiative_feedback(
        tmp_path,
        candidate_id=str(first["candidate_id"]),
        action="dismiss",
        feedback_at="2026-05-13T02:02:00+08:00",
    )
    second = run_initiative_orchestrator(tmp_path, checked_at="2026-05-13T02:03:00+08:00", trigger="test")

    feedback_state = (tmp_path / "memory/context/initiative_feedback_state.md").read_text(encoding="utf-8")
    assert feedback["recorded"] is True
    assert "future_effect: lower similar future initiative priority" in feedback_state
    assert second["status"] == "hold_private"
    assert "recent_feedback_dismissed" in second["reasons_negative"]


def test_reply_feedback_records_without_stable_memory_promotion(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)
    first = run_initiative_orchestrator(tmp_path, checked_at="2026-05-13T02:00:00+08:00", trigger="test")

    result = record_initiative_feedback(
        tmp_path,
        candidate_id=str(first["candidate_id"]),
        action="reply",
        feedback_at="2026-05-13T02:02:00+08:00",
    )

    feedback_state = (tmp_path / "memory/context/initiative_feedback_state.md").read_text(encoding="utf-8")
    assert result["recorded"] is True
    assert "personality_promotion: blocked" in feedback_state
    assert "stable_memory_write: blocked" in feedback_state


def test_reply_feedback_bias_increases_similar_future_candidate(tmp_path: Path) -> None:
    feedback_root = tmp_path / "feedback"
    plain_root = tmp_path / "plain"
    _seed_dream_output(feedback_root, dream_id="dream-first")
    first = run_initiative_orchestrator(feedback_root, checked_at="2026-05-13T02:00:00+08:00", trigger="test")
    record_initiative_feedback(
        feedback_root,
        candidate_id=str(first["candidate_id"]),
        action="reply",
        feedback_at="2026-05-13T02:02:00+08:00",
    )

    _seed_dream_output(
        feedback_root,
        dream_id="dream-second",
        surface="A second quiet dream residue asks for later review.",
    )
    _seed_dream_output(
        plain_root,
        dream_id="dream-second",
        surface="A second quiet dream residue asks for later review.",
    )
    biased = run_initiative_orchestrator(feedback_root, checked_at="2026-05-13T02:03:00+08:00", trigger="test")
    baseline = run_initiative_orchestrator(plain_root, checked_at="2026-05-13T02:03:00+08:00", trigger="test")

    assert biased["total_score"] > baseline["total_score"]
    assert "feedback_bias_replied" in biased["reasons_positive"]


def test_failed_feedback_bias_lowers_similar_future_candidate(tmp_path: Path) -> None:
    feedback_root = tmp_path / "feedback"
    plain_root = tmp_path / "plain"
    _seed_dream_output(feedback_root, dream_id="dream-first")
    first = run_initiative_orchestrator(feedback_root, checked_at="2026-05-13T02:00:00+08:00", trigger="test")
    record_initiative_feedback(
        feedback_root,
        candidate_id=str(first["candidate_id"]),
        action="failed",
        feedback_at="2026-05-13T02:02:00+08:00",
    )

    _seed_dream_output(
        feedback_root,
        dream_id="dream-second",
        surface="A second quiet dream residue asks for later review.",
    )
    _seed_dream_output(
        plain_root,
        dream_id="dream-second",
        surface="A second quiet dream residue asks for later review.",
    )
    biased = run_initiative_orchestrator(feedback_root, checked_at="2026-05-13T02:03:00+08:00", trigger="test")
    baseline = run_initiative_orchestrator(plain_root, checked_at="2026-05-13T02:03:00+08:00", trigger="test")

    assert biased["total_score"] < baseline["total_score"]
    assert "feedback_bias_failed_delivery" in biased["reasons_negative"]


def test_metrics_written_after_decision_and_feedback(tmp_path: Path) -> None:
    _seed_proactive_request(tmp_path)
    first = run_initiative_orchestrator(tmp_path, checked_at="2026-05-13T02:00:00+08:00", trigger="test")
    record_initiative_feedback(
        tmp_path,
        candidate_id=str(first["candidate_id"]),
        action="dismiss",
        feedback_at="2026-05-13T02:02:00+08:00",
    )

    metrics = json.loads((tmp_path / "runtime/initiative_metrics.json").read_text(encoding="utf-8"))

    assert metrics["updated_at"] == "2026-05-13T02:02:00+08:00"
    assert metrics["window_hours"] == 24
    assert metrics["event_count_24h"] == 2
    assert metrics["decision_event_count_24h"] == 1
    assert metrics["feedback_count_24h"] == 1
    assert metrics["desktop_shown_count_24h"] == 1
    assert metrics["dismiss_count_24h"] == 1
    assert metrics["pending_feedback_count"] == 0
    assert metrics["status_counts_24h"]["desktop_inbox"] == 1
    assert metrics["feedback_counts_24h"]["dismissed"] == 1


def test_bridge_autonomous_sidecar_publishes_local_only_initiative(monkeypatch, tmp_path: Path) -> None:
    runtime = _make_runtime(tmp_path)
    calls: dict[str, object] = {}

    def fake_orchestrator(root, *, checked_at, trigger, delivery_level, dry_run):
        calls["args"] = {
            "root": root,
            "checked_at": checked_at,
            "trigger": trigger,
            "delivery_level": delivery_level,
            "dry_run": dry_run,
        }
        return {
            "status": "desktop_inbox",
            "source_type": "reflection_question",
            "total_score": 120,
            "delivery_level": "desktop_inbox",
            "notes": ["desktop_inbox_local_only"],
            "desktop_item": {
                "candidateId": "procand-test",
                "status": "candidate_only",
                "deliveryLevel": "state_only",
                "claimable": False,
                "source": "initiative_orchestrator",
                "candidatePreview": "local only",
                "createdAt": "2026-05-13T02:00:00+08:00",
                "initiativeLifecycle": True,
            },
        }

    monkeypatch.setattr(
        "xinyu_bridge_autonomous_maintenance.run_proactivity_scorer_shadow",
        lambda root, *, checked_at: {"status": "hold"},
    )
    monkeypatch.setattr("xinyu_bridge_autonomous_maintenance.run_initiative_orchestrator", fake_orchestrator)
    monkeypatch.setattr(
        "xinyu_bridge_autonomous_maintenance.run_emotion_council_shadow",
        lambda *args, **kwargs: {"status": "ok"},
    )
    monkeypatch.setattr(
        "xinyu_bridge_autonomous_maintenance.run_impulse_soup",
        lambda *args, **kwargs: {"status": "ok"},
    )
    monkeypatch.setattr(
        "xinyu_bridge_autonomous_maintenance.run_initiative_spine",
        lambda *args, **kwargs: {"emergence_level": "shadow", "action_permission": "hold"},
    )
    monkeypatch.setattr(
        "xinyu_bridge_autonomous_maintenance.run_desire_drive_state",
        lambda *args, **kwargs: {
            "status": "active",
            "dominant_drive": "repair",
            "drive_intensity": "0.5",
            "autonomy_tension": "low",
        },
    )
    monkeypatch.setattr(
        "xinyu_bridge_autonomous_maintenance.run_contextual_self_observatory",
        lambda *args, **kwargs: {
            "posture": "balanced_or_insufficient_data",
            "latest_scene": "initiative_feedback",
            "recall_admitted_count_24h": 2,
            "initiative_held_by_context_count_24h": 1,
        },
    )

    notes: list[str] = []
    runtime._append_proactivity_shadow_note(notes, checked_at="2026-05-13T02:00:00+08:00")

    assert calls["args"]["delivery_level"] == "desktop_inbox"
    assert calls["args"]["dry_run"] is False
    assert "desktop_initiative_candidate_ready_scheduled" in notes
    assert "contextual_self_observatory:balanced_or_insufficient_data/initiative_feedback/2/1" in notes
    inbox = runtime._desktop_proactive_existing("procand-test")
    assert inbox["claimable"] is False
    assert inbox["source"] == "initiative_orchestrator"


def test_bridge_suppresses_duplicate_initiative_ready_notification(tmp_path: Path) -> None:
    runtime = _make_runtime(tmp_path)
    published: list[dict[str, object]] = []

    def fake_publish(event_type, payload, *, privacy="internal_summary", severity=None):
        published.append(
            {
                "event_type": event_type,
                "payload": payload,
                "privacy": privacy,
                "severity": severity,
            }
        )

    runtime._desktop_publish_event_threadsafe = fake_publish  # type: ignore[method-assign]
    item = {
        "candidateId": "procand-test",
        "status": "candidate_only",
        "deliveryLevel": "state_only",
        "claimable": False,
        "source": "initiative_orchestrator",
        "candidatePreview": "same preview",
        "initiativeLifecycle": True,
    }

    assert runtime._desktop_publish_initiative_candidate_threadsafe(item)
    assert runtime._desktop_publish_initiative_candidate_threadsafe(item)

    assert len(published) == 1
    assert published[0]["event_type"] == "proactive.candidate.ready"


def test_bridge_desktop_ack_records_initiative_feedback(monkeypatch, tmp_path: Path) -> None:
    runtime = _make_runtime(tmp_path)
    recorded: dict[str, object] = {}
    runtime._desktop_upsert_proactive_inbox(
        {
            "candidateId": "procand-test",
            "status": "candidate_only",
            "deliveryLevel": "state_only",
            "claimable": False,
            "source": "initiative_orchestrator",
            "candidatePreview": "local only",
            "initiativeLifecycle": True,
        }
    )

    def fake_feedback(root, *, candidate_id, action, feedback_at, details):
        recorded.update(
            {
                "root": root,
                "candidate_id": candidate_id,
                "action": action,
                "details": details,
            }
        )
        return {"accepted": True, "recorded": True}

    monkeypatch.setattr(xinyu_bridge_desktop_proactive_routes, "record_initiative_feedback", fake_feedback)

    result = runtime._record_desktop_initiative_feedback(
        runtime._desktop_proactive_existing("procand-test"),
        action="dismiss",
    )

    assert result["recorded"] is True
    assert recorded["candidate_id"] == "procand-test"
    assert recorded["action"] == "dismiss"
    assert recorded["details"]["claimable"] is False


def test_desktop_proactive_history_writes_standard_event_time(tmp_path: Path) -> None:
    runtime = _make_runtime(tmp_path)

    runtime._desktop_remember_proactive_history(
        {
            "candidateId": "procand-test",
            "status": "dismissed",
            "updatedAt": "2026-05-13T03:00:00+08:00",
        }
    )

    rows = [
        json.loads(line)
        for line in (runtime.xinyu_dir / "memory/context/proactive_request_history.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    assert rows[0]["handledAt"] == "2026-05-13T03:00:00+08:00"
    assert rows[0]["event_time"] == "2026-05-13T03:00:00+08:00"


def test_desktop_xinyu_state_exposes_initiative_metrics(tmp_path: Path) -> None:
    runtime = _make_runtime(tmp_path)

    state = runtime._desktop_xinyu_state(
        environment={},
        entropy_state={},
        active_desires=[],
        proactive_items=[],
        recent_turns=[],
        recent_memory_events=[],
        initiative_metrics={
            "observed": "true",
            "updated_at": "2026-05-13T02:02:00+08:00",
            "window_hours": "24",
            "desktop_shown_count_24h": "1",
            "feedback_count_24h": "2",
            "dismiss_count_24h": "1",
            "reply_count_24h": "1",
            "pending_feedback_count": "0",
        },
    )

    assert state["initiative_metrics"]["observed"] is True
    assert state["initiative_metrics"]["updatedAt"] == "2026-05-13T02:02:00+08:00"
    assert state["initiative_metrics"]["desktopShown24h"] == 1
    assert state["initiative_metrics"]["feedbackCount24h"] == 2
    assert state["initiative_metrics"]["pendingFeedbackCount"] == 0
