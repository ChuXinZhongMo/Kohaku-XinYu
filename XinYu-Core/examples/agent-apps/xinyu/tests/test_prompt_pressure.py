from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

from xinyu_prompt_pressure import (
    PROMPT_PRESSURE_REPORT_REL,
    PromptSidecar,
    select_prompt_sidecars,
    write_prompt_pressure_report,
)


def _visible(
    turn_kind: str = "ordinary_owner_chat",
    *,
    technical_work: bool = False,
    owner_style_pressure: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        turn_kind=turn_kind,
        technical_work=technical_work,
        owner_style_pressure=owner_style_pressure,
        owner_no_change_pressure=False,
        relationship_pressure=False,
        rest_silence=False,
    )


def _sidecar(name: str, admission: str, text: str | None = None) -> PromptSidecar:
    return PromptSidecar.from_parts(name, [text or f"{name} block"], admission=admission)


def test_ordinary_owner_chat_defers_background_runtime_and_old_episode() -> None:
    selection = select_prompt_sidecars(
        [
            PromptSidecar.from_parts("memory_braid", ["memory block"], required=True, admission="core"),
            _sidecar("goldmark_auth", "background"),
            _sidecar("runtime_presence", "status"),
            _sidecar("continuity_handoff", "continuity"),
            _sidecar("recent_action", "episodic"),
            _sidecar("qq_rich_message", "current_turn"),
        ],
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="hello",
        visible_turn=_visible(),
    )

    admitted = {sidecar.name for sidecar in selection.admitted}
    blocked = {decision.sidecar.name for decision in selection.blocked}

    assert selection.mode == "ordinary_owner_quiet"
    assert {"memory_braid", "qq_rich_message"} <= admitted
    assert {"goldmark_auth", "runtime_presence", "continuity_handoff", "recent_action"} <= blocked


def test_status_reference_admits_runtime_but_not_goldmark() -> None:
    selection = select_prompt_sidecars(
        [
            _sidecar("runtime_presence", "status"),
            _sidecar("goldmark_auth", "background"),
        ],
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="xinyu status?",
        visible_turn=_visible(),
    )

    admitted = {sidecar.name for sidecar in selection.admitted}
    blocked = {decision.sidecar.name for decision in selection.blocked}

    assert selection.mode == "status_reference"
    assert "runtime_presence" in admitted
    assert "goldmark_auth" in blocked


def test_three_fix_reference_counts_as_context_reference() -> None:
    selection = select_prompt_sidecars(
        [
            _sidecar("continuity_handoff", "continuity"),
            _sidecar("goldmark_auth", "background"),
        ],
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="这三件事到底是哪三件",
        visible_turn=_visible("ordinary_owner_chat"),
    )

    admitted = {sidecar.name for sidecar in selection.admitted}
    blocked = {entry.sidecar.name for entry in selection.blocked}
    assert selection.mode == "context_reference"
    assert selection.context_reference is True
    assert "continuity_handoff" in admitted
    assert "goldmark_auth" in blocked


def test_context_reference_admits_continuity_and_recent_action() -> None:
    selection = select_prompt_sidecars(
        [
            _sidecar("continuity_handoff", "continuity"),
            _sidecar("recent_action", "episodic"),
            _sidecar("daily_digest", "digest"),
        ],
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="\u521a\u624d\u65ad\u5728\u54ea\u91cc\u4e86",
        visible_turn=_visible(),
    )

    admitted = {sidecar.name for sidecar in selection.admitted}
    blocked = {decision.sidecar.name for decision in selection.blocked}

    assert selection.mode == "context_reference"
    assert {"continuity_handoff", "recent_action"} <= admitted
    assert "daily_digest" in blocked


def test_direct_owner_pressure_admits_repair_bias_without_background() -> None:
    selection = select_prompt_sidecars(
        [
            _sidecar("learning_closed_loop", "repair"),
            _sidecar("goldmark_auth", "background"),
        ],
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="too much template voice",
        visible_turn=_visible("owner_style_pressure", owner_style_pressure=True),
    )

    admitted = {sidecar.name for sidecar in selection.admitted}
    blocked = {decision.sidecar.name for decision in selection.blocked}

    assert selection.mode == "owner_pressure_quiet"
    assert "learning_closed_loop" in admitted
    assert "goldmark_auth" in blocked


def test_conversation_experience_defers_quiet_chat_but_admits_relevant_work() -> None:
    quiet = select_prompt_sidecars(
        [_sidecar("conversation_experience_hint", "conversation_experience")],
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="hello",
        visible_turn=_visible(),
    )
    assert "conversation_experience_hint" in {decision.sidecar.name for decision in quiet.blocked}
    assert quiet.blocked[0].reason == "conversation_experience_deferred_quiet_turn"

    active = select_prompt_sidecars(
        [_sidecar("conversation_experience_hint", "conversation_experience")],
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="continue the implementation progress",
        visible_turn=_visible(technical_work=True),
    )
    assert "conversation_experience_hint" in {sidecar.name for sidecar in active.admitted}
    assert active.admitted[0].admission == "conversation_experience"


def test_non_owner_preserves_existing_sidecars() -> None:
    selection = select_prompt_sidecars(
        [
            _sidecar("goldmark_auth", "background"),
            _sidecar("runtime_presence", "status"),
            _sidecar("continuity_handoff", "continuity"),
        ],
        payload={"message_type": "group_text", "group_id": "100", "metadata": {"is_owner_user": False}},
        user_text="hello",
        visible_turn=_visible("external_chat"),
    )

    assert selection.mode == "preserve_non_owner"
    assert {sidecar.name for sidecar in selection.admitted} == {
        "goldmark_auth",
        "runtime_presence",
        "continuity_handoff",
    }
    assert not selection.blocked


def test_prompt_pressure_report_writes_last_snapshot(tmp_path: Path) -> None:
    selection = select_prompt_sidecars(
        [_sidecar("runtime_presence", "status")],
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="hello",
        visible_turn=_visible(),
    )
    report = selection.to_report(
        live_prompt_chars=1234,
        session_key="qq:private:owner",
        turn_id="turn-1",
        source="QQ private chat",
        speaker_relation="owner",
        user_text_chars=5,
    )

    write_prompt_pressure_report(tmp_path, report)

    saved = json.loads((tmp_path / PROMPT_PRESSURE_REPORT_REL).read_text(encoding="utf-8"))
    assert saved["live_prompt_chars"] == 1234
    assert saved["blocked_sidecars"][0]["name"] == "runtime_presence"
