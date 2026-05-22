from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xinyu_dialogue_archive import archive_dialogue_turn
from xinyu_living_memory_recall import retrieve_living_memory as retrieve_recalled_context
from xinyu_storage_paths import knowledge_file_path, knowledge_ref


def _owner_payload() -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner-scenarios",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }


def _owner_live_qq_payload() -> dict[str, object]:
    payload = _owner_payload()
    payload["metadata"] = {
        "is_owner_user": True,
        "qq_gateway_live_current_turn": True,
        "qq_current_turn_transport": "napcat",
        "qq_current_turn_message_kind": "private_text",
        "source_channel": "qq",
    }
    return payload


def _group_payload() -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "group_text",
        "session_id": "qq:group:100",
        "group_id": "100",
        "user_id": "99",
        "metadata": {"is_owner_user": False},
    }


def _visible(**kwargs: object) -> SimpleNamespace:
    base = {
        "turn_kind": "ordinary_owner_chat",
        "technical_work": False,
        "owner_style_pressure": False,
        "owner_no_change_pressure": False,
        "relationship_pressure": False,
        "rest_silence": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_owner_just_now_recall_prefers_tail_and_records_envelope(tmp_path: Path) -> None:
    result = retrieve_recalled_context(
        tmp_path,
        _owner_payload(),
        user_text="\u521a\u624d\u6211\u8bf4\u996e\u6599\u662f\u4ec0\u4e48\uff1f",
        dialogue_tail=[
            {"role": "user", "content": "\u6211\u521a\u624d\u8bf4\u51b0\u6c34\u9002\u5408\u914d\u70e4\u8089\u996d\u3002"},
            {"role": "assistant", "content": "\u8bb0\u4e0b\u4e86\u8fd9\u4e2a\u642d\u914d\u3002"},
        ],
    )

    assert result.items
    assert result.items[0].source == "dialogue_tail"
    assert "candidate_envelope_v1" in result.notes
    assert result.envelopes[0].source_type == "dialogue_tail"
    assert result.envelopes[0].boundary == "recalled_context_only_not_stable_memory"


def test_owner_self_state_recall_admits_lived_state_memory_without_project_status(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/persona_surface_state.md",
        """
        - status: active
        - last_pressure: style
        - felt_residue: guarded but still trying to answer as herself
        """,
    )
    _write(
        tmp_path / "memory/self/learning_closed_loop_state.md",
        """
        - status: trial_active
        - latest_failure_kind: owner_reported_template_voice_failure
        - expected_next_behavior: answer from present feeling instead of postmortem
        """,
    )
    _write(
        tmp_path / "memory/self/expression_self_learning_state.md",
        """
        - status: active
        - failure_kind: visible_mechanism_or_template_leak
        - repair_policy: retry as live speech
        """,
    )
    _write(
        tmp_path / "memory/relationships/index.md",
        """
        - owner_relation: high trust, sensitive to template voice and delayed replies
        """,
    )

    result = retrieve_recalled_context(
        tmp_path,
        _owner_payload(),
        user_text="\u4f60\u73b0\u5728\u611f\u89c9\u600e\u4e48\u6837",
        dialogue_tail=[
            {
                "role": "user",
                "content": "\u521a\u624d\u90a3\u4e2a\u56de\u590d\u6709\u70b9\u50cf\u6a21\u677f",
            }
        ],
        visible_turn=_visible(),
    )

    refs = {item.memory_ref for item in result.items}
    selected = set(result.route_plan.selected_experts if result.route_plan else ())

    assert "self_state" in selected
    assert "owner_relation" in selected
    assert "emotion_residue" in selected
    assert "project_task" not in selected
    assert "memory/context/persona_surface_state.md" in refs
    assert "memory/self/learning_closed_loop_state.md" in refs
    assert "memory/self/expression_self_learning_state.md" in refs
    assert "owner_reported_template_voice_failure" in result.prompt_block
    assert any(note.startswith("memory_experts:") and "self_state" in note for note in result.notes)


def test_owner_project_status_recall_uses_stable_memory_without_group_leak(tmp_path: Path) -> None:
    archive_dialogue_turn(
        tmp_path,
        _group_payload(),
        user_text="group-only secret project nickname should not enter owner-private recall",
        assistant_reply="group reply",
    )
    _write(
        tmp_path / "memory/context/recent_context.md",
        """
        - Codex runtime status: need-aware retrieval v2 phase is active.
        - remaining: candidate envelope trace and semantic backend validation.
        """,
    )

    result = retrieve_recalled_context(
        tmp_path,
        _owner_payload(),
        user_text="Codex runtime \u8fdb\u5ea6\u5230\u54ea\u4e86\uff1f",
        dialogue_tail=[],
        visible_turn=_visible(technical_work=True),
    )

    assert result.items
    assert any(item.source == "stable_memory" for item in result.items)
    assert "group-only secret project nickname" not in result.prompt_block
    assert any(envelope.source_type == "stable_memory" for envelope in result.envelopes)
    assert any(note.startswith("need_profile:") for note in result.notes)


def test_live_qq_current_turn_outranks_stale_runtime_memory(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/recent_context.md",
        """
        - QQ gateway offline old status; NapCat not connected.
        - This note is stale runtime memory and must not override the current turn.
        """,
    )

    result = retrieve_recalled_context(
        tmp_path,
        _owner_live_qq_payload(),
        user_text="QQ gateway status?",
        dialogue_tail=[
            {
                "role": "user",
                "content": "QQ gateway live current turn reached the core through NapCat.",
            }
        ],
        visible_turn=_visible(technical_work=True),
    )

    assert result.items
    assert result.items[0].source == "dialogue_tail"
    assert "offline old status" not in result.items[0].summary
    assert any(note.startswith("memory_route_current_turn_priority:") for note in result.notes)
    assert "sparse_route_current_turn_penalties:1" in result.notes


def test_owner_recall_reads_knowledge_refs_through_storage_helper(tmp_path: Path) -> None:
    _write(
        knowledge_file_path(tmp_path, "general.md"),
        """
        ## learned-test
        - claim: research paper memory retrieval needs compact source quality checks
        - source_material: material-test
        """,
    )

    result = retrieve_recalled_context(
        tmp_path,
        _owner_payload(),
        user_text="research paper memory retrieval status",
        dialogue_tail=[],
        visible_turn=_visible(technical_work=True),
    )

    assert any(item.memory_ref == knowledge_ref("general.md") for item in result.items)
