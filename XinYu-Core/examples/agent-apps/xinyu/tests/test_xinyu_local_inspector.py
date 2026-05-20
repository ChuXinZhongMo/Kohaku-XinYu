from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_archive import store_memory_candidate
from xinyu_local_inspector import build_inspection, render_text, write_dashboard
from xinyu_turn_route_trace import record_turn_route_stage


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_local_inspector_summarizes_runtime_without_private_text(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/runtime_self_presence.md",
        """
# Runtime Self Presence

## Current Runtime
- bridge_process: running
- current_turn_state: running
- current_turn_started_at: 2026-01-01T00:00:00+08:00
- current_turn_id: turn-private-123456789
- current_turn_kind: owner_private_live_turn
- current_turn_source: owner_private
- current_turn_relation: owner
""",
    )
    record_turn_route_stage(
        tmp_path,
        turn_id="turn-private-123456789",
        stage="model_inject",
        route="slow_live",
        status="timeout",
        elapsed_ms=9000,
        notes=["model_inject_timeout"],
    )
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        """
# Proactive Request State
- status: sent
- kind: clarify
- reason: ask_owner:active_question:D:\\XinYu\\secret\\x.md
- urgency: low
- risk: low_owner_private
- owner_relevance: owner_action:owner_answer
- channel: owner_private
- delivery_level: queue_owner_private
- request_answer_state: pending
- concrete_question: private owner question should not be rendered
""",
    )
    _write(
        tmp_path / "memory/context/proactive_qq_dispatch_state.md",
        """
# Proactive QQ Dispatch State
- last_claim_status: sent
- last_ack_status: failed
- adapter_error: failed for qq 2692167682 at D:\\XinYu\\secret\\x.md
""",
    )
    _write(
        tmp_path / "xinyu_qq_gateway.config.json",
        json.dumps(
            {
                "enabled": True,
                "core_chat_url": "http://127.0.0.1:8765/chat",
                "onebot_port": 6199,
                "send_replies": True,
                "qq_outbox_enabled": True,
                "owner_user_ids": ["2692167682"],
                "whitelist_user_ids": ["2692167682"],
            }
        ),
    )
    assert store_memory_candidate(
        tmp_path,
        candidate_id="cand-1",
        candidate_type="project_fact",
        source_message_ids=[],
        candidate_text="private memory candidate should not render",
        confidence_score=70,
        target_gate="owner_review",
        target_memory_layer="context",
        reason="test",
    )

    summary = build_inspection(tmp_path, include_network=False)
    rendered = render_text(summary)

    assert summary["current_turn"]["state"] == "stale_running"
    assert summary["operator"]["route_status"] == "timeout"
    assert summary["memory_candidates"]["pending"] == 1
    assert "turn_stale_running" in summary["warnings"]["critical"][0]
    assert "proactive_last_ack_failed" in summary["warnings"]["items"]
    assert "private owner question" not in rendered
    assert "2692167682" not in rendered
    assert "D:\\XinYu" not in rendered


def test_local_inspector_writes_minimal_dashboard(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/runtime_self_presence.md",
        """
# Runtime Self Presence
- current_turn_state: idle
""",
    )
    summary = build_inspection(tmp_path, include_network=False)
    output = write_dashboard(tmp_path, summary)

    html = output.read_text(encoding="utf-8")
    assert output == tmp_path / "runtime/local_inspector_dashboard.html"
    assert "XinYu Local Inspector" in html
    assert "Sanitized JSON" in html
    assert "&lt;xinyu_dir&gt;" in html
